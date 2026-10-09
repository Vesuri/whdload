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
installed slave. This is a reference reconstruction; the modern KickEmu development slave
and VERIFY build are still to be made.

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
and original slave; do not use it unchanged with a future KickEmu slave.

`tools/adf.py` lists/extracts the local disk image; `tools/patchlist.py` decodes original lists.
See `docs/open-work.md` before interpreting a capture as a benchmark.
