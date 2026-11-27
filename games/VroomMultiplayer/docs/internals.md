# Internals

The program, its display and game time, every slave patch (as offsets into the game's code
hunk or file), current measurements and known limitations.

## Loading and memory

A direct slave in 512 KB of chip memory (`ws_BaseMemSize` $80000). The slave loads the boot
block's loader from disk offset 0 to $40000, patches it and jumps to $4000C; the loader
loads the main program and calls the slave's `_PatchV1` or `_PatchV2`, which patch it and
jump to its entry at $3658. Addresses here are BaseMem addresses of v1 (the Retroplay
disk): the program is loaded at fixed addresses, so they are its file layout too. In v2
the loader and part of the program sit $8C lower.

## The original slave's patches

| Where (v1) | What |
|---|---|
| loader $40030, $4007A, $401EE/$401F8 (v2 $40224) | trap #0 for the loader, `move.l a1,a2` removed, `_PatchV1`/`_PatchV2` called |
| loader at $6EE88 | the track loader replaced by `_LoadTrack0` (`resload_DiskLoad`), MFM decoding skipped |
| $394E, $3BCE | disk protection |
| $1EA84-$1EB1E | drive head moves and delays removed |
| $1EBA0, $1ED06 | highscore save (`resload_SaveFileOffset`) and track loads |
| $ACCC | keyboard: quit key, F9 |
| $1B526, $1B5F0, $1B8A2, $1B568, $1B626, $1B8C8 | the scaler's self-modifying `move.l (a4,d0.w),(a5)`/`(a6)` moved to the slave ($100, $106), after every track load |
| $6F23C/$6F428, $1EF0A/$1F118 (v2 $1EE7E/$1F08C) | the loader's and the program's decrunchers, copies in the slave |
| $89B2 (v2, with $61EE) | a second track protection |

## The program against Vroom's

Vroom's engine rebuilt for split-screen two-player races: the same routines with the data,
the variables and some code moved, and new code around the race loop and the swap.
`tools/addrmap.py` aligns the two programs instruction by instruction (images at $3658 of
both, original slaves) and gives each Vroom address's Multiplayer address, by the aligned
code and by the operands that differ. Every site below was mapped so and then read in both
listings. Some of Vroom's names here: the field counter $98DE (Vroom $A884), the VBL's
jsr vector $B028 ($A56C), the screen the VBL shows next $972E ($A71C), the draw buffer
$8F00 ($86EA), the blitter queue's wait $11FDE ($1123A) and the queue $12032 ($11268).

The game sets `$C8` from its boot block: $64, or $F0 on AGA (its check at $401FC); the
original slave skips that part of the boot block and sets $F0. It counts the keyboard
handshake's delay loop, and the race's frame end waits for the next field unless it is
$50, which no machine gives.

The new slave's patches are for v1 only (`_cont`, `tst.l d0`): v2 runs as the v1.6 slave did.

## Fixes (every CPU)

`src/fixes.i`, from `_cont` before the jump to $3658 and after a decrunch onto the program
(`fix_Decrunch`, the program's decrunch call at $1EA00; `Fix_Decrunched` checks the
destination $1F25A and the length $3623A). Vroom's fixes at their addresses here, and the
original Vroom slave's blitter waits, which the Multiplayer's slave never had.

