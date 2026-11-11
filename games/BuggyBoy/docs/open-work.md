# Open work

`src/` is Codetapper's 1.3 with the start of 2.0b (`$VER: slave 2.0b (11.11.2026)`): on a
68020 or better the slave enables the caches and, when the ExpMem is fast memory, runs the
program, COURSES.DAT and the stack from it. The race runs its logic on a fixed 12.5 Hz tick
and draws as often as the machine manages, with each frame interpolated between the last
two ticks (`src/Enhanced.s`; [internals.md](internals.md), "2.0b"). The frames between ticks
are the option "Enhanced framerate" (`CUSTOM2`); without it the game draws at 12.5 fps,
and every screen outside the race is locked at 12.5 fps either way (1.3's default). A 68000 or 68010 and
the disk versions run 1.3 unchanged. The 50 fps plan below is at step 4b.

Nothing is released from here. The ReadMe has the 2.0b entry; a release needs the plan
finished.

## 50 fps at the original game speed

Goal: on the a1200-030, draw 50 frames a second while the game runs at its original speed.
Every other machine must run at least as well as before.

### Verdict

- **Running the simulation tick five times as often does not work.** The game has no clock
  but the frame ([internals.md](internals.md), "Frames and time"): everything advances once
  per frame in integer steps, and those steps are coarse.
  - The road phase moves 2 to 8 of the 8 units per segment each frame. The renderer can
    show only 4 phases.
  - At a segment crossing the overshoot is thrown away.
  - Objects jump one depth slice per segment.
  - The timer counts 12 frames.
  - Speed is 8 bands with 8-entry step cycles.

  A 1/5 step would need new tables and constants everywhere, would change the gameplay
  (the discarded overshoot, collisions, the timer), and would still move the picture in
  the same coarse steps, because the renderer has no finer positions.
- **Presentation between ticks is required, and it must be finer than the game's own
  state.** Interpolating the existing variables only repeats their steps. The renderers
  need a continuous forward position (phases between the 4, slices between the 14) and
  a continuous lateral position. The logic stays native.
- **The game logic is cheap.** It takes 0.13 fields per frame on the A500 and 0.01 on the
  030; the road projection (`$2352`) is part of it and could run once per drawn frame.
- **50 fps on the 030 needs drawing work, not only memory and caches.** Drawing one frame
  takes 1.34 fields at best today (program in fast memory, both caches on), against 1 field
  available. **25 fps with smooth motion is within reach without it**: 1.34 fields fits
  in 2, on the stock A1200 with the instruction cache too (1.74).
- **Bottlenecks:**
  - The caches are off: the instruction cache alone doubles the frame rate.
  - Everything is in chip memory, although only the screens, graphics and samples need to be.
  - The drawing is by the CPU, word-wide, into chip: the road writes every row of every
    plane, the objects are CPU-masked sprites, and the whole screen is cleared each frame.
  - The blitter is busy in 5% of the slots.

### Decisions (11.11.2026)

1. **The game runs at 12.5 Hz**: one logic tick every 4 fields, 1.3's default lock on a fast
   Amiga. 10 Hz (1.3's `CUSTOM2=5`, the A500's best case in the benchmark window) was the
   first choice, but the race timer counted down too slowly at it (changed 11.11.2026).
2. **Interpolation**, not prediction: each drawn frame shows a pose between the last two
   ticks, so the picture is one tick (80 ms) behind the logic.
3. **The slave enables the caches** where they apply, instead of leaving them to WHDLoad's
   `Cache`/`DCache` options.

### Design

1. **Fixed tick.** Run the race loop's logic (`$153E`) once per tick of 4 fields.
   The drawing runs every field, or every second field where one field is not enough. A
   frame longer than a tick delays the tick, as the original does; catch-up is not needed
   for the 030.
2. **Draw-path side effects** (done): instead of splitting the routines, a tick frame
   draws the committed state with all its writes, and a frame between ticks saves and
   restores the state around its drawing ([internals.md](internals.md), "The fixed tick").
3. **Presentation pose.** Each drawn frame gets the forward position (phase, sub-phase,
   parity, slice offset) and the lateral position between the last two ticks. Derived from
   it:
   - the road's row table (`$2352` with finer phase tables: `$7DAA` has 4 phases of 14
     slice heights; finer ones can be generated from the same perspective);
   - the object positions between their slices, at the size of the nearer slice;
   - the lateral skew.
4. **Memory** (done in step 1). The program, the stack and COURSES.DAT (allocated as
   public) are in the ExpMem when it is fast memory. Copies of the CPU-read graphics
   (alloc 2 and 4) can follow. DMA buffers stay in chip.
5. **The 68000 and 68010** keep 1.3's path.

### Steps

