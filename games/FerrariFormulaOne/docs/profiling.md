# Ferrari Formula One baseline build and runner

Run commands from `games/FerrariFormulaOne` after sourcing `../../common/env.sh`. The authoritative
source is `src/FerrariFormulaOne_WHD.s`. The harness,
input copies, listings, builds and captures remain ignored. See
`baseline-validation.md` for the tested equivalence scope and results.

## Build

```sh
cd games/FerrariFormulaOne
. ../../common/env.sh
python3 tools/verify_inputs.py
bash tools/build.sh imported
bash tools/build.sh release
bash tools/build.sh verify
```

Each invocation assembles afresh. Outputs are
`tmp/build/{imported,release,verify}/FerrariFormulaOne.slave`, each accompanied by
`build.log`, `build.list`, the disposable build source and `source.json`.

The imported mode retains DEBUG. The published source cannot be assembled by
vasm completely unchanged: its `IFD BOOTDOS` has no closing ENDC. The wrapper
appends that terminator to its disposable copy. It also resolves Amiga assigns
through local `SOURCES:Include` and `Sources:whdload` symlinks, and supplies guarded
`lvo/{dos,exec,graphics,expansion}.i` wrappers for NDK's `_lib.i` names. The
repository source, shared includes and installed tools are never rewritten.

Release additionally comments out the one DEBUG directive. This removes the
DEBUG banner, private Amiga data path and SPS RMB wait. VERIFY adds `-DVERIFY=1`
to that release configuration; there are no VERIFY blocks in the source yet, so
these two binaries are identical. The separate RNG/input diagnostic copies are
not this normal VERIFY artifact and must never be distributed.

Toolchain: vasm 1.9, M68k backend 2.5, devpac syntax, 68000 PIC hunk executable,
no symbols. Includes come from shared WHDLoad 20.0 and the shared toolchain NDK.
Exact dependency hashes are in `manifest/baseline-build.json`.

## Run and inspect

```sh
SLAVE="$PWD/tmp/build/release/FerrariFormulaOne.slave" \
  WHD_ARGS=CUSTOM1=0 WARP=1 WINDOW=none python3 tools/game.py serve
```

Run the server in its own terminal. From another terminal, with the same working
directory/environment:

```sh
python3 tools/game.py shot "$PWD/tmp/current.png"
python3 tools/game.py stop
python3 tools/game.py cont
python3 tools/game.py quit
```

To use the shipped slave, set SLAVE explicitly to
`$PWD/tmp/game/FerrariFormulaOne_v1.01_0481/FerrariFormulaOne/FerrariFormulaOne.slave`.
CUSTOM1=0 retains StingRay's timing fix; CUSTOM1=1 disables it. There is no new
performance option. Omitting SLAVE or naming a missing file fails before launch.
Do not launch another case until the previous one has stopped.

Defaults: A500, 68000, PAL, 512 KiB chip, 1.5 MiB slow, zero Fast RAM, both host
input ports disabled. Kickstart 3.1 hosts WHDLoad 20.0; KickEmu loads the shared
Kickstart 1.3 image and RTB. The native ARM FS-UAE build is the default. Each
launch recreates `tmp/run/default/.run/dh0` and `dh1` from pristine inputs, records the
selected slave hash and configuration in `.run/launch.json`, and uses its own
PID, debugger port and socket. Never point a writable drive at the pristine game.

WARP=1 fast-forwards the long automatic demo startup. It is suitable for these
correctness checks; no performance result is taken from them. Set WARP=0 for
normal-speed runs. Capture timing measurements only after step 2 supplies a
validated frame marker and step 3 calibrates the timing instruments.

The debugger is read-only in this installed build: memory **and register writes
are silently ignored**. Read back any future write before trusting it. Input
fixtures must execute guest code; they cannot use `set` commands as injection.
Screenshots use one-field captures. The ARM server intentionally does not invoke
the x86 LLDB profiler-window workaround; do not treat its screenshots as validated
instruction profiles.

## Reproduce the comparisons

```sh
python3 tools/capture_baseline.py shipped 0 shipped-c0-valid
python3 tools/capture_baseline.py release 0 release-c0-valid
python3 tools/capture_baseline.py shipped 1 shipped-c1-valid
python3 tools/capture_baseline.py release 1 release-c1-valid
python3 tools/map_loaded.py tmp/baseline/shipped-c0-valid/race-0.bin \
  > tmp/baseline/loaded-map.json
python3 tools/make_rng_control.py
SLAVE_OVERRIDE="$PWD/tmp/build/rng-control/shipped.slave" \
  python3 tools/capture_baseline.py shipped 0 shipped-c0-controlled
SLAVE_OVERRIDE="$PWD/tmp/build/rng-control/release.slave" \
  python3 tools/capture_baseline.py release 0 release-c0-controlled
python3 tools/compare_baselines.py
```

