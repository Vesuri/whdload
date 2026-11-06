# Development

## Active performance work

The experimental launcher selects **15 Hz (N=3) for 68000/68010 and
60 Hz (N=12) for 68020+**, without interpolation. Selection resolves `AMIGA_SETUP` first, then uses the launcher's
`CPU` setting, defaulting to 68000, and builds a separate slave for each path.
Each build keeps one fixed rate and scales movement and clocks to real time.
Input history supplies each tick's recorded controls; native modal input is live.
Selected-rate checks pass. The normal loader remains unchanged.

```sh
. ../../common/env.sh
make slave                         # both playable variants
make play60                             # default A500, 15 Hz
make play60 SIM68000_SUBSTEPS=4          # A500 playtest at 20 Hz
make play60 SETUP=a1200-fast             # 60 Hz
make play60 SETUP=a1200-060              # 60 Hz, fast end
```

The `Stellar7-Sim68000` variant has default N=3; `Stellar7-Sim60` has default N=12. `SIM68000_SUBSTEPS=4` selects N=4 for
the former. Named machine presets take precedence over an explicit `CPU`,
matching the shared launcher. `tools/test_play60_launcher.py` checks selection
without booting, including contradictory CPU settings and invalid presets.
Explicit `VASM_EXTRA=-DS60_SUBSTEPS=N` still selects diagnostic
rates for the latter. For actual hardware select the appropriate slave file;
there is no runtime CPU dispatch or rate switching inside a slave. The source
and matrix-driver default remain N=12, so use `--substeps 3` for A500 matrix runs.

The stationary-star experiment is not retained: its selected-rate presentation
gains were below the retention threshold. The ordinary star simulation remains
unchanged. Rate-selection evidence is under `tmp/optimize60`; current rendering
optimization evidence is under `tmp/render60`; buffer-reuse correction and
current validation evidence are under `tmp/fast60/corrected`. The normal loader
remains byte-identical.

## Installer archive

Run `make dist` in this directory (or `make dist GAME=Stellar7` at the repository root;
`game.sh` hands it to `tools/package_release.py`). It forces fresh non-VERIFY builds,
then creates `dist/Stellar7Enhanced-<version>-<YYYYMMDD>.lha` at the repository root
with an adjacent `.sha256`. The version and date come from the release slaves' `$VER`
strings (`$VER: <installed name> 2.0b (05.11.2026)`, each named as the installer ships it:
`Stellar7.slave`, `Stellar7-Sim68000.Slave`, `Stellar7-Sim60.Slave`); all three must agree.
The string ends the code hunk, so it is the only byte change from the builds the evidence
in this document was recorded with. The 2.0b label and date are provisional: nothing is
released until open-work step 11, which sets them.

