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
selects it in `amiga/run.sh`. Both retain the original CRC acceptance check. `CUSTOM1=1` enables the
experimental fixed-step timing patches; without it the game code is unchanged
except for explicitly enabled VERIFY fixtures.
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

The 68020 configuration uses `AMIGA_MODEL=A1200 KICKSTART=$KICKSTART_A1200
CHIP_KB=2048 FAST_KB=4096 CPU=68EC020 EXTRA_ARGS=--slow_memory=0` after sourcing
`amiga/env.sh`. This is an A1200 with fast RAM, not a stock A1200.

`tools/state_summary.py CAPTURE...` reports only mapped player/RNG/timer state.
It is not a full-state equivalence test. `tools/compare_traces.py A/trace.bin
B/trace.bin` checks whole screenshots, instruction records, DMA records and
chip snapshots; it deliberately reports the known raw-register/DMA differences
between the current repeated captures instead of masking them.


## Fixed-step timing tests

`WHD_ARGS='CUSTOM1=1 CUSTOM3=1' python3 tools/fixed_window.py
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
