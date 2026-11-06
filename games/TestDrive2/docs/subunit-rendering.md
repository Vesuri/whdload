# Sub-unit rendering (duel v1)

Enhanced framerate (`CUSTOM2` nonzero) projects the road and cars at fractional positions in
both views and smooths sideways motion and hill crests. `CUSTOM2=0` keeps original rendering.
The optional hooks (nine calls and the walker branch) patch duel v1 only. Code:
`src/render.s`. The original renderer is described in [game.md](game.md).

## Road and first-segment integration

The frame camera distance is the 16.16 long at -13394(a4), with fraction F at
-13392. Use unsigned Q15 weight F>>1 for 68000 signed multiplies. The immutable
height, lateral and width tables supply scale fields 18/22/26/48 (main) and
20/24/28/50 (mirror) in each 52-byte row. Main rows 1..43 interpolate towards
the preceding table entry; mirror rows 1..22 towards the next. Both row-0
near planes and mirror row 23 remain fixed. Width×162 supplies the car scale.
Row field 46 is 0..43; sprite size indices remain unchanged.

Renderer-only heading/slope/height/lateral seeds account for the camera's
fraction of the first segment before the original complete-segment walker.
Both views use the attributes of camera.high+1. Angle fractions round to
nearest; position fractions round down. Angles are 8.8. Heading and slope use the
interpolated table described below. Even a straight segment needs the lateral
correction when the camera heading is nonzero. F=0 bypasses seed correction.

The scanline table has 117 entries of 16 bytes and ends immediately before
row 0. Captured projected rows stay inside it in both views.

## Cars

Both traffic lists move with separate 16.16 origins. Their fractions are
latched while the original frame's Forbid protects list construction.
Opponent and active police use separate frame snapshots. Ordinary car x/y
projection adds the car fraction between the matched row and its neighbour:
main +52 bytes, mirror -52. Road rows already incorporate F, so subtracting
F again would be wrong. The fixed near plane uses signed relative fractions.
Segment matching, painter order, culling, HUD and sprite LOD stay unchanged.

## Sideways motion

The segment loop at duel:0b312..0b444 updates raw heading (-13390(a4), 8.8)
and lateral position (-13386, 16.16) only when crossing a road segment. Heading
gains four times the curve plus half the steering; lateral position subtracts
the simulation sine of heading times 144. Lane changes and recovery can also
change lateral position within a segment.

The frame latch at 06474 writes interpolated heading and lateral values to
the view-only snapshots -13388 and -13382. Positive advances retain history,
including advances across several segments; initialisation, backward motion and
course wraps reset it. Within-segment heading changes shift both endpoints.
Lateral smoothing delays only the sine-driven crossing displacement: it derives
the previous position from the current raw position plus that displacement.
AI lane changes and recovery therefore pass through immediately. Interpolating
all observed lateral changes caused the demo lane-change wobble.

At low speed the heading/mountain interpolation has a one-segment display delay.
At speed, a rendered frame can cross several segments, so heading and mountains
interpolate between the last observed samples. Lateral correction uses only one
crossing. These changes affect drawing snapshots, not simulation state. The
low-speed delay is an accepted tradeoff (user decision).

The original draws the mountains from the integer curve sum -13398 minus heading's
high byte at 08c90, in four-pixel steps. The sum is updated at 072b8 via 08898; -17234
identifies its last segment. `render_subunit_curve_sum` aligns it to the frame
camera when they differ by one segment. The latch interpolates the combined
curve-sum-minus-heading offset; the 08c90 hook rounds it to pixels. Aligning the
two inputs removes their opposing timing steps.

The road walker and all four seed lookups interpolate the table at -26166
using the full 8.8 angle, for heading (sideways) and slope (hills). Index 127
clamps to its own entry. Integer angles (flat road, straight heading) read the
table directly. Fractional angles use an exact 1024-entry cache of full angle
keys and signed results in 4 KiB of private slave memory. Changing the table
pointer invalidates it, including bucket 1023; negative fractions, collisions,
rebinding and the walker hook have VERIFY fixtures.

