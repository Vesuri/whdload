# Open work

No slave changes yet. `src/` is Codetapper's 1.3 source as upstream has it. It builds
byte-identical to the shipped slave given its date string ([development.md](development.md))
and boots to the attract sequence on the a500 and the a1200. The 50 fps investigation below
is measured; its plan is not started.

Nothing is released from here. A release needs a new slave version with a
`$VER: <name> <version> (dd.mm.yyyy)` string (the packager reads the version and date from
it; 1.3's has neither a name nor, in our build, a date) and a ReadMe entry above
Codetapper's history.

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

### Decisions needed

1. **Which speed is "original".** The A500 does 9.0 fps in the benchmark window (5 or 6
   fields a frame), and less in busier scenes. 1.3's default gives 12.5 fps on a fast
   Amiga, not the labelled 10. Candidates:
   - 10 Hz, a tick every 5 fields, which is the A500's best case and 1.3's `CUSTOM2=5`;
   - the A500's measured average over a whole lap (not yet measured);
   - 1.3's 12.5 Hz.
2. **Latency.** Interpolation shows each tick one tick (100 ms at 10 Hz) late. The forward
   motion can be predicted instead: its next step comes from the speed table and the cycle,
   so it is exact until the speed band changes. Lateral motion depends on input.
3. **Cache policy.** Enable the caches in the slave (instruction cache for chip code; both
   for an ExpMem program), or leave them to WHDLoad's `Cache`/`DCache` options.

### Design

1. **Fixed tick.** Run the race loop's logic (`$153E`) once per tick of N fields (decision 1).
   The drawing runs every field, or every second field where one field is not enough. A
   frame longer than a tick delays the tick, as the original does; catch-up is not needed
   for the 030.
2. **Split the draw path.** The writes to game state in the object and HUD routines
   (`$41E2` and the others in [internals.md](internals.md), "The road and the objects")
   run once per tick. The routines are then pure drawing and can run any number of times.
3. **Presentation pose.** Each drawn frame gets the forward position (phase, sub-phase,
   parity, slice offset) and the lateral position between the last two ticks (or predicted,
   decision 2). Derived from it:
   - the road's row table (`$2352` with finer phase tables: `$7DAA` has 4 phases of 14
     slice heights; finer ones can be generated from the same perspective);
   - the object positions between their slices, at the size of the nearer slice;
   - the lateral skew.
4. **Memory.** The program and the stack go to an optional ExpMem when it is fast memory,
   and COURSES.DAT (allocated as public) too. Copies of the CPU-read graphics (alloc 2 and
   4) can follow. DMA buffers stay in chip. Without fast memory the slave keeps 1.3's
   layout.
5. **The 68000 and chip-only machines** keep 1.3's path, byte for byte where possible.

### Steps

Each ends measured with `tools/bench.py` on the a500, a1200 and a1200-030, with `end.png`
checked.

0. **Harness.** Record the race state per tick with `tools/states.py`. Add a VERIFY switch
   that logs each tick, and a check that two runs give the same tick sequence. Measure the
   A500 over a whole lap (decision 1). Check DMA on the other screens (title, course select,
   name entry, game over) before moving the program out of chip.
1. **Slave skeleton.** A `$VER` with a date, the optional ExpMem, the program in it, the
   cache policy (decision 3), and the gate: a 68020 or better, with the ExpMem in fast
   memory. Done when the gate-off path gives 1.3's benchmark, and the program in fast
   memory reproduces the experiment's 1.34 fields per frame.
2. **Fixed tick, unchanged drawing.** Run the logic every N fields and redraw the
   committed state in between. Done when the ticks match 1.3 at the same tick rate, and the
   draw cost per frame is reported.
3. **Draw-path split** (design 2). Done when drawing twice per tick leaves the state block
   identical.
4. **Presentation pose** (design 3): road first, then objects, then lateral. Contact sheets
   per field around segment crossings and in the top speed band.
5. **Drawing cost** to under one field on the 030. Candidates, each A/B measured:
   - 32-bit long-aligned road writes (about 8,200 word writes a frame now);
   - the HUD digits drawn only when they change, into both buffers;
   - the screen clear by the blitter in parallel with CPU work, or only where the road does
     not overwrite it;
   - the CPU sprite plotter long-aligned, or by the blitter;
   - fast-memory copies of the graphics the CPU reads.
6. **Matrix and release.** a500 and a1200 without fast memory: 1.3's behaviour. a1200-fast,
   a1200-030, 040 and 060: functional and measured. A ReadMe entry and the option, then
   package.

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
