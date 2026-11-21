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
`_fastpatches`).
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

The QUICKSTART build (`_quickstart`) skips the name entry (`$136bc`), starts a random land
(`$13712`) and sets the random seed `$137f0` to a constant.

## Limitations

- The world advances once per drawn frame, so on fast Amigas, and with fast memory on a
  68030 or better, the game runs too fast. CUSTOM2 limits the frame rate.