Packaging starts with a fresh extraction of `tmp/archives/Stellar7.lha`. It replaces the
normal slave, ReadMe (its `Short:` line and title read "Stellar 7 Enhanced", with a
version 2.0b history entry above Psygore's) and Install-Stellar7 script, adds the two CPU-specific
simulation slaves, and preserves all eleven other original members exactly.
The installer targets English NTSC disks and offers 15 Hz for 68000/68010,
60 Hz for 68020+, or original timing through the reconstructed development
loader. Fixed-rate installation sets the selected slave and CUSTOM1=1 in the
installed game icon. Original destination handling and icon choices remain.
Game data, Kickstarts and WHDLoad itself are not bundled.

The packager uses LHa level-1 headers, tests archive integrity, extracts it again
and compares every member byte-for-byte with staging. It rejects VERIFY menu
options, checks both simulation labels and statically validates Installer
expression balance and procedure references. The changed Installer choice UI
has not been exercised under Amiga Installer; these checks establish package
contents, not end-to-end installation. Temporary extraction drawers are removed
automatically. The final archive, checksum and small build log (`tmp/dist-build.log`) remain.

## Scratch retention

Raw traces, memory dumps, save states and the assembler listings copied beside
captures are pruned once their reports are written, including those behind
current `tmp/fast60/corrected` and `tmp/release60` evidence. Reports, scripts,
built slaves and measurement summaries remain available. Re-running a checker
that reads a pruned `trace.bin`, `chip.bin`, `code.bin` or `.lst` requires a fresh
build and capture. Installed game files and build references are retained.
Local deletion inventories are `tmp/cleanup-manifest.json`,
`tmp/cleanup-obsolete-dumps.json`, `tmp/cleanup-raw-dumps.json` and
`tmp/cleanup-listings.json`.

Keep a raw trace or capture listing only while its finding is still being
analysed. Once its report is written, keep the report and reproduction settings
and delete the trace, dumps and listing.

## Release playtest still required

Automated captures do not establish physical controls, audible output or
acceptable gameplay pace. Use normal-speed launches with sound and real input,
one at a time, after debugger captures have stopped. From a fresh shell:

```sh
. ../../common/env.sh
AMIGA_SETUP=a500 NTSC=1 DEBUG=0 WARP=0 SOUND=1 SILENT=0 \
  WINDOW=front JOY0=mouse JOY1=keyboard WHD_ARGS='' make run SLAVE=original
AMIGA_SETUP=a500 NTSC=1 DEBUG=0 WARP=0 SOUND=1 SILENT=0 \
  WINDOW=front JOY0=mouse JOY1=keyboard make play60
AMIGA_SETUP=a1200-fast NTSC=1 DEBUG=0 WARP=0 SOUND=1 SILENT=0 \
  WINDOW=front JOY0=mouse JOY1=keyboard make play60
```

The first launch uses the installed original slave as the pace/loader reference.
The next two use the selected 15 Hz and 60 Hz conversion builds. Do not add
CUSTOM3/CUSTOM5, VERIFY pilots or emulator warp to these observations. Keep the
chosen physical device and native Mouse/Joystick preferences consistent;
record a real joystick mapping if testing that instead of keyboard emulation.
Original timing depends on presentation speed, so comparing native fast-CPU
pace alone does not establish the intended real-time conversion pace.

For each conversion path, record the machine preset, slave identity, device,
preferences and actual observations for:

- Steering, release/braking, firing and short taps during busy combat; delayed
  responses or repeated actions after a catch-up burst.
- SOL traversal and combat pace against the original A500 reference; power
  duration, jump/landing and enemy movement, without using emulator warp.
- Music and effects while firing, selecting powers, taking damage and destroying
  a mine; Music/Sounds off and on, and audio after menus or Continue.
- Viewport/cockpit stability during turns, damage and power changes; distinguish
  native hit flashes from repeated whole-buffer flashing.
- A later full encounter, natural death and Continue/No, recording the reached
  level, outcome and any control or sound defect rather than just elapsed time.

Keep screenshots, recordings and raw notes in `tmp/`. Reconcile confirmed
findings into internals and open-work; do not turn unchecked items into a pass.
The current release decision is to keep SIM60 experimental and the normal
loader unchanged until these observations and the remaining encounter checks
support release.

## Rendering validation

Both playable builds enable `BUFFER_REUSE=1`, `RENDER_NEW_TICK=1` and
`RETICLE_CLOCK=1`. `BUFFER_REUSE` keeps simulation polling while the native
post-presentation field saved at `-22(a5)` still equals the current field.
Drawing resumes after the field advances, allowing the display handoff to
finish before reusing the old bitmap. This adds no interpolation and does not defer owed simulation updates.
`BUFFER_REUSE=0` is an unsafe diagnostic reference, not a playable setting.
`sim68000` additionally enables `POLYGON_BLIT_IRQ=1`, which marks the 68000
target and defaults `BLIT_IRQ_IDLE=1` (BLIT masked while Kickstart's blit queue is
idle, superseding the polygon-only wrapper) and `SOUND_FAST=1` (the exact sound-timer
channel pass); the `sim60` source defaults are zero. The matrix driver matches this CPU policy for non-native 68000 cells,
including PAL; explicit route flags can select the reference arm.
For direct VERIFY captures, add `-DPOLYGON_BLIT_IRQ=1 -DS60_SUBSTEPS=3`
when testing the playable 68000 path. `-DBLIT_IRQ_IDLE=0 -DSOUND_FAST=0` with it
reproduces the step 5 68000 slave (polygon wrapper, native sound pass). The all-off
diagnostic definitions
`-DBUFFER_REUSE=0 -DRENDER_NEW_TICK=0 -DRETICLE_CLOCK=0 -DPOLYGON_BLIT_IRQ=0` reproduce the
preceding input-history N=12 release/VERIFY bytes.

```sh
. ../../common/env.sh
tools/rate_matrix.sh tmp/render-check --substeps 3 --machines a500-1.5m --routes type10-heavy sol boss
tools/rate_matrix.sh tmp/render-stock --substeps 12 --machines a1200-fast --routes type10-heavy
WHD_ARGS='CUSTOM1=1 CUSTOM3=1' \
VERIFY_FLAGS='-DSIM60=1 -DS60_SUBSTEPS=3 -DPOLYGON_BLIT_IRQ=1 -DRETICLE_TEST=100 -L tmp/reticle.lst' \
python3 tools/fixed_window.py tmp/reticle --tick 101 --state-only --fields 1
cp tmp/reticle/slave.slave tmp/reticle.slave
python3 tools/reticle_state.py tmp/reticle --listing tmp/reticle.lst
```

Retain exact binary/listing pairs. Repeat the reticle fixture at N=12 on
68020+, omitting the polygon flag. The VERIFY-only `RETICLE_BAD_RENDER=1`
negative must fail; neither fixture is present in release builds.
Use `simulation_state.py --projection --presentation` for matched-tick state;
this now includes the native target-reticle flag as well as HUD state.

For a `FRAME_TEST` held-render capture, `display_dma.py CAPTURE --listing LISTING`
compares all settled fields' fetched bitplane words, beam positions, palette
and display controls. It accepts bounded native viewport shake, including equal
fine-scroll nibbles, and rejects unsupported modes. `polygon_irq_trace.py`
with the same arguments checks ownership, masking/restoration and caller
preservation when the polygon wrapper is compiled. Capture at most 100 Barto
fields per window. Performance uses field/counter intervals, not screenshot
counts or a single held frame. Complete-call CPU costs exclude interrupts and
boundary partials; inclusive helper costs must not be summed.

Polygon, reticle and redundant-draw evidence is in `tmp/render60`: the
throughput/reference matrices, `reticle-frames`, `reticle-fixtures`, `final-cross`,
`final-input`, `final-lifecycle-n3`, `final-builds` and both `play60-smoke-*`.
Run only one capture at a time with the shared project lock. Fast-CPU timing diagnostics are under `tmp/fast60`; current corrected-build
measurements and regressions are under `tmp/fast60/corrected`. The corrected matrix, scanout, extended combat, input, delayed-draw and lifecycle
checks and both actual launcher smoke tests pass. Current evidence includes
`cross/validation.json`, both `lifecycle-n*/validation.json` reports and both
`play60-smoke-*/validation.json` reports. Earlier rendering checks alone do not
validate the buffer guard.

## Input-history validation

Use `HISTORY_TEST=1` without CUSTOM3: its device samples change at active fields
20,40,60,80,100,120,140,160. The native gameplay readers must consume them at
NTSC ticks 21,41,61,81,101,121,141,161 at N=12, or
6,11,16,21,26,31,36,41 at N=3, irrespective of drawing. CUSTOM3's older
pilot is indexed by completed ticks and cannot establish this property.
`HISTORY_QUEUE_TEST=1` adds private native-reference assertions, including
future-key filtering, LIFO order, pressure, modifiers, register independence,
all electrical joystick directions and button states. It restores its state.

Run one capture at a time, with a fresh prefix. Automated serial runners use
`tmp/rate-matrix.lock`:

```sh
. ../../common/env.sh
WHD_ARGS='CUSTOM1=1' \
VERIFY_FLAGS='-DSIM60=1 -DHISTORY_TEST=1 -DHISTORY_QUEUE_TEST=1 -L tmp/input-edge.lst' \
python3 tools/fixed_window.py tmp/input-edge --tick 200 --tick-checkpoints 220 --state-only --fields 1
cp tmp/input-edge/slave.slave tmp/input-edge.slave
python3 tools/input_history_state.py tmp/input-edge/checkpoints/220 --fixture
python3 tools/audit_hooks.py tmp/input-edge.lst
```

Repeat with `S60_SUBSTEPS=3` for the 68000 path, `SLOW_DRAW=20`, the usual CPU/memory configurations and PAL clock
compatibility. Retain exact listings and slaves; `audit_hooks.installed` checks
real reader hooks and explicitly selected CUSTOM3 fixture overrides.
Compare tick 200 and 220 with `simulation_state.py --projection --presentation`.
Only deferred projection scratch may differ. `input_history_state.py` also
checks recorded-field identity and input/simulation clock accounting at
completed-tick boundaries.

`PAUSE_TEST=100 PAUSE_FIELDS=600 SLOW_DRAW=20` exercises a long real native pause.
Capture ticks 100,101,200,220. The VERIFY `PH60` record contains independent
native dialog entry/return fields; supply their difference to `pause_state.py`,
not just PAUSE_FIELDS, since native dialog cleanup also takes time.
`S60_HISTORY_COUNT=16 SLOW_DRAW=80 HISTORY_TEST=1` deliberately exhausts history:
require a nonzero missing-sample count and continued owed ticks. It must fail
the ordinary exact-input fixture gate. The release default is 256 fields.
`HISTORY_LIVE_TEST=1` is a negative control that consumes the newest sample;
the delayed-render fixture must reject it.

The field fixture reports event-to-input-consumption and first subsequent
render-completion fields. Render completion is not a scanout or physical-input
measurement. Evidence and retained serial runners are under `tmp/input-history`.
Normal and playable release builds are restored after validation.

## Reproducing the performance matrix

Use fresh prefixes and one capture at a time:

```sh
. ../../common/env.sh
tools/rate_matrix.sh tmp/current60/matrix
python3 tools/rate_matrix_report.py tmp/current60/matrix
tools/rate_matrix.sh tmp/current60/native-combat --routes native-type10-early native-type10-late native-boss
python3 tools/rate_matrix_report.py tmp/current60/native-combat --routes native-type10-early native-type10-late native-boss
tools/rate_matrix.sh tmp/current60/heavy --machines a500-1.5m --routes type10-heavy
python3 tools/rate_matrix_report.py tmp/current60/heavy --partial --routes type10-heavy
```

The heavy report intentionally requests only A500. Main/native-combat reports
require all three machines. Successful fresh captures retain the emulator's
accepted settings separately from requested metadata. The initial two restored
A500 cells predate that logging addition; the remaining A500 cells confirm its
configuration. Chip and slow memory core units are 512 KB and 256 KB; fast
memory units are 1024 KB. Observed Exec frequency is checked during capture.
Cross-check the supplementary log against that observed clock and requested
settings; PAL may omit the core `ntsc` option while logging `ntsc_mode = 0`.

At the N=12 default, the delayed-render regression uses SLOW_DRAW=20 on 68020
with 2 MB chip/4 MB fast/SLOW_KB=0. Use the matrix route fixtures and unscaled
endpoints (600→1500, 1800→2400, 4500→5400, 3500→4100). Death and exit tests
use DEATH_TEST=200 or LEVEL_TEST=200 LEVEL_LAST=6; add DEATH_DECLINE=1 or
LEVEL_EARLY=1 for alternate paths. Capture restarted ticks 600→1500, and level
six for exits. Compare both endpoints with `simulation_state.py --projection
--presentation`; only deferred projection scratch may differ. Run death_state
and level_state as appropriate. `fixed_window.py --session S --tick T`
waits for a specific simulation session, preventing a pre-death tick from
matching a post-Continue capture. Combine it with `--level`; the session must
be positive and requires `--tick`. The natural Continue check uses session 8,
level 6 after six fixture-controlled earlier exits, with DEATH_NATURAL=1.
It observes actual combat death without writing energy. Combine DEATH_NATURAL=1
with DEATH_DECLINE=1 to check No, native menu return and a new SOL game, then
validate with `death_state.py --natural --decline`. Capture session 8, level 0
at ticks 25/40 for N=3 or 100/160 for N=12: these precede LEVEL_TEST=50/200,
which would otherwise force exits again in the new game. Use exact retained listings for hook and
CUSTOM1-off code audits. The restoration reference is under `tmp/restore60`; input-history lifecycle
evidence is under `tmp/input-history/lifecycle`.

## Substep validation

Build an explicit rate with `make slave VARIANT=Stellar7-Sim60 VASM_EXTRA=-DS60_SUBSTEPS=12`
or a diagnostic with `make verify VARIANT=Stellar7 VERIFY_FLAGS='-DSIM60=1 -DS60_SUBSTEPS=12 ...'`.
The current ABI version word keeps layout 30 in its low byte and encodes 12-N
in its high byte. Layout 29 remains readable for the restoration reference.
Readers must decode it through
`sim60_state.decode_version`; `sim60_state.read` reports `substeps` and `rate_hz`.

`tools/substeps_fixtures.py GROUP CAPTURE --listing LISTING --substeps N`
checks exact retained build identity, ABI rate, and all native-reference
results in that fixture group. The serial validation run and its build
inventory are under `tmp/substeps-prototype`. The recorded runtime checks
pass for all 78 combinations.
The private groups use tick 100 for injection and tick 101 for capture:

| Group | VERIFY definitions (in addition to SIM60 and S60_SUBSTEPS) |
|---|---|
| input-hud | QUANTA_TEST=100 INPUT_NEUTRAL_TEST=100 HUD_TEST=100 |
| knock-shake | KNOCK_TEST=100 SHAKE_TEST=100 |
| contact-terrain | CONTACT_TEST=100 TERRAIN_TEST=100 |
| motion | FLYING_TEST=100 SPECIAL_TEST=100 PICKUP_TEST=100 |
| animation | ANIMATION_TEST=100 |
| post-friction | POST_TEST=100 COLLISION_TEST=100 FRICTION_TEST=100 |
| boss | BOSS_TEST=100 BOSS_PATH_TEST=1 |
| linear-idle | LINEAR_TEST=100 IDLE_TEST=100 |
| input-play | INPUT_NEUTRAL_PLAY=200 PREFERENCES_TEST=100 PREFERENCES_CHOICE=2 |
| geometry-flat | GEOMETRY_TWIN=1 GEOMETRY_TEST=100 HEADING_TEST=100 FLAT_TEST=100 |
| projection | RADIUS_TWIN=1 RADIUS_TEST=100 PROJECT_TEST=100 BATCH_TEST=100 |
| ai-recenter | AI_STACK_TEST=100 RECENTER_TEST=100 BOSS_GATE_TEST=100 |
| scan-sort | SCAN_TWIN=1 SCAN_TEST=100 SCAN_FLAG_TEST=1 SHOT_TEST=100 SORT_TWIN=1 SORT_TEST=100 DISTANCE_TWIN=1 DISTANCE_TEST=100 |

Prefix each definition with `-D` in `VERIFY_FLAGS`. Retain the exact listing
with `-L tmp/NAME.lst` and the corresponding `tmp/NAME.slave`. Capture with
`fixed_window.py tmp/NAME --prebuilt tmp/NAME.slave --tick 101 --state-only
--fields 1`, supplying the same VERIFY_FLAGS and only `CUSTOM1=1 CUSTOM3=1`
in WHD_ARGS. Run one capture at a time. Validate with the group reader above;
repeat all thirteen groups for each of N=1,2,3,4,6,12. The byte-identity gate applied to the parameterization reference; current
input-history builds use native-state, field-input and hook checks instead.

`tools/cross_substeps.py REFERENCE CANDIDATE` requires equal native-update
boundaries and session identity. It reports every mapped difference, keeping
internal integrator records and deferred projection scratch separately visible.
No cross-rate divergence is automatically accepted.
`power_state.py --activation TICK --refresh TICK CAPTURE...` also checks the
separate speed-power clock after a native same-value refresh. Omit `--refresh`
for the ordinary full-duration fixture.
`jump_state.py --activation TICK CAPTURE...` checks the direct `JUMP_TEST`
fixture against the native height equation and landing at 45*N ticks. It does
not replace the input-driven pickup/jump selection check.
Use `fixed_window.py --level 6` when an early tick must be captured after
entering type-10 combat. The boundary condition checks both level and tick;
the captured state is checked against the requested level again. Cross-N
correctness builds use `LEVEL_TEST=17*N` (triggering inside update 17*N+1)
to align prior native decision counts across rates; the
performance baseline retains its separately specified fixture and windows.

## Rate matrix

`S60_SUBSTEPS` accepts 1, 2, 3, 4, 6 or 12; the simulation rate is five times
that value. The source default is N=12 (60 Hz); the 68000 playable target explicitly selects N=3 (15 Hz). The matrix driver scales route windows and level setup to equivalent game time
with `--substeps`, rounding up to the next completed tick. `LEVEL_TEST=T`
executes inside update T+1, so its scaled definition is
`ceil((T+1)*N/12)-1`; the 200 baseline trigger remains in native update 17
at every N. The explicit
`type10-heavy` route samples the 600–5400 nominal window every 300 nominal
ticks and retains per-segment pending counts. All five lower-rate matrices and heavy windows are complete.


To reproduce the retained lower-rate experiments, run serially with a fresh
prefix per build:

```sh
. ../../common/env.sh
for n in 1 2 3 4 6; do
  tools/rate_matrix.sh tmp/candidate-n$n --substeps "$n" --routes sol type10-early type10-late boss
  python3 tools/rate_matrix_report.py tmp/candidate-n$n --routes sol type10-early type10-late boss
  tools/rate_matrix.sh tmp/candidate-n$n-heavy --substeps "$n" --machines a500 --routes type10-heavy
  python3 tools/rate_matrix_report.py tmp/candidate-n$n-heavy --partial --routes type10-heavy
done
```

The heavy report deliberately uses `--partial`: only its A500 cell is requested;
the ordinary candidate report still requires all three machines.

The retained N=1 regression below requires explicit `S60_SUBSTEPS=1`.
The source-default regression uses `SIM60=1` alone and must report N=12;
the 68000 regression adds `S60_SUBSTEPS=3` and must report N=3. Retain a release
listing with `make slave VARIANT=Stellar7-Sim60 VASM_EXTRA='-L tmp/selected-release.lst'`
and copy its slave to `tmp/selected-release.slave`; run
`python3 tools/audit_hooks.py tmp/selected-release.lst` against that exact build.
For route comparisons, capture 68020 + fast RAM with `SLOW_DRAW=20` at ticks
50→125 (SOL), 150→200 and 375→450 (type-10), and 292→342 (boss).
The type-10 fixture uses `LEVEL_TEST=16 LEVEL_LAST=6 APPROACH_TYPE=10`;
the boss fixture uses `BOSS_ENCOUNTER=1 APPROACH_TYPE=0 APPROACH_FIRE=1
LEVEL_TEST=16 LEVEL_OBSERVE=1`. Match both endpoints against the
N=1 A500 matrix using `simulation_state.py --projection --presentation`.
Only deferred `projection_scratch` may differ; inspect every reported difference.

At N=1, use `DEATH_TEST=16` for death/Continue, adding `DEATH_DECLINE=1` for
No; use `LEVEL_TEST=16 LEVEL_LAST=6` for normal exits, adding `LEVEL_EARLY=1`
for early exits. Capture restarted ticks 50→125 on A500 and SLOW_DRAW=20
68020, with `--level 6` for exits. Validate with `death_state.py` (and
`--decline` for No) or `level_state.py`, then compare both endpoint pairs.
Keep the ordinary CUSTOM1-off frame-90 capture for `check_disabled.py` with
its exact listing and menu-only allowance. `make play60` must also reach
the native menu using its default release/CUSTOM1 setting with VERIFY absent.
These selected-rate checks do not establish physical-input or audible-output
playtesting. Evidence is retained under `tmp/rate-selected-n1`.

For matched A500 presentation comparisons, record the corresponding native frame
windows, rather than comparing only the shorter 100-field spot references:

```sh
. ../../common/env.sh
CPU=68000 AMIGA_MODEL=A500 CHIP_KB=512 FAST_KB=0 SLOW_KB=1536 NTSC=1 VERIFY_FLAGS='-DSIM60=1 -DS60_SUBSTEPS=12 -DNATIVE_SCENE=6 -DAPPROACH_TYPE=10 -L tmp/native-exact.lst' WHD_ARGS='CUSTOM3=1' python3 tools/fixed_window.py tmp/native-exact --frame 150 --level 6 --checkpoints 200 375 450 --state-only --native-events --fields 1
cp tmp/native-exact/slave.slave tmp/native-exact.slave
python3 tools/native_rate.py tmp/native-exact --listing tmp/native-exact.lst --scene type10 --window 150 200 --window 375 450
```

Run this only after all other captures have finished. An automated runner must
hold the exclusive `tmp/rate-matrix.lock`, as the matrix driver does;
`fixed_window.py` does not acquire that parent-owned lock itself. `--native-events` observes every native presentation
anchor at $2c16 using debugger variables only. Its contiguous counter log
rejects skipped presentations or resets. The reader checks original-code
preservation, the exact retained slave, raw debugger observations and saved
checkpoint clocks. Its full-window rates provide matching-scene comparisons; the active plan
uses 15 Hz on 68000 and retains 60 Hz on 68020+. The original
spot measurements remain useful local references.

The initial matrix has 48 cells. Capture the additional native combat
comparators in a separate directory:

```sh
tools/rate_matrix.sh tmp/rate-native-combat --routes native-type10-early native-type10-late native-boss
python3 tools/rate_matrix_report.py tmp/rate-native-combat --routes native-type10-early native-type10-late native-boss
```

These use `NATIVE_SCENE=6` for type-10 frames 150/375 and `NATIVE_SCENE=0`
with the controlled boss setup at frame 292. CUSTOM1 is disabled; CUSTOM3
provides the same approach pilot. The fixture removes its own setup hooks
before capture. `native_scene_state.py` verifies native code preservation,
zero simulation ticks and scene identity for every cell. Ordinary release
and VERIFY builds omit this fixture. Do not resume a pre-fixture baseline
under changed source identity; retain its directory and use a fresh prefix.


### Validation machines

The matrix, extended combat and new release checks run on three AmigaXDev named
setups, always NTSC, listed in `game.conf` `SETUPS` and `tools/machines.py`:

| Setup | Machine | Build |
|---|---|---|
| `a500-1.5m` | A500 OCS, 68000/7 MHz, 512 KB chip, 1.5 MB slow | Sim68000, 15 Hz |
| `a1200-fast` | A1200 AGA, 68EC020/14 MHz, 2 MB chip, 8 MB fast | Sim60, 60 Hz |
| `a1200-060` | A1200 AGA, 68060/50 MHz with MMU/FPU and data cache, 2 MB chip, 8 MB fast | Sim60, 60 Hz |

`tools/machines.py` reads each setup's values and launch arguments from the
shared launcher's `fsuae_setup`, so a capture boots exactly what
`make run SETUP=<name>` boots. `fixed_window.py` boots `SETUP` (default
`game.conf`'s); explicit `CPU`/`CHIP_KB`/`FAST_KB`/`SLOW_KB`/`AMIGA_MODEL`/`KICKSTART`
without `SETUP` select `SETUP=custom`, as the earlier release-validation runners
under `tmp/release60` do. Capture metadata records `setup` and `setup_args`, and
`rate_matrix_report.py` checks the emulator's accepted CPU model, clock, cycle
exactness, data cache and MMU against those arguments. `a1200-060` is not cycle-exact:
UAE accepts its 50 MHz request but runs it as `cpu_multiplier=8`, so its clock is
nominal, not exact. Recorded results from the
earlier eight-configuration matrix (custom 4 MB fast RAM, 68030/68040/68060
without MMU and cycle-exact, PAL checks) are references, not cells of this matrix.

The step 7 baseline used these commands (results in internals, "Three-machine
baseline"). They run one capture at a time under `tmp/rate-matrix.lock`:

```sh
tools/rate_matrix.sh tmp/three/main --selected-rates --routes sol type10-early type10-late boss native-90 native-240 native-type10-early native-type10-late native-boss type10-heavy
python3 tools/rate_matrix_report.py tmp/three/main --routes sol type10-early type10-late boss native-90 native-240 native-type10-early native-type10-late native-boss type10-heavy
# the step 6 control and 20 Hz on the A500
tools/rate_matrix.sh tmp/three/control --selected-rates --machines a500-1.5m --routes sol type10-early type10-late boss type10-heavy --define BLIT_IRQ_IDLE=0 --define SOUND_FAST=0
tools/rate_matrix.sh tmp/three/n4 --substeps 4 --machines a500-1.5m --routes sol type10-early type10-late boss type10-heavy
python3 tools/sustained_combat.py tmp/three/sustained
python3 tools/baseline_checks.py tmp/three/checks builds --reference 52e52251
python3 tools/baseline_checks.py tmp/three/checks input delayed lifecycle buffers buffers_normal --matrix tmp/three/main
```

`--define NAME=VALUE` adds a define to every SIM60 cell for a paired control.
`baseline_checks.py` selects machines by setup and writes
`<prefix>/<check>/validation.json`: input fixtures and same-rate state, delayed
drawing against the matrix cells, lifecycle scenes and CUSTOM1-off preservation,
buffer stability (warp and normal speed), and the build identities against a git
revision it exports into `tmp/`. Its docstring lists each check's machines.
It replaces the scratch `tmp/release60` and `tmp/fast60` runners for these checks;
the encounter runners there still select explicit machines.

Run `tools/rate_matrix.sh tmp/rate-current` for
the current default, or `tools/rate_matrix.sh tmp/rate-reference --substeps 12`
for a fresh N=12 reference. Retain existing evidence under its original prefix.
The driver runs one capture at a time and restores the normal development build.
Use `--machines a500-1.5m a1200-fast` or `--routes sol native-90` for a subset;
rerunning the same prefix skips completed cells with matching source/configuration.
Incomplete cells are retained and reported, never silently replaced.
`--boot-timeout 1800` is a wall-clock deadline for the same boot, not a dump
count. Captures read the game from the machine's slow or fast RAM region.
For a retained diagnostic build, `fixed_window.py --prebuilt SLAVE` skips
rebuilding and copies those exact bytes into the capture. Supply its matching
flags/listing and do not mix it with another emulator run.

Each SIM60 cell captures completed-tick endpoints for `simulation_rate.py`
and a 100-field read-only breakpoint window for `simulation_latency.py`.
The latter measures update-start gaps on CPU backends without instruction traces.
Its largest complete gap applies only to that observation window. The boss
window starts at tick 3500 and ends at 4100. Native baseline cells use frames
90 and 240 and measure complete inter-presentation intervals; these are not
matched native heavy-combat scenes.

Validate and render the table with
`python3 tools/rate_matrix_report.py tmp/rate-current`. It checks captured
settings, slave hashes/listings, observed fields, completed-tick rates and
installed SIM60 hooks. Missing cells fail unless `--partial` is requested.
A partial table is not the step-0 acceptance result.

Per-cell JSON and `matrix.json` retain settings, exact slave hashes, endpoint
debt and requested cache policy. Separate live CACR observations and their
limits are recorded in internals; do not infer cache enables from SetCPU alone. Captures
also retain the effective `debug.uae` as `emulator-effective.uae`. Verify private
UAE option records and the observed Exec clock; FS-UAE first writes to a shared
startup log, so simultaneous project boots can contaminate the copied frontend
`cpu =` / `ntsc_mode =` header. That header is not authoritative runtime evidence.
PAL defaults and an omitted disabled MMU are checked with the serializer's
conventions rather than treated as missing enabled settings.
The driver passes CUSTOM1/CUSTOM3 only for SIM60; `fixed_window.py` prepends
CUSTOM5=1 itself. Passing CUSTOM5 in `WHD_ARGS` as well duplicates the argument:
AmigaDOS stops at a "wrong number of arguments" prompt and the driver reports
"game/SIM60 patch did not become ready". Use `WHD_ARGS='CUSTOM1=1 CUSTOM3=1'` and
diagnose such a failure from a screenshot, not the log. Reports and exact built
slaves remain in `tmp/`; raw captures and listings are pruned (Scratch retention).


### Fast-CPU and extended-combat instruments

`tools/rate_matrix.sh tmp/rate-selected --selected-rates` selects N=3 on
68000 and N=12 on the other configurations. Add the native combat and
`type10-heavy` routes with `--routes` for the full selected-rate matrix.
For the complete set use:

```sh
tools/rate_matrix.sh tmp/rate-selected --selected-rates --routes sol type10-early type10-late boss native-90 native-240 native-type10-early native-type10-late native-boss type10-heavy
```

For normal-speed field captures, put `--warp_mode=0` in `EXTRA_ARGS`; the shared
launcher puts those options first, and FS-UAE uses the first occurrence. This
overrides the capture tool's usual warp boot. Such captures automatically retain
`emulator-command.txt` from the running project PID to verify frontend options;
`--retain-command` enables the same check for other captures. The field capture
itself runs without per-field debugger stops.

The report checker accepts the same route list. Completed cells resume only
when their source identity and settings match exactly; preserve incomplete
captures separately before retrying. Run one capture at a time.

`python3 tools/sustained_combat.py tmp/combat-extended` runs the selected rates
serially through nominal tick 9600, sampling every 300 nominal ticks. It stops
at the first inactive completed tick, before death or exit can reset the
scheduler. Checkpoint directory names retain the requested boundary;
`terminal.json` records the actual terminal tick. Reports contain active actor
counts, energy, pending debt and input-history integrity. No invulnerability
is added, and modal/menu time is excluded.

For native render scopes, retain a matching listing and binary and pass
`fixed_window.py --presentation-listing LISTING --state-only --tick T`.
`presentation_fields.py` guards the native sites and records VBL epochs, beam
positions, native field counter, buffer indices and the handoff request.
`presentation_report.py CAPTURE` accounts for alternating NTSC long lines and
the emulator's VPOSR/VHPOSR read convention. Complete-call times include
interrupts and wrapper overhead; overlapping scopes cannot be summed.
These are beam elapsed times, not instruction-cycle profiles or pure DMA costs.

`fixed_window.py --raw-trace` retains Barto fields without requiring CPU
instruction records. `presentation_buffers.py CAPTURE` maps every bitplane
fetch to the native bitmap allocation and rejects mixed or incomplete fields.
It also reports changed fetched words across consecutive fields using the same
bitmap; `--require-stable` rejects such changes. This catches unstable displayed
content, but cannot exclude writes restored before the next fetch. Use it with
the phase observer to distinguish buffer reuse from a legitimate buffer switch.
The fast-CPU backend has no validated instruction timing; with non-cycle-exact
blitter settings, missing blitter DMA records do not mean zero blitter cost.

The presentation-only probe preserves the saved presentation field required by
`BUFFER_REUSE`. To reproduce the retained pre-guard diagnostic binaries, pass
`--define BUFFER_REUSE=0` to both arms. Neither arm is a playable renderer.

`python3 tools/swap_only_probe.py tmp/swap-check/probe` builds a separate
N=12 VERIFY diagnostic that calls native presentation at hunk $6a0a in place
of full rendering. Additional `--define NAME=VALUE` arguments select scene
fixtures. Build its matched full-render arm with `--control`; the two binaries
must have identical size/layout and differ only in the two-byte NOP/branch
word. Run both as retained `--prebuilt` captures with matching
`--latency-listing` and compare their field/counter endpoints. The bypass
deliberately presents stale pixels; it is a ceiling experiment, not
an optimization or playable target.

`python3 tools/cache_probe.py build tmp/cache-check/probe` generates a separate
scratch-only VERIFY slave and listing. Capture that exact slave with
`fixed_window.py --prebuilt tmp/cache-check/probe.slave --tick 201 --state-only`,
using CUSTOM1 and the desired machine configuration. Read it with
`cache_probe.py read CAPTURE --listing tmp/cache-check/probe.lst`. The probe
records CACR after SetCPU and at tick 200; it changes no cache enables and must
never be used for performance comparisons. Its 68000 guard is separately tested.

Keep supplied archives and all derived game material in ignored `tmp/`.
`inputs.sha256` pins the installer `Stellar7.lha` and the Retroplay pack
`Stellar7_v1.0_NTSC_2026.lha`; `make unpack ARCHIVES=<directory>` copies them to
`tmp/archives/` and unpacks both into `tmp/game/` (the installer as `Stellar7HD/`).
The playable directory is `tmp/game/Stellar7NTSC/`.

The `make` targets load AmigaXDev's shared environment (`common/env.sh` sources
`AMIGA_ENV`, default `~/.local/share/amiga/env.sh`); before running a tool by hand,
source it with `. ../../common/env.sh`. Overrides include
`AMIGA_PREFIX`, `AMIGA_TOOLCHAIN`, `KICKSTART` (host A600 3.1), `KICK13`, `RTB`,
`KICKSTART_A1200`, `WORKBENCH_ADF`, `WHDLOAD`, `WHDLOAD_BINARY`, `FSUAE`, `VASM`,
`NDK`, and `FSUAE_COMMON`. See AmigaXDev `docs/environment.md`. The shared
Python environment and cross tools are added to PATH; source it before running
the tools. The trace reader, patch-list decoder, gdb server and disassembly
helpers are AmigaXDev's `amigaxdev` package (`tools/_amigaxdev.py` finds it
under any python3): `python3 -m amigaxdev.disasm disd DUMP BASE HUNKBASE START
END` disassembles by hunk offset, `python3 -m amigaxdev.disasm hotspots --label
s7 TRACE DUMP BASE HUNKBASE OFF[,OFF...]` lists the hottest instructions, and
`python3 -m amigaxdev.patchlist SLAVE LIST_OFFSET` decodes a patch list. The build takes API headers and KickEmu sources directly from
`$WHDLOAD/Include` and `$WHDLOAD/Src/sources`; do not use removed vendored paths.
Missing inputs are reported explicitly. There are no fallbacks into another
project. The SIM60 type-10 combat build has also been checked byte-identical
with this environment (`tmp/type10-shared-env.{lst,slave}`).

`SCAN_GEOMETRY_FIRST=1` defaults on within SIM60 after native-reference,
boundary, paired-performance and extended-combat checks. It tests X distance
before actor flag/type classification and adds no native hooks. Zero reproduces
the preceding release bytes. For correctness captures, combine `SCAN_TWIN=1`,
`SCAN_TEST=200` and `SHOT_TEST=200`; both `SCAN_TWIN` and `SCAN_TEST` are needed
for the live twin and synthetic scan cases respectively. Reports:
`tmp/scan-order-twin-validation.json`, `tmp/scan-order-boundary-validation.json`,
`tmp/scan-order-profile-validation.json` and
`tmp/scan-order-extended-validation.json`. The retained N=12 heavy A500 capture grows
simulation debt; the selected N=1 measurements are reported above.

When launching for a manual check from an agent command, keep its parent
session alive and verify the emulator process still exists. A printed PID from
a completed short-lived command is not proof that the emulator remained open;
the command host can clean up background children. App-control inventory may
not expose the FS-UAE process even while it is alive. Use the existing VERIFY
fixtures for scripted gameplay controls; they do not require host app access.
Physical input and audible output still need a separate check.

`make play60` builds and starts the CPU-selected experimental conversion
with normal controls and sound. It selects `Stellar7-Sim68000.Slave` or
`Stellar7-Sim60.Slave` and defaults to CUSTOM1=1; every `make run` option applies.
To build without launching, run `make slave VARIANT=Stellar7-Sim60`.
These builds contain no VERIFY fixtures. The selected N=3/N=12 launcher smoke
checks reach the native menu with 107/106 installed hooks and release bytes
matching the audited builds. They use debug/warp/silent mode and disconnected
input; fresh results are under `tmp/release60/play60-smoke-68000` and
`play60-smoke-68020`. The latter checks AMIGA_SETUP=a1200-fast overriding a
contradictory CPU=68000 before build selection. They do not verify interactive gameplay or audible output.
If overriding WHD_ARGS, include CUSTOM1=1 to enable the replacement. Current
selected-rate performance and its scene limits are recorded in internals.

`make run SLAVE=original` boots the shipped slave windowed with sound (debug and warp runs
are silent and open behind other windows; `SOUND=` and `WINDOW=` override); without
`SLAVE`, `make run` builds and boots the release `Stellar7` variant. The default machine
(`game.conf`) is `SETUP=a500-1.5m` with `NTSC=1`: 68000, 512 KB chip, 1536 KB slow RAM, no
fast RAM. `SETUP=custom` starts from the same A500 values. The supplied game is NTSC;
the simulation uses 5*N Hz (default N=12) regardless of display mode. `NTSC=1` uses the emulator's `uae_ntsc=true` core option.
The older `ntsc_mode` option did not alter this emulator's PAL scan timing.
The driver now rejects a requested mode that disagrees with Exec's observed
field frequency. NTSC boot and scan timing are verified. Use `NTSC=0` to reproduce
the earlier PAL baseline and prototype measurements. GLib queue warnings also occur
in successful PAL runs and are not proof of a stall.

`JOY0=none DETERMINISTIC=1 python3 tools/stellar7.py serve` starts the debugger
harness. `python3 tools/stellar7.py shot tmp/screen.png` captures a field;
`profile 10 tmp/trace.bin` captures ten fields with instruction PCs. Use `stop`
and `cont` to hold/resume the emulated CPU. The `gdb` command is read-only;
the emulator stub silently ignores memory/register writes.
The server uses the shared `amigaxdev.gdbserve` profiler-window handling: the
native FS-UAE build (it answers `monitor harness`) records PCs as it is, and only
the older x86_64 build gets its PC window fixed through lldb.

Use `gdb 'dump binary memory tmp/slow.bin 0xc00000 0xd80000'` for the default
slow-memory snapshot, and `python3 tools/stellar7_report.py tmp/trace.bin
tmp/slow.bin --base 0xc00000` for attribution. Hold the CPU while collecting
matched snapshots. For comparable benchmarks, use the fixed-window driver below.
Use `quit` to stop this project's emulator and debugger.

The report retains patched original entries as routine boundaries and tracks
pending calls separately for each stack context, including calls interrupted
before their first instruction. `python3 tools/test_stellar7_report.py` checks
both cases. Self-time ranges still use discovered entries rather than complete
symbols; inline jump targets and unobserved routines can remain grouped with a
preceding entry. Confirm optimization candidates with `routine_cost.py` and
an exact matching listing. Inclusive averages can include partial calls at the
capture edges; use complete-call measurements for performance comparisons.
`routine_cost.py` reports instruction-record cycles only: it excludes records
with no PC and all between-instruction gap costs, including non-interrupt CPU
overhead. Its stack-context filtering also excludes other contexts. Historical
complete-call means have this same scope; they are not total CPU time or elapsed
wall-clock measurements. Use field/tick deltas for actual simulation throughput.
The tool also reports `mean_same_context_gap_cycles` and
`mean_cycles_with_same_context_gaps` separately. A gap is attributed only when
its snapshot matches the next record, adjacent records share the inferred stack
context, and the call is already active and has not returned. Entry, return,
context-switch and missing-PC gaps are excluded; this remains a scoped cost,
not total elapsed time. `tools/test_routine_cost.py` checks call/interrupt edges,
partial calls and corrupt gap snapshots.

### Interrupt and sound-timer checks

`python3 tools/interrupt_profile.py CAPTURE --listing EXACT.lst [--out
interrupts.json]` splits a traced capture's interrupt cycles by source (INTREQ
vector, CIA-B ICR bit), with the handler call tree and Kickstart dispatch cost
for each. It also lists the interrupted main-context chains of BLIT dispatches
outside the polygon wrapper (when the build has one). The step 6 profiles use the
usual VERIFY build on `a500-1.5m`, for example SOL:

