# Test Drive II — Amiga performance study

Profiling (and possibly optimising) the original 1989 Amiga release of Accolade's
*Test Drive II: The Duel*, run as installed by JOTD's WHDLoad package (v1.5).
Nothing from the game, Kickstart or the WHDLoad package is committed: all of it is
local input under `tmp/` (see `.gitignore`).

| Path | What |
|---|---|
| `amiga/run.sh`, `amiga/env.sh` | boot the WHDLoad install in FS-UAE (Kickstart 3.1 host, kick 1.3 kickemu inside WHDLoad) |
| `amiga/run-a1200.sh` | build the patched slave and play it on an expanded A1200 (`CPU=68030` for a 25 MHz 68030) |
| `tools/td2.py` | long-lived gdb session on FS-UAE's Barto stub: screenshots, cycle-exact traces |
| `tools/profile_demo.sh` | one command: boot, wait for the attract demo to drive, trace, report |
| `tools/fixed_window.sh` | A/B benchmark: fixed race window; cycle trace or read-only swap counter (`SWAP_ONLY=1`) |
| `tools/td2_report.py`, `tools/frames.py` | attribute a trace to routines; frame rate, blitter waits, interrupts, bus use |
| `tools/barto.py` | reader for the stub's `monitor profile` trace format |
| `tools/hotspots.py`, `tools/disd.py`, `tools/dis.sh` | hottest instructions per routine, disassembly by `duel` hunk offset |
| `tools/ingame.py` | "is this screenshot the driving view" check |
| `whdload/` | JOTD's slave source (v1.5, public domain) + vendored `kick13.s`; `make -C whdload` cross-builds it with vasm |
| `docs/open-work.md` | handoff: goal, findings, ordered open work items |
| `docs/profiling.md` | the profiling procedure, exactly, with every trap found setting it up |
| `docs/optimisation-plan.md` | how to speed the game up through slave patches, in order |

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

## Optional fixed-time simulation (duel v1)

Build and run the local slave with the fixed-time mode enabled:

```sh
source amiga/env.sh
make -C whdload
WHD_ARGS=CUSTOM2=3 SLAVE="$PWD/whdload/TestDrive2.slave" amiga/run.sh
amiga/run-a1200.sh               # the same on an expanded A1200 (68EC020)
```

`CUSTOM2=1` runs the simulation on a fixed PAL period, independently of drawing:
every 6 fields (8.33 Hz, the original period) on a 68000, every 2 fields (25 Hz)
on a 68020+. Rendering is chip-bus bound at 25 fps even on fast CPUs, so steps
nobody sees are not simulated. Bit 1 (rendering) gives the blitter bus priority
(BLTPRI) and suppresses unused blitter interrupts; it retains every original
wait and JOTD's display fix. `CUSTOM2=3` enables both; `CUSTOM2=2` changes only
rendering. First-race fixed window, CUSTOM2=3: A500 7.1 fps (original game 6.1),
A1200 16.7 fps; 68030/25 MHz and faster reach the 25 fps cap. See
`docs/optimisation-plan.md`.
Motion rates are scaled, the race clock follows elapsed field time, and nonfatal
crash/engine-damage recovery lasts 240 fields with a 20-second penalty. Handling
and recovery presentation change; see `docs/simulation-design.md`. Leave CUSTOM2
off to use the original game. v2 has no simulation patches. CUSTOM1's infinite
lives trainer remains supported. NTSC timing has not been validated.

`make -C whdload verify` adds tools for the study: CUSTOM3 removes RNG beam
entropy from the original mode, CUSTOM4 slows drawing, and CUSTOM5 bit 0 drives
an input tape. CUSTOM5=3 also forces engine damage once; CUSTOM5=5 instead forces
a fatal crash.
CUSTOM5=17 uses a straight acceleration/braking fixture; it does not follow road bends.
These verification options are absent from the normal build.
Use `tools/fixed_window.sh` for fps, state captures for game-time comparisons,
and the retained `OUT/slave.slave` when analysing older traces.
