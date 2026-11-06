# Hard Drivin’ development

The slave source is `src/` (`HardDrivinHD.s` is authoritative), from JOTD's
`whdload_slaves` at `7003fc6fa65634d5affc55d6e5acac0d1e83dccb` (`H/HardDrivin/usr`), with
this work's history on top. `tools/` is the development harness; it never ships. It keeps
the tools this document and `ARCADE_HANDLING_PLAN.md` use; the one-off checks, captures and
reports that the step documents and old log entries name were removed on 2026-11-06 and are
in git history before that date. Every command below runs in the game directory
(`games/HardDrivin`), and paths are relative to it.

Follow AmigaXDev `docs/playbooks/new-game-playbook-jotd.md`. Read this document,
`internals.md`, then `open-work.md` when continuing.

## Inputs

- Install page: https://whdload.de/games/HardDrivin.html
- Installer: `HardDrivin.lha` from the install page
- Full installation: the Retroplay `HardDrivin_v3.0_0126.lha`
- Arcade ROM set: MAME's `harddriv.zip`, for `tools/arcade/` only

`inputs.sha256` pins all three; `make unpack ARCHIVES=<directory>` copies them to
`tmp/archives/` and unpacks each Amiga archive into a drawer named after it (`game.sh`
`game_unpack`): the installed game is `tmp/game/HardDrivin_v3.0_0126/HardDrivin`, with
`HardDrivin.Slave` and `data/HardDrivin`, and the installer is
`tmp/game/HardDrivin/HardDrivinInstall`. `harddriv.zip` stays packed in `tmp/archives/`,
which `tools/arcade/mame/run.sh` gives MAME as its ROM path. Installer sources are
reference material; edit only `src/`.

## Build

`make slave` builds the release slave to `tmp/build/release/HardDrivin.Slave` (vasm
`-pic`, against the NDK 3.2 includes: `game.conf` sets `NDK`); `make check` compares it
with `release/slaves.sha256`. The diagnostic builds are VERIFY_* defines:

- `make verify` takes them from `VERIFY_FLAGS`, by default `-DVERIFY_HANDLING_MATH=1`
  (`make verify VERIFY_FLAGS='-DVERIFY_ATTRACT=1 -DVERIFY_CEILING=1'`);
- `make build BUILD=attract` is VERIFY_ATTRACT, `BUILD=development` HD_DEVELOPMENT;
- `make build BUILD=name VASM_EXTRA='-D... -L tmp/build/name.lst'` builds any other set.

The harness names its builds by output file: `OUTPUT_SLAVE=tmp/build/NAME.slave
tools/build.sh [flags...]` runs the same build (`tmp/build/tool_NAME/`) and copies the slave
to `OUTPUT_SLAVE`; the commands below use it. Flags are word-split, so listing paths must
not contain spaces. Tools that assemble by themselves (`build_feel.py`, the C4 probes, the
Unicorn checks) need the shared environment with the NDK 3.2 includes: `. tools/env.sh`
first. Lists of plans or environment settings kept in a shell variable must be word-split:
zsh does not split `$N`, so use `${=N}` or run the line through `/bin/bash -c` (the same
for `env $envs` in the MAME sessions). A failed capture leaves `tmp/prof/ROOT/NAME`
behind and the rerun stops with `FileExistsError`: delete it first. A run killed by
`timeout` can leave its FS-UAE running; stop only process IDs verified to belong to that
run's instance directory. The VERIFY_DRIVE builds (and VERIFY_SLOW with them) no longer assemble at the
current source: `HardDrivinPhase.s` line 20 is out of displacement range with the drive
fixture.

## Run

```sh
make run SLAVE=original FSUAE="$FSUAE_ARM" WAIT=1   # the shipped slave
make run                                            # the release build
make aja                                            # A1200/040, CUSTOM1=2 CUSTOM5=2 (tools/aja.sh)
```