```sh
SETUP=a500-1.5m VERIFY_FLAGS='-DSIM60=1 -DS60_SUBSTEPS=3 -DPOLYGON_BLIT_IRQ=1 -L tmp/irq6/sol.lst' \
  WHD_ARGS='CUSTOM1=1 CUSTOM3=1' python3 tools/fixed_window.py tmp/irq6/sol --tick 150 --fields 100
```

`python3 tools/paula_writes.py list CAPTURE` lists every CPU write to an audio
register from a trace's DMA records (DMACON and INTENA/INTREQ only when they touch
audio bits), with field and beam slot. `compare A B` passes only on an identical
(register, value) sequence and reports the largest timing shift. Windows from
different builds start at different points of the music, so use the twin below
for per-call equality. `tools/test_paula_writes.py` checks the register filter.

`SOUND_FAST=1` (the 68000 default) builds the exact replacement of the sound
timer's channel pass ($134c). `SOUND_TWIN=1` (VERIFY, requires `SOUND_FAST=1`)
compares it with a RAM copy of native $134c on every timer call, and
`SOUND_TWIN_BAD=1` perturbs it as a negative control.
Capture state-only to a later tick and read the record from the last
checkpoint:

```sh
SETUP=a500-1.5m VERIFY_FLAGS='-DSIM60=1 -DS60_SUBSTEPS=3 -DPOLYGON_BLIT_IRQ=1 -DSOUND_TWIN=1 -L tmp/irq6/twin-sol.lst' \
  WHD_ARGS='CUSTOM1=1 CUSTOM3=1' python3 tools/fixed_window.py tmp/irq6/twin-sol --tick 150 --tick-checkpoints 375 --state-only --fields 1
cp tmp/irq6/twin-sol/slave.slave tmp/irq6/twin-sol.slave
python3 tools/sound_twin_state.py tmp/irq6/twin-sol --listing tmp/irq6/twin-sol.lst
```

The checker passes on compared calls, observed written words and zero state,
write, real-run and reference errors; `--expect-errors` inverts it for the
negative control.

`BLIT_IRQ_IDLE=1` VERIFY builds count, in the field callback, the fields checked,
masks applied, fields left enabled because Kickstart's queue or a QBlit was active,
and masks undone because work was queued in between.
`python3 tools/blit_idle_state.py CAPTURE --listing EXACT.lst` reads them from the
last checkpoint and passes when the enable was masked and the queue was never found
active. `tools/polygon_irq_trace.py` applies only to `-DBLIT_IRQ_IDLE=0` builds,
which keep the polygon wrapper.
The four retained collision-order profiles reproduce every prior instruction-only
mean and completed-call count. Adding attributable gaps gives full-update means
92303.10→90004.42 on A500 (2.49% lower) and 53499.50→52422.49 on delayed 68020
(2.01% lower). Actor/projectile scans improve 9.16%/12.77% on A500 and
7.71%/12.05% on delayed 68020 with this accounting. No gaps were attributed to
these A500 calls. Results: `tmp/scan-order-gap-costs.json`. This does not alter
field/tick throughput or resolve the heavy A500 backlog.
The pinned FS-UAE profiler emits `$7fffffff` whenever cycles elapsed outside an
instrumented instruction, then records the same saved registers on the following
instruction. The source comment calls this an IRQ marker, but its condition is
not IRQ-specific (shared pin `b70b1180b44ab25b97cd66466c70879897d8a362`,
`src/newcpu.cpp`, `cpu_profiler` constructor). Missing PC means no PC was recorded,
not proof of STOP. The installed x86 binary's source identity is not independently
established; the return audit checks the required snapshot pairing in each trace.


The harness is adapted from Indianapolis 500 (single-attach profiler fix),
Their Finest Hour (boot and call attribution), and Battlehawks 1942 (empty
input-port mode). A busy debugger port fails instead of killing its owner.
Never use process-name-wide kills.


`python3 tools/heading_inputs.py CAPTURE` audits native heading-table results
and division ranges in a retained full trace, and reports complete-call costs.
It validates the ordinary non-overflow model only; unmodeled extremes are
reported separately. Use native boundary fixtures before replacing the routine.

The native pace capture `tmp/prof/native-pace-expanded` uses the reconstructed
loader without CUSTOM1 or SIM60. Read-only update/presentation breakpoints
measure 100 NTSC fields at native frames 90/120/180/240. Complete update
intervals give 5.00/5.00/3.30/4.00 updates/s respectively; the simple 100-field
counts include partial intervals and must not be presented as exact cadence.
`tmp/native-pace-expanded-validation.json` checks the actual anchor PCs,
clock mode, native loop opcodes and normal-build restoration. It supports the
early-scene reference rate but demonstrates later native slowdowns. The SIM60
conversion intentionally retains a single reference rate, currently five
native updates per second split into twelve substeps.

## Build and fixed captures

Startup detection in `fixed_window.py` uses the unpatched game entry prefix,
then requires the relocated A4 pointer and DOS segment link to identify the
same mapped data hunk. It does not search ROM and slave images while the guest
is paused. Eight retained A500/68020 captures match their recorded anchors;
invalid relocation and preload-only snapshots are rejected
(`tmp/boot-game-locator-validation.json`). Full patch validation remains separate.

Within SIM60, `LINEAR_ACTOR_HASH=1` selects straight-motion cache slots by actor
address, retaining the full yaw/speed validity key. Set it to zero for the old
yaw index in A/B measurements. It adds no instructions or storage.

`SHORT_BRANCHES=1` also defaults on within SIM60. It enables only vasm's branch
encoding optimization inside the simulation sources; explicit `.w` branches
retain their sizes. Set `SHORT_BRANCHES=0` for the preceding encoding in paired
measurements. Normal legacy builds are unaffected. Native-reference and
cross-render checks pass on both CPUs; the heavy A500 route still falls below
sustained 60 Hz, despite reduced update cost and a smaller simulation build.

`MOVE_TRIM_SAVE=1` defaults on within SIM60 and omits redundant saves of
D5–D7/A4 in the movement wrapper. Set it to zero for the preceding full save
set. Both CPUs pass movement, idle and boss fixtures; L861 checks those four
registers explicitly and rejects its deliberate-corruption control. The
production change alters only MOVEM masks and stack argument displacements.

`RECENTER_FAST=1` defaults on within SIM60 after native-reference and matched
long-run validation. Set it to zero for the preceding loop. It caches the player's
X/Z only within that call and resumes the original secondary-object/player-reset
tail. `RECENTER_TEST=100` in VERIFY runs 128 native-reference cases; read them
with `python3 tools/recenter_state.py CAPTURE --listing EXACT-BUILD.lst`.
`RECENTER_BAD=1` corrupts a test actor after the candidate call and must fail
all 128 cases. The diagnostics are absent without VERIFY; RECENTER_FAST=0
reproduces the preceding SIM60 release byte for byte.

`SORT_INLINE_DISTANCE=1` defaults on within SIM60's `SORT_WALK=1` sorter.
Set it to zero for the preceding per-actor distance calls. It removes call
setup/save overhead using identical signed-long arithmetic in the sort context;
it adds no persistent state or hook. `SORT_TWIN=1 SORT_TEST=100` in VERIFY runs
64 native-order cases, checked by `python3 tools/sort_state.py CAPTURE`.
`SORT_DISTANCE_BAD=1` additionally corrupts distance keys at that fixture tick;
the negative capture must stop at the mismatch handler, not reach its requested
completed tick. Diagnostics are absent without VERIFY. Paired performance and
five-checkpoint gameplay evidence is in `tmp/sort-inline-long-validation.json`.

`make slave VARIANT=Stellar7` builds the normal development loader. `make verify VARIANT=Stellar7`
builds the menu fixture; `make run BUILD=verify WHD_ARGS=CUSTOM5=1` boots it. Both retain the original CRC acceptance check. `CUSTOM1=1` enables the
experimental fixed-step timing patches; without it the game code is unchanged
except for explicitly enabled VERIFY fixtures.
SIM60 labels CUSTOM1 with its compiled rate (“Experimental 60 Hz simulation”
at the default N=12; explicit lower-rate builds display their own rate) and omits the legacy
CUSTOM2 rate selector, which the replacement does not use. The legacy build
retains that selector.
Only the supplied English layout has been tested; hook-byte guards
reject other layouts. This is a reconstruction of the game-specific loader
on modern KickEmu, not a byte-identical reconstruction of the 2008 slave.

`python3 tools/fixed_window.py tmp/prof/base --fields 50` builds and retains
its exact VERIFY slave, boots with both input ports empty, waits for gameplay
frame 90, and saves snapshots, first/last images, trace and analysis reports.
Use a capture subdirectory without spaces; the repository path may contain
spaces. Capture output must be under `tmp/` in a new or empty directory.
Existing captures are not overwritten. Only one capture runs at a time.
`--state-only` saves the anchor without tracing; `--swaps-only` uses read-only
breakpoint counting. The default window is 100 fields when `--fields` is omitted; the profiler
supports at most 100 fields per capture. The driver rejects larger requests.

To check the disabled replacement, build with SIM60 but omit CUSTOM1 and
CUSTOM3, retain the exact listing/slave pair, and capture legacy frame 90 with
`--state-only`. Run `python3 tools/check_disabled.py CAPTURE --listing LISTING
--allow-menu-fixture`. The checker relocates the original executable, checks
151969 code-hunk bytes including every compiled simulation patch range, and
verifies the three menu-fixture jumps exactly. Six guarded native data objects
embedded in the code hunk are reported separately; no simulation patch may
intersect them. This is a disabled-code check, not gameplay-state equality or
an enabled-hook boundary audit. Current A500/68020 captures are
`tmp/prof/disabled-sort-inline-{a500,020}`, each with `disabled-check.json`
and all 87 compiled simulation patch ranges covered.

For enabled SIM60 hook checks, retain the exact assembler listing and sibling
`.slave`, then run `python3 tools/audit_hooks.py LISTING --capture CAPTURE
--out tmp/hook-audit.json`. Omit `--capture` for a static release-build audit.
This checks complete original instructions, conservative direct interior
entries and relocated code pointers; the capture additionally verifies exact
installed bytes and destinations. Computed indirect entries and replacement
semantics require separate evidence.

The 68020 configuration uses `AMIGA_MODEL=A1200 KICKSTART=$KICKSTART_A1200
CHIP_KB=2048 FAST_KB=4096 CPU=68EC020 SLOW_KB=0` after sourcing
`../../common/env.sh`. This is an A1200 with fast RAM, not a stock A1200.

`tools/state_summary.py CAPTURE...` reports only mapped player/RNG/timer state.
It is not a full-state equivalence test. `tools/compare_traces.py A/trace.bin
B/trace.bin` checks whole screenshots, instruction records, DMA records and
chip snapshots; it deliberately reports the known raw-register/DMA differences
between the current repeated captures instead of masking them.


## Fixed-step timing tests

`NTSC=0 WHD_ARGS='CUSTOM1=1 CUSTOM3=1' python3 tools/fixed_window.py
 tmp/prof/fixed-a500 --frame 115 --fields 100 --checkpoints 140 160`
uses fixed timing plus the VERIFY native movement/firing route. `CUSTOM3`
requires the `CUSTOM5` menu fixture (enabled by the driver). It supplies forward
input at steps 100–139, adds turning at 120–139 and holds fire at 105–134.
The route changes input API results, not positions, velocities or RNG.

`CUSTOM2` is the simulation frequency (1–25 Hz, zero/default means 5).
The default is a provisional A500 reference, not a claim of historical intent.
`CUSTOM4=2` in VERIFY presents every second eligible simulation step.
`VERIFY_FLAGS=-DSLOW_DRAW=20` adds twenty VBL fields to each drawn frame,
allowing a deliberate slow-renderer catch-up test. Neither test option exists
in a normal build. Build normally again after running capture tests.

`tools/timing_state.py CAPTURE...` reports scheduler credit and presentation
counts. `tools/simulation_state.py A B` compares mapped state at an equal
simulation boundary. Checkpoint folders can be passed directly. Comparisons
include player/world/active objects (including projectiles), visibility flags,
positions, motion, behavior counters, power timers, score, RNG and star x/y.
Raw pointers, projected coordinates and unused allocation padding are excluded;
this is not a complete state-equivalence proof. Input edges use simulation
steps, while the trace independently measures simulation steps per elapsed field.

The original anchor remains the pre-swap point at hunk 0:$2c16, even when that
step will skip presentation. Actual presentation counting uses $6a0a; simulation
completion counting uses $2d4e. Never treat anchor hits as displayed frames in
the timing build. Profiles show completed work per window and can include one
step of boundary jitter. Saved `metadata.json` records Custom and build options.


