# Open work

Set up from StingRay's v1.2 slave. Both variants boot to the title and into archipelago
1, SPS 627 on the a500 and SPS 628 (NTSC) on the a1200, and F10 quits cleanly on both. The
frame loop, the game's clocks and the rendering cost are measured
([internals.md](internals.md#the-frame)). Game time is decoupled from the frame rate
(step 1 below), and steps 2 to 4 of the 50 fps plan are done.

## Release

2.0b (18.11.2026): StingRay's v1.2 code, which the whdload.de install package lacked, with
`$VER` and the info text in the slave and the ReadMe entry above StingRay's, and game time
decoupled from the frame rate. Still to do: play-test both versions on every machine in
`SETUPS`, including saving and loading a game and an archipelago with blood eggs (20 or
later). `tools/play.py` plays archipelago 1 to its end.

## 50 fps on the a1200-030

The soft target is 50 fps in play on the a1200-030, which drew 8.2 fps on archipelago 1
before step 2, 15.8 after it, 23.2 after step 3 and 43.6 since step 4. Before step 2 a frame there took
124 ms: 90 ms of CPU work, 12 ms waiting for the blitter and 27 ms waiting for fields. The causes, largest first:

- **Caches off** (fixed in step 2). WHDLoad's default marks BaseMem uncacheable, and
  without the MMU in use (the 68030's default) that turns both caches off. The slave set no
  cache flags, so the whole game ran uncached from Chip RAM. WHDLoad's `CACHE` option alone took the
  emulated 030 from 8.0 to 15.0 fps.
- **Nothing in fast memory** (fixed in step 4). No ExpMem. Code, stack, tables, the span list and the map all
  sit in Chip RAM. With the instruction cache on, 80% of the CPU's chip accesses outside the
  wait loops go to things DMA never reads: about 31000 a frame, at least 8.7 ms.
- **Two field waits a frame** (fixed in step 3). One before drawing, which double
  buffering needs, and one before the swap, which it does not. That capped the game at
  25 fps and added a field to every frame.
- **Waiting for the blitter.** 10.6-11.7 ms a frame, 7 ms of it the sky fill. The CPU waits
  before each of its five plane blits and does nothing meanwhile.
- **The renderer's CPU work.** With the instruction cache: span drawer 9.5 ms, fill routines
  7.6, near rows 3.9, row set-up 3.6, far-row loop 2.6.

What does not matter: the world update (0.03%), interrupts (1-2%) and the swap (0.1%).

The decoupling came first: without it every later step would also speed up moves, the
spread and the animations. Measure every step with `tools/archipelagos.py frames 250 4` on
the a1200-030, a1200 and a500, with `tools/bench.py` (030 without the MMU model) for the
breakdown, and with `tools/timecheck.py` for game time. The a500 must neither slow down
nor change behaviour.

1. **Decouple game time.** Done (`src/timing.s`; [internals.md](internals.md#decoupled-srctimings-20b)).
   Decided 18.11.2026: every frame-counted step takes at least 6 fields (the game's world
   tick, 8.33 Hz), so today's a1200-030 pace holds on faster machines. The world tick stays
   as the game has it unless the a500 gets faster too. Checked with `tools/timecheck.py`
   on the a500, the US a1200 and the cached 030: moves, the renderer's steps and both
   effects (a stone's collapse, the Obelisk's ramps), and an image scan finds nothing
   else at the frame rate. Not checked in play: the blood spread (`$C99E`), which needs
   archipelago 20 or later; it runs in the renderer's steps, which are checked.
2. **Instruction cache.** Done. The level 3 handler's self-modifying `jsr` jumps through a
   slave variable that its four writers now write, and the slave turns on the instruction
   cache for BaseMem with the data cache off (`resload_SetCPU`; a 68040/060 with the MMU
   would otherwise make the screens data-cacheable). `tools/smc.py` finds no other
   self-modifying code through every screen, on both versions
   ([internals.md](internals.md#rendering-cost)). Panning on archipelago 1
   (`tools/archipelagos.py frames 250 4`), the previous slave against this one: a1200-030
   8.20 to 15.80 fps, a1200 6.40 to 12.60, a500 5.40 and 5.40.
3. **One field wait a frame.** Done. On a 68020 or better the frame skips the wait before
   the swap (`$1185C`); the 68000 keeps it. The swap's copper-list writes run with all
   interrupts off and wait out lines 0-2 and a frame's last three, on every CPU
   ([internals.md](internals.md#the-frame)). Panning (`frames 250 4`), the step 2 slave
   against this one: a1200-030 15.80 to 23.20 fps (3.15 to 2.17 fields a frame), a1200
   12.60 to 16.60; SPS 628 (60 Hz fields) a1200-030 15.12 to 19.92, a1200 13.68 to 17.76;
   a500 5.40 and 5.40. The a500's timecheck state and effects are identical to the
   original slave's, SPS 628's on the a500 to step 2's. Game time on the a1200-030: a move
   46 fields, 8.17 renderer steps a second, collapses 33 and 32 fields, the ramps 384. The
   world tick, which is not decoupled and is checked once a frame, runs 7.3-7.8 times a
   second there (8.17 at step 2's 3-field frames, 6.33 on the uncached original): frames
   of 2 and 3 fields check it late more often than frames of 3.
4. **Fast memory for what DMA never reads.** Done, more widely than planned: on a 68020
   or better with ExpMem in fast memory the whole body runs there, with the stack; only
   what DMA reads stays in chip (the replayer with its samples, sprites, copper lists, the
   blitter's tables and a buffer), each relocation resolved to the copy its target is in
   ([internals.md](internals.md#the-body-in-fast-memory-20b)). `tools/smc.py` finds no
   self-modifying code that way either, no DMA reaches beyond the game's memory on any
   screen, and nothing reads the chip copy outside the blocks. The map stays in chip
   (0.13 ms a field). The data cache stays off. Panning (`frames 250 4`), step 3's slave
   against this one: a1200-030 23.20 to 43.60 fps (1.15 fields a frame), a1200-fast and
   a500-020 (68020 with fast memory) 16.60 and 15.00 to 23.80; a1200 without fast memory
   16.60 and 16.60; SPS 628 (60 Hz) a1200-030 19.92 to 30.00, a1200 17.76 and 17.76,
   a1200-fast 19.92; a1200-040 and a1200-060 50.00 before and after; a500 5.40 and 5.40.
   On the a1200-030 (`tools/bench.py`, no MMU model) the frame's work without waits went
   from 1.40 to 0.59 fields, CPU work to 12.2 ms and blitter waits to 8.7 ms a frame;
   `tools/cpuchip.py` counts 5216 CPU chip accesses a field outside the wait loops, from
   15984, 82% of them the screens. Game time there: a move 44 fields, 8.33 renderer steps
   a second, collapses 31 fields, the ramps 384. The a500 runs the chip path unchanged,
   and its moves are identical to the original's field by field, but asking for ExpMem
   changes WHDLoad's memory layout and with it the timing below a field: in
   `timecheck.py effects` one click takes effect a frame (10 fields) earlier, and the
   play-through differs from there (a build without the ExpMem request is identical; so
   is SPS 628's move check).
5. **Overlap the blitter with the CPU.** The sky (lines 20-112) and the ground (113-179)
   do not overlap. Start the sky's plane blits before draw view and start each next one
   when the blitter is idle, polled once a ground row or from the blitter interrupt. The
   CPU then draws the ground while the blitter fills the sky. The objects wait only for
   what is left. Also check which sky planes need clearing at all: only object pixels dirty
   them. Gate: the blitter-wait line of the bench report.
6. **The renderer's CPU work**, re-profiled after steps 2-5.
   - Inline the per-word `jsr 12(a1)` fills as long-word writes: the view is long-aligned,
     and AGA's chip bus takes a long in one access.
   - Keep the far-row loop's two direction constants in registers, not pc-relative chip
     reads.
   - Fold the span drawer's lookups.
   - A 68020+ path in the slave is allowed. Keep the 68000 path as it is.
7. **Triple buffering**, only if frames still end just after a field. It needs another
   40000 bytes of Chip RAM, so map what BaseMem uses between `$16314` and `$5C780` first.

After step 4 (18.11.2026), the measurement for that decision: on the a1200-030 a frame
is 12.2 ms of CPU work and 8.7 ms waiting for the blitter, 21 ms against a field's 20.
So 50 fps there looks reachable with step 5's overlap, and step 6 would add margin. The
a1200-040 and a1200-060 already run at 50. Without fast memory (a stock a1200) the frame
still takes 3 fields, and steps 5 and 6 are what is left for it.

## Other candidates

- SPS 628 (NTSC): the same analysis on its offsets, once SPS 627's patches work.
