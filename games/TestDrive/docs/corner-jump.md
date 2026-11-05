# Cornering continuity in 2.0b

The main-view near-plane cutoff at y=125 discarded a partial bend and bank
step whenever its first visible road row changed. The earlier lane-anchor
correction covered straight-road lateral motion, but not this curve seed.
The user's recording is pinned under `tmp/corner-video/`: consecutive distinct
images show the cliff edge moving +32 then -72 recording pixels. Those are
not native-pixel measurements.

`render_curve_seed`, installed only with CUSTOM2 at h4:$7EAA, now seeds the
curve from the fraction of the current height span beyond the cutoff. The
following native h4:$7DFA descriptor update completes that fraction instead
of adding a whole segment. The same fraction contributes the missing bank
movement to the projected x coordinate. Banking is latched with the camera
under the existing Forbid. The last clipped height is private renderer state;
`render_walk_start` initializes it and the clipped path updates it. No
per-visible-row bookkeeping is needed. Simulation, collision state, road
maps and raster shifts are unchanged. Original mode and the VERIFY zero
oracle retain their original seed.

The fraction calculation uses a 24.8 span and a bounded Q15 quotient. Equal
rounded numerator/denominator selects 32767, avoiding a narrow rounding hole
at the cutoff. Large denominators are normalized before DIVU. The sine step
uses the game's interpolator and bounded unsigned products. The helper
preserves registers; the caller does not consume its CCR. The six-byte hook
replaces a complete MOVE; h4:$7EA2 branches to its start, with no direct
interior target in the conservative word-aligned audit. Its tail return
replaces the original MOVE/RTS path. Indirect targets are not statically proven.

## Reproduction and native checks

Evidence lives under `tmp/corner-jump/`. `corner_capture.py NAME LANE SEGMENT`
uses a guest VERIFY draw-only fixture: 94 selected camera fractions, including
the narrow discontinuity around 64881/65536. `CORNER_BANK` pins only private
draw-side banking; `ROAD_SHIFT_SOURCE` selects retained comparison source.
Each run captures 96 frames and all 40 main-view rows, using A1200/68040,
CUSTOM2 and CACHE. Each owns its emulator directory/port and cleans only its
own processes. No debugger game-memory writes or host accessibility is used.
The native demo map is stage 3, not the player's stage-0 map.

`native-before-after.json` compares previous release and final code on a
right bend, lane -180, bank -5. Camera 64880 -> 64881 gives:

| Measurement | Previous release | Corrected |
|---|---:|---:|
| Projected endpoint x jump | +13.674606 pixels | +0.019882 pixels |
| Road scanline 100 jump | +7 pixels | 0 pixels |

The independent integer model matches every x/y/scale/curve value in these
native rows. `geometry-regression.json` also covers the opposite bend/edge/
bank and a hill transition (288 frames / 11,520 rows). The left-bend capture
uses the arithmetic-identical candidate before the final bookkeeping
optimization; right-bend and hill captures use final production source.
The model exhausts all 65,536 fractions in six signed lane/bank/curve/hill
cases. Previous discontinuities reach 13.675 pixels; corrected adjacent
fraction steps stay below 0.026 pixel. This measures projection continuity,
not a promise of constant frame rate or absence of original raster rounding.
Run `tools/check_corner.py` after sourcing `tools/env.sh` to reproduce it.

The early `curve-*`, `corrected-left-bank` and `final-right-bank` runs are
retained diagnostics. In particular, `corrected-left-bank` exposed the Q15
rounding hole and the first `final-right-bank` row probe did not match the
intermediate source layout. Neither is final acceptance evidence.

`audit.json`, `enabled.json` and `disabled.json` check all 88 current patch
ranges. `zero.json` has no mismatches in 40 main / 30 mirror rows, scanlines
and queues. The final `zero-on/end/code.bin` passes all 668 simulation and
1,421 renderer assertions. `release-040-on` and `final-040-off` retain the
exact final normal slave and cover startup, moving attract mode and native
keypad-* return to AmigaDOS, with CACHE. Their screen/quit images were checked.

## Cost and acceptance exception

The original 50-field cost check failed: 3.519% before bookkeeping optimization
and 3.212% after it, including the shared lane helper. The matched longer
comparison requests 200 fields, but the monitor caps the trace at 100; the
report uses the actual 100 captured fields. Both previous and final builds
complete nine main views. Renderer self cycles, hook/displaced instructions,
shared lane helper and the new bank-sine callee use 3.019% for the previous
release and 3.195% for the correction: +0.175 percentage points.

The former 3% finite-sample gate is **not passed** in this window (including
by the previous release under this accounting). This small measured cost is
accepted for the cornering correctness fix, with no view-count loss in the
matched sample. It is not a whole-race performance bound. `corner_cost.py`
writes `cost-comparison.json`, explicitly retaining the failed old threshold;
it does not relabel it as a passing gate. Historical phase-10/11 and flat-road
cost samples remain historical evidence, not current universal claims.

## Release

Version remains 2.0b (13.10.2026). Current normal slave is
`tmp/dist/2.0b/TestDrive.slave`; exact checksums are in its manifest and SHA256SUMS.
Previous packages are preserved under `tmp/dist/2.0b-before-corner-fix/` and
`tmp/release-2.0b/package-before-corner-fix/`. The overlay-only real-hardware
1.4/1.5b A/B bundle is untouched. Real A1200/68040 testing remains deferred,
NTSC unvalidated, and no changes are pushed or published.

Current cornering fix: local commit `9f17952`. Normal slave SHA-256:
`6987a32ba7854629b136428650fa40620d7eccfe29539872d180d5c21ad1b30f`.