`common/run.sh` boots a disposable copy of the installed drawer from
`tmp/run/<INSTANCE or default>/.run/`, with the shared process helper. The machine is
`game.conf`'s: PAL A500, 68000, 512 KiB chip, 1536 KiB slow and no fast RAM, windowed with
sound and the mouse on port 0. `WAIT=1` keeps an automation terminal attached. The native
arm64 emulator (`FSUAE_ARM`) was selected after the x86_64 launch reported drawable-size
errors. `tools/harddrivin.py serve` boots through the same launcher with the gdb stub
(`DEBUG=1`); the capture tools start it themselves. Screenshots go to `tmp/shots/`.
The attract benchmark and rebuilt-slave comparison are documented below and in
`internals.md`; real-gameplay verification uses the separate VERIFY_DRIVE fixture.

Memory writes through the stub (`gdb set {short} ADDR = V`) are acknowledged but do not
reach the emulated memory: read the address back, or use `harddrivin.py poke ADDR HEX
SIGHEX SIGADDR`, which writes through lldb and prints `VERIFIED`. Its first call after
`serve` can fail while lldb attaches, so retry once. Breakpoints, `x` and `dump memory`
through the stub work.

## Repeatable attract benchmark

The validated A500-equivalent baseline is in `tmp/prof/benchmark-report.txt`.
Two fresh-boot captures contain 1,000 consecutive PAL fields each (20.031887 s),
with identical instructions, DMA, screenshots and before/after memory. Independent
read-only breakpoint counting reproduces all 129 buffer swaps field-for-field.

From the game directory:

```sh
. tools/env.sh
OUTPUT_SLAVE=tmp/build/HardDrivin-verify.slave tools/build.sh -DVERIFY_ATTRACT=1
python3 tools/capture_demo.py tmp/prof/NEW-RUN-NAME
```

The capture script requires a new output directory, retains its exact slave and
input hashes, disables host inputs and uses the shared x86_64 debugger-capable
emulator. `PROFILE_FSUAE` overrides that binary, but its host-profiler control is
binary-specific and guarded by an instruction-byte assertion. Host LLDB attachment
may take minutes. Capture timing comes from emulated CPU clocks, never host time.
The profiler's 100-field clamp is extended by a one-shot host debugger action;
its log is retained and the trace header must confirm all requested fields.

`tools/compare_profiles.py FIRST SECOND` compares all recorded fields and full
before/after snapshots; paths are relative to the caller. `tools/harddrivin_report.py`
provides call-target-aware self/inclusive attribution, with the run's slow-before
snapshot and `--base 0xc00000`. `tools/hardware_metrics.py RUN` reports the exact
blitter-wait range cost. The independent `tools/count_demo_swaps.py` takes a new output directory and
a named `--profile`; it refuses to overwrite an existing capture.

The benchmark uses VERIFY_ATTRACT, which supplies one title-screen key and is
absent from normal builds. Its first clean cockpit at game offset $10844 matches
the user's screenshot. Normal gameplay code is unchanged. The current scripts recalibrate the code/global addresses on every invocation
and reboot with the anchor armed. Use `--profile` to select a named machine.

## Repeatable gameplay windows (step 1, items 1–3)

From the game directory:

```sh
. tools/env.sh
OUTPUT_SLAVE=tmp/build/HardDrivin-drive.slave tools/build.sh -DVERIFY_DRIVE=1 -L tmp/build/drive.lst
python3 tools/capture_drive_fields.py NEW-DRIVE-RUN1 6000
python3 tools/capture_drive_fields.py NEW-DRIVE-RUN2 6000
python3 tools/analyse_drive_fields.py tmp/prof/NEW-DRIVE-RUN1 tmp/prof/NEW-DRIVE-RUN2
python3 tools/analyse_drive_fields.py tmp/prof/NEW-DRIVE-RUN2
python3 tools/validate_drive_windows.py tmp/prof/NEW-DRIVE-RUN1 tmp/prof/NEW-DRIVE-RUN2
```

Run names must be new directories. The tool is intentionally limited to the fixed
A500 layout and asserts the game address and a4 at native race entry. It locates
fixture state from the slave publication and assembly listing; never reuse a listing
from another build. Captures run sequentially using only this harness's owned PIDs.
No LLDB memory injection is needed for the frozen tape. Source comments define A
[1,1251) and B [3000,5600); both require the full preceding tape from a fresh boot.
The accepted pair is `drive-a500-jump1` / `drive-a500-jump2`. See `internals.md` for
counts, event evidence, exact equality scope and the rebuilt-versus-shipped caveat.

