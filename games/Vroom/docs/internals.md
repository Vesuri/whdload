# Internals

The program, its display and game time, every slave patch (as offsets into the game's code
hunk or file), current measurements and known limitations.

## Loading and memory

A direct slave in 512 KB of chip memory (`ws_BaseMemSize` $80000, no ExpMem). The slave
loads the boot block's loader from disk offset 0 to $60000, patches it and jumps to $6000C;
the loader loads the main program (about $3658-$1E000) and calls the slave's `Patch`, which
patches the program and jumps to its entry at $3658. Files are decrunched by the program's
streaming loader at $1D798; `Decrunch` wraps it. Addresses here are BaseMem addresses: the
program is loaded at fixed addresses, so they are its file layout too. The data disk's
program differs from Vroom's only in its init code ($3600-$4400) and a few data words.

## The original slave's patches

| Where | What |
|---|---|
| loader $60030, $6007A, $6020E | trap #0 for the loader, `move.l a1,a2` removed, `Patch` called |
| loader at $6EE88 | the track loader replaced by `Load` (`resload_DiskLoad`), MFM decoding skipped |
| $39C2 (data disk $395E), $81A8, $81BE, $6534, $13126, $1D9F6 (data disk) | disk protection |
| $3E00-$3F00, $11000-$19C00, $11DD6 | blitter waits after `move.w Dn,$58(a6)` (`WaitBlit0`-`6`, `WaitBlit7`) |
| $19EBE, $19F8C, $1A23E, $19F02, $19FC2, $1A264 | the scaler's self-modifying `move.l (a4,d0.w),(a5)`/`(a6)` moved to the slave (not a cache fix: the stored instructions still run from the game's code) |
| $1D0F8 | `Decrunch`: re-removes the protection after a reload to $439C |
| $1D16C-$1D24A | drive head moves and delays removed |
| $1D280, $1D3D8 | highscore save (`resload_SaveFileOffset`) and track loads |
| $A1D4 | keyboard: quit key, F9 |