## Fixed-rate replacement development

The retained capture names and numerical timing examples below use N=12 unless
explicitly stated otherwise. Add `-DS60_SUBSTEPS=12` to reproduce their build
flags; use the rate-aware commands above for the selected default or another N.
These retained reference measurements do not describe current N=1 performance.

Audit generic AI cadence in an existing full instruction trace with
`python3 tools/ai_dispatch.py CAPTURE --listing tmp/EXACT-BUILD.lst`.
The listing must have a sibling `.slave` byte-identical to the capture's retained
slave. This checks callback order against the observed scheduler gate, rather
than assigning ticks from the earlier snapshot. At least two decision boundaries
must be fully recorded. It reports observed callback coverage; a passing SOL
window does not validate unobserved type-8/9/10 firing and spawn behavior.
For observed $f136 calls, the audit also reports actor types, cooldown-helper
calls, $f646 spawn attempts and successful returns with matching native owner writes.
These counts exclude partial updates and do not require that a window fires.
The gate decoder accepts the exact short- or word-branch instruction sequence
using listing-derived phase/logic offsets; `python3 tools/test_ai_dispatch.py`
checks both encodings and rejects modified gates.
`python3 tools/type10_firing_state.py CAPTURE --listing tmp/EXACT-BUILD.lst`
validates retained native-return/after snapshots directly, including ownership,
full actor/projectile consequences and the twelve-tick gate. It requires all
three firing sites and a completed tick-5400 stop; allocation failures are
reported as observed coverage, not assumed. Current three-configuration results
are retained in `tmp/type10-native-cross-validation.json`.
Use `LEVEL_TEST=200` to reach level 1 and profile at tick 3700 for the retained
type-8 firing opportunity; later checkpoints still compare gameplay state.

Extended type-10 gameplay captures at 600/1500/3000/4500/5400/7200/9000 now
agree through native player death at tick 9212. The requested checkpoint 10800
is an explicit early stop, not a reached boundary. Results are in
`tmp/sort-inline-extended-validation.json`. Separate traces at anchor 9200 use
`tools/natural_death_trace.py` to verify native death cleanup on both CPUs;
`tmp/sort-inline-death-validation.json` also records exact tick loads and the
cross-render state comparison. A field trace can start partway through an
update after the snapshot; do not derive its absolute ticks by simply adding
observed update-entry counts to that earlier snapshot.

`VERIFY_FLAGS=-DSIM60=1` selects the incomplete replacement implementation;
`CUSTOM1=1` enables it at runtime. Its rate is fixed at 5*N Hz (default 60 Hz); the older
`CUSTOM2` rate selection does not configure this path. Normal builds still
select the older opt-in timing prototype.

Use `--tick 1500 --state-only` with `tools/fixed_window.py` to capture the
completed 1500th simulation tick. `--tick` cannot be combined with legacy
`--checkpoints`; use `--tick-checkpoints 1512 1600` for later completed ticks.
`tools/sim60_state.py CAPTURE` reports ticks, rendering,
clock credit, phase and total pending ticks (including fields elapsed since the
last batch poll). Frame counters automatically recognize this build's
fixed-tick completion marker. `tools/simulation_state.py A B` also compares
fractional movement state for the current SIM60 capture ABI.

`MOVE_ZERO=1` is the default zero-forward-speed movement shortcut within
experimental SIM60, after native comparisons and measured savings on both CPUs.
Set MOVE_ZERO=0 for the previous implementation.
MOVE_IDLE defaults on within experimental SIM60 after full-state/CCR fixture,
native regression and performance checks on both CPUs. Set MOVE_IDLE=0 for
the preceding integration path. It skips fully stationary ordinary movement;
MOVE_ZERO separately omits zero forward-speed products while still integrating
nonzero rotations and linear velocities.

`IDLE_TEST=100` with VERIFY and MOVE_IDLE=1 runs 64 A/B comparisons of the
whole movement wrapper. It executes the existing integration path, restores
the actor and its full 144-byte record, then executes the guarded path.
The fixture checks all actor/record words and all five CCR bits, with zero
and set incoming flags. Cases cover stale rollback state, each nonzero
velocity and remainder guard, out-of-range remainders, forward speed and
type-7 fallback. Capture at tick 150 with --state-only. Read with
`python3 tools/idle_state.py CAPTURE --listing tmp/EXACT-BUILD.lst`; the
sibling slave must match the capture. I760 results use an exact listing
symbol rather than changing the gameplay-state ABI. The fixture and its
runtime reference gate are absent without VERIFY or IDLE_TEST.
The all-register-saving simulation wrapper still integrates rotations and
three linear velocity terms, but omits native trigonometric products when the
forward-speed word is zero. With FLAT_TEST, signature F762 reports the same
480 native actor comparisons as F761, with 80 zero-speed cases routed through
the shortcut. Run boss/collision fixtures and gameplay comparisons as well;
this helper deliberately does not reproduce native scratch-register outputs.

`VERIFY_FLAGS='-DSIM60=1 -DSLOW_DRAW=20'` deliberately delays each render by
20 display fields. Compare at equal completed ticks, using the same input
fixture and source revision. A short field window can end with outstanding
clock credit; report that rather than claiming the measured completion count
is the configured rate. The replacement remains experimental and incomplete.

Use `python3 tools/simulation_latency.py CAPTURE --listing tmp/EXACT-BUILD.lst`
to measure update-start and native presentation-entry gaps from a full trace.
The listing's sibling slave must match the retained capture. Reports include
complete endpoint pairs, field-resolution uncertainty, and lower bounds for
unobserved leading/trailing gaps. Render-phase spans run from s60_render entry
to the next clock poll; deliberate SLOW_DRAW waits precede that phase but
remain part of update gaps. A short trace with fewer than two presentations
cannot establish a complete presentation interval or maximum game-wide latency.
Injected SLOW_DRAW waits are reported separately from renderer spans, including
an unfinished wait at the capture edge. The current collision-order A500 trace
has one 13-field render and a largest complete update-entry gap of 14 fields
(0.217–0.250 seconds with field-resolution uncertainty). Its sole presentation
cannot establish an inter-presentation interval. Delayed 68020 records three
five-field renders, each preceded by the requested 20-field diagnostic wait,
and begins another wait at the trace end. Its largest complete update-entry gap
is 25 fields; presentation intervals are 32 fields. These are bounded saved
100-field windows, not worst-case latency or direct input-to-display evidence.
`tmp/scan-order-latency-validation.json` retains both reports and checks the
injected delay against the fixture setting.

`python3 tools/render_write_inventory.py CAPTURE --listing tmp/EXACT.lst`
reads retained `render-before`/`render-after` dumps from one render interval.
It guards native storage references, retains every changed data byte and
reports unresolved bytes explicitly. Storage labels are not a gameplay-safety
whitelist or proof that only rendering caused the changes: timer interrupts
continue during drawing. The tick-229 capture identifies all 561 changed
bytes by family. No mapped-state exclusions are added. Model-sort labels cover
only the observed first nine slots, not the arrays' total capacity.
`python3 tools/model_sort_lifetime.py CAPTURE` checks native model-sort reads
against writes within each complete observed model pass. Thirteen passes in
retained A500/boss/delayed-68020 traces pass; omitted-initialization controls
fail (`tmp/model-sort-lifetime-validation.json`). Unseen paths remain open.

The VERIFY-only `LEVEL_TEST=200` diagnostic clears the native active-game flag
when the pre-completion tick counter is 200. Exit occurs at completed tick 201;
native cleanup and loading then advance the level.
Do not combine it with DEATH_TEST. Capture with `--tick 201 --state-only
--tick-checkpoints 600 1500 3600`; the root is still the outgoing session,
whereas checkpoints are in the next session. Run `python3 tools/level_state.py
CAPTURE/checkpoints/600` to validate exit, level increment, clock reset and the
fixture's private-state checks. ABI 28 exposes its result at entry+130.
W761 extends the older W760 record with a completed count, target level and
six retained transition records. `LEVEL_LAST=5` repeats the requested exit in
each session until level index 5; its default is 1 and supported range is 1–6.
For a chain, start at `--tick 600`, above LEVEL_TEST+1, to capture the final
session, then add `--tick-checkpoints 1500 3600`. The validator checks every
retained reset, consecutive level/session numbers and the requested target.
LEVEL_TEST and DEATH_TEST cannot be combined. This exercises native transition
machinery, not the boss/collision exit trigger or the ending.

Add `LEVEL_EARLY=1` to request exit at the native inactive-game check $2b4e,
before projection and stars. Capture `--tick 190 --fields 60
--tick-checkpoints 600 1500` and audit with `python3 tools/exit_audit.py CAPTURE
--listing tmp/EXACT-BUILD.lst`. Its sibling `.slave` must match the retained
capture. The audit follows the actual native BEQ destination through interrupts
and checks a complete exiting update: no projection/stars/shake, but exactly
one call to each required post-update routine. EXIT_GUARD defaults to 1;
EXIT_GUARD=0 reproduces the incorrect old path for a failing negative control.
The early injection is VERIFY-only and does not exercise a natural boss kill.

Build with `SIM60=1 BOSS_GATE_TEST=200` and capture tick 201 to compare the
simulation-owned boss eligibility predicate with native radar instructions.
Retain the exact listing/slave pair; run `python3 tools/boss_gate_state.py
CAPTURE --listing LISTING`. Require 262 cases and zero errors. The fixture
restores the active list/count and eligibility byte; BOSS_GATE_BAD=1 is the
VERIFY-only negative control and must yield five classification failures.

`BOSS_ENCOUNTER=1` is a VERIFY-only setup for boss-encounter testing.
`BOSS_ENCOUNTER_LEVEL` selects level index 0..6 (default zero). At that level's
first tick, it sets wave progress to the native target and clears initial
ordinary enemies through native damage at $3f04. The BE62 record reports the
requested/actual level, session and count cleared; their normal death effects
remain. It requires the expected session number and does not repeat after
setup. The reader also accepts the earlier BE60/BE61 records. Subsequent
spawning, carrier/boss creation, AI, damage and exits then run normally.
For level zero use passive LEVEL_OBSERVE. A later selected level may use
injected earlier exits only when LEVEL_LAST equals BOSS_ENCOUNTER_LEVEL, so
injection stops before that encounter. The final-level setup is
`BOSS_ENCOUNTER_LEVEL=6 LEVEL_TEST=200 LEVEL_LAST=6`; it does not itself
validate earlier bosses or the ending. Invalid levels and injection-stop
mismatches fail the build. Read the retained setup with `python3
tools/encounter_state.py CAPTURE --listing LISTING`. This is a shortened-wave
fixture, not evidence of completing the preceding wave. Its register save/restore
covers d0-d7/a0-a3 symmetrically. The exact-build 68020 capture
`sim60-boss-encounter-fixed` reaches ticks 60/600/1800/3600 with two initial
enemies cleared and zero setup errors; type 44 is present at tick 3600.
No level transition occurs in that initial window. Results are retained in
`tmp/boss-encounter-fixed-validation.json`. Combining this setup with
`JUMP_TEST=3500 APPROACH_TYPE=0 APPROACH_FIRE=1 LEVEL_TEST=200 LEVEL_OBSERVE=1`
reaches a boss kill and native level-0 exit at tick 4264. Paired A500 and
SLOW_DRAW=20 68020 captures `sim60-boss-exit-{a500,slow-020}` match gameplay,
HUD and fresh projection through that exit and session-2 ticks 600/1500;
reset checks pass with zero errors. The session-2 captures explicitly select
the session counter as well as the tick counter, since ticks reset on entry.
Results are in `tmp/boss-exit-cross-validation.json`. Jump activation bypasses
normal acquisition/selection. Later boss/ending coverage remains open; the
setup is byte-excluded from the 16502-byte release build.

`BOSS_TERRAIN_TEST=3600` is a separate VERIFY-only level-5 contact setup.
It requires BOSS_ENCOUNTER_LEVEL=5 and cannot combine with BOSS_FINISH_TEST.
At the selected update it changes only the existing type-44 boss's state byte
at actor+$59 to one. BE64 records the prior/assigned state, setup count and tick.
The native level handler then allocates terrain; input-only APPROACH_CONTACT
steering supplies the subsequent approach. Health, terrain positions, allocation,
contact and damage are not injected. Use `tools/encounter_state.py CAPTURE
--listing EXACT.lst --terrain` to require the completed setup and
`tools/terrain_contact_state.py CAPTURE --listing EXACT.lst` to check raw
before/after native allocation/contact snapshots. The latter reads N from the
ABI and requires 2*N+1 consecutive contacts, with damage at offsets 0, N and
2*N. The retained N=12 run has 25 contacts.
This validates the path after an explicit state selection, not the boss's
random decision to select it. A500, normal 68020 and delayed 68020 pass native
allocation at tick 3603 and 25 contacts at 3604–3628, with damage at
3604/3616/3628. All 53 before/after gameplay/HUD/fresh-projection snapshots
match across configurations; deferred projection scratch is reported separately.
For jump/contact coverage, `--airborne` instead reads `spawn`, `air-contact`
and `land-contact` before/after snapshot pairs. Each pair must retain native
breakpoint PC/register transcripts in `anchor.txt` and the exact captured slave.
Use an existing jump charge via POWER_SLOT=2, with POWER_ROUTE before the
BOSS_TERRAIN_TEST attack. This mode checks positive height at allocation and
first contact, zero height after landing, consumed charge and the same raw
energy/private-clock rules. It does not require consecutive contacts or prove
that jumping avoids terrain. Selected-rate evidence is in
`tmp/release60/air-terrain`, including corrupted-snapshot controls.

Results are in `tmp/terrain-contact-cross-validation.json`; omitted-damage and
no-contact controls are rejected. All setup code is excluded without VERIFY.

`BOSS_FINISH_TEST=7200` is a separate VERIFY-only ending-lifecycle setup,
permitted only with BOSS_ENCOUNTER_LEVEL=6. At the exact selected update it
requires a live type-44 boss, active gameplay and no death, then sets boss
health to one once. It does not damage/remove the boss, award score, clear
active, advance a level or select an ending. BE63 records the original and
assigned health, setup count and tick. Require `tools/encounter_state.py
CAPTURE --listing LISTING --finished` after setup. Its purpose is to test a
native player hit followed by ending cleanup; it cannot prove a full-strength
boss victory. The BE62 fixture and release binaries are unchanged when this
option is absent or VERIFY is disabled, respectively. The native ending lifecycle passes on normal 68020, A500 and delayed-render
68020 at the same hit/exit ticks (8009/8010). `tools/ending_state.py CAPTURE --listing LISTING`
checks the retained before-hit, final-active-clear, completed-update and
ending-entry/return snapshots against the exact slave. It requires native
breakpoint PCs, a player-owned projectile, the explicit BE63 health setup,
zero death, and unchanged update/presentation counts during the ending.
Manually interrupted debugger stops are rejected.

For a boss with unchanged native health, add `--native-health`. Retain the
lethal hit at native $11202 (player projectile) or damage entry $3f04, then
$3ff4, the completed exit, ending entry $2ebc and return $2ec0. This mode
rejects BOSS_FINISH_TEST and the reduced-health setup record; it validates
shield-wrapper callers through the original native return address. Earlier
level/wave shortcuts remain explicit in capture metadata. Selected-rate
captures are under `tmp/release60/full-ending-any` and `full-ending-cannon`.

`LEVEL_TEST=200 LEVEL_OBSERVE=1` selects passive transition observation instead
of the requested exit: it records the first inactive, non-death update and checks
native resume/reset state. The W762 result distinguishes this mode from W761
injection. It writes only diagnostic results, without populating private clocks
or clearing the active flag. It currently expects ordinary +1 level changes;
warp exits and the final ending need distinct checks. This observer is under
validation and does not establish actual trigger coverage by itself.

`APPROACH_TYPE=10` selects an optional VERIFY/CUSTOM3 joystick route instead
of the fixed movement/fire schedule. It reads a live matching enemy's native
heading and distance, steers toward it, and stops accelerating below 18000
distance units (native enemy firing range is 24576). Player firing stays off.
Only input API results change; positions, velocities, health, AI and RNG are
not written. This route requires SIM60. The 68020 pilot reaches distance 17999
by tick 1200 and observes three native type-18 projectiles owned by the type-10
enemy at tick 1800. Normal A500 and delayed 68020 combat captures match the
pilot at 1200/1800/2400 and audit the first native firing branch. The fixture
does not force projectile creation.

`APPROACH_FIRE=1` lets that route keep steering and press the native fire key
while aligned, closing to 4000 distance units. `APPROACH_TYPE=0` selects the
nearest live grounded hostile or boss, and prioritizes a type-25 exit. This
input-only route does not change health, actor positions, projectile allocation
or level flags. Combined with the separately described wave/jump setup it
validates the first boss-to-level transition. These options exist only in VERIFY.
`APPROACH_CONTACT=1` requires `APPROACH_TYPE=46` and no APPROACH_FIRE.
This VERIFY-only route approaches an active terrain actor regardless of its
health byte and removes the ordinary 18000-unit stopping distance. With no
terrain target it supplies forward/turn input to avoid waiting stationary.
Only native input values change: terrain spawning, player state and damage remain native.
The flag is byte-excluded from non-VERIFY builds. A level-5 encounter uses
BOSS_ENCOUNTER_LEVEL=5 with the explicit wave shortcut, LEVEL_LAST=5 and
LEVEL_TEST=200; contact is not established merely by reaching that scene.

`APPROACH_LOCK=1`, with APPROACH_TYPE=0, retains a target while it remains
in the active list and passes the existing hostility, health and height checks.
Carriers (type 7) remain unlocked: they are temporary spacing targets before
boss deployment. Exit pursuit still takes priority. `APPROACH_AIM=1..2048` selects the steering
deadband (default 2048); 512 is used by the current full-wave pilot. These options
change only the VERIFY input pilot, not gameplay state or playable builds.

The verified N=3 full-wave SOL route uses APPROACH_TYPE=0, APPROACH_FIRE=1,
APPROACH_STANDOFF=6000, APPROACH_LOCK=1, APPROACH_AIM=512 and POWER_ROUTE=5500.
Do not add BOSS_ENCOUNTER, LEVEL_TEST or JUMP_TEST: this route completes the
opening wave and activates existing powers through input. The N=12 SOL route
uses the same flags with POWER_ROUTE=34200. Both pass direct native kill
and exit evidence is under `tmp/release60/powered-boss-events`; see internals
for the observed boundaries and the remaining coverage limits.

`APPROACH_RAM=1` removes the approach route's stopping distance without firing;
it requires APPROACH_TYPE and excludes APPROACH_FIRE/APPROACH_CONTACT. It does
not place actors or force a collision.

