# Step 13: selection, options and regression

Completed. Selector commit: `b0a1139`; tracked completion record: `adbfde4`. The aggregate checker passes all 49
supported flight cases, 16 startup cases and eight unchanged-build baselines.
Evidence is under `tmp/step13/`, relative to this harness.

The selector previously preferred the integer `TFX` whenever C4 bit 2 was clear.
The candidate selects the newest `tfx.020` when CUSTOM3 is automatic, the 68040
flag is set, the 68060 flag is clear, and the integrated FPU flag is set. Explicit
CUSTOM3 choices bypass the new check. Other CPUs retain their previous policy.
Original rendering remains available with C4 bit 2; CUSTOM5 disables direct FPU
patches while keeping FPSP available.

The unchanged step-12 build is retained as `baseline.slave`; the normal candidate
and CHIP_ONLY build have separate outputs. All captures use disposable fresh HDF
seeds for their exact slave/options. No fixture writes or altered game data are
used in this step's boot matrix.

## Method

`tools/step13_matrix.py OUTPUT baseline|candidate` identifies the actual loaded
executable by original-code signatures and hunk chains. It reaches action flight
with the enrollment portion of the existing native input tape, checks relevant
live patch opcodes and memory placement, then requires three actual COP1LC
publications in neutral flight and captures one field. The later swap-10/20
right/release tape events are not reached in these short boot checks. This is boot/patch coverage, not a performance measurement or a full
state-equivalence test. CPU metadata is captured by the final candidate checker.

`tools/step13_startup.py OUTPUT` captures automatic startup with C4 values 0, 2,
3 and 16: introduction, non-action menu, configuration program, and action with
the skip-intro bit clear (C4=16). Native screenshots must be inspected; a capture alone is
not proof that the intended screen or flight was reached.

`tools/step13_no_fpu.py OUTPUT` records the three forced FPU executables on the
020 without FPU. These are unsupported configurations, not successful flights.
They must remain explicitly separate from the supported boot matrix.

Use the private step-9 observer emulator and debugger socket access. Each CPU
runs its own cases sequentially; separate CPU runtimes may run concurrently. Build with `tools/build.sh`; from the game directory, set FSUAE to the
private emulator under `tmp/step9-emulator/fs-uae/fs-uae` and run the tools
with absolute new output directories. Normal shared emulator files are unchanged.

## Pitfalls

The first baseline attempt could not connect to the local debugger under the
filesystem sandbox. Its verified emulator PID was stopped, and captures were
rerun with local socket access. The first original-render baseline checker
incorrectly expected a long-address JSR for native tan. The actual installed
instruction is absolute-short `4eb801fc`; source and captured bytes agree. The
checker was corrected and that row rerun; the failed attempt is retained.

The instruction source retains CRLF; run Git whitespace checks with
`-c core.whitespace=cr-at-eol`. No palette change is part of this step: step 12
remains unreproduced, with the possible debug-build explanation unconfirmed.

The 020 original-renderer probe showed that 1,500 startup fields were insufficient:
the initial capture was still black, and the tape started before enrollment was
ready. That row uses 3,000 startup fields, 40-field key holds and 80-field menu
release waits. The first 8-field and then 40-field-only failed attempts are kept.
The matrix bounds discovery to fast RAM $41a00000..$41e00000, where all retained
layouts load, rather than dumping all 32 MiB each time. Original signatures and
hunk-chain sizes still validate every loaded executable; an out-of-arena layout
fails discovery. The effective replay source is saved with the evidence.

The 030's initial 1,500-field command exceeded the host debugger's 90-second
timeout. Startup waits are now split into at most 250 fields per command. Each
command completes its current partial field, so this is a boot recipe, not the
fixed performance window. Native input and actual publications remain verified.
The installed TFXAGA icon has no CUSTOM3 override; automatic selection is available
without an icon change.

## Runtime separation

`step13_environment.py` gives each CPU its own runner, `.run` directory, disk
copies, seed paths and debugger port. Only pristine game inputs and the immutable
build are shared through local symlinks. `step13_run_cpu.py CPU` runs that CPU's
matrix and startup captures in order. Baseline 030/060 runs used frozen
`baseline-inputs/` while the normal build advanced to the candidate.

