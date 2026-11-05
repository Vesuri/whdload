# Harness testing

Run commands from the game directory (`games/TestDrive`). Source `tools/env.sh` in
Bash to select the shared Python environment and toolchain.
All outputs are ignored. A capture owns one server/emulator in this harness;
stop an existing interactive server with `python3 tools/td.py quit` before using
a fresh-boot wrapper. Other games' and instances' processes are never stopped.

## Reference machines

Use `TD_SETUP` for the TD2 reference settings below (`game.sh`). Do not also set a
named SETUP. The shared named machines (SETUP or AMIGA_SETUP), including a1200-040,
remain available.

| TD_SETUP | Model / CPU | Chip / fast / slow RAM | Additional setting |
|---|---|---|---|
| a500 | A500 / 68000 | 512 / 0 / 1536 KiB | contended slow RAM; sufficient capacity for WHDLoad |
| a1200 | A1200 / 68EC020 | 2048 / 4096 / 0 KiB | A1200 Kickstart host |
| a1200-030 | A1200 / 68030 | 2048 / 4096 / 0 KiB | 25 MHz, real CPU speed, cycle-exact |

Presets are sourced after the shared environment and keep runtime files in the
same disposable drawer. `EXTRA_ARGS` remains available, but changes are diagnostic
variants, not the named reference configuration. Read the saved `machine.json` (first-value-wins launch options) and `fsuae.log`
for effective settings before comparing captures. FS-UAE stdout can be buffered
at the first breakpoint; dump ranges must not be inferred from a partial log.

## Builds and input guards

`tools/build.sh` and `VERIFY=1 tools/build.sh` build the authoritative source into
`tmp/build/`. Build dependency hashes are checked first. Normal 1.5b remains
byte-identical to the hardware handoff; VERIFY contains the CUSTOM3 profiling
fixture. The original 1.4 rebuild and fixed 1.5b A/B artifacts are preserved.

`python3 tools/check_inputs.py` checks pinned archives, all pristine extracted
files and runtime dependencies. `run.sh` performs this before changing runtime
files, and rejects unpinned executable/ROM overrides. New dependency versions need
an explicit manifest review. Do not regenerate manifests to hide unexpected changes.

`python3 tools/check_profiler.py` checks the pinned x86_64 emulator and the machine
code references to the profiler base/size window. The documented setup writes and
profile-command reads both match. Every profile call checks the binary hash before
the shared server's LLDB fix/read-back. A new emulator requires rederivation.

## Captures

```sh
TD_SETUP=a500 SLAVE="$PWD/tmp/build/release/TestDrive.Slave" FIELDS=3 \
  tools/profile_demo.sh "$PWD/tmp/prof/demo-new"

TD_SETUP=a500 ANCHOR=0x18ba STATE_FIELDS=8 SKIP_FIELDS=600 STATE_ONLY=1 \
  tools/fixed_window.sh "$PWD/tmp/prof/state-new" "$PWD/tmp/build/release/TestDrive.Slave"
```

Outputs must be fresh directories under harness `tmp/` with space-free names below
that point. The worktree's own path may contain spaces. GDB changes into the harness
and writes relative paths, so dumps never pass through a shared `/tmp` directory.
Each capture retains its exact slave, effective config, code/chip dumps and metadata.
Fixed captures verify the CPU is still at the requested anchor and the VBL sampler
checks a4/a1 against the loaded data hunk. Missing hunks at a fixed anchor fail
without advancing the guest.
The calibration cache includes machine settings, slave and runtime-input hashes.

Demo captures verify the first and last screenshots are driving and require real
instruction PCs. They are profiling diagnostics, not comparable FPS benchmarks.
Fixed captures default to the phase-4 fixture, first-attract-race h4:$F6 anchor
and root:$7AAA publication marker. See phase4.md for the two-boot matrix and limits.
ANCHOR=0x18ba selects the legacy phase-1 VBL diagnostic only.