`POWER_TRIGGER_TYPE=TYPE` makes POWER_ROUTE the earliest arming tick, then waits
for a live actor of TYPE in the native active list. Optional
`POWER_TRIGGER_DISTANCE=D` also requires its recorded distance to be at most D.
The trigger is private input-pilot state and resets each simulation session.
`POWER_SLOT=0..6` selects a single one-second power stage instead of the default
six-stage route; slot 3 is the mine. These options are checked on the selected
N=3/N=12 paths and remain VERIFY/CUSTOM3-only. With forced earlier level exits,
arm after LEVEL_TEST so ordinary enemies cannot consume inventory in an earlier
level: for example POWER_ROUTE=150 with LEVEL_TEST=50 at N=3, or 600/200 at N=12.
Capture before activation and check the required charge is still present. Carrier
arrival is not boss deployment; use POWER_TRIGGER_TYPE=44 to wait for the boss.
Contact and final-boss outcome checks remain separate from trigger validation.

`contact_effect_state.py --kind airborne-projectile` reads `before`/`after`
raw dumps and `registers.txt` at native damage entry $3cc2 and return $333e.
It requires positive player height and damage, a consumed jump charge, inactive
shield/death flags, exact native caller/opcodes and the expected same-tick energy
loss. Selected-rate captures use APPROACH_TYPE=10, APPROACH_RAM=1,
POWER_SLOT=2 and POWER_ROUTE=313/1466 at N=3/N=12 after earlier fixture-controlled
exits to level 6. These timings come from separate no-jump impact observations,
not a position or health injection. Evidence and negative controls are in
`tmp/release60/air-hit-timed-events`.

`contact_effect_state.py --kind mine-destruction` reads `mine-damage-before`
and `mine-damage-after`, retaining raw memory and `registers.txt` at native
$3f04 and return $32be. It verifies the projectile caller, type-43 health
1→0 or another lethal positive-damage result, same tick, consumed mine charge,
SOL level and exact-build hooks. Use APPROACH_TYPE=43, APPROACH_FIRE=1,
POWER_ROUTE=150/600 and POWER_SLOT=3 for the selected N=3/N=12 routes.
No wave or level shortcut is needed. This establishes native destruction;
visual and audible detonation still require observation.

For lethal shield contact, use APPROACH_TYPE=10, APPROACH_RAM=1,
POWER_TRIGGER_TYPE=10, POWER_TRIGGER_DISTANCE=5000 and POWER_SLOT=1. Select
level 6 with LEVEL_TEST/LEVEL_LAST and arm after earlier exits as above. Retain
raw before/after snapshots and stopped PCs at $35a8/$35ae. The checker accepts
the recorded hit-directory format under `tmp/release60/shield-only-events`:

```sh
python3 tools/contact_effect_state.py CAPTURE --listing EXACT.lst --kind shield
```

The same checker supports mine contact at $38b2/$38b8 with `--kind mine`;
a missing return-PC transcript fails validation. Neither kind alone proves mine
destruction, audible output, or a completed encounter.

`POWER_ROUTE=TICK` supplies native second-button and both-button input for six
seconds starting at TICK. It selects clone, shield, jump, cloak, cannon and speed
in order, using the current inventory; it leaves the mine unused. It requires
SIM60/VERIFY/CUSTOM3 and cannot combine with PICKUP_USE. No pickup, health,
position or inventory setup is performed. Use TICK=150 at N=3 or 600 at N=12
for the current ten-second entry point. Retain snapshots around each one-second
stage and after landing. `tools/power_route_state.py CAPTURE --listing EXACT.lst`
checks exact build/input-hook identity, ordered activation, simultaneous powers,
charge consumption, jump/landing, unchanged mine charge and input-history
integrity. It does not establish individual combat effects or full timer lifetimes.
Current paired captures and exact sample points are under
`tmp/release60/power-route`; release exclusion is under `pilot-builds`.

`APPROACH_STANDOFF=12000` additionally selects the arriving carrier as a spacing
target and uses native reverse input below 11000, forward input above 13000
for ordinary targets, and neither in between. It does not fire at the carrier
or drive toward a distant carrier. Exit pursuit remains forward. The option
requires APPROACH_TYPE=0 and APPROACH_FIRE, with a permitted distance 2000..30000.
The final-level pilot survives through tick 7200 but has not killed the boss.
Paired A500/SLOW_DRAW=20 68020 captures `sim60-ending-boss-cross-{a500,slow-020}`
match the normal 68020 pilot at 600/1800/3600/6000/7200, including mapped
fractional state, HUD and fresh projection. All six preceding reset checks and
87 installed patches pass. The final state has player energy 472 and boss
health 38. `tmp/ending-boss-cross-validation.json` records comparisons and rates;
this is combat coverage, not proof of the ending. The option is byte-excluded
from release builds and leaves the prior fixture binary unchanged when absent.


The generic AI audit also records type-10 state decisions and checks native
projectile returns at $f86e/$f8e4/$f912, alongside $f630 for types 8/9. A
nonzero result must have an observed owner write for that enemy. Results include
per-return-site counters to distinguish the three type-10 branches. State-0
observations alone do not prove the firing or later-state branches execute.

The VERIFY-only `JUMP_TEST=1205` diagnostic calls the native jump activation
routine after tick 1205. `PAUSE_TEST=1307` invokes the real native P handler,
holds its dialog for at least 60 fields, and chooses Continue through its
poll hook. These diagnostics bypass inventory/key selection; the normal
`CUSTOM3` movement/firing route still uses native input APIs.

`SORT_TWIN=1` runs both the original and cached depth sort on the same live
input list and aborts on any ordering difference. It is for correctness, not
performance measurement. `POWERS_TEST=1205` activates all five timed powers
through native routines, then shortens their native counters to two units so
the individual decrement and expiry boundaries can be captured promptly.
The power diagnostic does not test normal inventory acquisition or durations.
Capture `--tick 1205 --tick-checkpoints 1206 1216 1217 1228 1229 1300` to bracket
the two twelve-tick intervals. Build normally again after diagnostic captures.

`POWERS_FULL=1` keeps the normal 900/500/500/500/200-unit durations in that
fixture. `POWERS_REFRESH=1210` invokes the native speed-power activation again
after tick 1210, before its first native decrement. With `POWERS_TEST=1205`,
its first decrement must then occur at tick 1222, instead of 1217. This tests
refreshing the same native value, which cannot be detected by value changes alone.

The 68000 update-cost profile is reproduced with `NTSC=1
VERIFY_FLAGS=-DSIM60=1 WHD_ARGS='CUSTOM1=1 CUSTOM3=1' python3
tools/fixed_window.py tmp/prof/update-cost --tick 300 --tick-checkpoints 600
--fields 10`. Compare completed-call cycle costs, not the short catch-up count
as a sustained simulation or presentation rate. The report uses each trace's
recorded field cycles, rather than a hardcoded PAL denominator.


`COLLISION_TEST=200` exercises the native collision-separation fragment after
completed tick 200 using four isolated actor pairs (speeds 0, 1, -1 and 12).
Capture tick 201 and read `tools/collision_state.py CAPTURE`. The fixture compares
native and replacement position, bounce speed and correction count, then checks
ordinary fractional rollback and remainder restoration. It restores player,
shield and bounce globals and removes its temporary motion record before play
continues. The native two-byte loop initializer becomes RTS only during those
isolated calls; the loop-back target remains untouched, and the original word
is restored with a cache flush before normal gameplay resumes.

`COLLISION_OLD=1` in a VERIFY build reproduces the pre-fix behavior. The diagnostic
watchdog forces only the isolated pair apart after 64 unsuccessful attempts;
normal gameplay has no such watchdog or forced displacement. Expect the result
checker to fail for that reproduction. These flags have no effect without VERIFY.


`SPECIAL_TEST=200` runs a native-callback oracle for special enemy motion.
Capture tick 201 and read `tools/special_state.py CAPTURE`. Twelve isolated cases
compare four calls to native $f328 with 48 calls through the replacement AI
entry. Every XYZ substep is checked against the native interval displacement;
complete actor bytes and gameplay RNG are checked after each twelve ticks.
The fixture restores RNG and releases its temporary motion records afterward.
It covers types 13, 47 and 48, not the other AI callbacks or boss encounters.
Use later `--tick-checkpoints 600 1500` and a `SLOW_DRAW=20` capture to compare
real gameplay after the oracle. The diagnostic does not exist outside VERIFY.


For full power deadlines, combine `POWERS_TEST=1205 POWERS_FULL=1` with the
VERIFY-only `POWERS_INVULNERABLE=1` (as `-D` build flags). The latter sets the
native damage-suppression flag so the diagnostic can survive until all timers
expire; it does not test death or normal difficulty. Capture tick 1206 with
`--tick-checkpoints 3604 3605 7204 7205 12004 12005`. Use
`tools/power_state.py CAPTURE CAPTURE/checkpoints/...` to check native timer
words, their twelve-tick phases and clone activation against the deadlines.

`AI_STACK_TEST=200` tests the flying-AI state-3 fallback with identical isolated
actor inputs and two different values in its otherwise uninitialized stack byte.
The original path must produce states 5 and 3. The corrected path starts with the
same RNG state for both inputs and must produce the same decision, consuming
exactly one native RNG draw. Capture tick 201 and read
`tools/ai_stack_state.py CAPTURE`. The fixture restores gameplay RNG afterward.
`--native-only` can read the earlier two-case reproduction. This diagnostic
checks the decision correction; it does not test flying integration or boss motion.
Add `AI_STACK_LOW=1` to select a fixture RNG seed whose next low byte is below
2, exercising decision 5 as well as decision 3. The bounded seed search and
all fixture draws restore the original gameplay RNG before normal play resumes.
Compare later tick-1500 snapshots between the two CPU/render configurations;
the fixture seed must not affect subsequent gameplay.


`FLYING_TEST=200` compares four direct native $f192 calls with 48 calls through
its 60 Hz dispatcher for each of twelve isolated actors. Capture tick 201 and
read `tools/flying_state.py CAPTURE`. Every XYZ/bank substep is checked, then
complete actor/RNG bytes are compared at each twelve-tick boundary. Reference
calls retain the corrected random fallback. Cases cover descent, climb/clamp,
signed banking, decision timers, steering, RNG and contact-triggered retreat;
projectile allocation is excluded from this isolated fixture. Gameplay RNG and
temporary motion records are restored afterward. Use checkpoints 600/1500 for
the real movement/firing route and compare with delayed rendering on the 68020.

ABI version 5 publishes the motion-record stride at offset 70 and the flying
fixture result offset at 72. Current records are 144 bytes, including the flying
bank increment/remainder and boss motion fields; the state comparator retains support for older
64-byte captures. Record clearing uses the declared stride in all fixtures.


`KNOCK_TEST=200` compares eight isolated signed impulse/input cases with the
native fragment at $2b0c. `tools/knock_state.py CAPTURE` requires all cases and
the same-value-impact refresh check to pass. Four native intervals are compared
with 48 substeps per case: active knockback overrides speed throughout each
interval; inactive input reaches the native endpoint; angular velocity stays
unchanged. The test temporarily returns at $2b38, restores its original word
with a cache flush, and restores the player pointer, impulse and phase state.
The collision oracle also preserves the new phase state.

`KNOCK_PLAY=1205` injects a -160 impulse through the collision setter before
tick 1206 of the ordinary input route. It bypasses impact geometry. Capture
1206 with checkpoints 1217, 1218, 1229, 1230, 1302 and 1500 to bracket decay
and return to input. `tools/knock_state.py --play CAPTURE...` checks the active
speed override and decay boundaries. Compare equal ticks with a delayed-rendering capture.
ABI version 6 exposes knockback phase offset/size at 74/76 and the isolated
fixture result offset at 78. The comparator includes the phase and native
pending impulse, including when either is zero. Both diagnostics require VERIFY.


`CONTACT_TEST=200` checks the five repeated contact paths through their actual
patched call sites. `tools/contact_state.py CAPTURE` requires five passing
paths, independent-clock checks and three allowed sound-preview calls. Each
path compares four unthrottled native effects with 48 simulation substeps,
checking every intermediate energy/health value and the final native endpoint.
The fixture uses nonlethal actor damage; death/removal is not exercised here.
The -25 player-damage cases retain a shield to verify their native bypass.

Temporary returns after each patched call's argument cleanup isolate the
fragment; sound and hit-animation helpers also return during the fixture.
All original words and affected globals are restored before real play resumes.
The sound test counts scheduled calls, not audible output. Clock checks cover
independent paths/actors, duplicate calls and unsigned tick-counter wraparound.
Use checkpoints 600/1500 and a delayed-rendering capture for mapped-state
comparison after the fixture. Other motion/collision oracles can be combined.

Contact results are exposed at ABI offset 80. Current ABI version 14 uses
144-byte motion records. The five last-effect tick values occupy record offsets 68/72/76/80/84, with
validity bits in byte 88. Removal/reset clears these alongside movement state.
The comparator includes all record bytes, player damage flash and shield-contact
state. These instruments remain VERIFY-only; rebuild normally after captures.


`PICKUP_TEST=200` checks the native $3d2a pickup sequence against continuous
rise/yaw integration. Read `tools/pickup_state.py CAPTURE`. Four cases cover a
full thirty-event sequence, its last four intervals, and signed/extreme motion
increments. The full oracle checks 504 substeps and 42 complete actor/global
boundaries, including unchanged counter/healing before each twelfth tick and
no early removal. Native removal, inventory presentation and audio entry points
are temporarily stubbed for the fake actor, then restored.

`PICKUP_ENCOUNTER=200 APPROACH_TYPE=31 APPROACH_CONTACT=1` provides
separate real-actor coverage under VERIFY. PE61 explicitly allocates and places
one type-31 pickup beside the player, sets energy to 300 and the first inventory
count to one, then leaves contact acquisition and all thirty callbacks native.
Read `tools/pickup_encounter_state.py CAPTURE --listing EXACT.lst`; the matching
slave must be retained beside that listing. The observer records acquisition,
each callback before/after, completion and a later completed tick.
Normal 68020, A500 and delayed 68020 acquire at tick 837, execute events at
849 through 1197 in twelve-tick intervals, heal to 680, grant three charges
from one, and unlink the actor and clear its fractional records. All 65 mapped
gameplay/HUD/fresh-projection checkpoints match, allowing only deferred shared
projection scratch; all 87 installed hooks pass. Results are retained in
`tmp/pickup-encounter-cross-validation.json`. Eight corrupt-copy controls reject
missing healing, grant, removal, cadence, height, cleanup, changed selection and
missing event coverage (`tmp/pickup-encounter-negative-validation.json`).
The fixture is byte-excluded from release builds and the normal build is
restored (`tmp/pickup-encounter-build-validation.json`). Separate normal
68020 and A500 runs omit the native-event breakpoint observer and capture only
completed ticks 200/201/1198/1318. All four mapped snapshots match their observed
counterparts exactly, including deferred projection scratch, and all 87 hooks
pass (`tmp/pickup-plain-validation.json`). This checks observer independence
at those endpoints. This controlled scene does not cover natural pickup
spawning or audible output. Selection/use has separate coverage below.

Add `PICKUP_USE=1400` to that scene to supply native button input: second
button down at tick 1400, release at 1401, both buttons at 1402, then release.
`tools/pickup_use_state.py CAPTURE --listing EXACT.lst` checks completed ticks
1318/1400/1401/1402/1403/1413/1414/1415/1426/1500. Native release selects
inventory index zero by completed tick 1402; activation consumes one of its
three charges and stores native byte -2 (two remaining, active) by tick 1403.
The 900-unit timer first decrements at completed tick 1414, then at 1426.
Normal 68020, A500 and delayed 68020 match all ten gameplay/HUD/fresh-projection
snapshots, except deferred projection scratch, with all 87 hooks passing.
Pre-input tick 1318 matches the acquisition-only capture. Four corrupt-copy
controls reject missing selection, consumption, timer decrement and phase.
See `tmp/pickup-use-cross-validation.json` and
`tmp/pickup-use-negative-validation.json`. This diagnostic is excluded from
release builds; the normal build is restored.

For speed-power coverage, add `PICKUP_USE_SELECTS=7` (default 1; range 1–7).
The input fixture presses/releases the second button seven times before
pressing both at tick 1414. Use `tools/pickup_use_state.py CAPTURE --listing
EXACT.lst --speed` with root tick 1318 and checkpoints
1402/1404/1406/1408/1410/1412/1414/1415/1425/1426/1500/3813/3814/3815.
This checks native slot cycling, last-charge consumption, the full 2400-tick
speed timer and automatic reselection of slot zero at expiry. A500 and delayed
68020 match at all fifteen points, with all 89 hooks verified and diagnostic
code excluded from the release (`tmp/pickup-speed-cross-validation.json`).
The scene controls pickup placement; the speed charge is its existing inventory
charge. The checker also guards the native boost addition and cap and checks
speed against the integrated 40-unit native acceleration per twelve ticks:
3/37/40/287 at completed ticks 1415/1425/1426/1500, capped at 400 at the
sampled expiry boundary, then zero at 3815 with neutral mouse input.
Both CPUs pass; changing the tick-1500 speed by one unit is rejected
(`tmp/pickup-speed-movement-validation.json`). This reuses captures from
before the collision-order release; displacement and audible output remain
outside this check.

The remaining phased timers use `--timed-slot 1`, `--timed-slot 4` or
`--timed-slot 5`. Set `PICKUP_USE_SELECTS` to the slot plus one. Keep root
1318 and use the completed checkpoints returned by
`pickup_use_state.timed_points(slot)`: every selection edge, activation,
first-decrement boundaries, a later point and both sides of full expiry.
The native 500-unit powers expire after 6000 ticks (100 simulation seconds),
and exhausted slots advance to the next available power. Six A500/delayed-68020
captures pass all 40 paired checkpoints and all 89 installed hooks; measured
render counts differ in each pair. See `tmp/pickup-timed-cross-validation.json`.
These checks cover timer lifetime and inventory/UI cleanup; effect-specific
combat and audible output still require separate validation.

For jump, set `PICKUP_USE_SELECTS=3` and use `--jump` with root tick 1318
and the checkpoints in `pickup_use_state.JUMP_POINTS`. Native activation at
1406 consumes the existing last jump charge. Landing at 1946 clears the
integrator and selects slot three. The checker guards the original launch and
gravity instructions, verifies all 45 native 5 Hz height boundaries, and checks
the exact rational integral (including the retained remainder) at additional
apex/landing samples. All 55 checkpoints match A500 and delayed 68020, allowing
only deferred projection scratch; all 89 hooks pass
(`tmp/pickup-jump-cross-validation.json`). This covers a controlled flat-ground
flight, not arbitrary terrain, midair impacts or audible output.