These are fresh boots, anchored at the first execution of the SPS timing site,
then 1, 10 and 100 subsequent visits. A visit is not yet proved to equal a full
simulation step or presented frame. Read-only natural runs and controlled RNG
runs are separate; the latter establish a cause for divergent natural demos.
The checker includes a deliberate changed-byte negative control.

```sh
python3 tools/make_input_fixture.py
python3 tools/capture_input_fixture.py shipped 0
python3 tools/capture_input_fixture.py release 0
python3 tools/capture_input_fixture.py shipped 1
python3 tools/capture_input_fixture.py release 1
```

The input copies append local stubs and install them through the existing SPS
screen-pointer hook. They feed native mouse sampling and keyboard consumers,
then exercise the native F10 decoder/abort path. They do not validate physical
keyboard/mouse delivery, and their overhead is unsuitable for performance tests.
Every normal, RNG-controlled and input-fixture artifact remains separate.

The current discovery addresses are valid only for this fixed SPS/A500 layout:
race overlay base `0x64a68`, race timing site `race:+0x589c`, keyboard poll empty
return `0x236b0`, native post-event bookkeeping `0x236d8`, return `0x23708`, and
mouse VBL sampler `0x24824`. Scripts assert key states/checkpoints and retain
logs. Step 2 must replace fixed runtime addresses with full overlay-aware mapping
before using other layouts or versions. None of these scripts supports Irek yet.

## Step 2 automatic demo

The accepted workload uses no input. Interactive routes are deferred. Read
`game.md` for boundary semantics and the correction to old input-fixture evidence.
The final diagnostic captures use a private copy of the installed aprof emulator:
`tmp/step2/emulator-build/fs-uae`. `tools/step2-emulator.patch` records its changes
against `~/.local/share/amiga/fs-uae-aprof-build/fs-uae`. To recreate that private
copy, copy the installed build tree, apply the patch there with `patch -p1`, and
run `make -W src/barto_gdbserver.cpp fs-uae -j4`. Do not patch the shared install.
The monitor switches warp through the native action queue and reads actual frame
warp state. Guest UAElib warp experiments are retired and rejected by the builder.

Run from `games/FerrariFormulaOne`, with the shared environment sourced:

```sh
export PYTHONPATH="$HOME/.local/share/amiga/pylib"
export FSUAE="$PWD/tmp/step2/emulator-build/fs-uae"
python3 tools/build_step2.py
SLOW_FIELDS=3 python3 tools/build_step2.py
python3 tools/capture_step2.py verified-demo-a
python3 tools/capture_step2.py verified-demo-b
python3 tools/capture_step2.py slow-demo probe-s3-p1-w0
python3 tools/inspect_display.py tmp/step2/verified-demo-a/display.bin > tmp/step2/verified-demo-a/display.json
python3 tools/inspect_display.py tmp/step2/verified-demo-b/display.bin > tmp/step2/verified-demo-b/display.json
python3 tools/inspect_display.py tmp/step2/slow-demo/display.bin > tmp/step2/slow-demo/display.json
python3 tools/overlay_map.py tmp/step2/verified-demo-a/anchor.bin > manifest/step2-overlays.json
python3 tools/check_step2.py
```

Use the shared Python environment if the shell's python3 lacks amitools/barto.
Capture names overwrite earlier evidence; use fresh names while investigating.
The builder defaults to WARP_OFF=0; emulator monitoring handles the warp exit.
Its inactive guest-warp code remains only to reproduce the accepted binary.
The release hash is guarded before diagnostic patching. These probes use fixed
SPS/A500 addresses and must be adapted before another machine configuration.

The 32-field windows validate observation and repeatability, not final FPS.
Do not derive steady rates from partial-loop counters or host capture duration.
Full time-domain semantics, non-demo controls and whole-machine timing remain
later steps. Artifact hashes and exact settling intervals are in
`manifest/step2-validation.json`.


## Step 3: focused performance measurements

Scope: 68000, 68020 and 68020 + Fast. 030/040/060 analysis is deferred.
Results are in `PERFORMANCE.md`; exact gates and artifact hashes are in
`manifest/step3-validation.json`. All paths below are from the worktree root.
Use the shared Python environment described above. Existing completed runs are
skipped; archive their folders before intentionally repeating a capture.

```sh
. ../../common/env.sh
python3 tools/matrix_step3.py
python3 tools/build_step3_ceiling.py
python3 tools/followup_step3.py
python3 tools/check_step3.py
python3 tools/write_step3_report.py
```

