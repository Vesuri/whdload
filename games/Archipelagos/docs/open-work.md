# Open work

Set up from StingRay's v1.2 slave. Both variants boot to the title and into archipelago
1, SPS 627 on the a500 and SPS 628 (NTSC) on the a1200, and F10 quits cleanly on both. The
frame loop, the game's clocks and the rendering cost are measured
([internals.md](internals.md#the-frame)). Game time is decoupled from the frame rate
(step 1 below), and steps 2 to 6 of the 50 fps plan are done.

## Release

2.0b (18.11.2026): StingRay's v1.2 code, which the whdload.de install package lacked, with
`$VER` and the info text in the slave and the ReadMe entry above StingRay's, game time
decoupled from the frame rate, and steps 2 to 6 below behind Enhanced framerate (CUSTOM1,
set in the installed icon). Played by the maintainer (SPS 627, a 68040 with fast memory):
archipelagos 1 to 5, saving with 5 completed and loading it in a new session; that play
found the sky's copper lists in fast memory at dusk (fixed). No full play-through (the
archipelagos are generated, thousands of them). Still worth a look: a dawn after a dusk,
an archipelago with blood eggs (20 or later), the Obelisk's destruction past archipelago 1. With CUSTOM1 off the
a1200-030 draws 8.2 fps (SPS 628 7.9), as before step 2, and the a500's moves (both
versions, CUSTOM1 on and off) are step 5's.

## 50 fps on the a1200-030

The soft target is 50 fps in play on the a1200-030, which drew 8.2 fps on archipelago 1
before step 2, 15.8 after it, 23.2 after step 3, 43.6 after step 4 and 50 since step 5
(panning archipelago 1; SPS 628 60), with a frame's work down to 0.41 fields after step 6. Before step 2 a frame there took
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
5. **Overlap the blitter with the CPU.** Done. On a 68020 or better draw view's two ground
   fills and the sky fill's five go into a queue at draw view's start and run from the
   blitter interrupt while the CPU draws the ground; the game's blitter wait waits for the
   queue first, so every other blit keeps its order. The border clear after the objects is
   the CPU's, and the wait sets BLITHOG while the objects' blits run
   ([internals.md](internals.md#the-frame)). Which sky planes need clearing (only objects
   dirty them) no longer matters: the fills end well inside draw view. Panning
   (`frames 250 4`), step 4's slave against this one: a1200-030 43.60 to 50.00 fps (every
   frame one field), a1200 16.60 to 18.40, a1200-fast and a500-020 23.80 to 25.00; SPS 628
   a1200-030 30.00 to 60.00, a1200 17.76 to 19.92, a1200-fast 19.92 to 29.28; a1200-040 and
   a1200-060 50.00 before and after; a500 5.40 and 5.40. The bench gate (a1200-030): the
   blitter waits went from 8.7 to 0.8 ms a frame, CPU work from 12.2 to 14.5 (draw view
   shares the bus with the fills, and the border clear is the CPU's). `tools/timeline.py`,
   facing two trees and two stones: the sky fill's 76 lines of waiting gone, the objects 65
   to 51 lines (BLITHOG), the border 35 to 15, the swap at line 280 instead of the next
   field's 63. Game time there: a move 43 fields, 8.33 renderer steps and world ticks a
   second, collapses 31 fields, the ramps 384. The a500 runs the 68000 path, and its moves
   and effects are identical to step 4's field by field (SPS 628's move too). `tools/smc.py`'s
   routes, both versions, play through with no difference but the known `rts`, and the
   screens match step 4's pixel for pixel at twelve headings but for the creatures' animation
   (a1200-030) and at one (a1200-060).