| Where | What |
|---|---|
| $401EA (boot block) | the AGA check called again (`bsr.w $401FC`, a write to `DENISEID` that SNOOP stops at) is skipped: its d0 is unused |
| $B004 | the VBL routine's drive motor off skipped (Vroom $A514) |
| $AB8C | the blitter-done interrupt acknowledges, then waits for the blitter (Vroom $A094) |
| $11D2A, $13070, $13122, $13206 | the blitter queue: these waited only for the current blit ($11FA6) before writing a new queue or programming the blitter; now the queue's wait $11FDE. $13070 and $13122 are the two tyre routines (Vroom has one, $11BE4) |
| $13076, $13128 | after $11FDE a6 is the queue, not $DFF000: `move.l a4,84(a6)` loads it first (Vroom's `fix_Tyres`) |
| $AD6A | the keyboard handshake: $C8 loops of `nop`/`dbf` (`move.w $C8.l,d0`, 6 bytes here) become a wait for 3 raster lines |
| 138 starts in $1309E-$1B25E, $13344, 5 waits $3C9A-$3D1A | each blitter start in the renderer waits for its blit, as in Vroom's original slave (`src/blitwait.i`, from `tools/blitstarts.py`: Vroom's 134 and the second tyre routine's 4); the init code's `btst #6,2(a6)` waits read `dmaconr` once first. Without them CHKBLTWAIT stopped at $1767E (a blit from $17656) |

On a 68020 or higher (`_fix_pl020`), the CPU-timed delays become beam waits of their 68000
length, as in Vroom: the menu's wipes $46E0 and $5334, after a menu choice $4822, and the
delay routines $8978 and $1682A.

Vroom's other 68020 fix, the wait before the landscape for the VBL to take the last frame
(its flickering objects), is not ported: here each view's drawing ($DB04) already waits for
the next field after the swap ($EB36 against $98DE), or, with two views and in the large
single view, for the beam to pass the view ("Enhanced framerate", "The screen on display").

## Self-modifying code (68020 and higher)

`src/smc.i`: Vroom's, at these addresses (`docs/internals.md` in `games/Vroom` has the
design). The original slave crashes on the a1200-040 and the a1200-060 with `CACHE` in the
first demo race: an access fault at $10614 (the line routine writing past BaseMem), the
renderer's recursion missing the `rts` written at $1056A, as in Vroom.

| Where | What |
|---|---|
| $B026, $B02C; writers $3ABA, $3AC4, $9A92, $9A9E, $ADC2, $AE1E, $AE88 | the VBL's two vectors |
| $10618, $10642; writers $EB72-$F862 (20, Vroom 16) | the line routine's `move.w $10788(pc),(a0)+`/`bsr.w $1078A`, copied from $ED6A-$ED79 |
| $1056A (set $105A8, clear $105B4); $11322 and $1064C (set $10966/$1096E, clear $1098E/$10996) | `rts` written over the first instruction and removed |
| $10112-$110A4 (16) | shift counts and masks copied into $102F8, $1036A, $1044C, $104BC, then a flush |
| $FA12 | `nop`/`asr.w` copied to $FA2E, then a flush |
| $1B526-$1B8C8 (6 stores), slots $1C60C-$1C631 (6); $1B316, $1B6D8, $1B702 | the bitmap scaler. The slots are outside the loop here: called with `bsr.w` ($1C628, $1C62E, $1C61C, $1C622, which return with `rts`) or branched to with `bra.w` ($1C60C, $1C614, which branch back); each slot becomes a `jsr` of its selected pair |

The decrunches from the boot through the title and three demo races all land outside the
patched range ($3ABA-$1C631).

## Frames and game time

