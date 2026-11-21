# Internals

Addresses are absolute: the slave decrunches `RUN_PROG` to `$1400`, so a code address
minus `$1400` is the offset in the decrunched program. Wepl's patches name the same
addresses.

## How it loads

The slave is a direct slave for a DIC disk image (`ws_Flags` Disk, NoError, NoDivZero, no
Kickstart), with a v18 header for `ws_config`. `ws_BaseMemSize` is `$80000` and `ws_ExpMem`
asks for an optional `$80000`.

1. The slave loads the disk directory (512 bytes at disk offset `$1600`) to `$400`. The
   directory lists the files by name, start track, end track and length: `START_UP`,
   `INTRODAT`, `RUN_PROG`, `TEXTURES`, `QAZ.PAK`, the sprites, `MAP.PAK` and others.
2. It loads and runs the intro (`INTRODAT` to `$22674`, `START_UP` to `$1000`).
3. It loads `RUN_PROG` to `$1000` and decrunches it to `$1400`. The decruncher signature at
   `RUN_PROG+4` is `$227c0000` in the original disk and `$61064cdf` in some cracks. The
   slave accepts both.
4. It applies its patches (the list in `_Start`, see [Slave patches](#slave-patches)) and
   jumps to `$1400`.

## Memory

The game uses fixed chip addresses up to the top of the 512 KB base memory. Important
addresses:

| Address | What |
|---|---|
| `$535c2`, `$535c6`, `$df16` | `BitplanePtr1`-`3`: the front, back and third display buffers (32000 bytes each, 4 planes of 8000 bytes) |
| `$535d6` | `BufferSwapped`: the level 3 handler sets it at the vertical blank after a swap |
| `$3b796` | `FrameCounter`: one count per field (level 3 handler, `$1702`) |
| `$535ba`, `$71b52` | the world tick counters (once per world step) |
| `$7e000` | a phase counter that world code reads (`$5cf4`, `$63c0`, `$6eb4`, `$152c4`) |
| `$7e002`, `$7e004` | the frame skip: draw every `$7e002`th pass, `$7e004` counts down |
| `$7e006` | paused when not zero |
| `$7e00a` | the seed of an effect generator in `$1b3c0` (only `$1b3c0` reads it) |
| `$7e0b4` | the random seed. The game sets it from the beam position (`$137ce`, `$bb5a`) |
| `$7e030` | the captains' command queue, 6 bytes per captain |
| `$6577c` | the world state that a save game holds (`$18be1` bytes) |
| `$6d984` | 128-byte records that `$14450` updates, probably a draw list |
| `$77b7a` | the person records, 50 bytes each (position at offset 8, step at 12 and 13, state at 31) |

With ExpMem in fast memory, v1.4 puts the stack, the three display buffers, the textures,
the masking tables (`$e51c`-`$e81c`) and the dialog data there (`_initbuffers`,
`_fastpatches`). Enhanced framerate adds the terrain renderer
([The terrain renderer in fast memory](#the-terrain-renderer-in-fast-memory)) and two
32000-byte shadows ([Copy only changed screen parts](#copy-only-changed-screen-parts)).
`_initbuffers` runs once: the game program calls its start routine `$1286c` once (`$1480`),
and new games and the menus run inside that routine's loop.

## The main loop

The in-game main loop runs from `$128ea` to the `bra` at `$13194`. One pass does this:

1. Clamps the camera (`$128ea`-`$12932`).
2. If the game is not paused (`$12938`: `tst.w $7e006`), increments the tick counters and,
   if `46(a2)` is not zero, runs the world step: `$12114`, `$6c34`, `$db64`, `$44f6`.
3. Counts down the frame skip (`$12986`). On a drawing pass it waits for the previous swap
   (`$129a2`: `jsr $1ac4`), draws (`$12636`) and, if not paused, draws more (`$171d0`,
   `$f152`, the terrain).
4. If not paused, runs `$1b3c0` (effects, the phase counter `$7e000`), `$1719a`, `$15e98`
   and `$14450` (the people: state machine and movement).
5. Runs `$7274` (the command queue), `$8298`, the camera turn (`$f854`), `$da7c`, `$7a38`
   and the input handling (`$12a14`-`$13170`, keys and mouse).
6. On a drawing pass, swaps the buffers (`$13178`: `jsr $1a6c`).

The swap routine (`$1a6c`) exchanges `BitplanePtr1` and `BitplanePtr2`, toggles
`$1ab8`, writes the copper list for the other buffer to `cop1lc` and clears
`BufferSwapped`. The level 3 handler (`$16d6`) reads the mouse (`$1ade`), sets
`BufferSwapped` and increments the field counters.

## Game time

The original game advances the world once per pass, and a pass lasts as long as the
drawing. The game speed is therefore the machine's drawing speed:

| Machine, opening view of the QUICKSTART land | Fields per pass | World ticks per second |
|---|---|---|
| A500 | 12-13 | about 4 |
| 50 MHz 68030 with fast memory (v1.4) | about 4 | about 12.5 |

v1.4's CUSTOM2 caps the rate of drawing passes (`_ingamewaitswap` waits on `FrameCounter`).
The world still advances once per pass.

Some game logic uses real time already: the world step sets timers as `FrameCounter` plus a
duration (`$12182`-`$121b8`), and `$bc76` and `$136da` add the low word of `FrameCounter`
to random values.

### Enhanced framerate (CUSTOM4)

With `CUSTOM4=1` the world advances by the field clock:

- `_tickgate` replaces `tst.w $7e006` at `$12938`. It runs the world step when
  `FrameCounter` reaches `_nexttick` and then adds `TICKFIELDS` (13, the A500's average,
  see [Measurements](#measurements)). When paused, or more than `MAXBEHIND` (52, four
  ticks) fields behind, the clock restarts. It sets `_ticked` for the rest of the pass.
- `_ticklogic` replaces `jsr $1b3c0` at `$129c2`. It calls `$1b3c0`, `$1719a`, `$15e98` and
  `$14450` when `_ticked` is set. A `bra.s` at `$129c8` jumps over the other three
  calls. In a pass without a world step it calls only the drawing that these routines do
  (see [Drawing inside logic routines](#drawing-inside-logic-routines)).
- `_tickcommands` replaces `jsr $7274` at `$129da`. It processes the captains' command
  queue only when `_ticked` is set. On an A500 a pass and a tick took about the same time,
  so the queue ran about once per tick there too. An order takes effect at the next tick, at
  most 13 fields later.
- `_drawgate` replaces `subi.w #1,$7e004` at `$12986` (with a `nop` at `$1298c`). It draws
  on every pass, except while the clock is still due after the world step: then it leaves
  out the drawing, at most `MAXSKIP` (8) passes in a row, so the world catches up.
- With fast memory, `_doswap` waits for `BufferSwapped` before it copies a frame to chip
  memory, and `_ingamewaitswap` no longer waits before drawing. The drawing goes to a buffer in fast
  memory that is not shown, so only the copy has to wait for the previous swap.

Still once per pass: `$8298`, `$da7c`, `$7a38`, the input handling and the camera. The
camera is not game logic, so it stays per pass on purpose: the keyboard steps
(`$130a8`-`$130fa`: 10 units, `$f854`: 16 units) and the quarter-turn animation (`$12868`
added to `$f854` until a multiple of 64) finish sooner at higher frame rates. That is the
faster response that the higher frame rate is for. Smaller steps per pass would make the
camera slower on slow machines, and steps per tick would leave the extra frames unchanged.

With CUSTOM4, `CUSTOM1` Auto turns on fast-memory drawing for a 68020 or better
(`AFF_68020`), not only for a 68030 or better as in v1.4.

#### Drawing inside logic routines

Some routines that the main loop calls after the drawing (`$129c2`-`$129d9`) also draw into
the frame that is being built (`BitplanePtr2`). If such a routine runs only in passes with a
world step, its graphics are only in those frames. The frames between them do not have the
graphics, so they blink at the tick rate. The players reported blinking map markers, a
blinking compass needle and blinking rain. In a pass without a world step, `_ticklogic`
does this drawing without the logic:

| Routine | Draws | Logic in it | What `_ticklogic` calls without a world step |
|---|---|---|---|
| `$1b3c0` | rain or snow (`$1b060`, while `$71b56` is not 0) | effects, the season's weather countdown `$71b58`, the phase counter `$7e000` | `$1b060` with the arguments of the call at `$1b550`: `d0`=16, `d1`=194, `d2`=4, `d7`=`$71b56` |
| `$1719a` | the compass needle, from the camera angle `$f854` | none | `$1719a` |
| `$15e98` | the captains' markers on the map (through `$e4b6`) | none | `$15e98` |
| `$14450` | nothing found | the people | nothing |

`$71b56` selects the effect: 1 is rain and 2 is snow (snow takes the path at `$1b1b4`).
The season (`$7dfe4`) sets it from the table at `$1b5b2`. `$1b060` advances the animation
phase at `$1b2de` on each call, so the rain moves faster at higher frame rates. The marker
of the selected captain still flashes once per tick, from the bit `$71b55`, as in the
original.

`_tickcommands` (`$7274`) and the world step can reach drawing code too. The frame test
below found no other difference, but it covers a quiet scene only.

To find such drawing, capture consecutive drawn frames and compare each frame with the
previous one. In a still view, a frame without a world step must equal the frame before
it. A difference right after a tick frame shows graphics that only the tick frame has.
Then set a gdb watchpoint on a byte of that area in `BitplanePtr2` from `$129b6` (after the
main drawing) and read the return address on the stack when it triggers. A static search
for code that reads `BitplanePtr2` is not enough: it missed `$1719a`.

Two runs of the same build on the same machine give the same world state at the same tick.
Runs on different machines or builds do not, for two reasons: the random seed comes from
the beam position, and the field timers fall on different ticks. The QUICKSTART build
(`BUILD=quick`) sets the seed to a constant for tests.

## The terrain renderer in fast memory

The terrain renderer is `$e1d4`-`$f14a`:

- `$e81c` is a triangle rasteriser. It takes the corners in `d0`-`d2` and the colour in
  `d3`, clips (`$eabc`, tables at `$efba` and `$f082`), builds a span table at `$ea9c` and
  jumps to the span filler.
- `$e1d8` is the span filler. It writes textured spans to the four planes of the back
  buffer, with the masking table (`a6`) and the texture (`a5`). `$e1d4` holds the buffer
  address, which the main loop writes (`$1297a`).

The tile renderer `$f152` calls `$e81c` 24 times per tile. In the a500-020 profile (100
fields, fast memory on) the span filler took 44% of all cycles and the rasteriser 11%. The
loop is longer than the 68020's 256-byte instruction cache, so every instruction fetch went
to chip memory.

With fast memory and CUSTOM4, `_fastrender` (called from the end of `_fastpatches`)
copies `$e1d4`-`$f14a` to fast memory and fixes these references:

| Where | What | Fix |
|---|---|---|
| `$e3b4`, `$e3fc`, `$e4b6`, `$e81c` | entries from outside | `jmp` to the copy |
| `$1297a` | `move.l a0,$e1d4` | writes the copy's `$e1d4` |
| `$e1e4` | `add.l $f85c(pc),d6`, out of range from fast memory | `bsr.w` to a stub with `add.l $f85c.l,d6` |
| `$ead2` | `move.b d1,$efb8.l`, an absolute write to the block's own data | writes the copy |
| `$e4c4` | the masking table address that `_fastpatches` sets | copied after `_fastpatches` |

The block does not touch the custom chips or the CIAs, and it does not call code outside
the block. A scan with capstone found no other code that refers to it, and each piece of
data that only looked like a reference was checked by hand.

## Copy only changed screen parts

With fast memory the game draws into a buffer there, and `_doswap` copies each finished frame
(32000 bytes) to the chip buffer that the next swap shows. Chip writes are slow: in the
a500-020 profile at 37.5 MHz the copy took 24% of all cycles, about 42 cycles per `move.l`.

With `CUSTOM4=1` (until 2.0b it was a separate option, CUSTOM5), `_initshadows` (called once by `_initbuffers`) allocates a 32000-byte
shadow in fast memory for each of the two chip buffers (`$434a6` for `CurBufferOffset` 0,
`$3b7a6` for 4). `_shadowcopy` replaces the copy:

- On the in-game swap (`_ingameswap` sets `_ingame`) with a valid shadow, it compares the new
  frame with the shadow in 16-byte blocks and writes a block to the chip buffer and the
  shadow only when it differs.
- On every other swap (menus, sequences: `_swapbuffers`), with a stale shadow, and on every
  64th in-game swap (`SHADOWREFRESH`), it copies everything and writes the shadow too. The
  shadow is valid after that.

In fast-memory mode only these places draw straight into a chip buffer, through
`_currentfb` (v1.4's comment in `_initbuffers`: "Other references ruled out"): `$4626`
(a sprite in the world step), `$1aa7e` (text), `$1add0` and `$1ad26` (after a file load),
and `_endseq` (the end picture). `_initshadows` replaces the first four with `jsr` to
`_fbdraw1`-`_fbdraw3`, which do the original load and mark both shadows stale. `_endseq`
marks them stale too. The marks use `movem`, `lea` and `Scc`, which keep the condition codes.
In 100 fields of play none of the four ran.

The checks used `tools/shadowcheck.sh` while the partial copy was CUSTOM5. It stops at the main loop and compares both chip
buffers with their shadows. The quick build stores the shadows' address at `$f4`.

| Setup and build | Samples | Mismatches where the shadow is valid |
|---|---|---|
| a500-020 at 37.5 MHz, quick, CUSTOM4=1 CUSTOM5=1 | 15 | 0 |
| a500-020 at 37.5 MHz, quick, CUSTOM5=1 CUSTOM1=2 (original speed) | 8 | 0 |
| a3000-50, quick, CUSTOM4=1 CUSTOM5=1 | 10 | 0 |
| a500-020 at 37.5 MHz, spin, CUSTOM4=1 CUSTOM5=1 | 10 | 0 |

Also at 5 stops in the quick build and 8 in the spin build, the chip buffer that is shown
equals the finished frame in fast memory (`BitplanePtr1`) byte for byte.

Without fast memory the partial copy does nothing: on the a500 with `CUSTOM4=1 CUSTOM5=1`, also with
`CUSTOM1=2`, WHDLoad gives no ExpMem, the display stays in chip memory (`BitplanePtr1`
`$3b7a6`), and the game runs as without the partial copy (3.6-3.9 frames per second, 13.0-13.3
fields per tick).

The `spin` build (`SPIN=1`) turns the camera by 4 units on every frame drawn, so every
frame differs: the worst case for the comparison.

## Slave patches

Wepl's and Paraj's patches (v1.4.1), as published:

| Address | Patch |
|---|---|
| `$1400+$aca0` | the copylock: `moveq` with the expected value |
| `$1474` | `nop`s: the check for expansion memory |
| `$dd94` | `_load_dd94`: the file loader, from the disk image |
| `$1a2d0+$1400` | "insert Powermonger disk": jumps over the request |
| `$1bdfa`, `$1ac02+$1400` | the save disk format: `rts` and `illegal` |
| `$1bf2e`, `$1ac54+$1400` | load and save games as files in `save/` |
| `$1a510+$1400` | `rts` |
| `$12870` | `_initbuffers`: the fast-memory display buffers and the swap patches |
| `$c73a`, `$bcc4` | the manual protection: no wait, dismissed at once |
| `$1aca0` | `_palfadedelay`: the palette fade delay |
| `$2462+$1400` | `_bug1`: an access fault (word read from `$82120`) |
| `$142a`, `$68` | the keyboard interrupt (`_keyb`), with the quit key |
| `$13762`, `$1ad04` | CUSTOM3 bit 0, "All maps conquered": `_alllevels` marks every map as conquered in a new game, and the first game can be won (`PL_IFC3X 0`) |
| `$db22` | CUSTOM3 bit 1, "Win on retire": `bra` (`PL_IFC3X 1`) |
| `$1a70`, `$1ad4`, `$129a2`, `$13178`, `$1ae4e` | fast-memory drawing: swap, wait and end sequence (`_initbuffers`) |
| `$e4c4`, `$f154`, `$82ac`, `$df22`... | the textures, masking tables and dialog data in fast memory (`_fastpatches`) |

Added for Enhanced framerate (CUSTOM4): `$12938`, `$12986`, `$1298c`, `$129c2`, `$129c8`
and `$129da` (see [Enhanced framerate](#enhanced-framerate-custom4)), and with fast memory
the renderer relocation (see
[The terrain renderer in fast memory](#the-terrain-renderer-in-fast-memory)) and for the
partial copy `$4626`, `$1aa7e`, `$1add0`-`$1add9` and `$1ad26`-`$1ad2f` (see
[Copy only changed screen parts](#copy-only-changed-screen-parts)).

The QUICKSTART build also skips the name entry (`$136bc`), starts a random land
(`$13712`) and sets the random seed to constants (`$137ce`, `$bb5a`, `$bc62`).

## Measurements

### Version 2.0b

The opening view of the QUICKSTART land with the constant seed, `tools/ticks.sh 10 3`, PAL,
CUSTOM4=1 and `CUSTOM1` Auto, `TICKFIELDS` 13:

| Setup | Frames per second | Fields per tick |
|---|---|---|
| a500 (7 MHz 68000, no fast memory) | 3.7-3.9 | 12.8-13.2 |
| a500-020 (14 MHz 68020, fast memory) | 13.3-13.4 | 13.0 |
| a500-020 with `EXTRA_ARGS=--uae_cpu_frequency=37500000` (a Furia-like 68020) | 25.7-27.0 | 12.9-13.2 |
| a3000-50 (50 MHz 68030, fast memory) | 42.3-43.1 | 12.9-13.1 |

v1.4 on the same view (original speed, fast memory on): about 12.5 frames per second at about
4 fields per tick on the a3000-50, about 7 at 7 fields per tick on the 37.5 MHz 68020, and
about 6.4 at 7.8 fields per tick on the 14 MHz 68020. Without CUSTOM4 a frame and a tick
are the same, so the game ran 1.6 to 3 times too fast there.

### Copy only changed screen parts

`tools/ticks.sh 10 3` (10 2 on the a500-020 and the a3000-50), CUSTOM4=1. "Still" is the
quick build's hands-off view, and "turning" is the spin build.

| Setup | View | Full copy | Partial copy (then CUSTOM5=1) |
|---|---|---|---|
| a500-020 (14 MHz) | still | 13.1-13.4 | 13.2-13.7 |
| a500-020 at 37.5 MHz (Furia-like) | still | 25.7-27.4 | 31.6-32.6 |
| a500-020 at 37.5 MHz (Furia-like) | turning | 25.4-27.2 | 27.6-28.8 |
| a3000-50 (50 MHz 68030) | still | 42.3-42.4 | 49.3-49.9 |

A second check on the Furia-like setup ran each case twice, the second time in the reverse
order, with four intervals of 15 seconds (`tools/ticks.sh 15 4`). The frames drawn per
emulated second over all four intervals:

| View | Full copy, run 1 / run 2 | Partial copy, run 1 / run 2 | Gain |
|---|---|---|---|
| still | 26.1 / 26.2 | 31.4 / 31.1 | 20% |
| turning | 25.7 / 25.6 | 27.4 / 27.4 | 7% |

The fields per tick stayed at 12.8-13.2 in all of them. Even when the view turns, the
panel, the icons and the frame around the 3D view do not change, so fewer blocks go to chip
memory. On the 14 MHz 68020 the comparison costs about as much as it saves.

These runs were made before `_ticklogic` drew the compass needle, the map markers and the
rain in passes without a world step ([Drawing inside logic
routines](#drawing-inside-logic-routines)). After that change, with the partial copy in
CUSTOM4, `tools/ticks.sh 15 3` on the Furia-like setup gave 30.6, 29.6 and 27.4 frames per
second in the still view at 12.95-13.06 fields per tick. A full-copy run with that change
was not made, so the cost of the extra drawing is not measured separately.

### On the way

The same view, `tools/ticks.sh`, PAL, `TICKFIELDS` 12, in the order the changes were made:

| Setup | Build and options | Frames per second | Fields per tick |
|---|---|---|---|
| a3000-50 (50 MHz 68030) | v1.4, original speed | about 12.5 | about 4 |
| a3000-50 | CUSTOM4=1, the world step only | 12-13 | 11.5-12.4 |
| a500-020 (14 MHz 68020) | CUSTOM4=1, CUSTOM1=1 (no fast memory) | 5.4-5.5 | 11.7-12.0 |
| a500-020 | CUSTOM4=1, CUSTOM1=2, without the renderer relocation | 6.5-7.1 | 11.5-12.6 |
| a500-020 | CUSTOM4=1, CUSTOM1=2, with the relocation | 8.1 | 12.1 |
| a500-020 | CUSTOM4=1, CUSTOM1=2, relocation and no wait before drawing | 8.9 | 11.9 |
| a500-020 | CUSTOM1=2 (v1.4, original speed), constant seed | about 6.4 | 7.8 |
| a500-020 | CUSTOM4=1, CUSTOM1=1, constant seed | 5.5-5.7 | 12.0 |
| a500-020 | CUSTOM4=1, CUSTOM1=2 or Auto, all the changes above, constant seed | 13.0-13.2 | 12.0 |

The last rows also run `$1b3c0`, `$1719a`, `$15e98`, `$14450` and `$7274` once per tick, not
once per pass, which leaves more time for drawing.

The original game on the a500 setup (QUICKSTART, constant seed, no CUSTOM4), 20 intervals
of about 4100 fields each (`tools/ticks.sh 15 20`): 12.52 to 13.35 fields per tick, 12.95
on average. The tick rate measurements above used `TICKFIELDS` 12.

The game pace over a long hands-off game (`tools/defeat.sh`, QUICKSTART with the constant
seed, CUSTOM4=1, `TICKFIELDS` 12): none of the three lost the game within the run.

| Setup | Ticks | Fields | Fields per tick |
|---|---|---|---|
| a500-020, CUSTOM1=1 | 5198 | 63400 | 12.2 |
| a3000-50, CUSTOM1=2, no relocation | 3675 | 44464 | 12.1 |
| a500-020, CUSTOM1=2, relocation | 4308 | 52576 | 12.2 |

Profile on a500-020 with the relocation and before the wait change: the renderer copy
about 31%, the frame copy to chip memory (`_doswap`) about 12%, the wait for the swap about
12%. The 68030 MMU core of FS-UAE records no instructions, so 68030 profiles need
`--uae_mmu_model=0`.

## Limitations

- Without CUSTOM4, `CUSTOM1` Auto turns fast-memory drawing on only for a 68030 or better,
  as in v1.4.
- Between two world ticks the extra frames show the same world: only the camera and the
  interface change. Nothing is interpolated.
- The camera moves and turns faster at higher frame rates (see
  [Enhanced framerate](#enhanced-framerate-custom4)).
- `TICKFIELDS` (13) is the A500's average in a hands-off game, which keeps one view. Views
  that the player turns or zooms, and large battles, are not measured.
- The renderer relocation needs fast memory. Without it the renderer stays in chip memory.
- The partial copy needs fast memory. Not tested yet: the end sequence and
  the other places that draw straight into a chip buffer (they mark the shadows stale, and none
  ran in the tests).
- The release sets `CUSTOM4=1` in three of the install's four icon variants. The
  `Powermonger.colexot` icon has no tooltypes, so an install with it starts without
  Enhanced framerate.