The race window defaults to FIELDS=100; SWAP_ONLY=1 uses publication breakpoints.
The explicit-ANCHOR diagnostic path retains FIELDS=1..100 (default 5), STATE_FIELDS,
SKIP_FIELDS, STATE_ONLY=1, WATCH_STATE=1, SWAP_OFFSET and SERVE_WAIT. DEMO_TIMEOUT
controls arbitrary demo capture; its default and SERVE_WAIT are 300 host seconds.

## Analysis and acceptance

```sh
SLAVE=OUT/slave.slave python3 tools/td_report.py OUT/trace.bin OUT/code.bin --base 0xc00000
SLAVE=OUT/slave.slave python3 tools/frames.py OUT/trace.bin OUT/code.bin 0xc00000
python3 tools/task_state.py OUT/code.bin 0xc00000 --chip OUT/chip.bin
python3 tools/state_report.py OUT/state --changes
python3 tools/state_writers.py OUT/trace.bin OUT/code.bin 0xc00000
python3 tools/compare_state.py A/state B/state --assert-match --raw
python3 tools/compare_state.py A/state LATER/state --allow-different-window --raw
python3 tools/check_harness.py
```

Use the capture.json base, not a guessed address (fast RAM normally uses $200000,
slow RAM $C00000). `frames.py` defaults to the validated root:$7AAA LoadView
marker. Use it as gameplay FPS only inside the fixed race window; an explicit
--swap-offset for another site is a diagnostic counter.

Acceptance evidence is under `tmp/phase1/`. `final-a` and `final-b` are separate
fresh boots of the same slave at fields 600..607: all seven table entries and all
$32A4 raw data bytes match. `rebuilt-later` is fields 1400..1407: the screen changes
from the Accolade logo to a car introduction and every raw sample differs.
`check_harness.py` additionally mutates a non-clock selector to prove sensitivity,
rejects a missing sample, verifies region/task parsing, recognizes two different
car dashboards and rejects four non-driving images, and checks trace PCs.

The `shipped-title` directory contains the VBL-marker/watchpoint diagnostic (its
last screenshot happens to be a transition, not a title-screen assertion). It
records eight marker hits in eight fields and VBL_INCREMENT_OK=1.
`a1200-verified` and `a1200-030-verified` record exact field-600 entry with the
intended RAM/CPU settings. Earlier unqualified accelerator captures were diagnostic
boot checks only and are not used as fixed-window acceptance.

The `shipped-a500` trace identifies VBL, sound and blitter-counter stores; the
`demo-profile` workflow validates the rebuilt slave's driving trace end to end.
The seed map and its limits are in `internals.md`. This is tool acceptance, not the
full gameplay/handling/performance regression suite.

## Phase-5 analysis acceptance

Run `python3 tools/check_phase5.py` with the shared Python. It checks consecutive
VBL samples, five-field deadlines, race-clock increments, exact first divergence,
all 14 direct RNG call sites, normal/VERIFY hashes, natural crash penalty and
blocking, and radar counter cadence through automatic release on both presets.
The inputs are the retained captures under `tmp/phase5/`, not screenshots.
See phase5.md for reproduction commands, native input and interpretation limits.
No gameplay implementation or same-period enhanced-state equivalence is claimed.

## Phase-6 local acceptance

`phase6.md` records the successful hook audit, unchanged normal/baseline hashes,
phase-3 display review and native-key quit to AmigaDOS on the 68040 preset.
`tmp/phase6/evidence.sha256` pins the retained acceptance inputs and outputs;
check it from the game directory with `shasum -a 256 -c tmp/phase6/evidence.sha256`.
Real A1200/68040 cache/MMU A/B remains a separate hardware follow-up.

## Phase-7 acceptance

Run `python3 tools/check_phase7.py` for retained-evidence acceptance and
`python3 tools/check_verify_tools.py` for deliberate checker failures. To reproduce
fresh runs, use `tools/verify_matrix.sh`; its output directories must not exist and
no interactive server may be active. See phase7.md for the options, twelve capture
cases, confirmed overlay unload/reload and bounded RNG/state claims.
`shasum -a 256 -c tmp/phase7/evidence.sha256` checks the frozen evidence from the
harness root. The normal slave and deferred hardware A/B pair remain unchanged.
