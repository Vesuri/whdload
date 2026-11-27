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
(its flickering objects), is not ported: here the frame's drawing ($DB04) already waits for
the next field after the swap ($EB36 against $98DE), or with two views for the beam to pass
the top view.

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

What an undrawn pass still runs: the players' steps, the landscape of every view (it follows
the track and decides whether the car is off the road, as in Vroom), the player's timers in
$D3A6, and the rest of $DB04 (start lights, crash sequences, pit stop, the panel), which
count passes. The scheduler's variables are at $1C0-$1D5 (`ENH_VARS`, as in Vroom).
`CUSTOM3=n` (for the checks) leaves out the drawing in n of every n+1 passes. The
Multiplayer has no link play.

Checks, from the first demo race's green light (`tools/vmp.py`):
- *The same ticks.* `statelog 300 FILE tick` on the a500 and on the a1200-040 with
  `CUSTOM1=1 CUSTOM3=2`: all 299 compared passes agree (`statecmp --align 3`), leaving out
  the map markers' positions per screen $E51C-$E52B, which follow the screen order.
- *Speed.* `bench 300` (two views): the a1200-030 and the a1200-040 16.70 fps; the a1200
  (68020, chip memory only) 13.45, with 71 of 371 ticks undrawn and none dropped. The second
  demo race (Monaco, one view), `bench 200`: 16.75 on the a1200 and the a1200-030, the same
  distance at the same frame.

## Verification

The title and the demo races (one and two views) render correctly with no WHDLoad dump on
the a500; the a1200, a1200-fast and a1200-040 with `CACHE`; the a1200-040 with `DCACHE`;
the a1200-060 with `CACHE` and with `DCACHE BRANCHCACHE STOREBUFFER SUPERSCALAR`; and the
a1200-040 with `SNOOPAGA CHKBLTWAIT DCACHE` (2 minutes). A player race through the menu
(1 PLAYER, ARCADE), driven with crashes, ran on the a1200-040 with `CACHE`.
