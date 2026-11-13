# Phase 11: local release regression

The retained 1.8b development snapshot passes local release regression.
The consolidated release is 2.0b (13.11.2026); see `release-2.0b.md`.
The version names, hashes and paths below describe the immutable regression snapshot. Real A1200/68040 results remain explicitly
deferred; no push or PR is authorized. The original phase-6 hardware A/B pair
remains in `tmp/dist/overlay-cache-ab/`.

## Release contents

The normal and VERIFY builds expose `C2:B:Enhanced framerate;`. The installer's
Normal icon (`TestDrive.inf`) enables `CUSTOM2=1` after its existing `preload`
tooltype; all other icon bytes are retained. Both optional GlowIcons (`TestDrive.glowicon`, `TestDrive.glowicon2`) gain the same
tooltype in the same place. The ReadMe explains how to disable the option and distinguishes
PAL emulator acceptance from hardware and NTSC validation.

`tools/package_release.py` uses the pinned original installer/preinstalled inputs,
replaces the normal slave and ReadMe, updates the intended launch icon and adds
source dependencies. LHa for UNIX writes level-1 LH5 archives. Exact member sets,
unchanged members, changed/added paths and roundtrip bytes are checked. The
packaged Makefile builds both variants byte-identically with the shared SDK.
The SDK is external (documented by packaged BUILDING.txt); no SDK is vendored.
The installer retains its original TD executable; both archives remain local.

Outputs are in `tmp/dist/phase11/`: normal `TestDrive.slave`, installer
`TestDrive-1.8b.lha`, preinstalled `TestDrive_v1.8b_0089.lha`, manifest and checksums.
A package contains no WHDLoad/Kickstart binaries and no VERIFY build.

## Regression reproduction

Build with `tools/build.sh` and `VERIFY=1 tools/build.sh`. From the game directory,
after sourcing `tools/env.sh`:

```
python3 tools/release_simulation_car_matrix.py release
bash tools/release_regression.sh
python3 tools/release_sideways_capture.py sideways
python3 tools/sideways_report.py tmp/phase11/sideways/sideways > tmp/phase11/sideways.json
bash tools/release_matched_matrix.sh
python3 tools/accept_release.py
```

Captures require fresh output names. The phase-11 wrappers preserve the earlier
phase-8/10 evidence. All new output is in `tmp/phase11/`. Emulators run one at a
time; input is debugger-native and telemetry is read-only. The car matrix covers
five cars, two simulation periods and straight/steering tapes (20 arms).
The regression queue covers forced events, same-period cross-CPU and slow drawing,
C2-disabled bytes, controlled VERIFY zero projection, downhill models, normal-build
render costs, two fixed windows per arm and both available WHDLoad runtimes.
The TD2 checklist means oldest/newest *available*: installed 19.2 and 20.0, pinned
in `manifest/runtime-inputs.sha256`; it is not a claim of testing WHDLoad 17.0.

The initial `normal-*` windows are diagnostic only: their native attract loops
selected different cars between arms. The accepted `matched-*` captures wait,
with read-only conditional breakpoints, for demo car 0, stage 3, position 30,
zero speed/gear and no published frames. Each arm has two consecutive 1,000-field
windows. Native RNG and original/fixed-time trajectories can differ afterwards;
these normal-build counts are not an isolated rendering performance comparison.
`projection-*` is the strict same-build/same-simulation comparison, with equal
start/end gameplay state and no FPS loss required in both windows.

## Accepted evidence

`tmp/phase11/acceptance.json` records the complete gate. Its companion manifest
pins evidence, tools and source. `manifest/phase11-inputs.json` records the source
base and input manifests. Normal SHA-256: `8a9bb095e10b1c6b2c2db82ebd93897de6370cd18ba48ad0ce394707b789ca41`.
VERIFY SHA-256: `a858b5c6188ec66594e6c72a651a0e98b2fc638db523c0748219ab2eadb73fad`.

- `release-matrix.json`, `handling-equivalence.json`: all 20 arms pass, matching
  prior handling/timing exactly; 668 native simulation assertions in every arm.
- `events-a500.json`, `events-a1200.json`: one forced crash, +240 penalty,
  one recovery, complete police stop with the retained five-field decision rate.
- `crosscpu-demo.json`, `crosscpu-route.json`, `slow-drawing.json`: gameplay/RNG
  state matches with different drawing rates; demos have nonempty RNG evidence.
- `audit.json`, `identification.json`, `verify-disabled.json`: 82 declarations,
  whole-instruction/direct incoming checks, original bytes when disabled.
- `zero.json`, `render-units.json`, `downhill.json`, `sideways.json`: zero oracle,
  1,421 native assertions, road/traffic model and all 128 mountain outputs pass.
  Max mountain draw step remains 19 pixels vs 18 for integer reference in this
  high-speed sample; no universal maximum-step reduction is claimed.
- `normal-cost-{0,1000,1600}.json`: 50-field A500 renderer samples use
  2.789%, 2.981%, 2.862% self cycles. Simulation budgets pass on the same traces.
- `projection-fps.json`: A500 4.70/4.75 to 4.80/4.95, A1200 8.30/8.35 to
  8.30/8.35, 68030 12.50/12.50 to 12.50/12.50; selected gameplay endpoints match.
- `whd-{19.2,20.0}-{off,on}` and `quit-review.json`: startup, 400-field demo,
  byte gates, exact runtime hashes and native key $5D. All four return images
  match the visually inspected AmigaDOS prompt. No host accessibility/input used.
- `package.log` and `tmp/dist/phase11/manifest.json`: archive membership, unchanged
  original bytes, roundtrip and packaged normal/VERIFY source builds pass.

Matched normal-build windows (nominal PAL FPS):

| PAL preset | C2 off FPS | C2 on FPS |
|---|---:|---:|
| A500 | 4.30 / 4.45 | 4.75 / 4.45 |
| A1200/68EC020 | 8.20 / 8.25 | 8.55 / 8.35 |
| A1200/68030 25 MHz | 11.10 / 11.85 | 12.50 / 12.50 |

The phase-6 1.4/1.5b hardware A/B bundle remains unchanged. Beta status is
retained: hardware/NTSC and publication are not part of completed local acceptance.

