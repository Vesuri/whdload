# Sub-unit rendering (duel v1)

Implemented 2026-10-05. Enhanced framerate (`CUSTOM2=1`, or any nonzero
value) enables fractional road and car projection in both views, together with
fixed-time simulation and blitter priority. `CUSTOM2=0` keeps original rendering.
The optional sub-unit hooks (nine calls and one branch) patch duel v1 only.

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

The frame latch at 06474 now writes interpolated heading and lateral values to
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
crossing. These changes affect drawing snapshots, not simulation state.

Mountains originally used integer curve sum -13398 minus heading's high byte
at 08c90, in four-pixel steps. The sum is updated at 072b8 via 08898; -17234
identifies its last segment. `render_subunit_curve_sum` aligns it to the frame
camera when they differ by one segment. The latch interpolates the combined
curve-sum-minus-heading offset; the 08c90 hook rounds it to pixels. Aligning the
two inputs removes their opposing timing steps.

The road walker and all four seed lookups now interpolate the table at -26166
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
units, like the heading accumulator. Reading only its high byte made the road
profile a chain of straight pieces whose joints moved with the camera, so far
rows and the horizon jumped vertically on crests.

To stay within the A500 budget, immutable scale tables are converted once per
view/source pointer into 43 main and 22 mirror gradient/base records. Equal Q15
fractions reuse the previous coefficients; reset/source changes invalidate that
reuse. Fixed coefficient rows are unrolled with the original three signed
multiplies. A generated 0..300 lookup gives exactly width times 162. It contains
mathematical constants, not game data. Road geometry and seeds still run each view.

## Hill slope validation (2026-10-07)

Normal and VERIFY builds assemble; the audit checks 73 hooks (the walker
branch span included) with zero errors. VERIFY passes 129/129 assertions
(two new: interpolated slope and heading through the walker hook).

A1200 demo, CUSTOM2=1 CUSTOM3=1, 300 completed main views, previous build
against this one (`tmp/slope/demo-head`, `demo-s3`): on the crest, the horizon
moved in single-frame jumps of 6-8 px between 1 px moves; it now moves 2-3 px
per frame. Largest per-frame vertical step: horizon 8 -> 5 px, rows 20/30/43
7/8/8 -> 5 px. One -4/-5 step remains. Sideways results are unchanged
(mountains at most 2 px, no reversals; lateral identical; steering tape
`steer-s3` mountains 1 px, drawn lane at most 4.1 units).

A500 normal 100-field windows (`tmp/slope/cost-*-s3`, `hill-s3`). The tool
figure now includes the 16 original walker instructions per row that the hook
replaces; their cost, measured in the previous build's hill trace, is 249
cycles per row. Patch cost after subtracting them:

| Window | Rows | Tool | Patch | Previous build |
|---|---:|---:|---:|---:|
| Initial | 952 | 3.615% | 1.947% | 2.018% |
| Moving, after 1,000 fields (flat) | 748 | 4.010% | 2.699% | 2.917% |
| Hill crest, after 640 fields | 704 | 4.136% | 2.902% | 2.865% |

The hill window has 503 rows with a fractional slope. Frame periods match the
previous build where comparable (7.08 and 9.40 fields per frame); these
windows hold 9-14 frames and cannot resolve smaller differences.

The A500 zero oracle (`zero4-off/on`, CUSTOM5=8) verifies 24,480 source-scale
words and 60 matched-input frames per view with no row or drawn-line
mismatches. The disabled capture (`disabled3`) passes 129/129 assertions and
retains original bytes in all 77 optional ranges.

## Earlier forward/curve validation

The following results predate sideways smoothing and the consolidated boolean
CUSTOM2 option. The old 3/7 arms differed then; they are identical options now.

That build passed normal/VERIFY assembly and 121 assertions.
CUSTOM5=8 forces fractions to zero and initialises the full scanline buffer
in both comparison arms. Completed views with identical camera/heading/lane
inputs reproduce every row and scanline byte. Interrupted VBL dumps are not
valid completed-row comparisons.

An independent geometry oracle first reproduces original captures, then all
1,198 final candidate view frames. Held-input world-boundary crossing jumps
fall from 13/4 pixels main/mirror to at most 1/0. Actual opponent and both
traffic-direction draw coordinates match fractional projection. Held flat-road
gap fixtures cover integer and fractional car/camera carries. The natural
demo has no qualifying constant-gap episode; natural police pursuit remains
unrecorded. Sprite size still changes discretely.