6. **The renderer's CPU work**, and the title's pre-scaler. Done, on a 68020 or better
   ([internals.md](internals.md#the-frame)).
   - With the body in fast memory the pre-scaler (the title's PLEASE WAIT) reads a fast
     copy of each object's source and scales into fast scratch, then copies the object to
     chip; the buffer is identical. a1200-030 190 to 35 fields (SPS 628 226 to 33),
     a1200-fast 369 to 320, now CPU-bound ([internals.md](internals.md#the-pre-scaler)).
   - The span drawer builds each row in registers and writes it a long at a time, with a
     paint routine for each terrain type (the plan's long-word fills and folded lookups).
   - The far rows' per-pixel loop goes from carry to carry.
   - Not done: the near rows' division loop keeps its variables in fast memory now, which
     would save about 0.6 ms a frame on the a1200-fast in registers; the plan's direction
     constants are cheap reads there since step 4. The map stays in chip: its read is 15
     cycles of each span on the a1200-fast.
   `tools/spancheck.py` finds no difference from the game's routines (3000 random rows
   each, both versions), and the screens at twelve headings match step 5's but for the
   creatures' animation. Panning (`frames 250 4`), step 5's slave against this one:
   a1200-030 50.00 and 50.00, a1200 18.40 to 24.60, a1200-fast 25.00 to 42.20, a500-020
   25.00 to 29.60; SPS 628 a1200-030 60.00 and 60.00, a1200 19.92 to 21.60, a1200-fast
   29.28 to 30.48; a1200-040 and a1200-060 50.00; a500 5.40 and 5.40. The bench gate
   (a1200-030): draw view 13.0 to 6.6 ms a frame, CPU work 14.5 to 8.2, blitter waits 0.8 to
   3.3 (the objects now wait for the queued fills), a frame's work 0.73 to 0.41 fields.
   Game time there and `tools/smc.py`'s routes as after step 5. The a500's moves (both
   versions) are identical to step 5's field by field, but its effects play-through is not:
   from field 112 a frame takes 10 fields where it took 9, and the route differs from there.
   The slave's size alone does that (the same source padded by 1500 bytes differs from both;
   each build repeats its own run exactly), as asking for ExpMem did in step 4.
6b. **The far objects between the rows.** Done (19.11.2026, after 2.0b; [internals.md](internals.md#the-frame)).
   The maintainer's video showed far trees flickering frame to frame: no row crosses the
   cells between the far rows, so the game's list (step 5's, unchanged) drops them. Walking
   on archipelago 1 (six moves, 300 frames, a1200-030), 2.0b's list drops three far objects
   for a frame or a few, seven times; with the gaps searched, none. `tools/spancheck.py`
   checks the search on 300 random gaps a version. Panning (`frames 250 4`), 2.0b against
   this: a1200-030 50.00 and 50.00, a1200 24.60 to 23.80, a1200-fast 41.60 to 38.60; SPS
   628 a1200-030 60.00 and 60.00, a1200-fast 30.48 to 30.00. The search costs about 0.65 ms
   a frame on the a1200-fast (traced), but its frames end just inside a field (work 0.92
   fields a frame, now 0.95), so some now take two.
7. **Triple buffering**, only if frames still end just after a field. It needs another
   40000 bytes of Chip RAM, so map what BaseMem uses between `$16314` and `$5C780` first:
   the pre-scaled objects fill `$193B8`-`$5C780` ([internals.md](internals.md#the-pre-scaler)),
   which leaves `$16314`-`$193B8` (12 KB) and what lies above the screens and the map.
   Now that a frame fits a field on the a1200-030, the objects decide the frame rate there
   (below): a frame of 1.1 fields shows at 25 fps with two buffers and at about 45 with
   three.

After step 6 (18.11.2026). The a1200-030 pans archipelago 1 at 50 fps and SPS 628 at 60.
A frame there is about 107 lines of draw view, the objects (0-98 lines, waiting for the
queued fills and then their own blits) and 19 lines of border clear, ending near line 226
of 313. On the a1200-fast a frame's work is 0.91 fields on average and 1.01 at the 95th
percentile, so frames fall either side of a field: 42 fps. Without fast memory (a stock
a1200) a frame takes 2 fields, CPU-bound.

The objects, which the frame rate follows on fast machines ([internals.md](internals.md#the-frame)):

- They are blitter-bound. Their 45 blits there are 1860 words of a four-channel blit, four
  bus cycles a word, and the blitter has 58% of the slots while the CPU waits, the rest
  going to the bitplanes and the CPU's set-up. BLITHOG in the wait (step 5) took 13-20% off.
- Queueing them too would save at most the CPU's set-up between blits (9 lines), and the
  queue's interrupt for every one of many small blits (36 words on average) would eat into
  that.
- The CPU drawing them: its chip accesses take about two slots each on the emulated 030
  (the border clear: 1600 long writes in 15 lines with no bitplane DMA), so a read and a
  write of a long (32 pixels) take about half the blitter's eight slots. With shifting and
  masking in software, perhaps 1.3-2 times faster, unmeasured, for a rewrite of every
  object routine that must match the blitter pixel for pixel. Not worth it before step 7.
- Triple buffering (step 7) is what keeps them from halving the frame rate: today a frame
  that runs over a field by a line takes two. The a1200-fast's frames are there now.
- The border clear (15 lines) could go if the display window ended at the view's edges in
  play. The in-game copper list does not set the window, though, and every screen shows
  it, so each screen would have to set its own.

So the next step, if any: step 7.

## Other candidates

- SPS 628 (NTSC): the same analysis on its offsets, once SPS 627's patches work.
