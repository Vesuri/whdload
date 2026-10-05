# Sub-unit rendering (duel v1)

Implemented 2026-10-05. CUSTOM2 bit 2 enables fractional road and car projection
in the main view and mirror. Use CUSTOM2=7 with fixed-time simulation and the
rendering-speed option; CUSTOM2=4 enables this renderer with original physics.
The seven optional slave hooks patch duel v1 only.

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
nearest; position fractions round down. Angles are 8.8 and the sine lookup
reads their signed high byte. Even a straight segment needs the lateral
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

## Validation

Normal and VERIFY builds pass. The VERIFY build has 121 assertions.
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
