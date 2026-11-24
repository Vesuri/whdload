# Internals

The program, its display and game time, every slave patch (as offsets into the game's code
hunk or file), current measurements and known limitations.

## Loading and memory

A direct slave in 512 KB of chip memory (`ws_BaseMemSize` $80000), with an optional 80 KB
ExpMem for Enhanced framerate's fast memory (below, "Enhanced framerate"). The slave
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
| $1DB32 (data disk, new) | the race start's directory read from `Disk.2` (`DataDir`, below) |
| $A1D4 | keyboard: quit key, F9 |

The new slaves keep all of these and add the fixes below (`src/fixes.i`, `src/smc.i`, called
from `Patch` before the jump to $3658 and from `Decrunch`). Both programs have the same code
at every address the fixes touch: a memory comparison of both variants at $3658 shows only
data addresses (the data disk's data sits $C8 higher), the slaves' own `jsr` targets and the
data disk's extra patch at $AA14. The one exception is the init code's two VBL vector writers,
at $3B54/$3B5E in Vroom and $3B44/$3B4E on the data disk (`SMC_VBLW1`/`SMC_VBLW2` in each
source).

### The data disk's two disks

The data disk's title asks for the Vroom disk ("Insert VROOM disk then click", the click
wait at $1DABC) and reads its directory: 23 file offsets from track 1 into $1D950 ($1DAC8).
The shared files come from it. Each race start ($36756) reads the directory again from the
disk in the drive and the highscores with it ($1DB32). The two disks differ in that
directory: on the data disk, entries 1-11 are empty and entries 1 and 2 are equal. When
they are equal ($1DB3E), the race takes the data disk's circuits and lap figures. The data
disk's own files are entries 12-21, with the circuits from archive $F and the scenery
archive $15.

The original slave's `Load2` reads `Disk.2` until the first load at offset $183C0 and
`Disk.1` after it, then `Disk.2` again after a load at $33614. So the race start read
Vroom's directory. It then asked for the data disk's sub-file $26 of archive $15, past the
end of Vroom's archive, and the load ran over the program from the buffer at $3458. That
crashed the first race, the demo's or the player's, on every CPU. The new slave has a
`jsr DataDir` at $1DB32, which selects `Disk.2` before the directory read, as a player
with the data disk in the drive would. Races on Vroom's own circuits, with the Vroom disk
left in the drive, are not offered; the Vroom slave has them.

Low memory holds `jmp` trampolines, so a 4-byte site can become `jsr $1xx.w`: the original
slave's at $100-$129, `smc.i`'s at $130-$1A7 and `fixes.i`'s at $1B0. `enhanced.i` keeps its
variables at $1C0-$1D5 and its blitter-start trampolines at $1E0-$1FD.

## Fixes (every CPU)

| Where | What |
|---|---|
| $A514 | the VBL routine's drive motor off (`or`/`and`/`or` on ciab.prb at $A50E) skipped: WHDLoad owns the drives, and SNOOP reports it |
| $A094 | the blitter-done interrupt's dispatcher acknowledges, then waits for the blitter before it starts the next queued blit |
| $10F90, $11BE6, $11CA8 | the blitter queue: before writing a new queue ($10F90) or programming the blitter ($11BE4, $11CA6), the CPU waited only for the current blit ($11202). A fast CPU then overwrote a queue the interrupt was still working through, and the interrupt jumped to a field as its next handler (a 68060 crash at PC $4 with a6 = 0, with the original slave too, caches off). These now wait in $1123A for the queue to drain, as the game's other blitter users do |

| $A2AC | the keyboard handshake waited $C8 loops of `nop`/`dbf`: the boot loader would have calibrated $C8 with a CIA timer, the original slave sets it to 0. It is now a wait for 3 raster lines (over the 75 µs the keyboard needs) |

The blitter queue: the dispatcher is at $A092, the queue pointer at $11264 (idle = $11260),
the queue at $11268, and the handlers at $110A8-$111E8.

## CPU-timed delays and the swap (68020 and higher)

