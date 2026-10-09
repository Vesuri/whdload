# Development

Keep supplied archives and all derived game material in ignored `tmp/`.
The installer is `tmp/Stellar7.lha`; the Retroplay pack is
`tmp/Stellar7_v1.0_NTSC_2026.lha`. Extract them under `tmp/installer/` and
`tmp/game/` respectively. The playable directory is `tmp/game/Stellar7NTSC/`.

Source `amiga/env.sh` to select the shared toolchain. Overrides: `KICKSTART`
(host A600 3.1), `KICK13`, `RTB`, `KICKSTART_A1200`, `WORKBENCH_ADF`, `WHDLOAD`,
`WHDLOAD_BINARY`, `FSUAE`, `VASM`, `NDK`, and `FSUAE_COMMON`. Assets default to
`~/.local/share/amiga`; executables use the shared `~/.local` toolchain.
Missing inputs fail explicitly. There are no fallbacks into another project.

`amiga/run.sh` boots the shipped slave windowed with sound. Defaults: 68000,
512 KB chip, 1536 KB slow RAM, no fast RAM, PAL. This is an A500-equivalent
bus configuration with enough memory for WHDLoad. The pack is labelled NTSC;
PAL/NTSC game-timing behavior remains to be established.

`JOY0=none DETERMINISTIC=1 python3 tools/stellar7.py serve` starts the debugger
harness. `python3 tools/stellar7.py shot tmp/screen.png` captures a field;
`profile 10 tmp/trace.bin` captures ten fields with instruction PCs. Use `stop`
and `cont` to hold/resume the emulated CPU. The `gdb` command is read-only;
the emulator stub silently ignores memory/register writes.

Use `gdb 'dump binary memory tmp/slow.bin 0xc00000 0xd80000'` for the default
slow-memory snapshot, and `python3 tools/stellar7_report.py tmp/trace.bin
tmp/slow.bin --base 0xc00000` for attribution. Hold the CPU while collecting
matched snapshots. For comparable benchmarks, use the fixed-window driver below.
Use `quit` to stop this project's emulator and debugger.

The harness is adapted from Indianapolis 500 (single-attach profiler fix),
Their Finest Hour (boot and call attribution), and Battlehawks 1942 (empty
input-port mode). A busy debugger port fails instead of killing its owner.
Never use process-name-wide kills.


## Build and fixed captures

`make -C whdload` builds the normal development loader. `make -C whdload verify`
builds the menu fixture; `SLAVE=whdload/Stellar7.Slave WHD_ARGS=CUSTOM5=1`
selects it in `amiga/run.sh`. Both retain the original CRC acceptance check.
Only the supplied English layout has been fixture-tested; hook-byte guards
reject other layouts. This is a reconstruction of the game-specific loader
on modern KickEmu, not a byte-identical reconstruction of the 2008 slave.

`python3 tools/fixed_window.py tmp/prof/base --fields 50` builds and retains
its exact VERIFY slave, boots with both input ports empty, waits for gameplay
frame 90, and saves snapshots, first/last images, trace and analysis reports.
Use a capture subdirectory without spaces; the repository path may contain
spaces. Capture output must be under `tmp/`. Only one capture runs at a time.
`--state-only` saves the anchor without tracing; `--swaps-only` uses read-only
breakpoint counting. The default window is 100 fields when `--fields` is omitted.

The 68020 configuration uses `AMIGA_MODEL=A1200 KICKSTART=$KICKSTART_A1200
CHIP_KB=2048 FAST_KB=4096 CPU=68EC020 EXTRA_ARGS=--slow_memory=0` after sourcing
`amiga/env.sh`. This is an A1200 with fast RAM, not a stock A1200.

`tools/state_summary.py CAPTURE...` reports only mapped player/RNG/timer state.
It is not a full-state equivalence test. `tools/compare_traces.py A/trace.bin
B/trace.bin` checks whole screenshots, instruction records, DMA records and
chip snapshots; it deliberately reports the known raw-register/DMA differences
between the current repeated captures instead of masking them.
