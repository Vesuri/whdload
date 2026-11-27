# Open work

Set up from Mr.Larmer's and CFou's v1.6 slave (the import builds byte-identically to it).
Vroom's fixes for CPU caches and fast CPUs are in (`docs/internals.md`, "Fixes" and
"Self-modifying code"), with the original Vroom slave's blitter waits; the v1.6 slave
crashes in the first demo race on the a1200-040 and a1200-060 with `CACHE`, the new one runs
there, on the a500 and the a1200, and under SNOOP. v1 only: v2 (NTSC) is not among the inputs.
With Enhanced framerate (`CUSTOM1=1`, 68020 and up) the race runs on a fixed 16.7 Hz tick
(`internals.md`, "Enhanced framerate"): Vroom's phase C, and the blitter starts the game
waits after itself no longer wait, AGA fetches the screens 64 bits wide, the CPU fills the
ground while the blitter draws the sky, frames are drawn between the ticks where they pay
(Vroom's phase D), and with fast memory the stack and the race block run there (phase E:
`bench 300` two views 36.95 fps on the a1200-040 and 39.37 on the a1200-030, one view 50.17
on both, against 16.5-16.7).

## Next

1. Untested: link play, the highscore save; v2.
2. Vroom's mixing of the crash's flying wheel in the frames between ticks ($E0C4-$E131
   here, a table of 8-byte steps) is not ported.
3. A release: a dated `$VER`, a ReadMe entry above CFou's.