Five delays count `dbf` loops to themselves. On a 68000 (10 cycles a loop, 454 cycles a raster
line) they last as below; on a 68040 next to nothing. On a 68020 or higher they become beam
waits of their 68000 length (`fix_WaitLines` counts changes of the beam's line). A 68000 or
68010 runs the game's loops.

| Where | What | 68000 length |
|---|---|---|
| $481A, $534A | the menu's two wipes ($47FE: 140 lines, $532E: 200), after each copied line: `move.w #3000,d2; dbf d2,*` | 66 raster lines a line, about 30 and 42 fields a wipe |
| $4986 | after a menu choice: 9 × 32001 `dbf` | 6344 lines, 20.3 fields |
| $816C | a delay routine, called by the menu's item actions ($4CBC-$4E0A): 11 × 32001 | 7754 lines, 24.8 fields |
| $153CA | the end of the routine at $15326: the same, d0 and d1 swapped | 7754 lines |

The same patch list holds one more fix for fast CPUs, at $C968: the race loop's landscape
(`jsr $E4F8`) starts the next frame in the buffer the frame end ($D51A) has just handed to the
VBL through $A71C. That buffer stays on screen until the next VBL takes the new one. On a
68040 (`CACHE`) the next frame starts drawing before that VBL in 34 of 40 demo-race frames, and
a screenshot of the next field catches it half drawn: the flickering objects. The landscape
now waits until the VBL has taken the buffer ($A71C = -1, at most 2 fields). That costs the
68040 the rest of a field per frame: `bench 300` 29.8 fps before, 24.6 after (mostly 2 fields a
frame), with the same distance. The a500 starts early in 37 of 40 frames as well, but draws so
slowly that little reaches the screen, and the wait would slow its game speed (which follows
the frame rate), so a 68000 keeps the original loop. A third screen (open-work, step 16)
would recover the field.

The sound player has no CPU-timed wait: it turns a channel's DMA off and back on at the next
VBL ($A040, read at $9452).

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

A decrunch that lands on patched code (the program reloads part of itself to $439C) gets all
of these patches and the fixes again (`Fix_Decrunched`, over $3B54-$1A26E). The variables keep
their state across a reload.

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
  4 planes of 8000 bytes each; 6 bytes lower with Enhanced framerate's 64-bit fetch). The wait comes before the frame's end, so at most one frame
  ends in a field, and $E258 changes at each: that is the frame count the tools read. The
  buffer index is not one: when the panel changes (laps, times), the race loop calls $12FA6
  in pairs ($CC12-$CCE6) to draw it into both screens.
- **The VBL** (level 3 $A076, then $A4F4): $A884 += 1; `jsr` through $A56C (in a race $A3A4:
  the race clock $8500 += 2 while $8504 >= 0, a palette from $A844, the copper list's
  bitplane pointers from $A71C) and through $A572 ($9432, the sound); then the mouse counters
  and buttons into the block at ($A2CC).
- **Game time.** The race clock is real time (2 hundredths of a second per field). The
  simulation takes one fixed step per frame, with no elapsed-time factor (with Enhanced
  framerate, below, one per tick). `tools/vroom.py racelog`
  logs the player's distance each field from the green light of the first demo race. It passes
  the same values in the same order on the a500, a1200, a1200-040 and a1200-060 (the 060 sometimes
  skips a value between two field samples). So game speed follows the frame rate, while the
  clock and the sound timers (the field counter, $8E7E-$905C) run in real time. A lap's clock
  time therefore depends on the machine. `statelog` makes the check exact: the race state
  block $DBC0-$E073 (globals, the 16 cars, the car order at $E050) at every frame end ($D510), from the
  green light of the first demo race, is the same in each of 300 frames on the a500, the
  a1200, the a1200-040 (`CACHE`) and the a1200-060 (`CACHE BRANCHCACHE`). 255 of its long
  words change in that time.

From the green light of the first demo race, 1000 fields (`racelog`; `DETERMINISTIC=1`):

| Setup | WHDLoad options | Frames | fps | Fields per frame | Distance after 1000 fields |
|---|---|---|---|---|---|
| a500 | - | 263 | 13.2 | 3-6, mostly 4 | 79935 (1.0x) |
| a1200 (68020, no fast memory) | - | 350 | 17.5 | 2-5, mostly 3 | 106183 (1.3x) |
| a1200-040 | - (BaseMem uncached) | 375 | 18.8 | 2-4 | 114203 (1.4x) |
| a1200-040 | `CACHE` | 635 | 31.8 | 1-3, mostly 2 | 218755 (2.7x) |
| a1200-040 | `DCACHE` | 785 | 39.3 | 1-2 | 279572 (3.5x) |
| a1200-060 | `CACHE BRANCHCACHE` | 889 | 44.5 | 1 (807 of 889) | 333548 (4.2x) |

These frames were counted from the buffer index (above, "The swap": not a frame count where
the panel's pairs fall across a field boundary). `bench` counts $E258 instead and reads the
distance at the last frame's end: 90006 after 300 frames on every machine it has run on.

With an MMU model, FS-UAE's `DCACHE` caches chip memory data, which no real board does
(AmigaXDev `reference/headless-fsuae.md`, "Chip RAM and the data cache"). The `CACHE` row
(instruction cache only) is the closer model of a real 68040 running this game. FS-UAE's
040/060 timing is near an instruction count, so these rows rank the machines and do not
predict an accelerator's frame rate.

## Enhanced framerate (68020 and higher, `CUSTOM1=1`)

`src/enhanced.i`, applied from `Fix` after the 68020 fixes, when `CUSTOM1` is set and the CPU
is a 68020 or higher. A 68000 or 68010, or `CUSTOM1=0`, runs the original loop.

**Every race loop pass is a tick**, due every 3 fields (16.7 Hz) or with `CUSTOM2=1` every
2 (25 Hz), counted by the game's own field counter $A884. The simulation is the original
one step per pass, so the game runs at the speed of a machine that draws at exactly that
rate, on every 68020 and up.

| Where | What |
|---|---|
| $AF50 (`clr.w $DC30`) | the loop's entry: the tick clock starts now |
| $AF56 (`tst.w $DC34`) | a pass starts: it waits while its tick is early; if the next tick is due already, it is a pass that does not draw |
| $B724 (`clr.w $8504`) | the end of a pause (the pause loops at $B676-$B6C8 inside a pass): the tick clock starts again |
| $C968 (`jsr $E4F8`) | the wait for the blitter queue, the landscape, then the wait for the VBL to take the last frame (`fix_WaitShown`; without the option `fix_Landscape` waits before it; with frames between ticks only while a tick draws, below) |
| $D13C (`jsr $10F90`) | a pass that does not draw leaves out the sky and ground clear but keeps its state: the horizon's scroll (`$13F16`, its blits written into the idle queue, which is not started) and the clamp of the ground's top line $1136C |
| $1103A-$11077 (the queue's ground entries) | left out: after `$10F90` the CPU fills the ground's planes 2 and 3 (`enh_Ground`) while the blitter runs the horizon and the sky |
| $D142-$D14D (the wait for a new field) | a pass that does not draw goes on at $D1C2, leaving out the road spans `$10CD2`, the three objects `$140C0` and the scaler `$18154` |
| $D510 (`move.l $A884,$E258`) | a pass that does not draw returns from `$D13C`, leaving out the swap ($E258, $A71C, `$12FA6`) |
| $E6A0, $E936 (`move.w d5,$9FC4`), $F396-$F39D, $D800-$D809 | with frames between ticks: the engine's pitch is the ticks'; a frame's pitch and height, and the crash wheel's position, are mixed (below, "Frames between ticks") |
| $366E (`movea.l #$2FC96,a7`, at the program's start) | with fast ExpMem, the stack moves there, below the race block's copy (below, "Fast memory") |
| $A924-$1B4FF (the race block) | with fast ExpMem, copied there at the first `Fix` and run from there; its 12 PC-relative reads out and its branch out become `bsr.w` to trampolines below the stack's copy (`_enh_edges`) |
| 91 blitter starts in $11C20-$19B1C (`src/blitwait.i`) | `jsr $10C`-`$124.w` (the original slave's start-and-wait) become `jsr $1E0`-`$1F8.w`: start, one read of dmaconr, return (below) |
| the screens' references, $A32C, $A388, $A3F4, $A4A6, $A4C0 | on AGA, the screens move 6 bytes down and the lores modes fetch 64 bits wide (below, "64-bit fetch") |

At most 3 passes in a row leave out the drawing; behind by more than 50 fields (1 s), the
debt past it is dropped and counted. Link play ($87BC not 0: the pass waits for the other
machine's data at $C4A0) keeps the original loop. The scheduler's variables are at
$1C0-$1D5 (`ENH_VARS`), where the tools read them: the next tick's field, ticks, frames
drawn, fields dropped, the period. `CUSTOM3=n` (for the checks, not in `ws_config`) leaves
out the drawing in n of every n+1 passes, whatever the time.

**Blitter waits.** The original slave made each blitter start in $11000-$19C00 wait for its
blit (`move.w Dn,$58(a6)` became `jsr $10C`-`$124`, `WaitBlit0`-`6`), so the CPU idles
through some 260 small blits a frame. The game waits itself before it programs the next blit
(`btst #6,2(a6)` loops). `tools/blitsites.py` finds the starts followed, in straight-line
code, by such a wait with no memory access in between but to the custom chips: 91 of 134
(the same in both programs' memory images). Three more ($15A96, $15B02, $15B78) write the
blit's edge words with the CPU before the game's wait and keep the full wait; the other 40
reach a branch first. Those 91 now only start the blit and read dmaconr once (Agnus sets the
busy bit a cycle late, as WHDLoad's `BLITWAIT` allows for). With the option off, on the
a1200 (68020) `bench 500` gives 19.11 fps with these 91 sites against 15.76 without (19.89
with all 134). With the option the 68020 draws 490 frames in 1200 fields at 25 Hz (486
before): a drawn frame still takes about 3 fields once it waits for its swap, so the gain
mostly lands below a field. The a1200-040 is unchanged (its frame is 2 fields either way).
`frames 150` at the swap on the a1200-040 and the a1200, before and after: every frame the
same in lines 0-30 and 36-174. Lines 31-35 are the race clock (real time) and lines 175-199
of the cockpit differ between two runs of the same build as well.

**64-bit fetch.** On AGA (Lisa, $F8 in `LISAID` $DFF07C: the chip revision bits WHDLoad
passes on can lack the AA ones) the lores modes fetch their planes 64 bits wide (`FMODE` 3,
`enh_Fmode`): a quarter of the chip bus slots FMODE 0 takes on each display line, the rest to
the blitter, whose time is the gap to 50 fps (an instant blitter draws every frame in a
field). It needs every plane 8-byte aligned, and the screens, $1FAC6 and $277C6, are 6 bytes
past it: they move down by 6, into fill nothing uses ($1FAC0-$1FAC5 holds $CC through the
boot, the menu and a race). Every reference to them, from memory images of both programs at
the title, the menu and a race (instruction operands and longs into $1FAC6-$2F4C5):

| Where | What |
|---|---|
| $3674-$36D2, $3BB2-$3BF2 (Vroom); $3674-$3705, $3BA8-$3BDB and the loader's copy $1DA6E-$1DAA3 (the data disk) | the startup: the first picture, unpacked to the second screen and copied to the first, and its plane pointers into the copper list $A720 |
| $86E2, $86E6, $86EA | the screens' pointers and the draw buffer |
| $A71C; $A726-$A73E, $A792-$A7AA | the screen the VBL shows next; the copper lists' initial plane pointers (low words) |
| $1278C, $12A62, $12BC4 (in the race block) | the race's map code: `movea.l #$20460`, `adda.l #$1FAC6`, `movea.l #$1FEFA` |

The rest takes the screens from the pointers (the loader's unpacks to $22686 are the first
screen plus $2BC0, for example). At the first `Fix` every one of a program's references must
hold its address, or nothing changes; at every `Fix` those that still hold it move (a load
brings the program's values back). The fetch follows the address a lores plane pointer
setting writes: the VBL's new screen ($A32C for the copper list $A720, $A3F4 for $A78C, the
race's) and a new mode ($A4A6, the last plane's end) fetch 64 bits from an aligned screen,
with `DDFSTOP` $B0 (FMODE 0's $D0 fetches 64 pixels more; `DDFSTRT` stays $38, every sprite
kept; the sprites' fetch width stays 16 bits), and 16 bits from any other. The hires mode
($A388, $A4C0) fetches 16 bits. The menu is a lores screen through $A720 and fetches 64 bits
too. Checked against the FMODE 0 picture: screenshots of the title, the menu, both programs'
races at the green light and 150 fields on are the same but for the time bar (lines 31-35,
real time).

**Fast memory.** The slave asks for an 80 KB ExpMem, optional (`ws_ExpMem` negative): the
1 MB a500 (512 KB of slow memory), where WHDLoad also allocates it, must still load
WHDLoad's overlays (at 136 KB it no longer did). When WHDLoad finds it in fast memory (not
below $200000, chip memory, nor in $C00000-$DFFFFF, slow memory on the chip bus), the stack
and the race block move there, and the loader's unpacker variables and tables. Without it (the
a1200, a 68000) nothing moves.

- **The stack** is set once, at the program's start ($366E), to $2FC96, just past the
  second screen. The race uses it down to about $2FC10, and in the a500's CPU accesses to
  chip memory it is the most used data: in 100 race fields of a Barto trace, 128000 of
  722000 data reads and writes, against 314000 to the screens and the custom chips, which
  must stay in chip memory. It moves to the copy's $A900 (4 KB below the block).
- **The race block**, $A924-$1B4FF: the race's setup and loop, the race state
  ($DBC0-$E25B), the renderer, the objects (`$140C0`), the scaler (`$18154`), the bitmap
  scaler ($19FB0-$1AF3F) and their variables (to $1B4FF). After it come data and the
  loader ($1CF00-$1D8FF). No DMA reaches the block (in the a500's trace of 100 race fields
  only the CPU reads or writes $B000-$1DFFF, and the copper lists end at $A8FF) and the program's
  reloads ($439C-$817E, $55DE-$678A) stay below it. The copy starts at the ExpMem's start
  (`ENH_BLOCK`, $1D6, holds its offset; the tools read it). Any offset works: the block
  moved by an offset that is not a multiple of $10000 gave the same state in 600 passes and
  the same frames. `enh_Move` copies it once, at the first `Fix`, after every patch is in,
  and relocates the long addresses into it (`RELOC_IN` in `src/reloc_<variant>.i`: 1384).
  One long immediate into the block is not an address in it: the title copies its load
  routine from $12D27 to $15294+32000, the loader's entry $1CF94 (the bytes the program
  loaded there), so `tools/reloc.py` keeps it as a number (`NOT_ADDRS`). Relocated, the copy
  wrote 302 bytes 6 KB past the ExpMem's end.
  The long addresses into it from outside (`RELOC_OUT`: 225 in Vroom, 235 on the data disk,
  whose race start writes the lap figures into the race loop's immediates at $CAE4-$CAFC)
  are relocated after every `Fix`, where the site still holds its value (a reload over the
  program brings it back). The slave's own references go through `_blk_ptrs` (with
  `src/smc.i`'s reads of the bitmap scaler's table at $1A33C-$1A37F). The block's
  PC-relative reads out of it ($825D-$8260, $8500, $86EA, $8764, $87BC) and its branch out
  ($CF52 to $7D30) go through trampolines below the stack's copy, in `bsr.w` range.
  `tools/reloc.py` makes the tables: a recursive disassembly from aprof profiles of whole
  sessions and the a500's trace, the dispatch, offset and branch tables and code addresses
  it lists, and a review of what it leaves undecoded (numbers, data tables, and code that
  holds no absolute address). Every `Fix` still applies the patch lists to the chip copy
  too, which nothing runs any more.

- **The scaler's pointer table** at $1B464, read PC-relative, runs past the block's end to
  about $1B5FB (`ENH_TAIL`, $1B600). Nothing addresses $1B500-$1B5FF absolutely, so in the
  copy its tail lives past the copy's end, as consistently as in chip memory: the space
  after the copy is the table's, up to `ENH_TAIL`.
- **The loader's unpacker area**, $34F36-$35581 ($34F4A on the data disk, `ENH_WORK_LO` in
  each source): the unpacker's escape byte and counters and its Huffman tables, read for
  every bit of a file. They go to the page after the copy (`ENH_WORK`, $1B800 in the
  copy's addresses); `enh_Move` copies them and rewrites the loader's 24 long addresses
  of them (`_enh_work`, the same sites in both programs, each only where it still holds
  one). The decrunched length before them ($34F32), which the slave and the tools read,
  stays. The race uses parts of the same chip memory as its own buffers ($34D92, $3517A:
  object spans), which it fills before it reads.

Checks of the moved block. `statelog 600 tick` against the a500 (`CUSTOM3=2`, pointers into
the copy logged as the program's addresses) agreed in all 600 passes on the a1200-040.
`frames 150` there, the block moved against `-DENH_NOBLOCK`: every frame the same in lines
36-171.
The cockpit (lines 172-199: its height and the speed digits) and an object on the horizon
(lines 31-35) follow the fields, not the ticks: even with the block in chip they differ between
two builds that reach the race a few fields apart (the moved block's build is 13 fields
earlier at the same tick). A developer build (`-DENH_PROTECT`, the a1200-030 with `MMU`)
protects $B000-$1B4FF in chip memory between `Fix`es (from the first whole page: the VBL
handler at $A076 can't run in a protected page). It ran the title, the menu, a driven
player race through its 5 laps, the scores, the menu and a second race with no access.
The data disk ran its prompt, the menu, a driven race and a second race on the a1200-040 (its
lap-figure sites held the copy's addresses).

Measurements (`bench 500`, the first demo race, at 25 Hz: `CUSTOM1=1 CUSTOM2=1`; the block
in chip with `-DENH_NOBLOCK`, a scratch knob that moves only the stack). The a1200-fast
(68020, Zorro II) draws 25.05 fps with none of 499 passes undrawn, against 23.19 with 41 of
540; the a1200-030 (`MMU`) 25.03 with 1 of 500, against 24.78 with 5 of 504; the a1200-040
(`CACHE`) is at 25 fps either way. The stack alone, option off: 25.05 fps on the a1200-040
against 24.75, 22.30 on the a1200-030 against 21.42. The block that ended at $11FBA (without the objects and
the scalers) gave 24.78 fps on the a1200-fast, with 6 undrawn. aprof on the a1200-040
(`CACHE`, 25 Hz): with the scalers in the copy the time waiting for the next tick rose from
43.6% to 52.1%, `$D13C` (the drawing) fell from 47.0% to 39.0% and the scaler `$18154` from
25.1% to 17.5%. On the a1200-040 the ExpMem is Zorro III memory (offset $41FD0000 in FS-UAE):
32-bit addresses throughout.

**What a pass that does not draw still runs.** The race loop's own code, the landscape
`$E4F8` whole, and every part of `$D13C` but the ones above.

**The wait for the shown screen.** Right after a swap the draw buffer is still on screen
until the next VBL takes the new frame ($A71C = -1). The landscape draws nothing (no
reference to the screens or the blitter in $E4F8-$10CD1; its one outside call, `$9D94`, is
the car order), so with the option the wait comes after it, before the race loop's panel
updates ($CA10-$CCFA) and `$D13C`: the landscape's work overlaps the wait, in every pass.
`shown 40` checks it: at each swap it reads the screen still on display, and again when the
VBL takes the new frame. On the a1200-030 at 25 Hz and on the a1200 with `CUSTOM3=2` the only
change is the map's position marker (line 22, planes 1-2, in 2-3 of 40 frames), which the
race loop draws at $C8F8-$C95A, before the landscape, as the original does. A first build
left the wait out of undrawn passes: they drew into the shown screen (flicker on the
a1200-030 at 25 Hz, in 41 of its first 43 undrawn passes). One with the wait before
`$D13C` instead let the panel updates through (lines 55-59 in 2 of 40 frames).
- `$E4F8` is not only drawing. Before its projection ($E4F8-$F417) it follows the track
  for the simulation: the curve under the car ($10AD9/$10ADB), the lateral force $10AC4,
  the view angle $DBEC, the car's height $10C4E, a bounce state machine ($E0D8-$E0E0),
  the engine sound's pitch ($9FC4, $A03C). Its projection decides whether the car is off
  the road: `$FA62` reads the road edges of the nearest projected line from the span table
  at $34D92 and writes $10AAA (with the camera shake index $10AA8, one long at $FAC6), which
  the acceleration, the steering and the crash code read. A build that left the projection
  out of undrawn passes diverged at that flag only.
- `$D13C` keeps time too: the ARCADE score ($D3C6-$D408: $8370 grows with the speed every
  pass), the start lights (`$D52A`, $DC36 counts passes), the pit stop (`$D5FC`, $DC38),
  the crash sequences (through $E0E4 and `$DAE0`, $E0DC counts passes, clearing $DC34's
  bit 0 and the steering).
- The panel, the mirrors, the lights and the crash sprites draw into the screen the next
  drawn pass draws again, keeping their per-screen bookkeeping (indexed by $86DE).

Every frame-counted timer is in the pass ($DC32's 50 at $CA50, the race countdown $DC20's
30 per step, the start lights, the pit stop, the crash sequences, the fuel and tyre
counters), so it now counts ticks. The race clock ($8500) and the sound timers run on the
VBL, in real time, as before.

**Input.** The race reads the mouse as positions once a pass ($AF56-$AFF2: y clamped to
±94, x to ±271), so a pass that catches up reads the same position again, as a slow frame
did. A gear change happens on the button's release ($DC1A remembers the press), so a press
counts once however many passes see it. The demo's recorded controls advance one entry a
pass ($DC26), that is one a tick.

**The checks**, from the first demo race's green light:
- *The same ticks.* `statelog 600 FILE tick` (the state at $CD0E, after the loop's
  `bsr $D13C`, in every pass) on the a500, on the a1200-040 with `CUSTOM1=1 CUSTOM3=2` (two
  of every three passes undrawn) and on the a1200 with `CUSTOM1=1 CUSTOM2=1` (193 of 668
  passes undrawn, as it falls behind 25 Hz). The state includes the drawing state an undrawn
  pass keeps (the ground's top lines $11368/$1136C, the horizon's scroll at $1407C). The two
  68020+ logs agree with the a500's in all 600 and 599 compared (`statecmp --align`: the a500 logs one more pass at
  the green light). Left out: $DBD8/$DBDC, the map marker's position in each screen ($C8FE,
  indexed by the draw buffer), which follow the screen order.
- *The same speed at equal fields.* `racelog 1200`: the distance at field 600 and at field
  1199 is the a500's after fields/period ticks, or one tick away (at most 0.56%), on the
  a1200, the a1200-030 (`MMU`) and the a1200-040, at both speeds; no fields dropped. Frames
  drawn in the 1200 fields:

  | Speed | a1200 (68020) | a1200-030 | a1200-040 |
  |---|---|---|---|
  | 16.7 Hz | 399 | 400 | 400 |
  | 25 Hz | 486 | 582 | 599 |

- *Pause.* On the a1200-040, 300 fields of pause ran no ticks; the 105 fields after it ran
  36 (one tick every 3 fields from the unpause), none dropped.
- *Gear changes.* From the green light, full throttle: six presses of the right button, 4
  and 10 fields long with 20 between them, change the gear 0 to 6 one step each, with the
  option (a1200, 25 Hz: a 10-field press spans 5 ticks) and without it.
- *A 68000.* The a500 with `CUSTOM1=1` runs the original loop: the scheduler's variables
  stay untouched.
- *The data disk.* Its first demo race (Hockenheim) with the option: the a1200 at 25 Hz drew
  546 frames in 1200 fields, the a1200-040 at 16.7 Hz 400; no dump.

**The cost of catching up.** An undrawn pass still runs the landscape and its projection.
Profiled on the a1200 (68020, aprof) with nearly every pass undrawn, one cost about 1.3
fields: 0.6 in the landscape, 0.3 waiting at `$118D8` for the blitter queue to finish the sky
and ground clear, and the wait for the VBL before the landscape. Without the clear and with
the wait after the landscape, the a1200 at 25 Hz draws 486 frames in 1200 fields (20.3 a
second, 15.8 without the option); it drew 356 before. Leaving the projection out of undrawn
passes as well would gain about 2% at most (open-work, step 22).

The a500's own speed, for comparison: the first three demo races (three circuits) run at
13.8, 17.5 and 13.9 fps (`meter 1500` from each green light; mostly 3-4 fields a frame), so
16.7 Hz is about 1.2 times its speed on two of them and the same on the third.

### Frames between ticks

With fast ExpMem (not on the a1200 without fast memory, which keeps the drawing in the
ticks, as above), the ticks draw nothing and the frames are drawn between them, as often as
the machine manages, each at its own time. A frame shows the last two ticks' states mixed:
with S(n-1) and S(n) the states after the last two ticks and alpha the fields since S(n)'s
tick was due over the period, a frame shows S(n-1) moved alpha of the way to S(n). The
picture is a tick late, as in any interpolation.

- **The snapshot.** At the end of every tick (`enh_Snap`, from the pass's start) the slave
  keeps a copy of the race state the drawing reads (`_enh_r`, 2212 bytes in the ExpMem
  after the unpacker's page): $DBE8-$E253 (the race state but the map marker's position in
  each screen $DBD8-$DBE7, the landscape's result $E254 and the swap field $E258),
  $10A90-$10C53 (the landscape's variables), and a few words the drawing reads elsewhere
  ($DBC0-$DBD7, $C46E, $1067C, $11784, $11C84, $12150, $133DC, $1407C, $1B28C, $1B3D4,
  $8370, $4988A). It keeps two, the tick before and this one, and swaps them.
  Left out: the screens, the blitter queue $11268-$11527 (with the ground's top lines
  $11368/$1136C: the steering wheel `$11C88` rebuilds the queue past them), the sound and
  the VBL's variables. The sound's interrupt state $9CD0-$9CEB (the engine's two-step
  sample change, below) was in it once: a frame put back the tick before's, the change
  ran its first step again and again, and the engine played one sample at the other's
  period, an octave off, until the next change.
- **A frame** (`enh_Frame`) loads the tick before, moves it, runs the drawing, and loads
  this tick back. The player's distance $DC50 moves by alpha of this tick's step ($10C30),
  and the landscape `$E4F8` runs again with that step: it integrates the lateral position,
  the steering and its ring buffers by the step, so it is re-run rather than mixed. It stops
  a step short of the line ($DBD4, the track's length: at the line $C7F8 takes the length
  off every car's distance). The speed and controls ($DC60, $10C46, $DBF8) are this tick's.
  The other 15 cars' distances (+2) and lateral positions (+8) are mixed; a car that jumps
  more than 4096 or crosses the line stays. Alpha is kept within 0..1: outside it the
  step turns huge, the camera jumps to the line, and the cars' sort by distance at
  $ED88-$EDA6 runs off its list into the landscape's code at $10A42 (a Line 1111
  exception on the a1200-fast in a first build of step 16). The order the cars are sorted
  in is the tick before's, so a car the player passes in this tick can be behind the
  mixed camera: its distance ahead is negative, and the same sort's walk runs below its
  list at $10B3E and moves the landscape's variables up (the road's detail $10ADA then
  indexes the jump table at $10776 past its end: an Illegal Instruction at $10B76 on the
  a1200-030 in a player race). A frame leaves such a car out (`enh_Sort`, at $ED76); a
  tick is unchanged. Then the landscape's result
  into $E254 and $DBEE/$DBF0 (as $C960-$C984), the wait for the shown screen, the map
  marker (as $C8F2-$C91C, after the wait: the CPU draws it into the screen) and `$D13C`,
  which swaps.
- **What a frame mixes besides.** Not everything the picture follows moves with the
  step. The race loop's steering ($BC9E-$BDAA) moves the camera's lateral position $DBEC
  once a tick, before the landscape: a frame takes it alpha of the way from the tick
  before to its value as this tick's landscape started (`_enh_lat`, kept at $C968), and the
  landscape adds the curve's part by the step. The player's lateral position $DC56 (the
  race loop's copy of $DBF0, $C55C; the mirrors and the crash read it) is mixed like the
  other cars'. The landscape's pitch and height ($F396: the bounce, the jump, the tilt
  from the step's change at $F282, the shake off the road) integrate once a pass, so a
  frame re-running it got a whole pass of them and a tilt from its own part step: at
  $F396 a frame takes the mix of the two ticks' $10ACA and $10C4E instead (`enh_Pitch`),
  which then make the horizon $10B32, and writes the mix back to $10ACA: on a flat road
  ($10AD8 zero) the road's slope reads it again at $F436, and with the frame's own
  re-run of the jump there the road and the ground's top line moved a tick at a time
  while the mountain glided. The horizon's scroll (`$13F16`) and the three sky
  objects ($4988A, moved at $C9C0-$C9FA; the mountain's top is one) move by $10C42, which
  in a tick the race loop sets after the landscape ($C99A, the steering's turn $DC3E); a
  frame moves both by alpha of this tick's $10C42 (`enh_Sky`), so the mountain's top and
  foot move together. The crash's flying wheel ($D7BE-$D814) takes its position from a
  table at $E134 by the pass count $E0DC (x at +4, the line's offset at +8): a frame draws
  alpha of the way from the step before (`enh_WheelXY`, at $D800). Before these, all of
  them moved once a tick (a player race at 16.7 Hz: the census of the race state at every
  frame and tick, `CUSTOM3=3`; field by field screenshots of a crash).
- **What a frame must not do twice.** While a frame runs, the race clock's gate $8504
  ($D530, $D602), the bump sound $A03C ($E6A6, $E93C) and the engine's pitch $9FC4 ($E6A0,
  $E936, from the revs $DC00) are not written. A frame's engine pitch came from the tick
  before's revs, so $9FC4 held the value a tick behind between the ticks' writes; the
  sound routine latches it in some of its states ($999A, from the VBL's sound code), glides
  to it, and switches the engine's sample at 138 ($9A0C). The switch takes two AUD0
  interrupts ($9C7C): the first, at a sample block's start, sets the other sample's
  location and length ($9CDC, $9CE4 by $9CDA) and $9CD2; the second, as that sample
  starts, its period and $A044. A tick leaves out
  what only the frames draw: the map marker ($C8F8), the HUD (`$120A6`; the wheel's lower
  part `$118D8`, from $D20A, patched at $118DE where the site holds no block address;
  $D21C-$D3BB: the cockpit, mirrors, gear, speed and wheel, after the pit stop `$D5FC`,
  which keeps time) and the score's or time's digits ($D414, $D43E). The rest of the per-screen bookkeeping is
  the frames'.
- **Pacing** (`enh_PassI`). A frame starts as soon as the last one has swapped: its
  landscape runs while the last frame waits for the VBL, then it waits for the shown screen
  and draws. Its alpha is for the field it will be shown in if it draws within a field:
  the next field, or the one after if a frame still waits for the VBL. When the next tick
  is due by that field, the tick runs first (up to 2 fields early; it reads the mouse that
  much earlier). Three ticks in a row without a frame force one, of the newest state
  (alpha 1). A first version waited for the field to change before each frame
  ($A884 against $E258), so the landscape never overlapped the wait: on the a1200-040, 28.8%
  of the time went idle there (aprof, 200 fields).
  `CUSTOM3=n` draws n frames a tick at alpha 0, 1/n, ... whatever the time (for the checks).
  `-DENH_NOINTERP` builds the earlier mode.
- **The landscape and the blitter queue.** Every landscape run (a tick's or a frame's) now
  first waits for the blitter queue to be idle (`enh_QueueIdle`, `fix_Queue`): the landscape
  writes the ground's top line $11368 at $F9E2, inside the queue the steering wheel's blits
  still run from. Without the wait a frame on the a1200-030 could corrupt a queued blit
  (a WHDLoad dump in a player race). A tick then waits for the shown screen, as before
  frames between ticks: the race loop's panel updates after the landscape ($CA10-$CCFA)
  draw into the screens, and a tick often runs while the last frame still waits for the
  VBL (`shown 80` on the a1200-030: lines 55-59 changed in the shown screen in 2 of 80
  frames, and the wheel's lines 191-194 in every tick, before both were fixed). Waiting
  every tick costs about 3% (`bench 300`: the a1200-040 41.32 fps against 42.49).

Checks (16.7 Hz, the first demo race; `CUSTOM1=1`):
- *The same ticks.* `statelog N FILE tick` against the a500 (`statecmp --align 1 --skip
  DBD8,DBDC,11368,1136C`): the a1200-030 (`MMU CACHE`, `CUSTOM3=2`) agreed in all 1500
  passes but for $DEFC, a number that falls in the copy's range and is translated
  (development, `statelog`), and the a1200-040 (`CACHE`, paced) in all 600 compared; with
  step 16's pacing, all 300 compared on the a1200-040.
- *Nothing drawn into the screen on display.* `shown 80`: none of 80 frames on the
  a1200-030 (`MMU CACHE`) and on the a1200-040 (`CACHE`).
- *A driven race.* The a1200-030 (`CACHE`) through 4000 fields of a player race: 1421
  ticks, 3991 frames, none dropped, no dump (1431 and 3546 before step 16's pacing).
- *The data disk.* Its first demo race, `bench 300` on the a1200-040: 49.34 fps (2.96
  frames a tick); no dump.
- *The a500* with the 80 KB ExpMem boots and runs the original loop (`bench 150`: 12.10 fps).

Measurements (`CUSTOM1=1`, 16.7 Hz, the first demo race; without frames between ticks every
machine drew 16.7 fps):

| Machine | step 15 | step 16 (`bench 300`) | frames a tick |
|---|---|---|---|
| a1200-fast (68020, Zorro II) | 24.44 (`bench 500`) | 26.50 | 1.59 |
| a1200-030 (`MMU CACHE`) | 36.87 (`bench 500`) | 41.67 | 2.49 |
| a1200-040 (`CACHE`) | 34.25 (`bench 300`) | 41.67 | 2.49 |

The a1200-030 and the a1200-040 give the same fields frame for frame here (239 frames of 1
field, 59 of 2, 1 of 3). On the a1200-040 a frame costs about 1.03 fields of work (aprof),
most of it `$D13C`'s drawing; the landscape now overlaps the wait for the VBL, so most
frames fit a field and the rest take 2. 50 fps needs every frame under a field.

## Input, the menu and the race controls

- **The input block** at ($A2CC), which is $825C: the word $825C holds the buttons (bit 0 the
  left mouse button, bit 1 the right one or the port-1 fire button). $825E (x) and $8260 (y)
  add up the mouse's movement, half the counter steps, every field. Each screen clamps or
  clears them.
- **The title** waits for the right button. It is still loading the menu in the background
  (through the slave's disk loads, during which the field counter stops and chip memory
  reads back as $FFFFFFFF from the gdb stub). It takes a click during that load, and the menu
  appears when the load is done.
- **The menu** ($4800-$4E80, waiting in $8DC0). $86EE points at the highlighted item: $86F2
  START, $8732 ARCADE (TRAIN), $878A NOCOMM, $87D2 ALL, $8826 5 LAPS, $8886 MOUSE,
  $88C6 MANUAL. An item holds its neighbours for eight directions at +0-+$1C, its position at
  +$28/+$2C and the setting's index at +$30. When $825E or $8260 passes ±35 the highlight moves
  to that neighbour and both are cleared; a diagonal move (both past 35) goes nowhere. The
  left button on START starts the race, but the loop reads the button ($4862) only between its
  waits, so the button must be held (30 fields are enough). On another item, the button
  changes that item's setting.
- **The race controls** (from $AF56, once a frame). With MOUSE, y ($8260, clamped to ±94) is
  the throttle ($DBF8 = -y: forward is faster) and x ($825E, clamped to ±271) the steering
  position ($10C46). Both are positions, not movements. With MANUAL, the right button shifts
  up and the left one down, on release ($DC1A; the gear is $DC04, 0 neutral to 6).
- **The demo race** replays the same controls from a table at $1E73E, three bytes a frame
  (y, x, buttons; index $DC26). It is therefore the same race, frame by frame, on every
  machine.
- The player's lateral position is the word at $DC56 (car table +8); the high word of $DBF0
  follows it.

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

## Where the time goes (68020)

aprof, `CUSTOM1=1 CUSTOM2=1` (25 Hz), 200 fields from the first demo race's green light
(`tools/vroom.py aprof` with `FSUAE=$FSUAE_APROF`, `SETUP=a1200` or `a1200-fast`; the inclusive
time of each call target, `tools/aprof_report.py`).

| | a1200 (no fast memory) | a1200-fast (the block in fast memory) |
|---|---|---|
| chip memory accesses | 89% | 48% |
| waiting for the next tick | 0 | 16% |
| `$D13C`, the drawing | 50% | 58% |
| `$E4F8`, the landscape (its own code) | 40% (31%) | 20% (17%) |
| `$18154`, the scaler (`$18330`, an object) | 29% (18%) | 31% (19%) |
| `$10CD2`, the road spans (`$10E72`, the span filler) | 9.7% (3.3%) | 11.5% (4.2%) |
| `$1123A`, the wait for the blitter queue | 1.8% | 8.2% |
| `smc_Sh1_10`/`smc_Sh1_12` with `resload_FlushCache` | 3.2% | 1.3% |

On the a1200 the landscape's time is spread thin (no instruction above 0.5%) and almost all
of it is fetches and data in chip memory; the projection's `muls` take 1.1% together. About
8 times a field a WHDLoad routine runs from wherever the CPU is (5% on the a1200; most likely
its interrupt entry), not from the game's calls.

## Where the load's time goes

An aprof profile of a boot to the first race's green light (`aprof race`, the a1200-040
without an MMU model, `CACHE`, the menu's START at once): 1224 fields. About 450 of them come
before the game starts: Kickstart, the startup sequence and WHDLoad with `PRELOAD`, mostly in
exec's idle `stop` while the emulated hard drive reads (FS-UAE's timing; nothing the slave
does). The game's 772:

| | fields |
|---|---|
| the program's unpacker ($1D798, with its reads from the track buffer, 23; its table setup $1D572) | 164 (54) |
| the boot loader's unpacker ($6F3FA), the program itself, before `Patch` | 58 |
| a sound sample's delta decode ($43AF8) | 28 |
| the race start's passes before the green light (`enh_Pass`) | 117 |
| the title's waits ($12F78), the menu's wipes (`fix_Wipe`) | 87, 29 |

The unpacker's time was its reads of its own Huffman tables in chip memory (`cmp.w (a2)+`
and `move.w (a3)+` for every bit, and a 256-byte selection sort for every file), not the
track reads or the code. With its tables and variables in fast memory (above, "Fast memory")
it is 85 fields (the setup 23), the game's part 666 and the green light at the game's field
603 instead of 709. The boot loader's unpacker runs before the slave reads `CUSTOM1`, and the
sample's decode is one pass; both are left.

## Verification

The demo race renders correctly and no WHDLoad dump appears on these setups:

| Setup | WHDLoad options | Run |
|---|---|---|
| a500 | - | 130 s, four demo races |
| a1200 (68020) | `CACHE` | demo race |
| a1200-040 | `CACHE`; `DCACHE` | demo race |
| a1200-060 | `DCACHE BRANCHCACHE STOREBUFFER SUPERSCALAR` | 150 s, several demo races |
| a1200-040 | `SNOOPAGA CHKBLTWAIT DCACHE` | five demo races; a player race (`race`, `drive` 6000 fields) |
