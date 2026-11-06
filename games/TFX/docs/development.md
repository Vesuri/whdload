# TFX development setup

The slave source is `src/` (`TFXHD.s` with `chip_reloc_new.i`, `native_fpu_sites.i`,
`native_math.i` and `ReadJoypad.s`; `code040.s` and `code060.s` with the Motorola FPSP
sources build `fpsp040` and `fpsp060`). Paths below are relative to the game directory
(`games/TFX`), where the harness that lived in the fork's ignored `tmp/dev/` is now
`tools/` and `docs/`. Commands run from here.

Source baseline: upstream `ce5a2a25e7f8443da5502d9755b6b1ae01080862` of
https://github.com/jotd666/whdload_slaves (`T/TFX/usr`), developed on the fork branch `tfx`;
commit hashes in these docs are that branch's (the commit messages here are the same).

## Inputs

- Installer page: https://whdload.de/games/TFX.html
- Installer archive: `TFX.lha` (from that page).
- Full install: `TFX_v2.1_AGA.lha` (a Retroplay WHDLoad pack).

`make unpack ARCHIVES=<directory>` checks both against `inputs.sha256`, copies them to
`tmp/archives/` and unpacks each into a drawer named after it (`game.sh`): the installed game
is `tmp/game/TFX_v2.1_AGA/TFXAGA/` (slave `TFXAGA.slave`, executables and data in `data/`),
the installer package `tmp/game/TFX/TFXInstall/` (slave `TFX.slave`). Keep both unchanged;
every run boots a disposable copy.

The executable survey (`executables.md`) also used two archives that are not build or run
inputs: the CU Amiga CD release (`TFX.lzx`, sha256
`e355764588331092ef5afaf8047375d51176cbef42a8114d4105ecf9a0d6867c`) and the 68040 download
(`tfx040b.zip`). They stay in `tmp/` with the other evidence.

## Build

`make slave` builds the three variants of `game.conf` into `tmp/build/release/`:
`TFX.Slave` (`src/TFXHD.s`, vasm `-nosym -Fhunkexe` against the shared WHDLoad includes,
the shared lvo bridges and the default NDK), `fpsp040.Slave` and `fpsp060.Slave`
(`-maxerrors=0 -devpac -nosym -Fhunkexe`). The FPSPs are byte-identical to the shipped
`data/fpsp040` and `data/fpsp060`, so the release leaves them unchanged. `make build
BUILD=chiponly` is the `CHIP_ONLY` diagnostic build. There is no VERIFY instrumentation:
`make verify` gives the release bytes. `make check` proves the release build still gives
`release/slaves.sha256`, compiles every Python tool and parses every shell tool.

`tools/build.sh` is the harness's build on `common/build.sh`: extra arguments go to vasm
for the slave (e.g. `-L tmp/x.lst`, `-DSTEP11_COPY=1`), `CHIP_ONLY=1` selects the chiponly
build, `OUTPUT_SLAVE=path` copies the slave there. The slave is
`tmp/build/release/TFX.Slave`, the FPSPs `tmp/build/release/fpsp040.Slave` and
`fpsp060.Slave`.

The 2.2 slave's `$VER` string carries its fixed date, `2.2 (22.10.2026)`; nothing is
generated into the source tree (`DATETIME` stays undefined).

## Run

`make run` boots the release build on the target machine: `SETUP=a1200-040` with 32 MB of
Zorro III RAM (A1200 + Apollo 1240/40), Kickstart 3.1 (kick40068.A1200 for the host and
the slave), SetPatch, WHDLoad with `PRELOAD SPLASHDELAY=0 CONFIGDELAY=0 NOREQ`.
`make run SLAVE=original` boots the shipped 2.1 slave. `WHD_ARGS='CUSTOM3=3 CUSTOM4=2'`
selects `tfx.020` and skips the intro. `game.sh` keeps the fork harness's run options:
`FPSP040=` and `FPSP060=` replace `data/fpsp040`/`fpsp060`, `EXTRA_FILES=` copies host
files to DH1:, `RUN_CMD=` runs a command instead of WHDLoad, `HDF=1` (with `HDF_SEED=`)
boots from disk images packed with `xdftool` (deterministic replays deadlock on directory
drives), and `EXTRA_ARGS` replaces the Zorro III default.