The matrix defaults only to the three requested profiles. The retained additional
A500 + Fast baseline can be reproduced with `matrix_step3.py a500-fast`.
`check_step3.py` and the report gate include that already completed baseline.
`analyze_step3.py NAME`, `events_step3.py NAME` and `costs_step3.py NAME` regenerate
field metrics, completed-call timings and exclusive costs from retained captures.
The runner invokes the applicable field/phase analyzers automatically.

Frozen private observers are `tmp/step3/fs-uae` (survey), `fs-uae-events`
(detailed spans), and `fs-uae-controls` (instant-blitter control). Their standalone
patches are `tools/step3-observer-{survey,events,controls}.patch`, each against
`tmp/step3/barto-before.cpp`, the preserved step-2 source. Rebuild only when no
capture is active, using `bash tools/build_step3_observer.sh VARIANT`.
The script makes a separate build tree and preserves the original step-2 source.
The binary resources `share`, `data` and `fsemu` must remain available beside it.

Each normal-release matrix run warps to completed car update 120, requests warp
off, advances to completed update 125, verifies actual warp is off, removes
breakpoints and captures 1,000 fields. `update120.bin` and `anchor.bin` retain
settling counters at $24ad2. Each cell has two fresh boots (`-a`, `-b`). Detailed
runs capture 500 fields with identical anchor and exact baseline field/PC data.
The end-of-window `detail.bin` is an additional 32-field diagnostic trace, not
part of the 500-field timing window. No external input is injected.

Each run retains `launch.json`, `result.json`, memory snapshots, `window.jsonl`,
`analysis.json` and logs; detailed runs add `phases.json`. CPU cost units are
calibrated against independently counted fields, and actual DMA plane changes
provide presentation rates. Missing instruction support means unavailable,
never zero CPU cost. A500 CPU-observer versus DMA-only calibration preserves
full Chip memory and every presentation; negative checks reject missing fields
and missing DMA. Cross-machine native seeds can differ.

Rendering ceilings use separately assembled equal-size control and road-edge-line
omission slaves. They are intentionally diagnostic. Instant blits are enabled
only after the settled matched-state anchor. The earlier instant-at-boot attempt
changed initialization and is retained as rejected evidence. None of these
experiments changes the ordinary release or establishes correct uncapped speed.


## Step 4: native game time and capacity

Report: `GAME_TIME.md`. Scope: SPS 0481 PAL, 68000 / 68020 / 68020 + Fast.
All paths below are from the worktree root. Run capture batches sequentially;
they share the harness's debugger port and disposable game drawer. Completed
named runs are skipped. Preserve old evidence before intentionally repeating.

```sh
. ../../common/env.sh
python3 tools/audit_step4.py
python3 tools/matrix_step4.py
python3 tools/build_step4.py
python3 tools/diagnostics_step4.py
python3 tools/build_step4_contact.py
python3 tools/contact_step4.py
python3 tools/build_step4_pause.py
python3 tools/modal_step4.py
python3 tools/check_step4.py
```

The checker regenerates `step4-measurements.json`, asserts the accepted state,
clock, fixture, anchor and modal gates, and writes `step4-validation.json` with
hashes. Its scope limitations are intentional: the report distinguishes direct
measurement, static modal evidence, capacity projections and release gates.
`finalize_step4_docs.py` was the one-time report assembly helper; do not rerun it
against the completed document because it inserts report sections.

The matrix captures complete loops 125, 150, 175 and 225 after warp exits at car
update 120 and settles to 125. It uses the frozen step-3 observer and native field
counter, not host/debugger duration. The contact arm also records handler entry
and completed loop 126. Earlier unused `requested_fields:1000` metadata is not the
capture length; observed elapsed fields come from loop snapshots. The reused
step-3 fixed-field windows are identified separately in the validation manifest.

The equal-size v2 controls differ by one mode byte. The logic arm retains the
boost/audio mutation found in drawing and some UI drawing, so its elapsed cost
is a conservative prototype, not a finished CPU-only tick kernel. Contact v3
injects one left-wall penetration at the native collision input boundary and
requires the wall handler rather than the pit path. No user input is needed.

Modal captures are two startup transitions (600 fields each) and two new
ESC-consumer pause fixtures (100 paused fields each). The pause fixture injects
two raw ESC events through native decoding, preserves its saved registers and
enters the native pause loop; this does not test physical host input. Startup
captures cross loading/countdown and do not establish steady-menu clock rate.
Rejected v1 omission/contact trials and host-ESC attempts are retained and
excluded. The normal slave and authoritative source hashes are asserted unchanged.