Each ends measured with `tools/bench.py` on the a500, a1200 and a1200-030, with `end.png`
checked.

0. **Harness.** Record the race state per tick with `tools/states.py`. Add a VERIFY switch
   that logs each tick, and a check that two runs give the same tick sequence. Still open:
   check DMA on the other screens (title, course select, name entry, game over) with the
   program in fast memory; the title, the course select and the race draw correctly. The route
   plays Offroad only: on the course select, joystick directions held 10 to 40 fields
   through the harness did not move the selection (fire works; the game reads port 1,
   `$DFF00C`, edge-detected at `$2502`), so the other four courses are not measured.
1. **Slave skeleton.** Done. Measured in the 200-field window with `CUSTOM2=1`:

   | Machine | fps | Work per frame, median (fields) | Before |
   |---|---:|---:|---|
   | a500 | 9.00 | 5.092 | 5.092, 1.3 |
   | a1200 | 24.00 | 1.742 | 1.744, 1.3 with `CACHE` |
   | a1200-030 | 25.00 | 1.178 | 1.344, the fast-memory experiment |

   The gate is the CPU alone: the stock A1200 gets the instruction cache, and the tick and
   the interpolation once they exist (it draws in 1.74 fields, so about 25 fps). The
   program moves only when the ExpMem is fast memory.
2. **Fixed tick.** Done. The state at each logic step is byte-identical to 1.3's at
   its default lock for 599 ticks of the route on the a1200-030 (`AT=153E tools/states.py`,
   one tick later in the recording); the first, 10 Hz tick matched `CUSTOM2=5` the same way.
3. **Save and restore around frames between ticks.** Done. The VERIFY build finds nothing
   changed after 962 such frames (`tools/verify.py`).