| Final normal first-race window | CUSTOM2=3 | CUSTOM2=7 |
|---|---:|---:|
| A500-equivalent 68000 | 7.1 FPS | 7.1 FPS |
| Expanded A1200, 68EC020 | 16.7 FPS | 16.7 FPS |
| Expanded A1200 configuration, 68030/25 MHz | 25.0 FPS | 25.0 FPS |

Each arm uses two fresh 100-field fixed-window runs. Full sub-unit code costs
2.796% in the initial A500 window and 2.429% in the moving window, within the
3% budget. All 35 core state variables match enabled/disabled for 6,000 demo
fields on A500/A1200, including recovery and clock pacing, and 1,800 on 68030.
The 68030 also matches same-period A1200 state. All 74 optional patch ranges
retain original bytes with CUSTOM2=0; the 70-hook audit reports zero errors.

See [open-work.md](open-work.md) for capture provenance and detailed results,
[profiling.md](profiling.md) for reproduction and instruments, and
[optimisation-plan.md](optimisation-plan.md) for measured costs. Code is in
`whdload/render.s`; build with `make -C whdload`.

## Sideways validation (2026-10-05)

Normal and VERIFY builds assemble. The instruction/branch audit checks 72 hooks
with zero errors. The current renderer has nine sub-unit ranges; the full
optional patch set has 76. Final regression results are recorded below.

The final normal A1200 demo (`tmp/horiz/ready-demo`, CUSTOM2=1 CUSTOM3=1) captures
300 completed main views. Raw and drawn lateral positions agree throughout;
the maximum step is 20 units, also in frames 225–250. The inherited `new3`
capture reached 25.8612 there (29.2515 over its full 300 frames). The final
mountains move 51 times by at most two pixels, with no direction reversals.
Road x/y match the prior validated arithmetic in all 206 identical-input main
views found between ready-demo and final-demo, across all 44 rows.

| Final normal A500, 100 PAL fields | Helper/call cycles | Total cycles | Cost |
|---|---:|---:|---:|
| Initial (`ready-cost-initial`) | 286,784 | 14,210,190 | 2.018% |
| Moving, after 1,000 fields (`ready-cost-moving`) | 414,468 | 14,210,196 | 2.917% |

Both are below 3%. The initial uncached implementation cost 4.635%; tangent
memoisation alone still cost 3.291% in the moving window. The final gradient,
width-product and unrolled coefficient changes bring that window within budget.
No new FPS comparison was made for sideways smoothing. Earlier FPS results
above belong to the preceding renderer. The user tested the normal build and accepted
the low-speed display delay on 2026-10-05 ("Tested, feels great"). NTSC and a natural police pursuit remain unverified.

The final VERIFY recovery capture (`ready-recovery`, CUSTOM2=1 CUSTOM3=1
CUSTOM5=3) contains 400 completed main views and 1,000 VBL states. It passes
127/127 assertions and one complete 240-field forced-damage recovery. All 45
completed damage views within the state window reproduce raw lateral position.
Over the common steering prefix through field 393 (`oldv` versus ready-recovery),
mountains change from seven moves, five reversals and a four-pixel maximum to
four moves, no reversals and a one-pixel maximum. Drawn heading quarter-units
change from ten moves with maximum 55 to 41 moves with maximum 18. These are
matched field prefixes, not two unrelated demo screenshots.

The A500 zero oracle (ready-zero-a500-off/on, CUSTOM5=8 in both arms) verifies
24,480 source-scale words and 60 matched-input frames per view, with no full-row
or scanline mismatches and no different unused-field history. The disabled
capture (ready-disabled-a500, CUSTOM2=0 CUSTOM3=1 CUSTOM5=16) passes 127/127
assertions and retains original instructions in all 76 optional ranges,
including the nine sub-unit ranges. The A1200 zero oracle (ready-zero-a1200-off/on) also verifies 24,480 words and
84 matched-input frames per view with no row/scanline mismatches or different
unused-field history. The A1200 disabled capture (ready-disabled-a1200) passes 127/127 assertions
and retains original bytes in all 76 ranges, including the nine sub-unit ranges.