- **The race loop** ($B98A-$D394, entered at $B984 `clr.w $E54E`): one step for each player
  ($B992-$BE18, over the list at $E566: a car table offset and a player block at $1254C,
  $106 bytes each), the keys and the pause ($BE1C-$C016: space toggles $E542, and the loop
  at $BE1C waits for a key), the opponents and the race order, the start lights ($D084: 30
  passes a light, then the race clock's gate $EA58 opens at $D0D0), then for each view
  ($D190-$D1FC: one or two, by the layout $11484 and its table at $11480) the landscape and
  the player's timers ($D3A6: `jsr $F1BC`, fuel, tyres, damage, laps) and the view's
  drawing ($DB04), then the frame's end and the swap ($D348-$D386).
- **The frame's end** ($D348) waits until the field counter $98DE passes $EB36 (the last
  swap's field) plus 0, or 2 with one view when Caps Lock has set $B1D2 (the keyboard
  interrupt at $ACDE: the game's own speed limit, 16.7 fps with one view), then hands the
  draw buffer $8F00 to the VBL ($972E), sets $EB36 and toggles the buffers ($145F8). Each
  view's drawing ($DB04) first waits for a new field (one view) or, with two, for the beam
  past the bottom view ($D0 or $AC) when no field has passed since the swap.
- **Game time.** As in Vroom: one simulation step per pass, so the game's speed follows the
  frame rate; the race clock $EA54 (+2 a field while $EA58 is not negative) is real time.
  The first demo race (Adelaide, two views) draws 10.87 fps on the a500 (`bench 100`: 4-5
  fields a frame).

## Enhanced framerate (68020 and higher, `CUSTOM1=1`)

`src/enhanced.i`, applied from `Fix` after the 68020 fixes when `CUSTOM1` is set (`ws_config`
`C1:B:Enhanced framerate`, `ws_Version` 17). A 68000 or 68010, or `CUSTOM1=0`, runs the
original loop. Vroom's design (`games/Vroom`, `docs/internals.md`), on this loop:

**Every race loop pass is a tick**, due every 3 fields (16.7 Hz, Caps Lock's speed with
one view), counted by $98DE. A pass waits while it is early; when the next tick is due
already, it leaves out what only draws (at most 3 passes in a row; behind by more than 50
fields the debt past it is dropped and counted).

| Where | What |
|---|---|
| $B984 (`clr.w $E54E`) | the loop's entry: the tick clock starts now |
| $B98A (`lea $E566(pc),a5`) | a pass starts: it waits while its tick is early; if the next is due already, it does not draw |
| $BE86 (`tst.w $E53E`) | the end of a pause: the tick clock starts again |
| $DB04 (`cmpi.w #1,$11484`) | in a pass that does not draw, each view leaves out the wait, the sky and ground clear, the road spans, the sky objects and the scaler ($DB04-$DBCF), keeping the clear's state: the horizon's scroll (`$14FA4`, per view at $15120) and the clamp of the ground's top line $12136 |
| $D348 (`cmpi.w #$50,$C8`) | a pass that does not draw goes on at $D38C, leaving out the frame end's wait and the swap |
| the screens' references, $ADEC, $AE48, $AEB4, $AF94, $AFAE | on AGA, the screens move 6 bytes up and the lores modes fetch 64 bits wide (below, "64-bit fetch") |
| $DB36, $DB54, $DB5C (`jsr $11D2A`); $11DDA-$11E1B (the queue's ground entries) | the entries are left out: after `$11D2A` the CPU fills the ground's planes 2 and 3 (`enh_Ground`) while the blitter runs the horizon and the sky |
| $D010-$13676, below ("Frames between ticks") | with the ExpMem, the frames between ticks |
| 94 blitter starts in $1309E-$1B25E (`src/blitsites.i`) | `jsr $10C`-`$124.w` (`src/blitwait.i`'s start-and-wait) become `jsr $1E0`-`$1F8.w`: start, one read of dmaconr, return |

What an undrawn pass still runs: the players' steps, the landscape of every view (it follows
the track and decides whether the car is off the road, as in Vroom), the player's timers in
$D3A6, and the rest of $DB04 (start lights, crash sequences, pit stop, the panel), which
count passes. The scheduler's variables are at $1C0-$1D5 (`ENH_VARS`, as in Vroom).
`CUSTOM3=n` (for the checks) leaves out the drawing in n of every n+1 passes. The
Multiplayer has no link play.

**Blitter waits.** As in Vroom: `src/blitwait.i` makes each blitter start in the renderer
wait for its blit, and the game waits itself before it programs the next one.
`tools/blitsites.py` finds the starts followed, in straight-line code, by such a wait (`btst
#6,2(a6)`, or a `jsr` of the queue waits $11FDE, $11FA6, $11FC2) with no memory access in
between but to the custom chips: 94 of the 138. With the option those only start the blit.
`bench 300` on the a1200 (68020, chip memory only): 14.14 fps with 53 of 353 ticks undrawn,
against 13.45 with 71 of 371. `frames 100` on the a1200-040 (`CUSTOM3=2`) with and without
them (`-DENH_NOBLITSITES`): every frame the same but for lines 31-35 in 24 of them, the race
clock (real time).

**64-bit fetch.** As in Vroom: on AGA (Lisa, $F8 in `LISAID`) the lores modes fetch their
planes 64 bits wide (`FMODE` 3), which leaves the blitter three quarters of the display's
chip bus slots. Every plane must be 8-byte aligned, and the screens, $21342 and $29042, are
2 bytes past it. They cannot move down as Vroom's do: a track's data, loaded from $20000, runs
up to $21341 (the Brazilian Grand Prix's). They move up by 6, into the fill above the second
screen ($30D42-$30D47 holds $CC through the title and the races). That fill is the bottom of
the stack ($30F36 down): the lowest stack write seen, through the title and five demo races
on the a1200-040, is $30DA2, 90 bytes above the moved screen's end (96 before). Every
reference to the screens, from memory images at the title and in a race (instruction
operands and longs into $21342-$30D41):

| Where | What |
|---|---|
| $3696-$36CC, $3B10-$3B40 | the startup: the first picture and its plane pointers into the copper list $9732 |
| $8EF8, $8EFC, $8F00, $972E | the screens' pointers, the draw buffer and the screen the VBL shows next |
| $DBEA | the panel's copy between the screens with two views: `cmpa.l #$29042,a5` |
| $13BF4, $13C08, $14114, $14138, $142A0 | the race's map code (Vroom's $1278C, $12A62, $12BC4) |
| $1448A-$144ED | the gauge's 25 line addresses on the right of the panel, read at $143DA (Vroom's $12CC0) |

The copper lists' plane pointers hold 0 until the startup sets them. The fetch follows the
address a lores plane pointer setting writes: the VBL's new screen ($ADEC for the copper list
$9732, $AEB4 for $979E, the race's) and a new mode ($AF94) fetch 64 bits from an aligned
screen with `DDFSTOP` $B0, and 16 bits from any other; the hires mode ($AE48, $AFAE) 16 bits.
`frames 150` on the a1200-040 (`CUSTOM3=2`) against `-DENH_NOFMODE`: the two-view demo race's
frames all the same but for the race clock (lines 31-35), the one-view race's too. A first
build missed the gauge's table, which the operand scan could not see: its piece at lines
30-32 stayed at the old address, 6 bytes left. `bench 300` on the a1200: 15.74 fps with 17 of
317 ticks undrawn (14.14 and 53 of 353 before).

**Frames between ticks** (with the slave's optional 80 KB ExpMem, fast or not: two snapshots
of the race state, after the race block's copy, below). As in Vroom, the ticks draw nothing, and while the next tick is early a
frame shows the race between the last two ticks, mixed by alpha (fields since the last tick
was due over fields a tick): it loads the tick before's snapshot (`_enh_r`: the globals, the
16 cars and the order $E52C-$EA53 and $E504-$E51B, after the clock and the view's buffer to
$EB35, the four player blocks $1254C-$12963, the landscape's variables $11866-$1199F, the
horizon's scroll per view $15120, the ground's top lines $12130, the ARCADE score $8B94,
the sky objects $8A7C, and a few more), moves the 16 cars by alpha of their way (distance +2,
lateral +8) and each player's camera by alpha of the player's step ($4 of the block, the
landscape's step; Vroom's $10C30), mixes the camera's lateral position ($8, kept as each
tick's landscape starts), and runs the race loop's drawing from the map markers to the swap
($D010-$D38B), then loads this tick's snapshot back. In Vroom the landscape's variables are
globals; here most are in the player block, so the frame's pitch, turn and lateral position
are kept per player. Not in the snapshot, as they follow the screens or real time: the map
markers per screen $E51C-$E52B, the race clock and its gate $EA54-$EA59, the view's buffer
$EA5A, the swap's field $EB36.

| Where | What |
|---|---|
| $D010 (`movea.l #$4BD9E,a1`) | the map markers: a tick leaves them out; a frame waits for the VBL to take the last frame first (the CPU draws them) |
| $D084 (`move.w $E53E(pc),d0`) | the start lights' count and the race end's bonus: the ticks' (a frame goes on at $D160, the views); a tick that changes the lights waits for the screen on display to be taken |
| $D38C (`move.b $E557(pc),d0`) | after the swap: a frame returns to the scheduler |
| $D3A6 (`move.l 2(a3),$A(a5)`) | a view's landscape: a tick keeps the camera's lateral position |
| $D3CA, $D3F0 | the horizon's turn ($1199C) and the view's sky objects: a frame takes alpha of this tick's turn and mixes the objects, then leaves out the view's timers ($D43C-$D6EF) |
| $10012 (`move.w $1187C(pc),d1`) | the landscape's pitch and height: a frame mixes the two ticks' values (kept per player) |
| $FC2A (`move.w 8(a5),d0`) | the road's projection: a frame mixes the two ticks' lateral position and heading against the road (`$24`; the simulation part clamps and halves them per pass against the road's limit), then goes on at $FCE6 |
| $F3F2, $F644 | the engine's pitch and the bump's sound per view: the ticks' |
| $FB26 (`sub.l d7,d1`) | the cars ahead, sorted: a frame leaves out a car behind the camera |
| $E10C-$E123 | the crash's flying wheel (`enh_WheelXY`; the step $3E of the player's block indexes the table $EAA6): a frame takes alpha of the way from the step before. Reviewed against the original, not yet seen in a crash: the wheel flies only in a hard one (strength $44 of 40 or more; full throttle from the grid gives 9) |
| $DCAA, $13676, $12CB0, $D258, $D282 | a tick leaves out the cockpit, the tyres' marks, the wheel, the score's and the time's digits; it waits for the screen on display before what it still draws (the lights, the crashes, the pit stop) |

A frame takes a tick's drawing plus a view's landscape, so they pay only where a frame takes
well under a tick. With two views a frame takes about 1.5 fields of work on the a1200-040
and 2 or more on the a1200-030 and a1200: one frame a tick at best, and on the slower two
fewer frames than the ticks' own drawing (a1200 8.80 fps against 15.66, a1200-030 13.81
against 16.70). So the slave switches (`enh_Window`, `enh_Drawn`): every 8 ticks with frames
between them, 8 frames or fewer go back to the ticks' drawing for 64 ticks (doubled at each
such try in a row, up to 1024); then 8 drawn ticks in a row of 2 fields or less try the
frames again.