The first separation probe still imported the main `tfx.server` inside the replay
source, interrupting the active TFX 030 capture. That capture is rejected. The
corrected wrapper supplies its server explicitly and asserts the expected runtime
path. A fresh independent probe uses its own PID file and reproduces the 020
baseline flight PNG. Its raw code snapshot differs; no state equivalence is claimed.
The original and interrupted captures remain as diagnostic evidence.

## Baseline selections

All eight unchanged-build cases reach flight and three actual publications:

| CPU | Automatic, new renderer | Automatic, original renderer |
|---|---|---|
| 020, no FPU | TFX | TFX |
| 030 + 68882 | TFX | tfx.020 |
| 040 + FPU | TFX | tfx.020 |
| 060 + FPU | TFX | tfx.020 |

Committed selector change: `b0a1139`. It changes only the 040/new-renderer
cell to `tfx.020`. The feature commit followed all eight candidate automatic
selection checks and all four explicit 040 executable choices; the broader
option/startup exit checks continue separately.

## Supported combinations and explicit exclusions

The four selectable executables are integer `TFX`, `TFX.FPU`, newest `tfx.020`,
and the installed symbol beta `TFX.040`. The damaged survey candidates and the
unselectable floppy executable are not advertised CUSTOM3 choices.

The no-FPU 020 supports integer TFX. Forcing the three FPU builds produces the
expected WHDLoad Line 1111 Emulator ($2c) exception, at executable offsets $48f7c,
$50f4c and $4ea74 respectively. Screenshots are retained in `no-fpu/*/failure.png`
and explicitly reviewed in `no-fpu/verified-results.json`. They are unsupported
combinations, not passing flights. The automatic no-FPU choice stays integer.

All 49 candidate flight cases have passed: 10 on 020 and 13 each on 030, 040
and 060. All 16 startup cases also pass visual review. All 239 static replacements are present in the automatically
selected 040 code, and all 239 original instructions return with CUSTOM5=1.
All 245 inspected 060 FPU sites match step 10. The 040/060 captures explicitly
use strict unimplemented-FPU trapping; no new FPSP or game binary is supplied.

The seven automatic choices whose executable is unchanged reproduce the baseline
checkpoint PNG exactly (`baseline-image-comparison.json`). The changed 040 default
uses the different, newer executable and has a different image. This is one
checkpoint per case, not full state equivalence or a new waiver of earlier state
mismatches. No performance claim is inferred from these short boots or FPS overlays.

## Final coverage and handoff

`validation.json` is the passing aggregate result. Every supported flight row
has the exact candidate slave and unchanged FPSPs, live CPU metadata, a validated
executable/hunk chain, three publications and a reviewed cockpit screenshot.

| CPU | Flight/option cases | Startup cases |
|---|---:|---:|
| 020, no FPU | 10 | 4 |
| 030 + 68882 | 13 | 4 |
| 040 + FPU | 13 | 4 |
| 060 + FPU | 13 | 4 |

Flight cases cover automatic/new and automatic/original rendering; every
supported explicit executable; FPS display with both renderers; uncapped,
one-frame, both frame-limit flags, both with original rendering; and CUSTOM5.
Startup covers C4=0, 2, 3 and 16. This covers each advertised choice and the
important combined-option precedence, not every possible bit-mask combination.
FPS numbers visible in the startup flight captures are not benchmark results.

The last three 030 option cases ran in separate runtimes after the other CPUs
finished. Their output directories are disjoint; the main driver reuses only
completed audit files, and the final checker reads all 13 individual records.
All emulators use the same private backend binary. `cpu-metadata.json` retains
actual models, frequencies, MMUs and cache states (including the existing
original-rendering cache differences). `build-identity.json` and `tool-hashes.json`
identify the normal/CHIP_ONLY builds, FPSPs, source and retained tools.

No other slave, shared emulator, shared environment, palette code or game bytes
changed. Step 12 remains unreproduced. Step 14 is next: real Apollo 1240 validation,
then the ReadMe/version and release work; no hardware speed claim or release is
made here. The normal build is `tmp/build/release/TFX.Slave` under this harness.

All task emulator PIDs have exited (`process-check.json`). The runner retains
stale PID files after quit; file existence alone does not indicate a live process.