`render_drive_frame.py RUN FIELD...` decodes captured front buffers for visual
review using the retained palette. `drive_session.py`, `record_route.py`,
`host_poke.py` and `freeze_drive.py` are calibration tools, not required for replay.
Do not rerun the freezer casually: it reconstructs the calibrated inputs and would
replace the curated source comments. The input tape in source is authoritative.

## Slowed-drawing instrument (step 1 item 4)

```sh
. tools/env.sh
OUTPUT_SLAVE=tmp/build/HardDrivin-slow.slave tools/build.sh -DVERIFY_DRIVE=1 -DVERIFY_SLOW=1 -L tmp/build/slow.lst
python3 tools/check_slow_delay.py 4 NEW-HOOK-CHECK
DELAY_FIELDS=0 python3 tools/capture_slow_drive.py NEW-ZERO 1251
DELAY_FIELDS=4 python3 tools/capture_slow_drive.py NEW-FOUR1 1251
DELAY_FIELDS=4 python3 tools/capture_slow_drive.py NEW-FOUR2 1251
python3 tools/analyse_drive_fields.py tmp/prof/NEW-FOUR1 tmp/prof/NEW-FOUR2
```

For manual launching, use the VERIFY_SLOW slave and `WHD_ARGS="CUSTOM4=4"` with
the existing launcher. Values 1–255 select extra VBLs; larger values saturate at
255, and zero leaves the two game ranges unpatched. The two VERIFY input fixtures
remain mutually exclusive. Large delays can invalidate their fixed menu timings;
use the hook checker (which anchors before menu input) for boundary tests.

## Generalized step 1 harness

