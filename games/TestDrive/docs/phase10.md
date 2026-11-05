# Phase 10: renderer adaptation (complete; PAL emulator beta)

This report records the retained 1.8b development snapshot. Current 2.0b also
fixes the within-segment lateral discontinuity; see `road-shift.md`. The old
endpoint crossing check below did not cover the whole camera-phase cycle. The preserved phase-9 1.7b baseline and hashes are
in `tmp/phase10/baseline/` and `manifest/phase10-inputs.json`. Final acceptance
is recorded in `tmp/phase10/acceptance.json` and its evidence hash manifest.

## Native representation

Unlike TD2, TD has no 52-byte road-row records or three immutable per-view
projection tables. Its h4:$1A14 walker streams at most 40 forward / 30 rear
segments into the blitter scanline routines. State is a4-relative:

| Field | Meaning |
| --- | --- |
| -22340 long | latched 16.16 camera position |
| -22372 long | latched 16.16 lateral position |
| -22364 long | latched 16.16 heading |
| -29852 word | unsigned projection scale |
| -29850 word | companion decaying scale |
| -29848 long | 16.16 screen y |
| -29844 long | 16.16 screen x |
| -29840 long | 16.16 accumulated curve angle |
| -29836 word | accumulated slope |
| -29834 word | visible bottom/crest clip |
| -29832 word | segment row index |
| -29308 word | first segment remainder, Q15 |
| -28800 word | view selector: 0 forward, -1 rear |

h4:$1114 is the forward pass. h4:$11A2 is the rear-view mirror. Native entry
captures in `tmp/phase10/map-native/` establish clip rectangles x=0..320,
y=0..117 and x=240..320,y=26..43 respectively, on the same five destination
bitplanes. The preceding exploratory `map/forward.txt` was caught mid-mirror;
its filename does NOT establish a forward-pass observation. The corrected
probe waits for each pass entry before the walker breakpoint.

h4:$1172 already uses the camera low word: main scale is
65535 - high16(((-fraction)&65535)*5899); the first span uses
(((-fraction)&65535)>>1), with zero replaced by 1. h4:$1434 decays both scales
by high16(scale*59637). h4:$1456 accumulates fractional projected y, including
first-span weighting. h4:$7DFA accumulates fractional curve, including that
same first-span weighting. Reapplying TD2 camera interpolation would double
an existing correction.

The curve projection export a4-32544 resolves to root:$2108. This is an
already interpolated **sine** table, not TD2's tangent table: values at 0/30/90
degrees are 0/32768/65535. Input is full 16.16; the helper interpolates the
adjacent unsigned entries using the low word. Root:$216C holds the immutable
table, with a duplicate 90-degree endpoint. Cache keys must preserve all
32 input bits, not TD2's 8.8 key.

Traffic projection h4:$1778/$17CC and $189E compares only position high words,
then queues integer screen coordinates with the current row scale. Queue
h4:$3B10 has 200-word x/y/type/scale arrays at a4-28796/-28396/-27996/-27596;
count is -28798. Forward types 25..29 map to snapshot slots 1..5 at -29374;
oncoming types 16..20 map to slots 0..4 at -29350. The first six road rows
have an intentional fixed-scale near-plane policy; do not accidentally remove
it when adding interpolation. Geometry and screen-space clipping need explicit
fixtures before accepting changes.

## Implementation

`render-patches.i` installs only with C2; normal C2=0 keeps original renderer
bytes. The common latch runs after native snapshots while Forbid is held, then
replays Permit and frame preparation. It latches heading/background phases,
checks for nearby traffic and invalidates the exact cache on a new root binding.
`simulation.s` installs the renderer patches on each h4 load and resets heading
history with the race state.

- Main camera weighting remains native except its discontinuous exact-zero
  special case: production C2 uses partial=32767, scale=59636 at fraction zero.
  The lane anchor uses unit scale 65535 independently of first-row scale.
