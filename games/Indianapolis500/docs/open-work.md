# Open work

The current state is in [slave.md](slave.md). These items are open, most important first.

## Check

1. **Real driving and replays with the current `Custom1=1`.** In driving the camera and the
   player's car extrapolate and opponents move exactly by their own rates; the demo and replays
   interpolate. The frame-by-frame checks pass (slave.md "Verification"); the feel needs the
   user's judgement.

## Accept the current build

- Pixel twins: 1,000 frames per demo fixture for the line drawer and the background planes 0/1.
  The span code has 1,000; these have 200.
- Gameplay state: compare the current build against the original over ≥1,010 SOFT ticks, in the
  demo (68000, 68020, max-speed 68030) and in a race. Compare cars, the published camera,
  track/director/mode, BSS hunk 5 and the observed SOFT-store union. The SOFT-store union also
  contains generated visual-object coordinates at `game:1ec0e…1ed27` and `game:2c9b2…`
  (assembled by `game:2c694/2c76a/2c6c0/2c796`). Those need classifying.
- Visual check of the normal build, including view transitions, replays and real driving.
- Gameplay with `DCache` on a chip-only A1200 (the toggle is off there, but caches are on).
- Optional: a real-hardware check, especially of 68040/060 chip timing.

## Release

- StingRay has passed away; no reply will come. Pull request MK1Roxxor/WHDLoad_Patches#2 is
  still open from the Vesuri fork's `indianapolis500` branch (version 3.1b, the history entry, a
  proposed ReadMe entry in the description, a greeting addressed to him).
- This repository now carries the release: `make dist` writes
  `Indianapolis500Enhanced-<version>-<date>.lha` from StingRay's installer archive, whose
  installer sets `CUSTOM1=1` in the game icon (profiling.md "Release"). The changed installer
  branch has not been executed in the Amiga Installer yet; run an installation from the
  original disk and read back the game icon's tooltypes. To decide: what happens to the pull
  request and the final version (3.1 or keep 3.1b).

## Not pursued

- **A faster player simulation** (one step per PAL field, to sample input more often and remove
  the extrapolation overshoot). The user decided against it. The analysis stays in
  [simulation-feasibility.md](simulation-feasibility.md).

## Possible further speed

- The heavy views (directors 200/800) sit at 23–25 fps on a 68030/25. A steady 25 fps needs
  3–4 ms off the worst frames. The remaining cost is blitter throughput on wide textured rows.
- 50 fps in the heavy views would need much less chip-RAM work per frame. The one untested
  structural idea: draw the 3D view into fast RAM and copy it to chip once per frame. Measure the
  copy cost first.