From the game directory, source `tools/env.sh`. All output arguments below are
relative to the game directory, must be new directories below `tmp/prof/`, and must not
contain spaces (GDB's dump command limitation). `--slave` should be absolute when overriding the default build.

```sh
python3 tools/capture_demo.py tmp/prof/NEW-ATTRACT --profile a1200-020 --fields 1000
python3 tools/count_demo_swaps.py tmp/prof/NEW-COUNTER --profile a1200-020 --fields 1000
python3 tools/summarize_profile.py tmp/prof/NEW-ATTRACT/trace.bin --out tmp/prof/NEW-ATTRACT --counter tmp/prof/NEW-COUNTER/counter.json
python3 tools/state_fields.py tmp/prof/NEW-STATE1 --profile a500 --fields 6000
python3 tools/state_fields.py tmp/prof/NEW-STATE2 --profile a500 --fields 6000
python3 tools/compare_state.py tmp/prof/NEW-STATE1 tmp/prof/NEW-STATE2 --domain vbl
python3 tools/compare_state.py tmp/prof/NEW-STATE1 tmp/prof/NEW-STATE2 --domain physics
python3 tools/capture_disabled.py tmp/prof/NEW-OFF --slave "$PWD/tmp/build/HardDrivin.Slave"
python3 tools/check_disabled.py tmp/prof/NEW-STATE1 --enabled VERIFY_DRIVE
```

Profiles: `a500`, `a500-fast`, `a1200-020`, `a1200-030-50`,
`a4000-040-25`, `a4000-040-40`, `a4000-060-50`. On 030 and above,
`capture_demo.py` produces `counter.json` instead of an unsupported instruction
trace. `--swap-only` or `SWAP_ONLY=1` forces that path on the other profiles too.
Trace captures support 1–1100 fields; swap/state captures can be longer. `SERVE_WAIT`
overrides the calibration/anchor boot deadline. State runs default to the drive
fixture; `--custom4 N --slave ABSOLUTE-SLOW-DRIVE-SLAVE` selects the coupling
instrument. Guest state is read only by these tools.

`compare_state.py --relocate` explicitly permits matching game-hunk-relative
pointers after a layout change. It does not normalize heap/OS pointers, ignore
clocks or drop unknown state. Inspect reported differences rather than broadening
masks until tests pass. Keep per-field and per-physics-step comparisons separate.
The `vbl-state.json` and `physics-state.json` files decode selected state as raw
big-endian hex; complete `.bin` snapshots are the comparison source.

The disabled checker has no emulator side effects on an existing capture. Declare
only gates actually enabled at runtime. For VERIFY_SLOW with CUSTOM4=0, do not
pass `--enabled VERIFY_SLOW`: the point is to prove both sites are original.
Current overlap is the shared title site of VERIFY_ATTRACT and VERIFY_DRIVE.
`test_step1_tools.py` contains the comparison/checker failure-path tests.

## Step 2 collection and reporting

The full matrix uses `baseline_capture.py PROFILE attract NAME` twice and
`baseline_capture.py PROFILE drive NAME` once per profile. `summarize_baselines.py`
requires exact fresh-attract equality and disabled-range checks before including
a row in `tmp/prof/step2-baselines.json`. Baselines retain complete globals/BSS
and front screens every field. Fast profiles count front-pointer flips at VBLs;
this is checked against explicit swap breakpoints on the 000/020 captures.

The user selected 500-field (10.015944 s) CPU/DMA gameplay samples, rather than
profiling the full long windows. `profile_gameplay.py PROFILE A|B|attract NAME`
starts A at race field 1, B at 4300 after replaying the complete preceding tape,
and attract at the cockpit anchor for 1000 fields. `window_metrics.py` reads the
retained source-matching listing, loaded banks and trace cycle unit. It reports
complete physics calls, call-target self/inclusive shares, exact wait ranges,
DMA slot types and representative images. Unsupported CPU instruction timing and
fast-core blitter DMA slot recording are explicitly unavailable. Completed matching
capture directories can be reused; an incomplete existing directory is rejected.

Independent emulator jobs MUST use distinct `INSTANCE` values. The launcher
uses a different working directory, runtime socket and owned PID files for each,
not just a different port. The shared process helper reclaims same-directory
instances. Do not run two jobs with the same INSTANCE at once.

A local profiler executable under `tmp/profile-emulator/` removes per-boot LLDB
attachment. `prepare_profile_emulator.py` verifies the original executable hash
and two instruction ranges, and changes only the capture address range and
100-field limit; it records both executable hashes and the exact patch bytes.
Use `PROFILE_FSUAE` pointing at this local copy and `HD_PROFILE_DIRECT=1`.
The server checks those patched bytes before using the direct path. The first
100 A500 fields match the prior profiler's instructions, DMA, screenshots and
cycle totals exactly (`s2-profiler-validation/equivalence.json`). This does not
change any guest CPU, DMA or timing implementation. The original debugger-assisted
capture path remains available without that flag.

Trace and snapshot streams are archived with zstd; uncompressed SHA-256 values
are retained. `barto_mmap.py` reads either trace.bin or trace.bin.zst, decompressing
the latter into a private temporary file inside its capture directory. Leave
room for the full uncompressed trace when analyzing archives. `trace_fingerprints.py`
stores every field's instruction/DMA/screenshot hashes and cycle count, allowing
repeat checks without keeping two decompressed traces in memory or on disk.

Build the diagnostic slave variants through the normal build wrapper:

- Cache audit: `-DVERIFY_CACHEAUDIT=1`, then `cache_audit.py PROFILE` with the
  resulting `tmp/build/s2-cache-audit.slave`. It logs setup and hardware CACR via
  WHDLoad FILELOG and exits; it is never used in a performance capture.
- Matched ceiling control: `-DVERIFY_ATTRACT=1 -DVERIFY_CEILING=1`.
- Polygon bypass: the same flags plus `-DVERIFY_NOPOLY=1`.
- Capture ceilings with `baseline_capture.py ... --slave ABSOLUTE-SLAVE`;
  use `--instant-blitter` with the matched control for the instant case.
- `mmu_functional.py` uses separate 040/060 MMU-enabled gameplay boots and labels
  all resulting counts functional-only, not timings.

`document_step2.py` generates the tracked PERFORMANCE.md tables from completed
JSON evidence. It requires all seven baselines and all sample reports. Source
and document changes are committed; local tools and raw evidence stay ignored.

## Step 3 coupling and timing audit

Build s3-coupling.slave with VERIFY_DRIVE + VERIFY_SLOW and its matching listing.
`capture_coupling.py PROFILE NAME --delay N` captures 1251 after-input boundaries
plus controls/physics entry and exit. For matched-input controls, add
VERIFY_STEPINPUT and build s3-stepinput.slave; `capture_stepinputs.py PROFILE NAME`
collects 108 complete returns. The fixture changes input only; do not substitute
guest GDB writes, which this stub silently failed to apply. Every run recalibrates.
Use separate INSTANCE values for concurrent instances.

`step3_compare.py`, `step3_costs.py` and `step3_validate.py` check the retained
captures and unchanged builds. The extra impact trace is 500 fields from race
field 1900; its whole-window swaps match the independent baseline field-for-field.
Current local evidence names and full inventory are in open-work.md. Normal,
VERIFY_DRIVE and VERIFY_ATTRACT hashes are unchanged; source adds only the gated
VERIFY_STEPINPUT experiment. See GAME_TIME.md for the f0 recommendation and its
low-confidence engineering range, native clock defects and substep cost limit.


## Step 4 timing foundation (incomplete)

VERIFY_TIME + CUSTOM1=1 installs only the elapsed-field observer; it does not
scale gameplay. VERIFY_TIME_MATH adds the boot arithmetic fixture. Combine
VERIFY_DRIVE with VERIFY_TIME_PAUSE for native keyboard pause/resume, or with
VERIFY_TIME_REPLAY for button release during native crash/replay. Build outputs
must remain under tmp/build. capture_time.py and check_time_math.py retain the
local evidence; see GAME_TIME.md and open-work.md for current test names and
remaining implementation. Normal builds remain unchanged.

The scalar module is a development-only constant-T experiment: build
VERIFY_TIME + VERIFY_TIME_SCALARS, optionally VERIFY_SCALAR_FIELDS=1..8 (default8).
VERIFY_DRIVE + VERIFY_STEPINPUT supplies matched inputs. VERIFY_STEPINPUT_RAMP
exercises both throttle directions; VERIFY_TIME_SCALAR_MATH exercises retention
in private fake globals. Current helpers/capture formats are in open-work.md.
Do not use these partial builds to claim frame-time-independent gameplay.

VERIFY_TIME_MOTION adds angular-rate and gravity-acceleration diagnostics on top
of TIME_SCALARS. VERIFY_MOTION_MATH tests private angle/spin/fall cases.
VERIFY_STEPINPUT_X=400 selects nonzero held steering; default remains320.
check_patch_branches.py audits direct branches into all scalar/motion ranges.
Ordinary position now has signed carries and a tested Euler correction.
check_position_hooks.py checks live ordinary-position operands;
check_fall_position_hooks.py checks falling displacement. Crash drift and
countdowns have math/native-state evidence; contact and fractional projection remain. See motion-next.md for the remaining unimplemented design.

VERIFY_CONTACT_MATH (requires TIME_MOTION) tests wide contact-response/projection
and actual contact/rate/reset routines with check_contact_math.py. Live hooks are
connected; VERIFY_CONTACT_TRACE records consumed inputs for check_contact_hooks.py.
Use short INSTANCE names to stay below the Unix socket path limit.

VERIFY_PROJECTION_MATH (requires MOTION) uses check_projection_math.py for the
fractional velocity projection/Euler arithmetic. check_projection_hooks.py checks
the full T=1/8 position path from live memory operands.

VERIFY_TIME_TRAFFIC requires TIME_SCALARS and enables elapsed-time traffic hooks
with CUSTOM1. check_traffic.py captures and models all records/poses;
VERIFY_TRAFFIC_MATH and check_traffic_math.py test reversals and initialization
in private memory. Companion storage uses the native record count.

## Per-frame cost budget (step 4 closure)

Build both slaves with `tmp/build_reference.sh NAME -DVERIFY_DRIVETRAIN_PHASE=1 -L
"$PWD/tmp/build/NAME.lst"`. For window A, add `-DVERIFY_STEPINPUT=1`; window B uses
the tape alone. Capture with `PROFILE_FSUAE="$PWD/tmp/profile-emulator/fs-uae"
HD_PROFILE_DIRECT=1 INSTANCE=UNIQUE python3 tools/capture_solver_profile.py RUN
--slave NAME.slave --listing NAME.lst --custom1 0|1 [--first-field 4000]`, then run
`python3 tools/frame_budget.py RUN...`. It writes `frame-budget.json` per run. The
G1 overhead definition is in STEP4_COST_PLAN.md section 1.

## Arcade handling (CUSTOM1=2, ARCADE_HANDLING_PLAN.md step G)

`HardDrivinHandling.s` runs the two-wheel model once per PAL field when CUSTOM1=2. The normal
build includes it (`VERIFY_HANDLING` in Release.i); `-DVERIFY_HANDLING_MATH=1` adds the boot
fixture. From the game directory, with `tools/env.sh` sourced:

```sh
OUTPUT_SLAVE=tmp/build/g-handling.slave tools/build.sh -L tmp/build/g-handling.lst
OUTPUT_SLAVE=tmp/build/g-handling-math.slave tools/build.sh -DVERIFY_HANDLING_MATH=1 -L tmp/build/g-handling-math.lst
python3 -I tools/check_handling_step.py tmp/build/g-handling.slave tmp/build/g-handling.lst
python3 -I tools/check_handling_math.py NEW-RUN
python3 -I tools/check_installed_code.py NEW-RUN OLD.slave OLD.lst NEW.slave NEW.lst --custom1 0|1
python3 -I tools/run_feel.py ROOT --custom1 2 --tag TAG
python3 -I tools/compare_feel_records.py OLD_ROOT NEW_ROOT
```

The tools do the following:
- `check_handling_step.py` runs the slave's `_handling_step` in Unicorn against
  `tools/arcade/handling_fx.py`, step by step.
- `check_handling_math.py` boots the fixture in FS-UAE (A500, CUSTOM1=2) and compares its
  checksums with the twin. `--unicorn` checks the script's mirror instead.
- `check_installed_code.py` compares the live game code two slaves install at the title screen.
  It allows patch calls to the same slave label, and game addresses moved by the load base.
- `run_feel.py --tag` keeps concurrent matrices on distinct INSTANCEs.
- `build_feel.py --source DIR --pad N --prefix P` builds control fixture slaves from another
  source tree, padded to a given size.
- `compare_feel_records.py` compares two matrices byte for byte.

## Arcade handling validation (ARCADE_HANDLING_PLAN.md step H)

From the game directory, with `tools/env.sh` sourced:

```sh
python3 tools/build_feel.py lap-main lap-stunt lap-jump lap-loop lap-offroad h2-brake-turn
INSTANCE=lap1 python3 tools/capture_feel.py tmp/prof/ROOT/lap-main --plan lap-main --custom1 2 --max-fields 20000 --timeout 1800
python3 tools/lap_report.py ROOT/lap-main [ROOT/RUN...]
PROFILE_FSUAE="$PWD/tmp/profile-emulator/fs-uae" HD_PROFILE_DIRECT=1 INSTANCE=prof1 \
  python3 tools/capture_solver_profile.py NEW-RUN --slave feel-c1c-60.slave --listing feel-c1c-60.lst --custom1 2 --first-field 600
cd tools && python3 frame_budget.py NEW-RUN
python3 -I tools/arcade/brake_sim.py ROOT [--torque T] [--old]
```

- **Laps:** the `lap-*` plans drive the real course with `feel_fixture.s`'s FE_FOLLOW: pure
  pursuit along the road sections' centres (`tmp/track-geometry.json`), with a speed
  profile. Unlike the step F plans they keep the native start and the native grass
  rules. `lap-jump` and `lap-loop` start on the stunt road at 112 MPH, as the step 4 probes
  seeded it, and `lap-offroad` drives 350 units right of the road.
- **Crashes:** crashes, replays and recoveries run their course with the buttons released,
  and the driver then finds the route again. Run with `--max-fields`, since a lap that
  times out stands still until then.
- **`lap_report.py`** prints how far each run got and its distance from the route. It
  lists flights, crashes and recoveries, replays, the loop's pitch and checkpoint bonuses.
  The contact mask is unreliable inside the loop, so flights there read long.
- **Cost:** `capture_solver_profile.py` accepts `--custom1 2`, and `frame_budget.py` reports
  `_handling` as a module. A trace is 2.4 GB: once `frame-budget.json` is written, the raw
  trace can be replaced by its hash.
- **`brake_sim.py`** replays a matrix's brake runs through `handling_fx` with other brake
  mappings, for quick trials before a build.

H3 round 1 (runaway spins) added:

```sh
python3 tools/build_feel.py --source OLD_TREE --prefix feel-old- h3-spin-60-counter ...
python3 tools/run_feel.py ROOT --custom1 2 [--prefix feel-old-] --tag TAG h3-spin-60-counter h3-spin-60-half h3-spin-60-centre h3-spin-90-counter h3-spin-90-half h3-spin-90-centre
python3 tools/spin_report.py ROOT
python3 -I tools/arcade/spin_sim.py MPH FX STEER_S centre|counter|half|hold [--old]
cd tools && INSTANCE=UNIQUE python3 fault_probe.py NEW-RUN --plan NAME --field N [--slave RUN/slave.slave]
```

- **`h3-spin-*`** plans: full throttle and full lock, then countersteer or centre, throttle held.
  `spin_report.py` prints their yaw rate, heading and speed every half second.
- **`spin_sim.py`** runs the same manoeuvre through the twin with the game's speed feedback,
  or G's rule with `--old`.
- **`fault_probe.py`** replays a deterministic fixture run to a record and stops at the first
  fault handler (bus/address error, illegal, zero divide, CHK, TRAPV, line A/F). It writes the
  registers, the exception frame and the memory at the fault. Map the PC to the slave by
  finding `HDHAND01` in the slow-memory dump and the listing.
- **The twin's force rule:** `handling_fx.FxCar.step(..., fx_total=False)` is the game's (the
  rear gets the force less the front wheel's own longitudinal force; `car.du` is the speed the
  step adds). The default `fx_total=True` is E2/E3's, for the arcade replays.
  `check_handling_step.py` and `check_handling_math.py` use the game's rule;
  `handling_fx.py sweep N --drive` sweeps it.

H3 round 2 (spins that never stop, roll-overs on slopes) added:

```sh
python3 tools/build_feel.py h3-curve-hold h3-rollover h3-bank-right ...
python3 tools/run_feel.py ROOT --custom1 2 --tag TAG h3-curve-hold h3-rollover h3-bank-right
python3 -I tools/tilt_report.py tmp/prof/ROOT/RUN [--every N] [--from F]
cd tools && python3 -I check_handling_turn.py SLAVE LISTING RUN
python3 -I tools/arcade/replay_run.py RUN          # a run's speed and mouse through the twin
python3 -I tools/arcade/donut_sim.py MPH YAW [--fx FX | --k K]
```

- **Route plans:** `build_feel.py`'s `ROUTE_OF` gives any plan a route (native ground rules,
  no bounds). A route's `seed` can be on the main road (`MAIN`: the road cursor only, so the
  race's progress messages are wrong), and seeds take the section's centre height (`Y`). A
  route's `at` gives a place: X, Y, Z, heading, velocity.