`python3 tools/tfx.py serve|wait|shot|quit` drives it through the gdb stub
(`common/tools/game_server.py`; run directory `tmp/run/<INSTANCE or default>/.run`).
`tools/smoke_step1.sh LABEL` boots one configuration and saves a screenshot to
`tmp/shots/step1/`.

Smoke check after the move: `WARP=1 WINDOW=none python3 tools/tfx.py serve`, `wait 60`,
`shot` reaches the "Create new pilot" menu with the release build.

## The harness

The tools are those of the fork's `tmp/dev/tools`, with their paths rewritten for this
layout (harness root and worktree root are both the game directory now; `T/TFX/usr/source`
is `src/`; `amiga/env.sh` is `tools/env.sh`; `tmp/build/TFX.slave` is
`tmp/build/release/TFX.Slave`). `tools/tfx.py`, `tools/build.sh`, `tools/env.sh`,
`tools/step13_environment.py` (an INSTANCE per CPU session instead of a copied
`amiga/run.sh`) and `tools/poly_poison.py` (a `BUILD=poison` of the poisoned source) were
ported by hand. Only `make check`, the builds and the boot above were run after the move;
the capture tools also need their private emulators and retained evidence (below), so a
tool that has not been rerun may still hold an assumption of the old layout.

Retained evidence, private emulator builds (`tmp/opt20-project-emulator`, rebuilt with
`tools/build_*_emulator*`), captures, screenshots and frozen slaves are game-derived and
stay out of git: they remain in the fork worktree's ignored `tmp/dev/tmp/`. Tools read
them from this game's `tmp/` (same subdirectory names), so copy what a check needs there.

Follow AmigaXDev's `docs/playbooks/new-game-playbook-jotd.md` for future development.

## Reproducible flight harness

See `replay-flight.md`:

```
python3 tools/replay_flight.py --clock-relative --output tmp/step2-new
```

Step 2 is complete: the user accepted the documented clock-origin mismatch on
2026-10-20. The output directory must be new. This runs two cold boots per CPU and reports
raw equality separately from clock-relative equality. Strict checking exits nonzero
when the 020/030 absolute-clock origin differs; `--clock-relative` explicitly accepts
only the documented five-timer translation. Screenshots match on all four tested
configurations.

## Frame counter

Step 3 is complete. See `frame-counter.md` for the read-only publication/vblank
counter, private full-trace emulator build, fixed validation window and checker.
No game or slave patches were needed. The trace records instruction order only;
step 5 still needs a cost measurement method.

## Baseline matrix

Step 4 is complete. See `baseline-matrix.md` for the frozen five-second nominal-PAL
window, results, unavailable no-FPU case, live cache states, timing controls,
reproduction commands and repeatability limits. The performance configuration uses
a frequency-sensitive 040 NOMMU core; the existing MMU configuration remains the
functional regression setup. A local metadata-only emulator build records actual
settings without changing game/slave code or the shared installation.

## 040 profiling

Step 5 is complete: `profile-040.md` documents the private cost observer, strict
FPU trap configuration, reproduction, full cost accounting and observer-off check.
Always use `--uae_fpu_no_unimplemented=true` for target-040 performance experiments;
the old default permissively handled unsupported opcodes without FPSP.

## Symbol and patch map

Step 6 is complete: see `symbol-map.md` for the accepted identities, Ghidra audit,
full patch-site inventory, reproduction commands and ABI warnings. Local tools:
`map_symbols.py`, `validate_symbol_spans.py`, `build_symbol_map.py`,
`audit_symbols_ghidra.sh`, `check_symbol_map.py`. All outputs stay in `tmp/step6/`.

## Correctness ports

Step 7's sort and duplicate-joystick-fire fixes are committed. See
`correctness-fixes.md` for guarded native-routine tests, actual missile allocation
counts, fresh/cached HDF seed rules, private fixture backend, performance results,
and the explicit full-state replay limitations. `tools/check_step7.py` validates
the retained correctness cases and reports (without waiving) failed full-state
gates. `tools/step7_regression.py` still returns nonzero for those failures.
The source builds normally; fixture injection exists only in the private emulator.

## DMA-only chip placement