For native mine placement, set `PICKUP_USE_SELECTS=4` and use `--mine` with
root 1318 and the checkpoints in `pickup_use_state.MINE_POINTS`. The checker
verifies slot-three activation at 1408, last-charge consumption, native type-43
allocation and immediate slot-four reselection. Guarded native trig tables
provide the exact full displacement of the placement call; it must not be
scaled by the twelve simulation substeps. The mine remains stationary through
2400. All eleven points match A500 and delayed 68020, allowing only deferred
projection scratch, and all 89 hooks pass (`tmp/pickup-mine-cross-validation.json`).
Mine impact and detonation require separate encounter checks.

The `--clone` option additionally checks completed ticks 1881/1882/1883/2000.
Native clone activation occurs at completed tick 1882, exactly 480 simulation
ticks after use: timer 861→860, active word 0→1 and the view mesh pointer
switches from data $4498 to $4598. All fourteen gameplay/HUD/fresh-projection
checkpoints match normal 68020, A500 and delayed 68020, allowing only deferred
projection scratch, and all 87 hooks pass. Four corrupt-copy controls reject
early/missing activation, an unchanged mesh and an incorrect timer. Results:
`tmp/pickup-clone-cross-validation.json` and
`tmp/pickup-clone-negative-validation.json`. Other power selections, cycling
while active, depletion and visible clone animation remain outside
this encounter check.

The `--expiry` option uses a separate capture with completed ticks
2000/3000/6000/9000/12201/12202/12203. Normal 68020, A500 and delayed 68020
all reach native expiry at tick 12202, exactly 10800 simulation ticks after
activation: timer 1→0, clone active word 1→0, mesh $4598→$4498 and inventory
-2→2, retaining selection zero. Its private phase remains 12 after expiry.
All seven gameplay/HUD/fresh-projection checkpoints match, allowing only
projection scratch; all 87 installed hooks pass. The normal build is restored.
Five corrupt-copy controls reject early/missing expiry, wrong mesh, timer and
inventory. Reports: `tmp/pickup-expiry-cross-validation.json` and
`tmp/pickup-expiry-negative-validation.json`. This does not verify depletion,
other powers or visible/audio output.

ABI version 8 publishes the sixteen-byte pickup state offset/size at 82/84 and
fixture results at 86. State holds a normalized actor pointer, remaining ticks,
height/yaw increments and signed remainders. The comparator also includes the
native pickup pointer, counter, acceleration words and completion flag. Capture
tick 201 with checkpoints 600/1500 and compare CPU/render configurations.


When `--tick` is requested, the capture driver waits in the same boot for the
SIM60 entry jump and ABI signature, not merely a discoverable game hunk.
LoadSeg can expose the hunk while the slave is still installing hooks/allocating
motion records. An early snapshot from the larger pickup fixture caught exactly
that interval; the identical retained slave completed after this readiness wait.


The fifth contact-oracle case calls the actual boss collision site $3cb8 with a
fake boss touching a fake player on native level zero. It checks both twenty
actor-health damage and one hundred energy damage per event, independent of
boss AI dispatch. The fixture restores the real player pointer and level too.
This case is nonlethal and does not exercise boss movement or projectile hits.


`BOSS_TEST=200` checks 34 callback cases, eighteen coupled braking cases,
and eight coupled curved-exit rollback/replay cases (B767).
Read `tools/boss_state.py CAPTURE`. Callback cases compare four native $10904 calls
with 48 substeps: XYZ/bank/pitch and acceleration speed each tick, then full actor/
RNG, animation byte, random heading and aim-target XYZ at each native boundary.
They cover all seven level handlers, altitude/clamp boundaries, sideways headings,
contact reversal, banking thresholds and type-7 pitch wraparound. Four cases
start exit acceleration at speeds 32717, 32718, 32742 and 32763, covering
positive speed-word overflow at different substeps and simultaneous pitch wrap.

The eighteen braking cases call native movement before AI, matching gameplay's
order. They compare every speed and complete actor/position boundaries for straight,
diagonal and pitched motion, stops, reverse motion and signed braking-speed wrap.
The first case also undoes and repeats movement to check vector-remainder rollback.
Native allocation returns null during the isolated fixture; its original entry and
all changed globals are restored before gameplay continues. Full encounters,
spawning/removal, temporary-Y collision tests and curved exit trajectory pace
(including positive speed-word overflow) still need validation.

The B766 captures `tmp/prof/sim60-boss-overflow-a500` and
`tmp/prof/sim60-boss-overflow-020` pass all 52 cases, including native
DEATH_TEST/Continue/retry. The 68020 adds SLOW_DRAW=20. Mapped gameplay and
projection state match at ticks 1500/3600 across CPUs and the preceding
terrain-clock baseline. The overflow cases call AI without coupled movement;
they establish speed publication and callback endpoint behavior, not trajectory
accuracy. These are state-only captures, with no performance claim. Rebuild
normally after diagnostics.


B767 adds eight type-7 state-4 sequences, each with 48 move-before-AI ticks.
Starting speeds include 32717/32718/32742/32763 with changing pitch and native
yaw velocity. Each tick checks published speed/pitch against independent
closed-form expectations, exact XYZ rollback, preservation of completed rotation,
and full actor/144-byte record equality after replay. For replay only, the fixture
restores starting angles and angular fractions: native collision rollback is
spatial and must not undo the completed turn. Spatial fractions are restored by
the actual rollback wrapper. These B767 checks establish rollback/replay consistency. The optional BP60
coordinate capture below supplies the independent continuous-path check.

`tmp/prof/sim60-boss-exit-spatial-{a500,020}` pass all 60 cases at tick 150,
including 384 curved-exit ticks per CPU. Gameplay/HUD/fresh projection matches
the preceding movement-trim captures and across CPUs; only deferred projection
scratch differs. All 87 installed hooks pass. `BOSS_BAD_EXIT_ROLLBACK=1` adds
one X unit after each rollback; the negative A500 capture rejects all eight new
cases while the preceding 52 still pass. The result words for the new cases are
bitmasks: position rollback, actor replay, record replay, speed, pitch, then
rotation preservation. `tools/boss_state.py` names each failed check. Results:
`tmp/boss-exit-spatial-validation.json`. Normal builds remain byte-identical.


Add `BOSS_PATH_TEST=1` alongside `BOSS_TEST=100` to retain every XYZ position
from the eight curved-exit sequences (BP60). Read these with
`python3 tools/boss_path_state.py CAPTURE --listing EXACT-BUILD.lst`.
The host model uses the original native cosine table and two-stage fixed-point
projection rounding, with independently calculated pitch/yaw evolution. It
integrates a linear projected velocity over each substep using rational
arithmetic, centered on the native move-before-AI interval. Every published
coordinate must remain less than one native position unit from that integral.
This checks the specified continuous trajectory, including signed speed-word
overflow, rather than asserting equality to coarse native curved positions.

`sim60-boss-path-{a500,020}` pass all 1152 coordinate checks per CPU (eight
cases, 48 ticks, three axes). Maximum error is 287/288 of a unit. Omitting the
acceleration term fails 890 coordinates; changing the first captured X by two
units fails exactly that point. Both still pass all 60 B767 cases and all 87
installed hooks. Gameplay/HUD/fresh projection matches preceding captures on
each CPU and across CPUs, apart from deferred projection scratch across CPUs.
Results: `tmp/boss-path-validation.json`. BP60 storage and writes are VERIFY-only.


ABI version 14 publishes boss results at entry+88 and a 144-byte record stride at
entry+70. Words 92/94, 96/98 and 100/102 store X/Z increments, X/Z remainders, and
pitch increment/remainder. Words 104/106/108 contain acceleration, interval-start
speed and published-speed remainder. Words 110/112 contain substep coefficient and
saved speed; 114 is reserved. Words 116/118/120 hold X/Z/Y vector remainders and
122/124/126 their rollback copies. Diagnostic motion calls use a VERIFY-only return
marker; normal builds contain no such recognized caller.

Earlier B760–B764 captures remain readable; the reported signature identifies the
scope. B760 has thirty callback cases; B761 adds six straight braking cases; B762
adds callback acceleration-speed and rollback checks. B763 adds six diagonal cases
and the retained probe fails two of them with the old scalar-speed correction.
B764 passes those 42 cases with vector integration. B765 adds signed-wrap and
pitched-direction cases for 48 total.


`ANIMATION_TEST=200` tests independent mesh/explosion cadence through the patched
callbacks and actual activation sites. Read `tools/animation_state.py CAPTURE`.
The A761 fixture compares four native update intervals with 48 substeps for each of four
cases, including actual type-11 and type-41 model frame arrays. Every substep
also invokes duplicate simulation and extra rendering calls. Same-callback refresh,
staggered actors and tick wraparound are checked separately. The global legacy
phase is held inactive during the fixture, so it cannot accidentally supply timing.
Fake-actor removal and the instruction following each initializer fragment return
temporarily; their original words and altered globals are restored before play.
This does not test real unlinking or visible sprite output.

ABI version 13 stores independent explosion/mesh timestamps at record 128/132,
with validity bits at 136 and a 140-byte stride. The animation result offset is at
entry+90. Use checkpoints 600/1500 and a delayed-rendering capture to compare the
ordinary gameplay route afterward. Earlier A760 captures are readable but do not
include the two-actor check and use a static mesh for the countdown case. Keep all
fixtures VERIFY-only and rebuild normally afterward.

The retained A761 captures are `tmp/prof/sim60-animation-final-a500` and
`tmp/prof/sim60-animation-slow020`. Both pass four cases, refresh and two-actor
independence checks and match mapped state at ticks 201/600/1500. The latter also
runs BOSS_TEST, COLLISION_TEST, SPECIAL_TEST, FLYING_TEST, CONTACT_TEST and
PICKUP_TEST at 200 with SLOW_DRAW=20; all pass. Normal SIM60 builds with and
without ANIMATION_TEST are byte-identical when VERIFY is absent.


The A762 animation fixture adds four oscillator cases for eight total. They use
the actual initializer hook at $92b6 and the native $394c frame/direction body,
checking normal cycling, endpoints and signed-byte extremes. Restarting the same
oscillator resets its clock without clearing the mesh-animation clock. The null-
actor path is also exercised. A temporary return at $92c2 isolates initialization;
its original word is restored before gameplay resumes.

ABI version 14 adds the oscillator timestamp at record 140 and validity bit 2 at
136, for a 144-byte stride. Other ABI offsets are unchanged. ANIMATION_TEST still
controls this combined diagnostic, and `animation_state.py` reports the signature
and expected case count when reading older captures.

The final A762 captures `tmp/prof/sim60-oscillator-a500` and
`tmp/prof/sim60-oscillator-slow020` pass all eight cases, refresh and independence
checks. Mapped gameplay matches at ticks 201/600/1500 (13 versus 41 renders).
The delayed run combines all seven oracles, including the 48-case boss fixture;
all pass with 144-byte records. The new twelve-byte initializer hook at $92b6,
restored word at $92c2 and unchanged full-placement call at $9304 were checked
in both captures. The normal build was restored after VERIFY-exclusion checks.


`SHAKE_TEST=200` checks native damage-shake timing and its separate byte RNG.
Read `tools/shake_state.py CAPTURE`. Four cases compare eight native update
intervals with 96 substeps each, including full-duration expiry, duplicate calls,
render exclusion, different RNG seeds and tick wrap. They compare the counter,
shake RNG, both offsets and the unchanged main-RNG array on every substep. The two
actual impact setter sites test same-value refresh, and native $c57a tests a menu
reset. Temporary returns after setter/reset fragments and the display-write entry
are restored before gameplay resumes; visible shake and full menus are not tested.

ABI version 15 exposes shake state offset/size at entry+92/+94 and VERIFY results
at +96. `simulation_state.py` now compares the private phase, data $3558 byte seed
and $7156/$7158 offsets as well as the already captured native counter. Record
stride remains 144 bytes. Compare ticks 201/600/1500 with delayed rendering, then
restore the normal build. CONTACT_TEST preserves this new clock around its native
damage-effect calls so it does not alter the subsequent gameplay route.


`POST_TEST=200` validates the per-tick post-update event split. Read
`tools/post_state.py CAPTURE`: require 48 death cases, 24 pending-quit cases,
768 periodic substeps and zero errors. The fixture compares the native signed
energy branch, first-update request guard and frame-mask cadence (including
word-counter wrap). Spawning, warning sound and the quit handler are counted
through temporary entry stubs and restored before gameplay resumes. It does not
exercise actual death screens, level transitions or the Quit to DOS dialog.
ABI version 16 adds the result offset at entry+98.


`DEATH_TEST=200` injects negative player energy once, lets native death cleanup
and the real Continue dialog run, holds that dialog for at least 60 fields, then
supplies Yes through its normal poll result. Capture tick 201 and checkpoints
600/1500: the first belongs to the dying session, the later checkpoints must be
in the restarted session. `tools/death_state.py CAPTURE/checkpoints/600` requires
one completed death/retry with zero reset errors. The oracle checks all motion
records and private fractional/timer state are cleared on reentry, and records
fresh clock credit, phase, ticks, energy and level. It bypasses lethal impact
geometry but does not stub the death screen, cleanup, allocations or level reload.
ABI version 17 adds a persistent gameplay-session count at entry+100 and the
VERIFY death-result offset at +104. `sim60_state.py` reports the session count.


Add `DEATH_DECLINE=1` to DEATH_TEST to select No, observe the native main
menu, and let the existing Begin fixture start a new game. Capture at tick 600
with `--state-only --tick-checkpoints 1500`; the injected death occurs at 200,
so both requested boundaries belong to session 2. Read with
`python3 tools/death_state.py CAPTURE --decline`. This additionally requires one
post-death menu visit with simulation stopped at its exit tick, followed by a
fresh clock and cleared private state. `DEATH_BAD_DECLINE=1` deliberately
chooses Yes: the native retry still succeeds, but the missing menu visit and
wrong dialog choice must fail the decline validator. All three flags remain
VERIFY-only. Exact builds and results are retained under `sim60-death-decline-*`.

For the batched scheduler's modal-credit check, combine `DEATH_TEST=200` and
`PAUSE_TEST=1307`; capture restarted tick 600 with checkpoints 1307/1308/1500.
Compare total pending ticks and clock origins across the pause, not just stored
credit. Existing owed simulation must survive the pause; only the actual modal
interval is excluded. The delayed 68020 test crosses exactly 60 native fields
and one update while pending ticks decrease by one. ABI version 18 exposes the
outer-modal flag at entry+106, which must be zero after return.

Run `tools/pause_state.py BEFORE AFTER --paused-fields 60` on the retained
1307/1308 checkpoints to require exactly one resumed tick, one modal return,
zero modal depth and preserved pre-pause debt. The explicit field count is the
known excluded interval in these captures, not a duration inferred from debt.
The corrected 68000 spans 61 observed fields: 60 paused and one active field.


The experimental SIM60 build defaults to `SCAN_FAST=1`, selecting the measured
collision-list scan replacement. Use `SCAN_FAST=0` for the native baseline. For native equivalence,
add `SCAN_TWIN=1 SCAN_TEST=200` (as `-D` assembler definitions), then read
`tools/scan_state.py CAPTURE`: require 68 synthetic cases, additional real calls,
and zero mismatches. Combining DEATH_TEST=200 also exercises native placement
and retry. Do not use the twin for speed measurements. Fast-only measurements
use the default SCAN_FAST=1 without SCAN_TWIN/SCAN_TEST; explicitly select
SCAN_FAST=0 for the native baseline. `tools/routine_cost.py CAPTURE --offset 0x3a54` measures
fully observed calls from entry until the caller stack returns, excluding other
stack contexts and boundary-partial calls. The retained slave determines whether
the entry jumps to the optimized implementation or executes the original body.

`SCAN_HOIST=1` defaults on within SCAN_FAST after native-reference validation
and measured scan savings on both CPUs. It loads query geometry once per scan
and handles type-7 query exclusion before traversing candidates.
Use the existing SCAN_TWIN/SCAN_TEST fixture and replacement-only captures;
SCAN_HOIST=0 reproduces the preceding optimized scan binaries on both CPUs.

`RADIUS_FAST=1` selects the scalar projection optimization at $16ff6,
the default within experimental SIM60. Use RADIUS_FAST=0 for its native baseline.
Add `RADIUS_TWIN=1 RADIUS_TEST=200` to compare D0 and D1
with native execution on every call and run 384 synthetic cases. Read results
with `tools/radius_state.py CAPTURE`; require all cases and zero mismatches.
The fixture crosses sixteen signed/boundary numerators with four large signed
denominators and shifts 0/1/7/8/16 (320 cases), then eight nonnegative numerators
with eight small signed nonzero denominators at shift 7 (64 cases). It includes
both sides of the 65535 shortcut boundary and wider fallback values. It does
not cover division by zero or every possible shift. ABI 20 exposes results at
entry+110. V762 adds the first failing input/output tuple; the reader also accepts
older V760 (128 cases) and V761 (384 cases without the tuple). The twin returns native outputs;
use RADIUS_FAST=1 alone for performance and replacement-only state checks.

`DIV_ZERO=1` is the default within SIM60. It bypasses division by N only
for zero numerators at the two ordinary-motion and two star-integration sites.
`DIV_ZERO=0` reproduces the preceding implementation for comparison. No new
fixture or ABI field is needed: the existing mapped-state comparison includes
motion and star remainders. The retained native baselines are byte-identical
with this switch disabled. Use `tools/routine_cost.py CAPTURE --offset 0x8682`
for complete movement-call costs; this includes the SIM60 wrapper.

`SORT_WALK=1` is the default pointer-walk cached sorter within SIM60.
Use SORT_WALK=0 for the preceding indexed cached implementation.
Add `SORT_TWIN=1 SORT_TEST=200` to compare each call with the native sorter and
exercise 64 synthetic configurations. `tools/sort_state.py CAPTURE` requires all
64 O761 cases and subsequent real calls; an order mismatch aborts the guest before a
successful checkpoint. ABI 21 exposes results at entry+112. Cases combine
counts 0/1/16/256 with sixteen order/boundary patterns, including ascending,
descending, tied, zero, mixed-zero, signed extremes and level-1 type-46 keys.
Full lists repeat sixteen distinct pointers. The reader also accepts O760/32-case captures.
All view/list/level state is restored after the fixture. Diagnostics are excluded
outside VERIFY. Omit SORT_TWIN/SORT_TEST for performance measurements.

`STAR_IDLE=1` defaults on within SIM60. It skips star arithmetic only when both
effective velocity inputs and both stored remainders are zero; bounds and
respawn logic still run. Use STAR_IDLE=0 for the baseline. Paired captures include
ticks 600/1206/1300/1500 to cover stationary, moving and turning inputs.