The new slaves keep all of these and add the fixes below (`src/fixes.i`, `src/smc.i`, called
from `Patch` before the jump to $3658 and from `Decrunch`). Both programs have the same code
at every address the fixes touch: a memory comparison of both variants at $3658 shows only
data addresses (the data disk's data sits $C8 higher), the slaves' own `jsr` targets and the
data disk's extra patch at $AA14. The one exception is the init code's two VBL vector writers,
at $3B54/$3B5E in Vroom and $3B44/$3B4E on the data disk (`SMC_VBLW1`/`SMC_VBLW2` in each
source).

Low memory holds `jmp` trampolines, so a 4-byte site can become `jsr $1xx.w`: the original
slave's at $100-$129, `smc.i`'s at $130-$1A7 and `fixes.i`'s at $1B0.

## Fixes (every CPU)

| Where | What |
|---|---|
| $A514 | the VBL routine's drive motor off (`or`/`and`/`or` on ciab.prb at $A50E) skipped: WHDLoad owns the drives, and SNOOP reports it |
| $A094 | the blitter-done interrupt's dispatcher acknowledges, then waits for the blitter before it starts the next queued blit |
| $10F90, $11BE6, $11CA8 | the blitter queue: before writing a new queue ($10F90) or programming the blitter ($11BE4, $11CA6), the CPU waited only for the current blit ($11202). A fast CPU then overwrote a queue the interrupt was still working through, and the interrupt jumped to a field as its next handler (a 68060 crash at PC $4 with a6 = 0, with the original slave too, caches off). These now wait in $1123A for the queue to drain, as the game's other blitter users do |

The blitter queue: the dispatcher is at $A092, the queue pointer at $11264 (idle = $11260),
the queue at $11268, and the handlers at $110A8-$111E8.

## Self-modifying code (68020 and higher)

The 3D renderer, the bitmap scaler and the VBL routine rewrite instructions while the game
runs. With the instruction cache on, stale code runs. The renderer then recurses until its
buffer runs past BaseMem (WHDLoad's access fault at $F984 with `DCACHE` on the a1200-040),
and the scaler draws garbage cars, cockpit, panel and objects. `smc.i` reads the CPU from
`WHDLTAG_ATTNFLAGS_GET`. It patches only on a 68020 or higher, so a 68000 runs the game's
own code. Its stubs use 68020 memory-indirect `jmp ([var,pc])` and leave the stack and
condition codes as the replaced instructions did.

| Where | Was | Now |
|---|---|---|
| $A56A, $A570; writers `SMC_VBLW1/2`, $9408, $9414, $A302, $A35E, $A3C8 | the VBL routine's two `jsr <vector>`, the vectors rewritten in place | `jmp` through `_smc_vecA/B`; the writers write the variables |
| $F98C, $F9B6; writers at $E292-$EAA4 (16) | `move.w $FAD4(pc),(a0)+` or `bsr.w $FAD6`, copied from $E48A-$E499 | the writers store into `_smc_insA/B`; the sites dispatch on them |
| $F8DE (set $F91C, clear $F928); $10654 and $F9C0 (set $FCB2/$FCBA, clear $FCDA/$FCE2) | an `rts` written over the first instruction and removed again | `jmp` through a pointer to `rts` or to the original instructions |
| $F4FE, $FBA8, $FDBA, $10076, $F49C, $FC5C, $FF4C, $10004, $F5A2, $101C6, $102BA, $103EE, $F61C, $1025A, $1031A, $10380 | a mask and shift counts copied into the routines at $F66C, $F6DE, $F7C0, $F830 | the same writes, then `resload_FlushCache` |
| $EC84 | `nop` or `asr.w #n,d4` copied to $ECA0 | the same write, then a flush |
| $19EBE-$1A26A (12 sites); $19CAE, $1A074, $1A09E | the scaler stores one of 16 instruction pairs from the table at $1A340 into six 4-byte slots in its loop, every 4 pixels; the table is rebuilt by two copies and a single-entry write | the stores select one of 20 precompiled pairs per slot (decoded from the table each time it is written) and each slot calls its selection |

A decrunch that lands on patched code (the program reloads part of itself to $439C) gets the
patches again (`SMC_Decrunched`). The variables keep their state across a reload.

## Frames and game time

- **The race loop** ($BC08-$CD40): the opponents' updates (from $BDE2, over the car table at
  $DC4E, 64 bytes per car: distance at +2, step at +16), the player ($C55A-$C7E4: the
  distance $DC50 grows by the step), the landscape (`jsr $E4F8` at $C968), more game logic
  ($C96E-$CCF2: frame countdowns such as $DC32, laps, sounds), then `$D13C` (`bsr` at
  $CD0A/$CD2E), which draws the objects and swaps.
- **The swap.** `$D13C` first waits ($D142) until the field counter $A884 differs from $E258,
  the field of the previous swap, so a frame takes at least one field. At its end ($D50A-$D524)
  it hands the draw buffer to the VBL through $A71C, sets $E258 and calls $12FA6, which
  toggles $86DE (0/4) and sets the draw buffer $86EA from $86E2/$86E6 ($1FAC6 and $277C6,
  4 planes of 8000 bytes each).
- **The VBL** (level 3 $A076, then $A4F4): $A884 += 1; `jsr` through $A56C (in a race $A3A4:
  the race clock $8500 += 2 while $8504 >= 0, a palette from $A844, the copper list's
  bitplane pointers from $A71C) and through $A572 ($9432, the sound); then the mouse counters
  and buttons into the block at ($A2CC).
- **Game time.** The race clock is real time (2 hundredths of a second per field). The
  simulation takes one fixed step per frame, with no elapsed-time factor. `tools/vroom.py racelog`
  logs the player's distance each field from the green light of the first demo race. It passes
  the same values in the same order on the a500, a1200, a1200-040 and a1200-060 (the 060 sometimes
  skips a value between two field samples). So game speed follows the frame rate, while the
  clock and the sound timers (the field counter, $8E7E-$905C) run in real time. A lap's clock
  time therefore depends on the machine.

From the green light of the first demo race, 1000 fields (`racelog`; `DETERMINISTIC=1`):

| Setup | WHDLoad options | Frames | fps | Fields per frame | Distance after 1000 fields |
|---|---|---|---|---|---|
| a500 | - | 263 | 13.2 | 3-6, mostly 4 | 79935 (1.0x) |
| a1200 (68020, no fast memory) | - | 350 | 17.5 | 2-5, mostly 3 | 106183 (1.3x) |
| a1200-040 | - (BaseMem uncached) | 375 | 18.8 | 2-4 | 114203 (1.4x) |
| a1200-040 | `CACHE` | 635 | 31.8 | 1-3, mostly 2 | 218755 (2.7x) |
| a1200-040 | `DCACHE` | 785 | 39.3 | 1-2 | 279572 (3.5x) |
| a1200-060 | `CACHE BRANCHCACHE` | 889 | 44.5 | 1 (807 of 889) | 333548 (4.2x) |

With an MMU model, FS-UAE's `DCACHE` caches chip memory data, which no real board does
(AmigaXDev `reference/headless-fsuae.md`, "Chip RAM and the data cache"). The `CACHE` row
(instruction cache only) is the closer model of a real 68040 running this game. FS-UAE's
040/060 timing is near an instruction count, so these rows rank the machines and do not
predict an accelerator's frame rate.

## Where the time goes (a500)

A cycle trace of 100 fields of the second demo race (Austria, 19.2 fps there;
`make server CMD="profile 100 ..."`, reduced with `amigaxdev.callprofile`):

- The CPU never idles. Chip bus slots: 32% free, 36% CPU, 22.5% bitplanes, 7% blitter.
- About 11% is simulation (the race loop's own code and `$13276`) and 89% rendering:
  `$E4F8` (the landscape: projection $F600-$F9FF with `muls`, polygon spans) 40%; inside
  `$D13C`, the road and verge spans `$10CD2` 22% (whole lines of each plane by the CPU), the
  scaled objects `$18154` 15% (the CPU scaler), `$11C88` 5% and `$118D8` 3%.
- The blitter: about 20 blits a field, mostly 1-5 words by 1-2 lines (the queue's
  handlers $110A8-$111E8 and the sites the original slave patched). Each is followed by the
  original slave's wait (`WaitBlit0`-`7`), 4.6% of all CPU cycles.
- Memory: the program, its data and both screens are in chip memory. CPU reads over 40
  fields: $10000-$10FFF 20% (the renderer's variables and tables, between its code),
  $2F000-$32FFF 23% (landscape work buffers), $34000-$35FFF 11.5% (span tables),
  $D000-$EFFF 10% (the car table, game state), $11000-$11FFF 7%, the object graphics
  $49000-$58FFF about 6%. Writes go mostly to the screens, to the tables at $30000 and
  $34000, and to the custom chips.

## Verification

The demo race renders correctly and no WHDLoad dump appears on these setups:

| Setup | WHDLoad options | Run |
|---|---|---|
| a500 | - | 130 s, four demo races |
| a1200 (68020) | `CACHE` | demo race |
| a1200-040 | `CACHE`; `DCACHE` | demo race |
| a1200-060 | `DCACHE BRANCHCACHE STOREBUFFER SUPERSCALAR` | 150 s, several demo races |
