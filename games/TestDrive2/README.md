# Test Drive II — Amiga performance study

Profiling (and possibly optimising) the original 1989 Amiga release of Accolade's
*Test Drive II: The Duel*, run as installed by JOTD's WHDLoad package (v1.5).
Nothing from the game, Kickstart or the WHDLoad package is committed: all of it is
local input under `tmp/` (see `.gitignore`).

| Path | What |
|---|---|
| `amiga/run.sh`, `amiga/env.sh` | boot the WHDLoad install in FS-UAE (Kickstart 3.1 host, kick 1.3 kickemu inside WHDLoad) |
| `tools/td2.py` | long-lived gdb session on FS-UAE's Barto stub: screenshots, cycle-exact traces |
| `tools/profile_demo.sh` | one command: boot, wait for the attract demo to drive, trace, report |
| `tools/td2_report.py`, `tools/frames.py` | attribute a trace to routines; frame rate, blitter waits, interrupts, bus use |
| `tools/barto.py` | reader for the stub's `monitor profile` trace format |
| `tools/hotspots.py`, `tools/disd.py`, `tools/dis.sh` | hottest instructions per routine, disassembly by `duel` hunk offset |
| `tools/ingame.py` | "is this screenshot the driving view" check |
| `whdload/` | JOTD's slave source (v1.5, public domain) + vendored `kick13.s`; `make -C whdload` cross-builds it with vasm |
| `docs/profiling.md` | the profiling procedure, exactly, with every trap found setting it up |

## Local inputs

```
tmp/TestDrive2_v1.5_0588.lha     pre-installed WHDLoad game     → unpack to tmp/game/
tmp/TestDrive2.lha               WHDLoad installer (slave source) → unpack to tmp/installer/
/path/to/kickstarts/       kick31.rom (host), kick34005.A500 (slave)
/path/to/kick34005.A500.RTB
/path/to/Workbenchv2.04rev37.67Workbench.adf
/path/to/WHDLoad/    WHDLoad package
/path/to/fs-uae, /path/to/bin  FS-UAE (Barto gdb stub) and m68k-amiga-elf toolchain
```

```sh
mkdir -p tmp/game tmp/installer
(cd tmp/game && lha xq ../TestDrive2_v1.5_0588.lha)
(cd tmp/installer && lha xq ../TestDrive2.lha)
amiga/run.sh                     # play it
tools/profile_demo.sh            # profile it (docs/profiling.md)
make -C whdload && SLAVE=$PWD/whdload/TestDrive2.slave tools/profile_demo.sh tmp/prof/mine
```