`tools/routine_cost.py CAPTURE --slave-offset OFFSET` measures a replacement
routine from its code-hunk offset in the retained slave. Obtain the offset from
a vasm listing for the exact flags, and compare the resulting binary with the
capture's slave before using it. The tool locates that retained slave in the
memory snapshot and excludes interrupts/partial calls as with game-hunk entries.
Do not reuse a symbol offset across builds without checking it.

`tools/motion_inputs.py CAPTURE` reconstructs complete native movement inputs
from traced register loads. `--inputs` includes the exact word tuples and
frequencies; `--capacity N` models a cold FIFO displacement cache of N entries.
It checks trigonometric argument consistency and reports opportunities only,
not implemented savings. The key is post-update pitch/bank/yaw, speed and three
linear terms. The analyzed entry is the native body at $868e..$87e2, including
calls through the existing trampoline.

`FLAT_PITCH=1` defaults on within SIM60, selecting the zero-pitch native movement
specialization. Use FLAT_PITCH=0 for the unmodified native path selection.
`FLAT_TEST=200` compares 480 complete fake actors after original and optimized
native movement. Read with `tools/flat_state.py CAPTURE`; require all cases and
zero errors. ABI 22 exposes the F761 result offset at entry+114; the reader also
accepts prior F760/384-case captures. The added pitch-$8000 cases cover a
+32768 intermediate from minimum signed speed. Combine with
BOSS_TEST=200 and COLLISION_TEST=200 for the existing motion/rollback oracles.
Those two fixtures now run once per boot so a death/retry tick reset does not
repeat them and inflate their result counts. The collision reader rejects counts
larger than its four allocated case records. No diagnostics enter non-VERIFY builds.


`RECORD_CACHE=1` defaults on within experimental SIM60 after validation and
measurements on both CPUs. It caches thirty-two fractional actor records; zero
retains the original search. Every hit
validates the record's actor pointer, and reset clears cache entries. The original
search/allocation path handles misses. VERIFY-only RECORD_COLLIDE=1 forces all
actors into one slot to exercise collisions. Combine boss, collision, animation,
special, flying, contact and pickup fixtures with native death/retry. These
fixtures now run once per boot, preventing duplicated counts after Continue.
Omit actor fixtures and RECORD_COLLIDE for normal-cache performance captures.

`MOVE_WORD_MUL=1` defaults on within experimental SIM60 after native-reference
validation and performance measurements on both CPUs. Zero selects the baseline.
Five native movement calls with sign-extended word inputs use MULS.W instead of
the general 32-bit multiplication helper. Two potentially wider intermediate
products remain native. FLAT_TEST switches all five sites back to native calls
for its reference and restores the candidate for comparison; the reader checks
restoration and the two unchanged wide call sites. Use BOSS_TEST and
COLLISION_TEST alongside it, then omit all three fixtures when measuring.

`DISTANCE_FAST=1` defaults on within experimental SIM60 and selects the shorter signed-distance helper at $4388;
DISTANCE_FAST=0 retains the native routine. `DISTANCE_TWIN=1 DISTANCE_TEST=200`
(with FAST=1) compares both returned registers against native calls and runs
512 signed boundary cases once per boot. Read with `tools/distance_state.py
CAPTURE`; require 512 cases and zero mismatches/failing cases. ABI 23 exposes
G760 at entry+116. Combine with SORT_TWIN=1, SORT_TEST=200 and DEATH_TEST=200
to cover sorter ordering and real retry. Performance captures must omit twins
and synthetic fixtures; use `tools/routine_cost.py CAPTURE --offset 0x4388`.


`tools/simulation_rate.py BEFORE AFTER [LATER ...]` reports consecutive
checkpoint update/presentation rates and pending simulation debt, using observed
fields rather than the scheduler's last poll. Checkpoints must belong to the
same active session with the same clock origin; reset and modal-rebase intervals
are rejected. These averages do not measure worst-case presentation latency.
The reader reproduces the retained distance A/B interval rates and rejects the
native retry and pause intervals in the existing captures.


`RADIUS_SMALL=1` defaults on within experimental SIM60 after native validation
and performance measurements on both CPUs. Zero retains the previous scalar path. It uses a shift for an
effective scale of 128 and a nonnegative radius at most 65535, then invokes the
native narrow division routine. Other inputs retain the existing wide path.
Use the radius twin and expanded fixture above before replacement-only captures.


`PROJECT_SKIP=1` defaults on within experimental SIM60, omitting unused
per-actor simulation geometry after native-reference guard validation. Zero
retains the preceding geometry path. Rendering,
visibility-tracked actors, unknown callbacks and the final processed geometry
remain native. See internals for the final-view-object fallback.
`tools/projection_work.py CAPTURE [--records]` audits completed native geometry
calls and bounds potential savings; it follows executed branches because trace
condition flags can be unmaterialized. It is not a performance measurement of
an implementation. `tools/simulation_state.py --projection A B` additionally
compares numeric scratch written by every simulation projection and fresh actor
coordinates. It deliberately excludes coordinates left from an earlier render
on untracked actors, and scratch touched only by rendering. Defaults are unchanged.


`PROJECT_BATCH=1` defaults on within experimental SIM60; zero retains the
preceding simulation projection pass. It preflights
an entire simulation list and advances only existing animation callbacks when
all non-view actors have visibility bit 3 clear, callbacks are null or native
$42b0, pre/post-list hooks are null, and count is 1..256. Other cases retain the
native pass before any callback executes. Rendering prepares camera state before
background drawing and retains native actor projection. Unlike PROJECT_SKIP,
this option intentionally defers shared projection scratch, so full `--projection`
equality is not expected. Gameplay and fresh actor projection must still match;
do not suppress arbitrary differences. The BATCH_TEST native comparisons cover the fallback cases below. A held
combat frame passes lossless guest-display comparison on both CPUs, and the
HUD-enabled level-5 comparison matches gameplay, HUD timing and fresh actor
projection through tick 3600 on the A500 and delayed 68020. Broader encounter
coverage remains outstanding. PROJECT_TEST alone
does not validate this new pass.

`tools/project_batch_trace.py CAPTURE --listing EXACT.lst` audits observed
whole-pass callback ordering against the guarded actor list. It verifies listing
opcodes against the retained build and rejects callbacks before fallback, wrong
actor/index order and unexpected targets. It reports incomplete trailing passes
separately; it does not establish state or display equivalence. Both level-5
traces pass (121/122 accepted passes and callbacks), and altered index, actor
and target controls are rejected. The earlier combat trace still reports its
92 accepted passes and callbacks.

`HUD_CLOCK=1` moves the cockpit indicator off the rendering clock within SIM60.
It executes the guarded native arithmetic immediately when visible and then
once per N simulation ticks (twelve in the N=12 reference). Native visibility condition and signed-word
bounds/step remain unchanged. Rendering does not advance it; inactive callers
retain native behavior. HUD_CLOCK=0 reproduces the preceding render-driven path.
`HUD_TEST=100` compares 64 cases and 2304 substeps with the copied native code,
including repeated renders, duplicate ticks, wrapping ticks, visibility changes
and inactive callers. Read with `tools/hud_state.py CAPTURE --listing EXACT.lst`;
require zero errors and the documented case/check counts. HUD_BAD_RENDER is a
VERIFY-only broken-render-gate negative control. Test hooks temporarily return
before rasterization and restore that instruction afterward.
`simulation_state.py --presentation` compares position/step and the optional
HU60 clock header without changing the main SIM60 capture ABI.

`FRAME_TEST=TICK` is a VERIFY-only rendering comparison. At that completed
simulation tick it draws once through the actual rendering wrapper, then holds
gameplay while display interrupts continue. Capture that same tick with
`fixed_window.py --tick TICK --fields 100`; the harness quits afterward.
`python3 tools/frame_state.py CAPTURE --listing EXACT.lst` requires one native
presentation, entry into the post-render hold loop and at least twenty settled
fields with identical full-image RGBA pixels. Multi-field captures are JPEG;
this checks decoded recorded pixels, not original lossless framebuffer bytes.
It writes a correctly encoded `settled.png` and
`frame-validation.json`. Compare hashes and mapped gameplay across builds;
ordinary screenshots from different last-render ticks are not equivalent inputs.
The first render entry may precede the trace's initial field. This diagnostic
is not a throughput/latency measurement and intentionally cannot resume play.

`tools/display_dma.py CAPTURE --listing EXACT.lst` verifies the settled
FRAME_TEST display without JPEG pixels. It compares the 16000 raw bitplane
words, their beam positions, and effective palette/control state in every held
field. The checker is deliberately limited to the observed 320x200 four-plane
mode with no scrolling, hardware sprites, bus conflicts or CPU display writes.
It validates AGA colors as OCS-compatible and rejects unsupported modes.
Allocation-dependent pointers and copper instruction-fetch timing are not pixel
values. All control writes and visible palette-write timing remain checked;
pre-fetch non-background palette changes are compared through their effective
values after verifying they precede horizontal display start. The separate
background-color writes retain exact beam timing. Matching this report proves
the guarded guest display, not host screenshot-buffer padding. The parser now
retains AGA color snapshots for these checks.

`BATCH_TEST=100` requires PROJECT_BATCH=1 and RECORD_CACHE=1. It compares
64 complete native projection passes with `s60_project`, using private actors,
mesh-frame arrays and preseeded motion records. Read the Q760 results with
`python3 tools/batch_state.py CAPTURE --listing EXACT.lst`; require 64 cases,
zero actor/record/scratch/path errors, busy zero and restored table/mesh entry.
Use PROJECT_SKIP=0 for the full native geometry baseline; default PROJECT_SKIP
also checks composition with the existing per-actor optimization. Cases cover
null/animation/unknown callbacks, first/last visibility actors, pre/post hooks,
empty/single/full/duplicate lists, view exclusions, inactive/rendering states,
callback-before/after-mesh flags and already-current animation clocks.
Mesh rasterization is temporarily suppressed on both sides and restored;
this fixture does not establish rendered-image equivalence. Shared scratch is
compared on every fallback case. VERIFY-only BATCH_BAD_VISIBILITY deliberately
removes that guard and must produce fixture failures. All test data and hooks
are absent when BATCH_TEST is not selected.

`PROJECT_TEST=200` (with PROJECT_SKIP=1) runs the projection guard fixture once
at the first actor boundary of that tick, after native view preparation. Read
`tools/project_state.py CAPTURE`; require J762, 240 cases, zero failures/busy,
no first failure, and a restored callback-boundary instruction. ABI 24 adds its
result offset at entry+118. Cases cross running/rendering state, visibility bit,
null/animation/unknown callbacks, final-entry view membership and list counts
0/1/2/3/256. Full lists repeat the three fake actor pointers. Intermediate-data
consumers model unknown callbacks and rendering/non-gameplay needs. Whole fake
actor bytes and final projection scratch are compared with native geometry.
The fixture temporarily returns at $12bfc, restoring the instruction and cache
before gameplay resumes. It does not rasterize or execute mesh animation;
ordinary route comparisons cover the existing animation callback. Fixtures,
buffers and the temporary patch are absent outside VERIFY. J760/J761 readers
retain the preliminary 192-case runs; use `project-final-*` for final coverage.


`SORT_ORDERED=1` defaults on within experimental SIM60 after native-order
validation and measured savings on both CPUs. It checks for positive, already-
descending keys after distance gathering in SORT_WALK=1. Zero retains the full
cached selection path for comparison. Lists containing any nonpositive distance retain the
full selection path. The current SORT_TEST=200 fixture has 64 cases (O761):
sixteen order/boundary patterns at counts 0/1/16/256. `tools/sort_state.py` also
accepts the prior O760/32-case captures. New patterns include descending ties,
zero/negative tails, inversions at either end, a single positive key, ties with
zero suffixes, and descending values starting at the largest signed long.


`TERRAIN_TEST=200` validates the independent player terrain-damage clock through
the actual installed $36f8 hook. `tools/terrain_state.py CAPTURE` requires 96
cases, 3456 substeps, four inactive-mode checks, 96 resets, eight intermittent
contacts and zero errors. Cases cross all twelve initial phases, four energy
words and ordinary/wrapping ticks. Every tick includes an extra rendering call,
alternating terrain actor pointers and duplicate contact calls. A copied native
SUBQ instruction supplies expected energy changes at the twelve-tick reference
boundaries. The following native branch is temporarily replaced with RTS and
restored with cache flushing. The reader checks the copied instruction's native
energy address and restored branch. Tests bypass contact geometry and level
selection; a real level-5 encounter remains necessary.

ABI 25 adds terrain-state offset/size at entry+120/+122 and the optional TR60
fixture offset at +124. `simulation_state.py` includes the eight-byte clock;
DEATH_TEST checks it is zero after native retry; combining TERRAIN_TEST seeds
a nonzero clock before death to make this clearing check meaningful. Use the
`terrain-final-*` captures for this check. The fixture runs once per boot
and is byte-excluded outside VERIFY. Ordinary gameplay uses the independent
clock whenever SIM60 is enabled; first contact is immediate, active repeats are
at least twelve ticks apart, rendering cannot consume the clock, and inactive
calls retain the native decrement without changing the clock.

`HEADING_FAST=1` defaults on within experimental SIM60 and selects the guarded
heading replacement; set it to zero for the native baseline. With VERIFY,
`HEADING_TEST=200` compares all register results in 4217 native-reference cases.
Read results with `python3 tools/heading_state.py CAPTURE`. ABI 26 publishes
the result offset at entry+126. Use `--tick 201 --state-only` and later tick
checkpoints for the fixture; omit HEADING_TEST for performance measurements.
Matched retained measurements are `sim60-heading-lean-measure-{a500,020}-{0,1}`.
They pass state/projection and native retry checks but do not meet the full
sustained-60-Hz goal. Normal builds exclude the diagnostic code.

`SHOT_FAST=1` defaults on within experimental SIM60 for the first projectile
collision scan at $34d6; zero is the native baseline. `SHOT_TEST=200` in VERIFY
compares all register outputs in 64 native-reference configurations. Read it
with `python3 tools/shot_state.py CAPTURE`. ABI 27 publishes its result offset
at entry+128. Capture `--tick 201 --state-only` with later checkpoints for the
fixture, and omit SHOT_TEST for timing. Retained matched measurements are
`sim60-shot-measure-{a500,020}-{0,1}`. The delayed 68020 uses SLOW_DRAW=20.
Normal builds exclude the fixture, and the normal development loader still
uses the legacy timing prototype unless built with SIM60.

For the longer default-build route, use SIM60 and DEATH_TEST=200 with
CUSTOM1=1/CUSTOM3=1, then run `tools/fixed_window.py CAPTURE --tick 3600
--state-only --tick-checkpoints 5400 7200 9000 10800`. Repeat with
SLOW_DRAW=20 on both A500 and 68020. Retained captures are `sim60-long-a500`,
`sim60-long-slow-a500` and `sim60-long-slow-020`. Use `simulation_rate.py`
on consecutive boundaries for interval rates, or first/last boundaries for
an aggregate; compare each equal tick with `simulation_state.py --projection`.
This reaches three simulated minutes, measuring the final two minutes, and
includes natural damage while remaining in level 0 and session 2.


`RECORD_CACHE_SLOTS` accepts 32 (current default) or 16 (baseline). The larger
cache adds 64 bytes without adding per-lookup instructions. It retains tagged
lookup/fallback and clears the full configured cache at session reset. Both
indices use `(actor >> RECORD_CACHE_SHIFT) & (slots - 1)`; the shift defaults
to 4 after the late-combat comparison described below. Both CPUs match baseline combat state
at 1800/2400 with all six resets passing; heavy-window mean update cost falls
1.99% on A500 and 2.09% on 68020. This does not resolve heavy A500 overload.
Use the makefile for retained listings so builds inherit shared WHDLoad paths,
e.g. `make verify VARIANT=Stellar7 VERIFY_FLAGS="-DSIM60=1 -L tmp/cache.lst"`.

### Radar backup flags in state comparisons

`tools/simulation_state.py` compares actor byte 0 as live `flags`. Byte 1 is the
radar renderer's saved copy and can legitimately retain a different value when
render schedules differ. Use `--render-scratch` to include it explicitly as
`render_scratch.radar_flag_backups`; `--presentation` still includes the
simulation-owned cockpit clock. The mapper guards the native save/restore
instructions before making this distinction. This is a mapped gameplay test,
not full-memory equality.

`tools/radar_flags.py CAPTURE` checks complete observed radar passes: save each
actor's flags, apply temporary radar flags, restore the same unique actors in
order. It rejects missing restores and duplicate actor lists, reports partial
passes, and checks whether the audited direct byte-1 readers alias those actors
in the trace. It does not prove the absence of every possible indirect read.
Reports and negative controls are in `tmp/radar-flags-validation.json`; both
live-flag corruption and an omitted restore are detected. Draw-backup changes
remain visible with the explicit comparison option.

### Straight-motion integration

`MOVE_LINEAR=1` now defaults on within SIM60 and requires FLAT_PITCH.
Use `MOVE_LINEAR=0` for the ordinary wrapper baseline.
After all normal rollback backups, it accepts only non-boss actors with zero
pitch, zero angular/linear velocities, zero angular/Y fractions, nonzero forward
speed, and X/Z fractions in -11..11. It caches a native flat vector's quotient
and remainder, then applies exact signed carry corrections instead of repeating
rotations, vector calculation and three divisions. Cold vectors outside
-32768..32768 fall back after restoring the original coordinates.

`LINEAR_TEST=100` compares the entire actor, motion record and CCR against the
ordinary wrapper for 3072 seeds, twice each. Yaws, signed speed limits,
coordinate wrapping, opposite-sign remainders, and every exclusion category
are included. `tools/linear_state.py CAPTURE --listing EXACT.lst` requires all
6144 comparisons with zero mismatches. `LINEAR_BAD_CARRY` is a VERIFY-only
negative control that omits one quotient correction. The corrected A500 fixture
passes on both the A500 and delayed-render 68020, with fixture-free gameplay/HUD
matching at tick 150. The broken-carry control produces 602 actor and record
mismatches. A500 combat gameplay/HUD and fresh actor projection match the
default build at 1800/2400; deferred shared projection scratch differs as
expected. Complete updates average 103557.23 versus 108427.04 cycles (4.49%
lower). The 600-tick interval takes 590 fields with four presentations and debt
142→132, versus 602 fields/four presentations/debt 154→156. A fourteen-field
update-start gap remains. Delayed 68020 gameplay/HUD/fresh projection also
matches at 1800/2400; complete updates average 55403.43 cycles. Its long
route reaches 9000 but ends in native death at tick 9212, so use 9000 as
the last completed boundary for this approach route. The interrupted snapshot
is retained separately as `interrupted-9212`, not as a tick-10800 result.
The long A500 baseline and delayed 68020 both match all sampled gameplay/HUD
and fresh projection state through tick 9000. A500 presentations increase
32→39 over 7200 ticks and ending debt falls 242→150. The matched 68020
window reduces complete update cost 3.60% (57474.49→55403.43 cycles),
with the same eighteen presentations across 600 ticks. Diagnostic flags are
byte-excluded from non-VERIFY builds; the explicit-off and legacy binaries
match their preceding defaults. These checks support enabling the shortcut
within experimental SIM60, but do not resolve the later A500 combat slowdown.


