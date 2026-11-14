# Open work

`src/StarWars_WHD.s` is StingRay's v2.00 source with three build fixes
(`development.md`). On top of it:

- The timing fix (StingRay's) and `src/StarWarsFixes.s`, the fast-CPU drawing and sound
  fixes: always on, as bug fixes (`internals.md`, "Display and game time", "Fast-CPU
  fixes").
- `src/StarWarsSmooth.s`: CUSTOM2, "Enhanced framerate": interpolated frames at 50 a
  second in the game and the attract loops, with the game at its own 16.7 updates a second
  (`internals.md`, "Enhanced framerate"). It replaces v2.00's CUSTOM2 "Disable Timing
  Fix", which ran the game too fast. Machines too slow for it (a500, a1200) fall back to
  the default's drawing.
- `src/StarWarsProbe.s`: the VERIFY-only work timer.

`release/slaves.sha256` records this build. With CUSTOM2 off the patched code is that of
the fixes alone (`internals.md`, the end of "Enhanced framerate").

## Next

- Play-test enhanced framerate through all three phases on a1200-030 and a1200-060: the
  surface's dots, towers and bases and the trench's walls and ribs are keyed by identity
  now (`internals.md`, "Towers and bases", "Ground dots", "Trench walls and ribs"); other
  ops still pair by draw order, so look for the same kind of jump wherever a loop's
  objects come and go (space stars, the trench's fireballs and towers), at the HUD strip
  and at the pause key. `tools/starwars.py recdump` and `tmp/scripts/paireval.py` measure a scene's pairs.
- The Obi-Wan text and the flight instructions scroll by plane copies, which move per
  tick in enhanced framerate: interpolate the copy's position.
- Cheaper frames: a1200-fast draws about 1.7 frames a tick (frames 380-540 lines), and
  a1200-030 only two of the wave select's three (frames about 330 lines). The replayed
  CPU clear $1c08 costs about 57 lines on a1200-030 (the zoom stayed smooth without it);
  clearing only the rows the screen's last frame drew, or pairing only when the
  recording changed, would help. The retry from direct mode uses the last smooth
  frame-time average, which direct ticks do not update.
- The ReadMe for 3.0b (the slave info says "Version 3.0b (13.11.2026)" and "Enhanced by
  Vesuri"; Features and History: the fixes, the timing fix always on, CUSTOM2 now
  "Enhanced framerate") before a release; gameplay tests on `SETUPS`.

## Later

- Only SPS 0403 is pinned; the fixes and enhanced framerate are written for it (SPS 2926 has
  other offsets and gets only the timing fix).