- **The plans:**
  - `h3-curve-*`: the drive's spin, in the curve after the bridge at 100 MPH.
  - `h3-rollover`: round 1's roll-over, seeded at its field 8150.
  - `h3-bank-*`: the stunt road's 46° bank.
  - `h3-hill-spin`, `h3-dip-spin`: the main road's slopes.
- **`model.bin`:** HDFEEL03 fixture slaves also log the first 80 bytes of `_handling_state`
  after each pass (zero unless CUSTOM1=2); `amiga_feel.models(run)` decodes it next to
  `steps(run)`.
- **`check_handling_turn.py`** runs `_handling_turn` in Unicorn with the game's own sine code and
  table from RUN (any capture with `game-code.bin` and `game-data.bin`), against a model.

H3 round 3 (braking) added:

```sh
python3 tools/build_feel.py h3-brake-floor-60 h3-brake-floor-100
python3 tools/run_feel.py ROOT --custom1 2 --tag TAG h3-brake-floor-60 h3-brake-floor-100 c1b-full
python3 -I tools/brake_report.py tmp/prof/ROOT/RUN...    # time to stop, deceleration per 20 MPH
python3 -I tools/brake_events.py tmp/prof/ROOT/RUN...    # each brake in a lap, and any spin after it
```

- **`h3-brake-floor-*`:** full throttle from rest (the throttle opens at 2 per native step, so
  31 at 57 MPH and 87 at 100), then both buttons until the car stands still.