- The mirror prefixes the next camera segment by its fractional span, then
  follows the original decreasing-segment walker. Row-zero slope remains zero.
- Private slope is full 16.16. Blend native crest limits toward the previous
  main / next mirror row with camera fraction. Rows >=16 have constant limit
  40; `audit_render.py` checks the original data-hunk table at $B38. Skip the
  original slope weighting only when descriptor and accumulator are both zero.
- Preserve native integer lane/slope multiplies, adding only missing fractional
  products at terminal updates. Split rounding is at most one 16.16 LSB per row;
  signed vectors and an exhaustive residue check cover it.
- Sample up to 40 private road records per view, and interpolate traffic toward
  the next main / previous mirror row. Do not subtract camera fraction twice.
  Preserve the first-six-row fixed near-car scale and final horizon policy;
  interpolate crest-clipped heights. Metadata is skipped with no nearby traffic.
- Cache sine*80 for the last integer angle; halve for the mirror. Changing
  fractional arguments go directly to the original full-16.16 interpolator.
  This is exact, without rounding the argument or approximating the table.
  The larger full-key candidate had 253 misses / 15 hits in the late moving
  sample and exceeded budget (`cache-diagnostic.json`); it is not retained.
- Interpolate the previous/current observed course heading over one segment,
  wrap at +/-180 degrees, reset on first/backward position and atomically latch
  all four mountain phases. Physics, wind and simulation state are untouched.

## VERIFY controls

- C1 bit 4 disables new projection hooks for same-build comparisons. The common
  latch still executes native preparation and explicitly selected draw fixtures.
- C5 bit 3 clears camera/lateral/heading/traffic low words and selects original
  mirror, slope, backdrop and exact-zero camera arithmetic. This is a controlled
  original-arithmetic zero oracle; production C2 deliberately fixes the native
  exact-zero camera discontinuity and retains slope fractions.
- C5 bit 5 selects isolated draw snapshots: C1 high word is the stage segment,
  C5 high word is camera fraction. Lane/traffic fractions exercise both views;
  native simulation positions are never overwritten.
- C5 bit 6 runs 1,421 renderer assertions once: 91 sine angles x five fractions
  x three width/repeat checks, plus 28 signed products and 28 main anchors.
  Cache hits apply to integer arguments; fractional arguments use native sine.

AmigaDOS /N requires signed decimal arguments. Capture tools serialize values
>=2^31 as signed 32-bit decimal while retaining unsigned option metadata.
GDB register prints use masked low words before host sign extension; `(short)`
formatting produced misleading diagnostic output. No host accessibility or
host-side game-memory writes are used.

## Evidence

`final-zero-off/on` pass the controlled zero oracle for 40 main / 30 mirror
rows, 400-byte scanline arrays and object queues. Both arms use the same slave;
the checker requires all selected snapshot fractions to be zero. `final-units.json`
records 1,421 renderer assertions with no failures, alongside the existing 668.
`final-downhill` exercises a three-quarter camera fraction, negative slopes and
all ten traffic projections; every recorded row and car matches the independent
fixed-width model.

`crossing-fixed.json` matches 39 main / 29 mirror world segments across
495.ffff -> 496.0000 with held lane position. Maximum difference is zero x /
one y pixel in the main view and zero in the mirror. This removes the measured
ten-pixel main-view sideways jump. The capture predates the exact cache and
slope fast paths; its projection formulas and boundary handling are unchanged.
`final-quarter-hill/curve` are retained earlier positive-slope/bend model checks.

`sideways-demo.json` validates 128 mountain outputs over 32 moving frames,
including 16 fractionally corrected frames. Its background implementation is
unchanged in the final build. Maximum draw step is 19 versus 18 integer-reference
pixels: this proves atomic interpolation, not a universal maximum-step reduction
when the camera traverses several units per frame. Road continuity is measured
separately by the held-lane boundary check.

