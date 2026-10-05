# Test Drive II — Amiga performance study

Profiling (and possibly optimising) the original 1989 Amiga release of Accolade's
*Test Drive II: The Duel*, run as installed by JOTD's WHDLoad package (v1.5).
Nothing from the game, Kickstart or the WHDLoad package is committed: all of it is
local input under `tmp/` (see `.gitignore`).

| Path | What |
|---|---|
| `amiga/run.sh`, `amiga/env.sh` | boot the WHDLoad install in FS-UAE (Kickstart 3.1 host, kick 1.3 kickemu inside WHDLoad) |
| `amiga/run-68030.sh` | play the PAL 68030/25 MHz setup, with all options enabled |
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

## Enhanced framerate (duel v1, slave 1.6b)

Build and run the local slave with the option enabled:

```sh
source amiga/env.sh
make -C whdload
WHD_ARGS=CUSTOM2=1 SLAVE="$PWD/whdload/TestDrive2.slave" amiga/run.sh
amiga/run-a1200.sh  # the same on an expanded A1200 (68EC020)
```

One option, "Enhanced framerate" (`CUSTOM2`), enables three changes together. WHDLoad
options cannot carry a default, so add the tooltype `CUSTOM2=1` to the game icon to
make it the default; the run scripts pass it. `CUSTOM2=0` is the original game.

- The simulation runs on a fixed PAL period, independently of drawing: every
  6 fields (8.33 Hz, the original period) on a 68000, every 2 fields (25 Hz) on a
  68020+. Rendering is chip-bus bound at 25 fps even on fast CPUs, so steps
  nobody sees are not simulated.
- The blitter gets bus priority (BLTPRI) and unused blitter interrupts are
  suppressed; every original wait and JOTD's display fix remain.
- Road and cars are projected at fractional positions, with fractional curve/hill
  integration, in both views. Car size selection remains discrete.

First-race fixed window: A500 7.1 fps (original game 6.1), A1200 16.7 fps;
68030/25 MHz reaches the 25 fps cap until the car is at speed, then 16.7 fps. See
`docs/optimisation-plan.md`.
Motion rates are scaled, the race clock follows elapsed field time, and nonfatal
crash/engine-damage recovery lasts 240 fields with a 20-second penalty. Handling
and recovery presentation change; see `docs/simulation-design.md`. v2 is
unchanged. CUSTOM1's infinite lives trainer remains supported. NTSC timing has
not been validated. Measurements in the docs that name `CUSTOM2=1`/`3`/`5`/`7`
predate 1.6b, when each feature was a separate bit.

`make -C whdload verify` adds tools for the study: CUSTOM3 removes RNG beam
entropy from the original mode, CUSTOM4 slows drawing, and CUSTOM5 bit 0 drives
an input tape. CUSTOM5=3 also forces engine damage once; CUSTOM5=5 instead forces
a fatal crash.
CUSTOM5=17 uses a straight acceleration/braking fixture; it does not follow road bends.
CUSTOM5=8 forces zero rendering fractions and initialises both scanline buffers
for the byte-identity oracle; use it in both comparison arms.
These verification options are absent from the normal build.
Use `tools/fixed_window.sh` for fps, state captures for game-time comparisons,
and the retained `OUT/slave.slave` when analysing older traces.

## Testing a normal release on 68030/25 MHz

```sh
cd "/path/to/Test Drive 2"
source amiga/env.sh
amiga/run-68030.sh
```

This builds the normal slave and launches real-time PAL play with CUSTOM2=1,
an A1200 chipset/ROM, 68030 at 25 MHz, 2 MiB chip and 4 MiB fast RAM. To run a
packaged slave instead, prefix the launcher with `SLAVE="/absolute/path/TestDrive2.slave"`.
Start a race normally, or leave the title screen for the attract demo. The demo
can drive off road; the normal release includes no scripted driver.

Ordinary launch mode runs at real wall time with sound. The previous measured
first-race window reached 25 game FPS on this configuration. Scene complexity
can change the rate during play; an emulator refresh overlay reports video
refresh rather than game drawing FPS.
