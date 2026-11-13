# Open work

`src/StarWars_WHD.s` is StingRay's v2.00 source with three build fixes
(`development.md`). On top of it:

- The timing fix (StingRay's) and `src/StarWarsFixes.s`, the fast-CPU drawing and sound
  fixes: always on, as bug fixes (`internals.md`, "Display and game time", "Fast-CPU
  fixes").
- `src/StarWarsSmooth.s`: CUSTOM2, "Enhanced framerate": interpolated frames at 50 a
  second in the game and the attract loops, with the game at its own 16.7 updates a second
  (`internals.md`, "Enhanced framerate"). It replaces v2.00's CUSTOM2 "Disable Timing
  Fix", which ran the game too fast. Machines too slow for it (a500, a1200, a1200-fast)
  fall back to the default's drawing.
- `src/StarWarsProbe.s`: the VERIFY-only work timer.

`release/slaves.sha256` records this build. With CUSTOM2 off the patched code is that of
the fixes alone (`internals.md`, the end of "Enhanced framerate").

## Next

- Play-test enhanced framerate through all three phases on a1200-030 and a1200-060: look
  for pairing glitches (short diagonal fragments seen in surface and trench captures, not
  yet confirmed as glitches rather than geometry), at the HUD strip and at the pause key.
- The cannon and cockpit boxes: their masks clear the whole bounding box (the black box
  over the wave select Death Star; `internals.md`, "Limitations"), also with StingRay's
  original slave on an A500. A fix needs masks that cover only the shapes, checked against
  what the boxes also erase.
- The unpaced wave select loop and the title zoom run faster on fast CPUs than on an
  A500 (`internals.md`, "Limitations"): pace them, as bug fixes, if wanted.
- The title recede logo and the crawl text are not interpolated (they are not drawn by
  the recorded primitives).
- a1200-fast (020 with Fast RAM) falls back to direct mode: frames average about 450
  lines. Cheaper frames would help it: the CPU clear $1c08 by the blitter or only over the
  drawn area, pairing only when the recording changed. The retry uses the last smooth
  frame-time average, which direct ticks do not update.
- `$VER` string and the ReadMe (Features and History: the fixes, the timing fix always on,
  CUSTOM2 now "Enhanced framerate") before a release; gameplay tests on `SETUPS`.

## Later

- Only SPS 0403 is pinned; the fixes and enhanced framerate are written for it (SPS 2926 has
  other offsets and gets only the timing fix).