The final moving samples measure 2.875% (`final-cost-demo`, after 1,000 fields,
camera about 265.6) and 2.877% (`integer-cost-late`, after 1,600 fields, camera
about 496.6) conservative A500 self cycles over 50 PAL fields each. Hook costs
and displaced instructions are included. The final `matrix4-*` frame-rate
checks pass. These are sampled scenes, not a universal worst-case bound. Historical `fps-*`, `matrix2-*`
and larger-cache candidates are diagnostic only; `matrix3-*` passed FPS before
the final cache reduction but is superseded for final build acceptance.

Final `matrix4-*` results (C2 simulation enabled in both arms, C1 bit 4 disables
only phase-10 projection; C3=1, C5=17):

| PAL preset | Projection off FPS | Projection on FPS |
| --- | --- | --- |
| A500 | 4.70 / 4.75 | 4.80 / 4.95 |
| A1200/68EC020 | 8.30 / 8.30 | 8.30 / 8.30 |
| A1200/68030 25 MHz | 12.50 / 12.50 | 12.50 / 12.50 |

Each pair uses an identical build and two consecutive 1,000-field windows from
the same player-race anchor. `fps-comparison.json` verifies no loss in either
window, selected gameplay state equality at start and both endpoints, all 668
assertions and option-selected bytes. Counts are nominal-PAL LoadView
publications, not whole-race averages. The 68030 has no CPU-cycle cost claim.

`audit_render.py` checks 82 optional ranges, whole instruction boundaries and
external direct candidates entering bypassed h4:$1184..$11A0 / $14CE..$14EA
(no matches). This word-aligned scan does not prove indirect targets.
`test_render.py` rejects corrupted assertion counts, road coordinates and
scanlines without altering saved captures. `check_disabled.py` checks original
or option-selected hook bytes and resolved helper targets.

## Reproduction and handoff

Source `tools/env.sh` from the game directory and use its Python. Build with
`tools/build.sh` and `VERIFY=1 tools/build.sh`. All outputs stay in `tmp/build/`.
Fresh captures refuse existing output directories or an active server.

- `render_capture.py NAME --c1 SEGMENT_SHIFTED --c5 FRACTION_AND_FLAGS`, then
  `subunit_geometry.py tmp/phase10/NAME/view-0`; `zero_render.py OLD NEW` checks
  the controlled zero pair. `check_render_units.py DUMP` verifies the native suite.
- `render_profile.py NAME --c5 0 --settle 1000|1600`, then `subunit_cost.py CAPTURE`.
- `render_benchmark.py NAME --preset a500|a1200|a1200-030 --c1 16|0 --c5 17`,
  then `check_render.py --prefix matrix4-`. Each arm uses two 1,000-field windows.
- `render_normal_capture.py NAME --preset a1200 --c2 0|1 --fields 400`, then
  `check_disabled.py CAPTURE`. Normal builds contain no VERIFY instruments.
- `sideways_report.py tmp/phase10/sideways-demo/sideways` and
  `subunit_boundary.py BEFORE/view-0 AFTER/view-0` recheck retained geometry.
- `audit_render.py` and the identification tool with
  `--manifest manifest/phase10-identification.sha256 --out tmp/phase10/identification`
  check pinned game/source inputs without overwriting the phase-2 inventory.

`final_render_checks.sh` records the final capture sequence. `accept_render.py`
requires all final reports, rejects mixed builds and preserves slaves/listings
under `tmp/phase10/accepted/`, with `acceptance.json` and an evidence hash manifest.
Both normal C2-off/on builds boot and run 400 fields of attract driving on
A1200; byte checks pass and the C2-on cockpit/road/mirror image was inspected.
Normal .text is 12,148 bytes. Real A1200/68040 stays deferred; NTSC is unvalidated. The preserved 1.4/1.5b hardware A/B pair is
unchanged. Full release regression, option label/icon and packaging are recorded in phase 11.
