# Development

## Inputs and shared tools

Keep both supplied archives in ignored `tmp/`. Extract the installer to `tmp/installer/`
and Retroplay pack to `tmp/game/`; the playable tree is `tmp/game/Powerdrome/`.
`tmp/archive.sha256` records local input hashes. Never commit proprietary inputs or captures.

Source `amiga/env.sh` for the existing Amiga toolchain. Shared inputs use these overrides:

| Variable | Default under the shared Amiga directory |
|---|---|
| `KICKSTART` | `Kickstarts/kick40063.A600` |
| `KICK13` / `RTB` | `Kickstarts/kick34005.A500` / its `.RTB` |
| `KICKSTART_A1200` | `Kickstarts/kick40068.A1200` |
| `WHDLOAD` | `WHDLoad-20.0` |
| `WHDLOAD_BINARY` | `$WHDLOAD/C/WHDLoad` |
| `WORKBENCH_ADF` | `Workbenchv2.04rev37.67Workbench.adf` |

`FSUAE` overrides the executable, `FSUAE_COMMON` the shared process/port helper.
The shared directory convention is `~/.local/share/amiga`. `VASM` and `NDK` override the
assembler and Amiga include directory in the makefile.

## Build and run

```sh
make -C whdload original
amiga/run.sh
SLAVE=tmp/build/Powerdrome-original.slave amiga/run.sh
```

`original` assembles with optimizations disabled and compares the entire result with the
installed slave. This is the reference reconstruction. `make -C whdload all` builds the WHDLoad 20 KickEmu
development slave with interface 17. `make -C whdload verify` additionally saves
`tmp/build/Powerdrome-verify.slave`; `CUSTOM5=1` submits an empty pilot name through the
native name-entry routine. `CUSTOM5=2` also selects Practice and submits Space in the pit.
`CUSTOM1=1` enables the optional fast planar renderer; it is off by default. The normal
build contains no input or twin-drawing fixtures. The slave requests 128 KiB of guest
expansion in addition to KickEmu's 256 KiB, including when the option is off. Slow-backed
expansion does not enable the renderer. See the [implementation and measured results](performance-implementation.md)
for supported states, diagnostic options and limitations. Full original/rebase behavior
equivalence remains unverified; performance A/B tests use the same development loader.

To launch the new slave explicitly (the runner otherwise uses the installed original):

```sh
make -C whdload all
FAST_KB=4096 WHD_ARGS=CUSTOM1=1 SLAVE=tmp/build/Powerdrome.slave amiga/run.sh
```

The default machine is 68000, 512 KB chip and 1,536 KB slow with no fast RAM. The host boots
Kickstart 3.1 and Workbench 2.04 provides Assign for the original slave's Kickstart files.
Windowed, real speed, sound enabled. `CPU`, `CHIP_KB`, `FAST_KB`, `AMIGA_MODEL`, `EXTRA_ARGS`,
`WHD_ARGS`, `WB`, `SILENT`, `WARP`, `JOY0` and `JOY1` override the setup.

## Inspection

```sh
JOY0=none DETERMINISTIC=1 WARP=1 python3 tools/powerdrome.py serve
python3 tools/powerdrome.py shot tmp/now.png
python3 tools/powerdrome.py stop
python3 tools/powerdrome.py profile 10 tmp/trace.bin
python3 tools/powerdrome.py gdb 'dump binary memory tmp/slow.bin 0xc00000 0xd80000'
python3 tools/powerdrome_report.py tmp/trace.bin tmp/slow.bin
python3 tools/powerdrome.py quit
```

The server occupies its terminal; issue clients from another. Only one server/capture per repo.
For reproducible captures unplug host inputs (`JOY0=none`, both device and mode) and avoid
interacting with the emulator. The debugger cannot write guest memory. `BOOT_BREAK` arms a
read-only breakpoint from reset, but must be calibrated against the current build/memory setup.
The x86_64 profiler window uses the existing single-attach LLDB workaround; its assertion
checks the write. Emulated time stops while attached. Screenshots come from trace captures.

The harness and parser derive from Indianapolis 500; OFS extraction and patch-list decoding
from Battlehawks 1942. The reporting locator has been adapted to Powerdrome's single hunk
and either the original or development slave.

`tools/adf.py` lists/extracts the local disk image; `tools/patchlist.py` decodes original lists.
See `docs/open-work.md` before interpreting a capture as a benchmark.

## Fixed attract-demo window

```sh
make -C whdload verify
FIELDS=100 tools/fixed_window.sh tmp/prof/demo-a
FIELDS=100 tools/fixed_window.sh tmp/prof/demo-b
python3 tools/compare_traces.py tmp/prof/demo-a/trace.bin tmp/prof/demo-b/trace.bin
SWAP_ONLY=1 FIELDS=100 tools/fixed_window.sh tmp/prof/demo-swaps
```

The first run calibrates the relocated code address. Each measurement boot arms game `$1067e`
from reset, after the first animated-inset render. The name fixture lets the native menu reach
its idle timeout. `FIELDS`, `ANCHOR`, and `SERVE_WAIT` are overridable. An explicit second
argument selects the input slave. Captures retain the slave, initial memory, anchor registers,
trace, profile, frame report, first/last images, and final memory dumps. Do not touch inputs during captures.

This is the moving inset on the title screen; its pixel workload and playback timing differ
from racing. It advances the recorded camera by two samples per rendered frame. It is useful
for renderer bring-up, but cannot establish simulation correctness or full-screen racing FPS.

For the 68020 comparison (run sequentially, after the A500 capture):

```sh
source amiga/env.sh
AMIGA_MODEL=A1200 CPU=68EC020 KICKSTART="$KICKSTART_A1200" CHIP_KB=2048 FAST_KB=4096 \
  EXTRA_ARGS=--slow_memory=0 FIELDS=100 tools/fixed_window.sh tmp/prof/demo-a1200
```

Add `SWAP_ONLY=1` to count the same marker with read-only debugger breakpoints instead of
instruction tracing. Compare the complete `demo frame completions per field` line, not just
rounded FPS. The trace comparator checks all initial chip RAM, instruction and DMA records,
and screenshots excluding only three rightmost host-border columns.

## Ten-second practice launch profile

```sh
make -C whdload verify
WHD_ARGS=CUSTOM5=2 ANCHOR=0x14764 FIELDS=500 \
  tools/fixed_window.sh tmp/prof/practice-10s
```

The route submits Enter at name entry, then the native `3` shortcut for the top-middle
Practice button, then Space at the pit's input loop. The capture anchor is the first
iteration of the pit departure animation, after the Space handling and stationary delay.
The ship then flies onto the track automatically; host inputs stay disconnected.

The stock profiler command clamps requests to 100 fields. Back-to-back requests omit one
field at each boundary (confirmed using the game's VBL counter), so they do not make a
continuous trace. For requests of 101–500 fields, the harness lifts the command cap in the
current emulator process during its existing debugger attachment. It verifies the exact
instruction bytes before and after the change. The installed emulator file and guest game
code are not modified. This workaround is specific to the documented x86_64 emulator build.

The 500 fields are recorded in one request, giving ten nominal PAL seconds without internal
gaps. The output retains the slave, anchor/memory dumps, `trace.bin`, `profile.txt` and
first/last images. Routine boundaries in the generic report are inferred. For normal driving, `$bc7c` is the
presentation marker; `tools/perf_report.py` and the independent `SWAP_ONLY=1` counter use it.
Departure animations are not counted as driving frames. `tools/perf_status.py` checks the
optional renderer's pixel/state/guard counters and static-code integrity.
