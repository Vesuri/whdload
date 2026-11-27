# Open work

Set up from Mr.Larmer's and CFou's v1.6 slave (the import builds byte-identically to it).
Vroom's fixes for CPU caches and fast CPUs are in (`docs/internals.md`, "Fixes" and
"Self-modifying code"), with the original Vroom slave's blitter waits; the v1.6 slave
crashes in the first demo race on the a1200-040 and a1200-060 with `CACHE`, the new one runs
there, on the a500 and the a1200, and under SNOOP. v1 only: v2 (NTSC) is not among the inputs.

## Next

1. Untested: a race to its end and a second race (Vroom's reload over its program came
   there), link play, the highscore save; v2.
2. A two-view race on the a1200-040: does a frame draw into the screen still shown (its
   frame end waits for the beam only past the top view, `internals.md`, "Fixes")?
3. Enhanced framerate (Vroom's `src/enhanced.i`): the race loop and the swap are rebuilt
   here around two views, so it is a new design on Vroom's, not a port.
4. A release: a dated `$VER`, a ReadMe entry above CFou's.
