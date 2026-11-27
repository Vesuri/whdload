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

## Verification

The title and the demo races (one and two views) render correctly with no WHDLoad dump on
the a500; the a1200, a1200-fast and a1200-040 with `CACHE`; the a1200-040 with `DCACHE`;
the a1200-060 with `CACHE` and with `DCACHE BRANCHCACHE STOREBUFFER SUPERSCALAR`; and the
a1200-040 with `SNOOPAGA CHKBLTWAIT DCACHE` (2 minutes). A player race through the menu
(1 PLAYER, ARCADE), driven with crashes, ran on the a1200-040 with `CACHE`.