### Natural combat death trace

Capture SIM60 with LEVEL_TEST=200, LEVEL_LAST=6 and APPROACH_TYPE=10 at
`--tick 9190 --fields 100`, with no later checkpoint. This route dies at
9212 and cannot reach tick 10800. Repeat with SLOW_DRAW=20 on the 68020.
`tools/natural_death_trace.py CAPTURE --listing EXACT.lst` checks guarded
native energy/flag instructions, simulation completion/exit, input restoration
and native death cleanup in order. It rejects subsequent simulation updates
or simulation rendering in that observed window. The exact listing and sibling
slave must match the retained capture. This does not check the Continue answer
or retry. Both CPU captures pass, with matching pre-death gameplay/HUD/fresh
projection; four altered-event negative controls are rejected in
`tmp/natural-death-validation.json`.

`RECORD_CACHE_SHIFT=4` now defaults on; 5 retains the preceding index.
It indexes the same tagged cache one address bit lower, using the same number
of instructions and no additional memory. Late-combat lookup means fall
248.38→116.97 cycles on A500 and 129.38→62.54 on 68020. Complete updates
fall 2.38%/2.20%, with matching gameplay/HUD/fresh projection at 4500/5400
and all six resets passing. The binary changes only two rotate opcodes. This
is retained despite the small total saving because each index is also cheaper
and adds no code, memory or lookup instructions. A500 still accumulates debt.


`PREFERENCES_TEST=200` drives the actual preferences screen and invokes a real
nested P dialog from its input poll. It waits at least twenty fields before
nesting, thirty inside the nested dialog, and ninety across the preferences
poll interval before selecting Done. `tools/preferences_state.py CAPTURE
--listing EXACT.lst` validates unchanged tick/debt, one outer clock rebase,
restored depth/render state and retained nonzero pre-existing credit.
`PREFERENCES_CHOICE=1..4`, with PREFERENCES_TEST, additionally selects one
native toggle (1 Mouse, 2 Joystick, 3 Music, 4 Sounds; buttons 2..5) before
Done. PF61 appends the selection count,
original value, returned value and option index; the checker requires exactly
one selection and a Boolean value change. The fixture writes only its own
record and supplies input, leaving the native handler to change the setting.
The Mouse toggle passes on A500 and delayed 68020: 1→0 persists through
tick 1500, modal entry/return stays at tick 200, and 32/30 owed updates are
retained. Gameplay/HUD/fresh projection, including all four preference words,
matches at ticks 201/600/1500. Results are in
`tmp/preferences-choice-validation.json`. Joystick, Music and Sounds each
also pass native 1→0 changes on A500 and delayed 68020, with matching
settings/gameplay/HUD/fresh projection at all three checkpoints. Every modal
entry/return remains at tick 200 and retains its existing 32/30 owed updates.
Those six captures and eighteen checkpoints are recorded in
`tmp/preferences-remaining-validation.json`. These checks cover turning each
setting off independently.

`PREFERENCES_SEQUENCE=1`, together with `PREFERENCES_TEST`, supplies native
buttons 2..5 twice, toggling all four settings and then restoring them. It is
mutually exclusive with `PREFERENCES_CHOICE`. The PF62 record contains nine
four-setting snapshots (initial and after every action); `preferences_state.py`
requires exactly the selected bit to change at each step, eight selections,
restored original settings and the existing nested-modal clock/debt invariants.
Capture tick TEST+1 and later gameplay checkpoints to check persistence.
The fixture writes only its record and supplies button selections. Build
exclusion and checker negative controls pass. Both selected CPU paths pass the
native dialog sequence, preserve tick 100 and modal credit, and retain the
restored preferences at ticks 101, 150 and 300. Evidence is under
`tmp/release60/preferences`.
The extension is byte-excluded from release; historical PF60 captures remain readable.

`PREFERENCES_BAD_CREDIT=1` deliberately clears that credit at modal return.
Both flags are byte-excluded without VERIFY. Both CPUs pass the real fixture,
retain 32/30 owed updates, and match fixture-free gameplay/HUD/fresh projection
at 201/600/1500. The broken build loses all 32 owed A500 updates and is
rejected. Results are in `tmp/preferences-validation.json`. Preferences choices
that actually change settings remain outside this no-change timing check.


`SCAN_FLAG_TEST=1`, combined with `SCAN_TWIN`, `SCAN_TEST` and `SHOT_TEST`,
adds all 256 actor-state byte values to each native collision comparison fixture.
Validate these captures with `tools/scan_state.py --flag-cases CAPTURE` and
`tools/shot_state.py --flag-cases CAPTURE`: totals are 324/320 cases instead of
68/64. The fixtures are excluded without VERIFY. Both CPUs pass the expanded
suite; mapped states match and all 89 installed hooks pass
(`tmp/scan-range-boundary-validation.json`).
The byte-range classification candidate is not part of the active implementation.
It reduces complete-update instruction costs by only 0.129% on A500 and 0.065%
on delayed 68020 in matched combat profiles. It does not meaningfully address
the outstanding backlog. Retained candidate sources are in
`tmp/scan-range-prototype/`; measurements and tick-1800/2400 state comparisons
are in `tmp/scan-range-profile-validation.json`. The playable release is
byte-identical to `tmp/scan-order-release.slave` after removing the candidate.

The stationary-star cache experiment is not part of the active build. Its
measured savings did not meet the full-frame threshold; retained experimental
sources and results are in ignored `tmp/stable-stars-prototype/` and
`tmp/stable-stars-validation.json`. There is no active STAR_STABLE option.

`tools/heading_lifetime.py CAPTURE --listing EXACT.lst` inventories explicit
native/slave memory operands that overlap observed actor heading words. It
supports indirect, brief indexed, displacement, absolute, increment/decrement
and MOVEM block spans; unknown instructions/modes are reported explicitly.
Six operand tests cover aliases, index sign/width, ordered address-register
updates, block spans and address-only instructions. Current A500/delayed-68020
traces contain 1053/1089 complete heading lifetimes, of which 1030/1065 have
no observed read before the next geometry write; eleven lifetimes per CPU
remain open at the trace end. No unsupported explicit operands occurred in
these traces. Injecting 1064 indirect reads reduces the A500 unread count to
zero; omitting producers exposes 42 reads without an observed producer.
`tmp/heading-lifetime-validation.json` retains results and controls. This is
not permission to defer headings: external code, implicit stack accesses,
actor allocation/reuse and unseen paths still need coverage, and current
mapped-state comparisons require up-to-date gameplay fields.

Add `--include-external` to inspect explicit operands in other executed code
mapped by the retained slow/chip snapshots. The decoder uses the capture CPU;
68020 MOVEC instructions are decoded rather than misreported as missing code.
The current A500/68020 windows add 70194/174166 external instructions with no
additional heading consumers and no unsupported decodes. An earlier late-combat
A500 trace has 930 unread values among 946 complete lifetimes. An earlier boss
trace has 653/770, three unlink events and two heading lifetimes crossing unlink
and later geometry reuse; no reads occur after unlink in those two completed
lifetimes. Unlinking does not stop the watcher, because references may survive.
That boss trace also includes 113 VERIFY pilot reads of prior enemy headings,
plus native readers at $10c00/$114a0. Fixture reads are not production behavior
but must be preserved or explicitly adapted in any future timing experiment.
These broader results are in `tmp/heading-lifetime-expanded-validation.json`.
They do not prove all allocation/reuse paths or implicit stack accesses safe.

`tools/return_entry_trace.py CAPTURE --listing EXACT.lst` separately checks
native/slave RTS, RTR and RTD transitions using the next observed PC and stack
adjustment. A profiler gap is bridged only if its snapshot exactly matches the
following instruction, D0–D7/A0–A6 are preserved across the return, and the stack
has the expected adjustment. It does not read stale snapshot return addresses
or infer CPU mode from SR. Only declared installed NOP padding may be entered
inside a patch. Discontinuous, missing-PC and trailing returns remain unverified;
exception returns and external-source returns are outside scope.
Current A500/delayed-68020 traces verify 23484/28843 transitions, including
0/10961 bridged gaps, and exclude 15/65 register-discontinuous boundaries.
Corrupted operand/odd-padding targets and mismatched gap snapshots are rejected;
changed stacks/registers and missing PCs are excluded. Results and controls:
`tmp/scan-order-return-gap-validation.json`. This is observed-path evidence,
not a whole-program return-address proof.

`tools/indirect_entry_trace.py CAPTURE --listing EXACT.lst` checks executed
indirect JSR/JMP effective addresses against compiled native patch interiors.
It verifies exact installed patches and supports address-register, displacement
and brief-indexed operands in native code and the loaded slave. Full-format
indexed operands fail explicitly. Targets are computed from recorded register
operands; this is not a whole-program control-flow proof. Returns, exceptions
and unobserved paths are excluded. Four retained combat traces cover 12116
executions, with no interior destination; a corrupted register target is
rejected (`tmp/indirect-entry-validation.json`).

`tools/patch_entry_trace.py CAPTURE --listing EXACT.lst` additionally checks
every observed PC against compiled patch interiors, without filtering by the
origin of a call, return or exception. It permits installed NOP padding,
including the explicitly guarded MULS/NOP flat-motion replacements. Missing-PC
records are counted as gaps. This verifies observed instruction destinations;
it does not validate exception-frame semantics or prove unobserved paths safe.

`tools/type9_firing_state.py CAPTURE --listing EXACT.lst` validates successful
native type-9 shot returns and the following channel-loop exit in the level-5
input-only approach route. Exact captures `sim60-type9-native-{020,a500,slow-020}`
match shots at 2052/3396 and all six mapped checkpoints through 3600. The checker
guards native code/table references, projectile ownership/position/lifetime,
cooldown initialization and full actor-state consequences. It rejects failed
allocations and the special firing variant rather than treating them as covered.
Reports: `tmp/type9-native-cross-validation.json` and
`tmp/type9-native-negative-validation.json`. All five reset records and 87
installed hooks pass; the normal build is restored. A single opening image from
the separate approach pilot was visually inspected; this is not animation or
audio validation.

`DEATH_NATURAL=1` with `DEATH_TEST=TICK` arms the existing death observer
without injecting negative energy. It records the current session and level,
answers the native Continue dialog, and checks reset state against the same
level in the next session. `tools/death_state.py --natural CAPTURE` reads its
RN61 extension; the legacy `injection_tick` result field is the arming tick in
this mode. Combining it with LEVEL_TEST requires an arming tick later than the
requested transition tick. Injected death plus LEVEL_TEST, and natural death
plus DEATH_DECLINE, remain rejected. Release exclusion, unchanged preceding
encounter bytes and three rejected configurations are recorded in
`tmp/natural-retry-build-validation.json`. All three configurations (normal
68020, A500 and twenty-field-delayed 68020) arm at tick 9000 and observe death
at 9212 with energy -80. Continue returns to level 6/session 8, restoring energy
680, credit 60, zero tick/render/phase counters and cleared private timing
regions. Both post-retry gameplay/HUD/fresh-projection checkpoints 600/1500
match, allowing only projection scratch; six prior level resets and 88 installed
patches pass on each configuration. Nine corrupted-record controls fail. See
`tmp/natural-retry-cross-validation.json` and
`tmp/natural-retry-020-validation.json`. The normal build is restored.

`AI_GEOMETRY_FUSED` now defaults to one within experimental SIM60, sharing
distance/heading setup at native $ee44. Set it to zero for the preceding baseline. `GEOMETRY_TWIN=1` compares the existing setup
sequence and the candidate on every call, including all fifteen register outputs,
CCR and actor distance/heading. `GEOMETRY_TEST=100` adds 128 synthetic coordinate
cases at tick 100 (axes, signed-word boundaries and signed-long wraparound with
two view origins). `GEOMETRY_BAD=1` deliberately corrupts distance under VERIFY.
`tools/geometry_state.py CAPTURE --listing EXACT.lst --boundaries` requires all
128 cases and no mismatches. The first combat-only 68020 build passes 29016
comparisons and two mapped-state checkpoints (`tmp/geometry-twin-020-validation.json`).
A500 and 68020 each pass 842 comparisons including all 128 boundary cases;
a deliberately bad distance produces 842 mismatches. Mapped boundary gameplay
matches across CPUs and 88 installed hooks pass. The release static audit covers
88 patches/68 merged ranges with no conservative direct interior entry. Diagnostic
flags are byte-excluded without VERIFY; the default release is unchanged. See
`tmp/geometry-boundary-validation.json`, `tmp/geometry-build-validation.json`
and `tmp/geometry-release-hook-audit.json`. The early replacement-only A500
window reduces sampled update means 95212.49→93032.24 cycles (2.29%) with
matching gameplay/HUD/fresh projection at 1800/2400. Its 600-tick interval uses
573 fields and six presentations versus 570 fields and five; both repay debt.
See `tmp/geometry-early-a500-validation.json`. Late A500 sampled update means
fall 94246.69→92036.74 cycles (2.34%); delayed 68020 falls 49310.33→48634.60
(1.37%). Gameplay/HUD/fresh projection matches at 4500/5400 on both, allowing
only deferred projection scratch, with six resets and 88 hooks verified.
A500 uses 855 fields for 900 ticks versus 876, with five presentations in each;
pending debt falls 163→118 versus 180→156. Delayed 68020 uses 901 versus
899 fields, with 28 presentations each. These are catch-up intervals and
sampled cost windows, not proof of sustained throughput. See
`tmp/geometry-late-a500-validation.json` and
`tmp/geometry-late-020-validation.json`. The three candidate traces also pass
indirect-entry checks over 8636 executed JSR/JMP destinations with all 88 hooks
verified (`tmp/geometry-{early-a500,late-a500,late-020}-indirect.json`). This
covers the observed address-register/brief-indexed calls and jumps, not returns,
exceptions or unseen paths. The extended encounter matches gameplay/HUD/fresh
projection against the preceding build and across A500/delayed 68020 at all
eight checkpoints through native death at tick 9212, allowing only deferred
projection scratch. A500 heavy ticks 600–5400 average 58.87 updates/s with
66 presentations and debt 26→118; the whole 600–9212 interval averages 59.65
with 109 presentations and debt 26→76. Delayed 68020 averages 60.07 across
that whole interval with 271 presentations and debt 25→15. This remains below
sustained realtime on the heavy A500 route. Six resets and 88 installed hooks
pass on each CPU, and the normal build is restored in the saved report:
`tmp/geometry-extended-validation.json`. The default SIM60 release is byte-identical
to the explicitly enabled audited candidate (`tmp/geometry-default-enabled.slave`
and `tmp/geometry-release.slave`). With CUSTOM1 off, both CPUs preserve all 151969 checked original-code bytes,
including all 88 compiled simulation patch ranges, with zero unexpected
changes. The six audited mutable code-hunk data areas remain separate; 4833
relocations and exact menu-fixture patches are checked. The normal build is
restored byte for byte. See `tmp/disabled-geometry-validation.json`.

`tools/vertex_cache_lifetime.py CAPTURE` guards native validity resets,
transformed-coordinate producers and projected-coordinate producers/consumers.
It uses trace register values for direct, signed-word-indexed and long-indexed
addresses. Early A500, late A500, delayed 68020 and boss A500 captures pass
3614 reads after initialization in the same cache epoch: 2554 transformed and
1060 projected coordinate reads, with 2294 writes across 27 epochs. No prefix
accesses were excluded in these four traces. The native full-width transform
writes at $17f84/$17f96/$17fa8 are included alongside the earlier producers.
A copied trace omitting projected writes is rejected at a projected-coordinate
read. See `tmp/vertex-projection-lifetime-validation.json`. Clipping consumers
and producers whose sites are listed but not executed are not validated by
these traces; the report records actual sites. Other scratch consumers and
unseen rendering-to-simulation paths remain outside this check.

The retained N=12 SIM60 type-10 combat route passes `NTSC=0` with
Exec reporting 50 Hz. Matched gameplay/HUD/fresh projection at ticks 1800/2400
agrees with its NTSC counterpart, allowing only deferred projection scratch;
all six resets and 88 hooks pass. Exact scheduler credit conservation uses
60 credits per elapsed field and 50 credits per completed update. See
`tmp/geometry-pal-validation.json`. The underlying game is still NTSC; this
checks the advertised 60 Hz timestep under PAL fields, not audiovisual parity.


### Input timing regressions

`INPUT_NEUTRAL_TEST=100` checks fifteen signed neutral-turn velocities across
all twelve starting phases against the original native braking fragment.
`INPUT_NEUTRAL_OLD=1` is its VERIFY-only negative control. The native input
encounter uses `PREFERENCES_TEST=200 PREFERENCES_CHOICE=2 INPUT_NEUTRAL_PLAY=300`
(with each option passed as an assembler `-D` flag), releasing direction at
completed tick 420. Choice 2 disables the native joystick fallback needed to
exercise this braking path.

`FRICTION_TEST=100` checks 2592 copied native terrain-input fragments, including
contact gaps, rendering, inactive behavior and tick rollover. Read the exact
build with `tools/terrain_friction_state.py CAPTURE --listing LISTING`.
`FRICTION_OLD=1` is the VERIFY-only negative control. The normal release excludes
both flags' diagnostic behavior. The direct contact observer's retained captures
are checked by `tools/terrain_friction_encounter.py CAPTURE --listing LISTING`;
these use explicit boss-state selection followed by native allocation/contact.
ABI 29 and later include the independent friction clock to mapped-state comparisons. Unknown
SIM60 state ABI versions fail instead of silently dropping private timing state.


### Input constant updates

`INPUT_QUANTA_UNROLL=1` enables direct per-tick stores generated from the same
sixteen-site list as the guard/restore table. It now defaults on within SIM60;
zero restores the table walk. With `SCAN_GEOMETRY_FIRST=0`, it reproduces
the preceding input-fixed release bytes. Cache flushing stays enabled.
With VERIFY, `QUANTA_TEST=100` compares the entire 558-byte input region with
the preceding table-loop updater at each of twelve phases. Original constants
are restored before each candidate call so skipped stores cannot inherit the
reference's values. `QUANTA_BAD=1` corrupts one immediate per phase as a negative
control. Read QI60 with `tools/input_quanta_state.py CAPTURE --listing LISTING`.
Native neutral braking is independently checked by INPUT_NEUTRAL_TEST.