One walker hook, `render_subunit_road_angles` (PL_PS 073ec plus PL_S 073f2 to
0742a), replaces the original span: curve accumulation, slope lookup, height
accumulation and row y, and heading lookup. It reproduces the original order
of side effects (the curve accumulator is independent of the slope work) and
returns the heading table value in d0 with a1 = the table, as at 0742a. One
call per row, with no NOP padding, pays for the second lookup: the slope's
fractional path is inline. The VERIFY zero oracle (CUSTOM5 bit 3) selects the
original high-byte reads.

The slope accumulator -14932 gains each segment's slope byte in 1/256 index
units, like the heading accumulator. Reading only its high byte, as the original
does, makes the road profile a chain of straight pieces whose joints move with the
camera, so far rows and the horizon jump vertically on crests.

To stay within the A500 budget, immutable scale tables are converted once per
view/source pointer into 43 main and 22 mirror gradient/base records. Equal Q15
fractions reuse the previous coefficients; reset/source changes invalidate that
reuse. Fixed coefficient rows are unrolled with the original three signed
multiplies. A generated 0..300 lookup gives exactly width times 162. It contains
mathematical constants, not game data. Road geometry and seeds still run each view.

## Cost budget

The sub-unit patch may cost at most 3% of A500 cycles. `tools/subunit_cost.py` measures it in
a normal-build 100-field A500 window (see [testing.md](testing.md)); its total includes the 16
original walker instructions per row that the walker hook reimplements, 249 cycles per row,
which are subtracted to get the patch's own cost. Current figures:

| Window | Rows | Tool total | Patch cost |
|---|---:|---:|---:|
| Initial (race anchor) | 952 | 3.615% | 1.947% |
| Moving, after 1 000 fields (flat) | 748 | 4.010% | 2.699% |
| Hill crest, after 640 fields | 704 | 4.136% | 2.902% |

What keeps it within budget: the exact tangent cache, gradient records converted once per
view/source pointer, the generated width×162 lookup, unrolled coefficient rows, reuse of
coefficients for equal fractions, and the walker hook's inline paths. An uncached first
version cost 4.6%.

Measured frame rates are unchanged by the sub-unit work: A500 7.1 fps, A1200 16.7 fps,
68030/25 MHz 25.0 fps in the first-race window.

## Checks

- **Zero oracle.** VERIFY `CUSTOM5=8` forces all fractions to zero and initialises both
  scanline buffers before each view, in both arms (`CUSTOM2=0` and `CUSTOM2=1`, both with
  `CUSTOM3=1`). Completed views with identical camera, heading and lane inputs must match in
  every row byte and all 117×16 scanline bytes (A500: 24 480 source-scale words, 60 matched
  frames per view). Unused scanline bytes otherwise keep history from different render
  cadences, and interrupted VBL dumps are not completed rows.
- **Disabled bytes.** With `CUSTOM2=0`, all 77 optional ranges (10 of them sub-unit) keep the
  original instructions.
- **Geometry oracle.** `tools/subunit_geometry.py` first reproduces original completed rows,
  then checks candidate rows; held-input world-boundary jumps drop from 13/4 px (main/mirror)
  to at most 1/0 px. `subunit_report.py --check-cars` checks opponent and traffic draw
  coordinates against fractional projection.
- **Sideways and hills.** `tools/sideways_report.py` counts per-frame steps and reversals of
  the mountains, drawn heading and drawn lane over matched field prefixes. Reference (A1200
  demo, 300 views): mountains at most 2 px per frame with no reversals; drawn and raw lateral
  agree, at most 20 units per frame; on the first crest the horizon moves at most 5 px per
  frame (8 px in the original, as single-frame jumps).
- **Recovery.** A forced-damage capture (`CUSTOM5=3`) must keep raw lateral position in every
  recovery view.

A natural police chase has never been captured; the police car's separate latched position
is implemented but only covered by unit checks.