- **`brake_events.py`** needs `model.bin` (HDFEEL03 slaves).

H3 round 4 (the jump) added:

```sh
C4_VELOCITY=300 C4_THROTTLE=100 python3 tools/build_c4_geometry_probe.py NAME jump_clear
python3 tools/hang_probe.py tmp/prof/OUT --plan lap-jump --custom1 2 --records 13800 --gdb FILE
```

- **`C4_VELOCITY`** seeds the probe's speed (G($9928), default 400, 0.28 MPH a unit);
  `C4_THROTTLE` the held throttle.
- **`C4_FORCE_RATE`** (C4 probes) and **`FEEL_FORCE_RATE`** (`build_feel.py`) make every
  rear-only contact pass set the pitch rate to N units per native step: experiments only.
- **`hang_probe.py`** runs a feel plan to a record count and then runs gdb commands from
  FILE (breakpoints, conditional breakpoints, `stepi` loops; the stub takes about 20
  breakpoints) and samples the stopped machine. FILE sees `$sig` (the fixture's signature) and `$code`
  (the game's code base); the server gives one gdb command 30 minutes, and each breakpoint
  hit with commands costs about 30 ms, so count a few thousand events, not tens of thousands. Games that end show exec's idle loop
  (`stop #$2000` in ROM): WHDLoad runs with NOREQ and has quit.

### Reaching the Phantom race (2026-11-04)

The Phantom (championship) race needs a qualifying lap, which the fixture's driver does not
make. A probe reaches it from the first race with a patched source copy:

- In the copy's `src/HardDrivinPhantom.s`, add to `_phantom_patches`:
  `PL_W $11958,$4e71`, `PL_W $1195a,$4e71`, `PL_L $1195c,$50ec9c9e`,
  `PL_W $11960,$4e71`. This marks the race as qualified (`st G($9C9E)`).
- Build it with `build_feel.py --source DIR`, and give the capture's `Session` the anchor
  `0x11664`, the Phantom loop (`capture_feel.py` passes `0x10ed4`, the race loop).
- The fixture's input does not reach the Phantom loop. Press the gas (the right mouse
  button) with FS-UAE's `monitor input JOY1_2ND_BUTTON`.

The code (game code-hunk offsets):
- `$1194c` is the per-game routine. `jsr $10ec8` runs the race, then `tst.b G($9C9E)` at
  `$1195c` (qualified) leads to the Phantom setup at `$116ee`.
- The setup sets the gear G($9936) to 1 for the automatic box (else 0) and centres the
  mouse through −$7ff8(a4).
- `$11664` is the Phantom loop, the race loop's counterpart. VERIFY_TIME_PHANTOM hooks
  `$11894`, `$11668`, `$116bc` and `$116e6`. The race loop's own hook is
  `_dispatch_after_physics`, entered from `$10f28`.

## Arcade race timing (CUSTOM5=1, ARCADE_TIMING.md)

From the game directory with `tools/env.sh` sourced:

```sh
OUTPUT_SLAVE=tmp/build/clock.slave tools/build.sh -L tmp/build/clock.lst
python3 tools/build_feel.py lap-main lap-slow lap-offroad c1a-auto
cd tools && python3 check_clock.py ../tmp/build/clock.slave ../tmp/build/clock.lst && cd ..
INSTANCE=UNIQUE python3 tools/capture_clocks.py tmp/prof/NEW-RUN --plan lap-slow --custom1 2 --custom5 1 --max-fields 14000
python3 tools/arcade_report.py tmp/prof/NEW-RUN       # CUSTOM5=1
python3 tools/clock_rates.py tmp/prof/NEW-RUN         # CUSTOM5=0, the native rates
```

- **`check_clock.py`** runs the module's routines in Unicorn against a Python model of the
  rules: the BCD helpers exhaustively, random VBL sequences and every hook.
- **`capture_clocks.py`** is capture_feel's record loop plus, at every 32-field flush, the
  clocks, the race flags at G($add4) and the clock gate.
- **`lap-slow`** is the main road at 55 MPH, slow enough to run out of time.
- **The arcade side:** `tools/arcade/mame/plans/clock.lua` logs the arcade clocks every
  frame; `settings.lua` dumps MAME's default time settings.
