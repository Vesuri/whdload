# Main-view lateral road continuity (2.0b)

The user reported sideways drift followed by a roughly 16-pixel jump when
holding either road edge or steering. The main renderer's near-plane y=125
cutoff suppresses early lane increments. As camera fraction advances, a
different row becomes the first admitted row, while its lateral anchor stayed
at unit scale. This produces a lane-dependent sawtooth even on a straight road.
It is not a change to blitter fine shifts or bitplane scrolling.

`render_walk_start` arms one main-view correction; `render_row` seeds the first
row below that cutoff before it is rasterised or sampled for traffic. Native
lane increments are 3/16 * lane * S and scale decays by 59637/65536, so the
remaining lateral projection is lane * S * 12288/5899. The helper removes the
unit anchor and substitutes that scale-based value, preserving the curve term.
It uses `sim_ratio` with a private cleared carry. Suppressed near rows, the
mirror, raster code and simulation state are unchanged. C2=0 remains original;
the controlled zero oracle also retains its original arithmetic.

## Cornering correction

The later cornering regression is fixed by retaining the partial curve and
bank span at the near plane, in addition to this lane-anchor correction.
See `corner-jump.md` for the user's pinned video, native before/after frames,
full-phase model, current release checks and the measured cost exception.
The evidence below describes the earlier flat-road correction and its
preserved builds; it did not establish continuity through moving bends.

## Evidence

Everything is local under `tmp/road-shift/`. `road_shift_capture.py` builds an
isolated VERIFY fixture from pinned source: 64 camera phases at lane -180, 0
and +180 on a native straight section. The guest changes draw snapshots and a
private draw-side curve seed only; no host game-memory writes, host accessibility,
or simulation writes. Each run uses its own emulator directory/port and leaves
the user's playing session untouched. Initial captures with native steering
still active are diagnostic; only `flat-*` are the controlled sweeps.

`projection-regression.json` checks 396 native frame dumps against an independent
integer model. At both edges the isolated projection drift falls from 17.147
pixels to below 0.042 pixel; centred-road scanlines are identical. The host model
also exhausts all 65,536 camera fractions at seven signed lanes, including
+/-1000, requiring less than one pixel of fixed-point rounding variation.
This is projection continuity, not a promise to remove all of the original
scanline rounding. The captured candidate differs from the final code only by
removal of a redundant TST after MOVE (which already sets the same flags).

`audit.json` checks all 82 patch ranges and direct incoming branches. Existing
hook boundaries are reused. `units` runs 1,421 renderer and 668 simulation
assertions. `final-cost.json` includes renderer self cycles and the new
out-of-range shared arithmetic helper: 2.9799% over 50 PAL A500 fields after
1,000 fields of native demo, below the 3% gate. This is a finite sample.

`normal-040-on`, `normal-040-off` and `final-040-on` cover native startup,
attract driving and keypad-* return to AmigaDOS at a1200-040. `disabled.json`
verifies all optional patch ranges remain original with C2 off. The final
normal binary is retained with `final-040-on`. The zero oracle compares 40 main
and 30 mirror rows plus scanlines and queues without mismatches (`zero.json`).
`final-downhill` matches all 40 main / 30 mirror rows and all ten traffic
projections against the independent model (`downhill.json`). The earlier
`downhill` launch used an unsigned AmigaDOS numeric option and is diagnostic
only. Hardware testing remains deferred.

Builds and archives stay version 2.0b (13.10.2026). Preserve pre-fix release
packages and the original 1.4/1.5b hardware overlay A/B bundle. Local commits only.