Checks (`tools/vmp.py`; the tools skip a frame's stops at $D38C):
- `statelog 300 FILE tick`, the a500 against the a1200-040 with `CUSTOM3=2` (two frames before
  each tick): all 299 passes agree (`statecmp --align 3`, leaving out $E51C-$E52B).
- `bench 300`, a player race (one view, `race`, then `bench 300 now` where the lights are out
  before the menu's button is let go): the a1200-040 25.04 fps and the a1200-030 25.00
  (1.51 frames a tick; 16.7 before), the a1200 18.59 (16.75). The two-view demo race: the
  a1200-040 16.61, the a1200-030 16.48, the a1200 15.37 (16.70, 16.70, 15.66 drawing in the
  ticks: the tries cost a little).
- `shown 60`: one view, no frame changed the screen on display; two views, 2 of 60 at lines
  48-59, the original's drawing once the beam has passed line $D0 into the screen the next
  field replaces (below).

**The ground by the CPU.** As in Vroom: the queue's ground entries fill planes 2 (with 0) and
3 (with 1) below the ground's top line $12136, as many lines as the view has left, with the
view's width ($113D6) and modulo ($113D4); the road spans draw the other planes. The CPU fills
them instead while the blitter runs the rest of the queue. `span 100 B992 D348` (a drawn
pass's work, from the end of its wait for the tick to the frame's end) on the a1200-040, the
two-view demo race: 1.534 fields against 1.576 with `-DENH_NOGROUND` (two runs of one build
differed by 0.01). On the a1200 (chip memory only) `bench 300` gives 15.66 fps against 15.74:
no change there. `frames 150` (`CUSTOM3=2`): every frame the same but for the race clock.

**Fast memory.** As in Vroom (its steps 19 and 20): with the ExpMem in fast memory (at
$200000-$BFFFFF or from $E00000), the race block $B254-$1CBAF (the race's setup and loop,
its state, the landscape, the renderer, the objects and the scalers with their variables)
and the scaler's pointer table after it (to $1CD13, 128 entries up to the buffers at $1CD14)
run from a copy there, and the program's stack (set once, at $365A: `movea.l #$30F36,a7`)
moves to $800 bytes below the copy. Chip memory is left to the screens, the blitter's and
the copper's data and the program outside the block. The copy's bottom (`ENH_BOTTOM`, $A940
in the copy's addresses: $100 bytes of trampolines, then the stack) is the ExpMem's start;
the copy's offset is kept at $1D6 (`ENH_BLOCK`, 0 when the block stays). `enh_Move` copies
the block once, in the first `Fix`, after every patch is in and before the program starts:

| What | How |
|---|---|
| 879 long addresses into the block, in it (`RELOC_IN`, `src/reloc.i`) | the offset added in the copy |
| 268 long addresses into the block from outside it (`RELOC_OUT`) | the offset added after each `Fix`, where the site still holds the address (a reload over the program brings back the original code) |
| 29 PC-relative reads out of the block, $B2C0-$DE18 (`_enh_edges`) | in the copy a `bsr.w` to a trampoline below the stack, which reads the absolute address |
| the PC-relative reads into the block at the race's end, $808E, $8444, $845A, $846A, $8538 | `jsr` to the slave, which reads the copy |
| the slave's own references to the block (`src/enhanced.i`, `src/fixes.i`) | `([ENH_BLOCK.w],address)`, and `src/fixes.i`'s pointers moved |

`tools/reloc.py` makes `src/reloc.i` from a memory image at $3658 with every patch (the
a1200-040, `CUSTOM1=1`) and aprof profiles of the demo races and a player race: it
disassembles from the profiled code, the tables of code addresses (the scaler's, the race
setup's dispatch $BB18, the crash sequences' states) and the long immediates after an
address operand's opcode, and lists every long into the block. Seven immediates fall in the
block's range without being addresses (`NOT_ADDRS`): a speed clamp ($1B800 at $F722, $F72A)
and the screen sizes added to or taken from a screen's pointer ($EA60 at $816E, $820C,
$8230, $FA00 at $14350, $143B8). No load writes into $3658-$1CD13 after the program starts:
`loads` through the boot, the title and the demo races (destinations from $1FFB8 up).

Checks, from the demo races' green lights (`tools/vmp.py`, which reads and breaks at block
addresses in the copy):
- `statelog 300 FILE tick`, the a500 against the a1200-040 with `CUSTOM3=2`: all 298 compared
  passes agree (`statecmp --align 3`, leaving out $E51C-$E52B); the log takes the race
  state's pointers into the copy back to the program's addresses.
- `bench 300` (`CACHE`), the first demo race (Adelaide, two views), then the second (San
  Marino, one view): the a1200-040 36.95 and 50.17 fps (16.61 and 16.72 with the block in
  chip memory, the same session), the a1200-030 39.37 and 50.17 (16.48 and 16.72). The a1200
  (chip memory only) keeps the block in place: 15.42 two views.
- `shown 60` (two views, a1200-040): 1 of 60 frames changed the screen on display.
- A player race on the a1200-040 driven to its end (ARCADE, time out), the scores, the menu
  and a second race; no WHDLoad dump. The a500 runs the original loop (10.35 fps, two views).

**The screen on display.** `shown 40` (the screen not handed to the VBL, read at the swap and
when the VBL takes the new one) on the a1200-040 and the a1200-030, two views and one: no
frame changed it. With the option off the a1200-040 changes it in 5-13 of 40 frames, all from
the original loop's design: in one view the map marker ($D010, lines 41-43), which the pass
draws before the view's wait for a new field; with two views and in the large single view
(layout 2) the drawing that starts once the beam has passed line $D0 or $AC ($DB1A), into the
screen the next field replaces.

Checks, from the first demo race's green light (`tools/vmp.py`):
- *The same ticks.* `statelog 300 FILE tick` on the a500 and on the a1200-040 with
  `CUSTOM1=1 CUSTOM3=2`: all 299 compared passes agree (`statecmp --align 3`), leaving out
  the map markers' positions per screen $E51C-$E52B, which follow the screen order.
- *Speed.* `bench 300` (two views): the a1200-030 and the a1200-040 16.70 fps; the a1200
  (68020, chip memory only) 13.45, with 71 of 371 ticks undrawn and none dropped. The second
  demo race (San Marino, one view), `bench 200`: 16.75 on the a1200 and the a1200-030, the same
  distance at the same frame.

## Verification

The title and the demo races (one and two views) render correctly with no WHDLoad dump on
the a500; the a1200, a1200-fast and a1200-040 with `CACHE`; the a1200-040 with `DCACHE`;
the a1200-060 with `CACHE` and with `DCACHE BRANCHCACHE STOREBUFFER SUPERSCALAR`; and the
a1200-040 with `SNOOPAGA CHKBLTWAIT DCACHE` (2 minutes). A player race through the menu
(1 PLAYER, ARCADE), driven with crashes, ran on the a1200-040 with `CACHE`.