Step 8 is complete (`a539348`). See `chip-placement.md` for the actual chip-object
map, 62 relocation sites, CPU/option gates, repeatable timing gains, synchronized
visual fixture, failed-fixture pitfalls and remaining clock/state differences.
`tools/check_step8.py` validates retained evidence; `tools/step8_final_checks.py`
runs the suite into a new output directory. The source includes
`chip_reloc_new.i`. Normal and chiponly builds pass.

## Native 040 FPU maths

Step 9 is complete. See `native-fpu.md` for exhaustive instruction coverage,
precision bounds, FPSP fallback limits, zero-trap profiles, explained state
changes and the retained 040 MMU replay failure. `tools/check_step9.py` checks
retained evidence; `tools/test_native_math.py` plus `tools/check_native_math.py`
run guest arithmetic against FPSP and an independent Decimal oracle. The private
`step9-emulator` adds read-only operand capture to the existing fixture backend.
`native_fpu_sites.i` and `native_math.i` are generated by `tools/generate_native_fpu.py`
and `tools/generate_native_math.py` (the upstream submission shortened the header comments
of `native_math.i` by hand; regenerating brings the long ones back). CUSTOM5 disables the FPU replacements as before.

## 040 rendering and frame limits

Step 10 is complete. See `rendering-port.md` for fill/line/box equivalence, original
renderer screenshot equality, frame-limit ABI tests, CPU gates and performance.
`tools/check_step10.py` validates retained evidence. `tools/step10_final_runs.py`
repeats the final suite into a new output directory, using sequential harness
sessions. C4 bit 2 retains original rendering; bits 5/6 now work on tfx.020/040,
with bit 6 taking precedence. The existing 32-pixel scanline C2P helpers are reused;
flat fill writes planes directly. The original flat routine is kept because its
replacement measured slower.

## 040 tuning

Step 11 is complete without a code change. See `tuning-040.md`: three same-build
copy A/B pairs showed no throughput gain, so the verified step-10 slave is retained.
`tools/step11_report.py CAPTURE LISTING` uses current symbols and independent code
anchors; `tools/check_step11.py` checks retained evidence and release-byte identity.
`tools/test_step11_report.py` exercises three deliberate invalid inputs.

## Palette investigation

Step 12 remains incomplete: `palette-investigation.md` records the unreproduced
symptom and exact coverage limits. `step12_survey.py` records native flight/view
requests, `step12_menus.py` records native menu/training input, `step12_report.py`
reports palette samples, and `step12_trace_audit.py` checks complete observed
SetPal calls. No palette code has been changed. Use new output directories and one
emulator session at a time; retain launch metadata and debugger logs with screenshots.

## Executable selection and option regression

Step 13 is complete (`b0a1139`, then `c4e56b93` for FPU-equipped 020/030/060):
automatic mode uses the newest `tfx.020` with an FPU and plain `TFX` without one. See
`selection-regression.md` and `executable-comparison.md` for coverage, expected no-FPU
exclusions and harness pitfalls. The exit checker is `tools/check_step13.py` against
retained `tmp/step13/` evidence.

A fresh 040 flight/option matrix (new output path):

```
FSUAE="$PWD/tmp/step9-emulator/fs-uae/fs-uae" STEP13_CPUS=040 \
  python3 tools/step13_matrix.py "$PWD/tmp/step13-recheck-040" candidate
```

Use `step13_startup.py` with the same environment and a separate fresh output path
for intro, menu and configuration captures. `step13_run_cpu.py CPU` resumes the
per-CPU suite; `step13_environment.py` gives each CPU session its own INSTANCE.
`step13_contact.py candidate-040` generates a labeled review sheet from retained
screenshots; screenshots still need inspection, not just existence checks.

## What was not imported

From the fork worktree's ignored `tmp/dev/`: `amiga/run.sh` and `amiga/env.sh` (replaced
by `common/run.sh` with `game.sh`, and `tools/env.sh`), `tools/__pycache__`,
`docs/cleanup-2026-10-22.json` (the file list of a scratch cleanup) and all of `tmp/`
(about 2 GB: archives, installed game, builds, captures, screenshots, emulator builds).
From the fork: `src/Makefile` (`game.conf` builds the slave), and the built
`usr/fpsp040`/`usr/fpsp060`, which `src/` rebuilds byte for byte.
