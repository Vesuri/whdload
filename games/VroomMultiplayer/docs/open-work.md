# Open work

Set up from Mr.Larmer's and CFou's v1.6 slave (the import builds byte-identically to it).
Vroom's fixes for CPU caches and fast CPUs are in (`docs/internals.md`, "Fixes" and
"Self-modifying code"), with the original Vroom slave's blitter waits; the v1.6 slave
crashes in the first demo race on the a1200-040 and a1200-060 with `CACHE`, the new one runs
there, on the a500 and the a1200, and under SNOOP. v1 only: v2 (NTSC) is not among the inputs.
With Enhanced framerate (`CUSTOM1=1`, 68020 and up) the race runs on a fixed 16.7 Hz tick
(`internals.md`, "Enhanced framerate"): Vroom's phase C, and the blitter starts the game
waits after itself no longer wait, AGA fetches the screens 64 bits wide, and the CPU fills the
ground while the blitter draws the sky.

## Next

1. Untested: a race to its end and a second race (Vroom's reload over its program came
   there), link play, the highscore save; v2.
2. The rest of Vroom's Enhanced framerate (games/Vroom `docs/open-work.md`, phases D and E):
   the stack and the race block in fast memory, and the frames between ticks (the
   snapshot holds both players' state; each view mixes its own).
3. A release: a dated `$VER`, a ReadMe entry above CFou's.