4. **Presentation pose** (design 3).
   - **4a, within the renderers' 4 phases.** Done: forward position (with the segment
     crossing), lateral and horizon interpolated, the projection re-run. On the 030 the
     drawn phase steps every second frame where 1.3 at 10 Hz jumps every frame (measured with the 10 Hz tick), and the
     lateral position moves every frame. Measured, 200-field window, default options:

     | Machine | fps | Logic steps | Work per frame, median (fields) |
     |---|---:|---:|---:|
     | a500 | 9.00 | 35 | 5.092 (1.3: 5.092) |
     | a1200 | 22.25 | 40 | 1.908 |
     | a1200-030 | 25.00 | 40 | 1.287 |

     The pose costs about 0.11 fields on the 030 (1.178 without it).
   - **4b, finer than 4 phases.** Done ([internals.md](internals.md), "Fine positions",
     "The smoothed position"): 64 positions per segment for the road's slices and stripes,
     the curve, the object rows and lanes, the sprites' lift, poles and tall objects; and
     the shown position moved on at the speed band's mean step, tick frames included. Per
     field from the race's start, joystick up held, a1200-030 (64 fields; the nearest pole
     tracked):

     | Build | Fields with the road unchanged | The pole |
     |---|---:|---|
     | `COARSE` (the program's 4 positions) | 43 of 63 | 4 to 6 pixels every 4 fields |
     | fine, `NOSMOOTH` | 18 of 63 | every field at speed; stops for ticks in the low bands |
     | fine and smoothed | 10 of 63 (the buggy still standing) | 1 pixel every 1 or 2 fields from the start |

     At a size change the pole's base stays on the kerb line (one field 1 row above it) and
     its top moves on smoothly. VERIFY: nothing changed after 102 frames between ticks.
     The tick states match 1.3's for 599 ticks outside `$98F8`–`$9915`, the road feature's
     drawing scratch (development.md, "Benchmark"). 200-field window: a1200-030 50.00 fps
     (median 0.853); a1200 23.75 (median 1.853, was 1.770: the second projection and the
     posed tick frames). Still coarse, as in the program: objects placed at an absolute row
     per size (`$399E`, `$39F0`) move only at crossings, and sprites change size there.
   - The menus and the start sequence use 1.3's default lock (12.5 Hz), as the race tick.
5. **Drawing cost** to under one field on the 030. In progress; 200-field window, default
   options, work per frame median (fields):

   | Change | a1200 | a1200-030 |
   |---|---:|---:|
   | after step 4a | 1.908 | 1.287 |
   | the road in fast memory, copied with misaligned longwords | | 1.273 |
   | the copy aligned | | 1.169 |
   | alloc 1 2 bytes later: the screens longword-aligned | 1.865 | 1.085 |
   | the clear's blits queued to the blitter interrupt, run during the road | 1.864 | 0.993 |
   | the sky's blits queued at the frame's start, before the logic and the pose | | 0.988 |
   | of the sky only planes 0 and 2 by the blitter, 1 and 3 by the CPU after the copy (1.3's split) | 1.865 | 0.967 |
   | the masked plotters' and/or merged, the column plotter's source from a fast copy of alloc 2 | 1.768 | 0.846 |

   On the 030 that is 50 fps in the window: all 199 frames in one field, p90 0.927, max
   0.965 (the a1200 24.75 fps; the a500 unchanged at 5.092). The tick states match 1.3's
   for 599 ticks (one tick later in the recording). Next for this step: the margin
   elsewhere (other courses, a full race, more objects on screen, the start sequence) and
   the a1200-fast setup.
   Before the plotters, the 030 measured 40.25 fps, p90 1.038. All
   four sky planes by the CPU measured 0.977, the CPU's two before the copy 0.966. The
   road's copy is slowed while the queue runs: 0.22 fields a frame with all four sky planes
   queued, against 0.11 alone (the blitter fills a word in 2 cycles, the CPU a longword in
   one access). A CPU access to chip costs
   about 60 cycles of the 030 (1.2 µs, several bus slots), so the bus has room the CPU
   cannot use: what was left was to make fewer CPU accesses (before the plotters, per frame
   about 9,600 by the objects, 6,700 by `$448A`, 3,900 by the road copy) or to give
   work to the blitter, which uses free slots at full speed. Candidates:
   - the object plotter (`$3D94`, `$418C`: CPU-masked `and`/`or` on the screen) by the
     blitter, from the graphics already in chip;
   - tried: the clear's two CPU planes by the blitter, each plane's fill overlapped with a
     plane of the road copy. Worse (1.115 against 1.085 on the 030): the copy waited for
     the fills, which share the bus with it;
   - the objects' waits for the blitter, about 0.10 fields a frame on the 030: the blit code
     at `$2D60` (reached from `$41E2` and `$424E`, which the profile charges for it) waits
     before each of its 6 blits (`$2D72`–`$2E7E`). The clear's queue (`_PL_Queue`) could
     take them, but the CPU plotter draws on the same screen in between, so each CPU plot
     would wait for the queue;
   - not the HUD alone: `$448A` draws the HUD text (`$4A70`) and also the player's buggy
     (masked, from alloc 2), and the clear wipes the sky behind the HUD every frame.

   Earlier candidates, each to be A/B measured:
   - 32-bit long-aligned road writes (about 8,200 word writes a frame now);
   - the HUD digits drawn only when they change, into both buffers;
   - the screen clear by the blitter in parallel with CPU work, or only where the road does
     not overwrite it;
   - the CPU sprite plotter long-aligned, or by the blitter;
   - fast-memory copies of the graphics the CPU reads.
6. **Matrix and release.** a500 and a1200 without fast memory: 1.3's behaviour. a1200-fast,
   a1200-030, 040 and 060: functional and measured. A ReadMe entry, then package.
   - **The option** is done: `C2:B:Enhanced framerate` replaced 1.3's frame rate list
     ([internals.md](internals.md), "2.0b"). 200-field window, 12.5 Hz tick: a1200-030 50.00
     fps with it (median 0.855 fields a frame), 12.50 without (4 fields a frame); a1200
     24.75 with it; a500 9.00 (1.3: 9.00).
   - **Steering** is interpolated: the pose took a lateral change over 16 a tick for a jump,
     but steering moves it up to 60, so it moved once a tick. With 128 the road's edge moves
     every field while steering (per-field sheets, `+JOY2_LEFT` in the race).
   - **Matrix** (200-field window, with the 10 Hz tick, before the option existed: the same path as it on).
     All draw the race correctly, with the same game state at field 3000:

     | Setup | fps | Work per frame, median (fields) |
     |---|---:|---:|
     | a3000 | 38.50 | 0.971 (44 of 153 frames over 1) |
     | a1200-fast | 25.00 | 1.302 |
     | a500-020 | 25.00 | 1.566 |
     | a1200-040, a1200-060 | not measured | |

     Open: 1.3 on the a3000, a1200-fast and a500-020 for comparison; the 040 and 060 need a
     frame count without the cycle tracer, which records nothing on them.

## Other candidates

Not started and not measured; each needs its own investigation first.

1. **The trainer option does nothing as configured.** Nothing tests `CUSTOM1`:
   - the DOS version (the installed archive's) never applies `_PL_BugOP_Tr`;
   - the disk versions always apply theirs;
   - `_SetCheat` is never called, so scores are saved with the trainer on.

   See [internals.md](internals.md), "Slave header". This is from reading; confirm it in a run.
2. **The frame-rate option's labels** are one step off (50/N, not 50/(N+1); internals.md,
   "Frame rate control").
3. **Disk versions.** The second Tenstar release lacks the frame-rate patch and its
   trainer. There is no image of any disk version here to test them.
