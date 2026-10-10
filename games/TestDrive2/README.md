# Test Drive II — WHDLoad slave with Enhanced framerate

WHDLoad slave patches for the original 1989 Amiga release of Accolade's *Test Drive II: The
Duel*, built on JOTD's public-domain v1.5 slave. The "Enhanced framerate" option makes game
time independent of the CPU and draws the road and cars smoothly; the game itself is
unchanged and the original remains one option away. Nothing from the game, Kickstart or
WHDLoad is committed: all of it is local input under the ignored `tmp/`.

Slave 1.6b (an unreleased beta of 1.6) runs with WHDLoad 17.2 or later.

## Enhanced framerate (`CUSTOM2`, duel v1)

WHDLoad options have no default, so add the tooltype `CUSTOM2=1` to the game icon (the release
archives do). `CUSTOM2=0` runs the original game; v2 of the game is unpatched.

- The simulation runs on a fixed PAL period, independently of drawing: every 6 fields (8.33 Hz,
  the original) on a 68000, every 2 fields (25 Hz) on a 68020+. Race time follows real time.
- A crash or engine damage costs 240 fields and a 20-second penalty while the opponent and the
  clock keep running, instead of a recovery whose length depended on the CPU.
- The blitter gets bus priority and unused blitter interrupts are suppressed.
- Road and cars are projected at fractional positions in both views; steering, lane position,
  mountains and hill crests move smoothly.

First race: A500 7.1 fps (original 6.1), A1200 16.7 fps, 68030/25 MHz 25 fps (the chip-bus
cap). Independently of the option, the slave fixes an original bug in duel v1: each intro car
jumped 16 pixels left for one frame, because the copper changed DDFSTOP after that line's stop
had passed (`intro_ddfstop_close` in `whdload/TestDrive2HD.s`). `CUSTOM1=1` is JOTD's
infinite-lives trainer.

## Layout

| Path | What |
|---|---|
| `whdload/TestDrive2HD.s` | the slave: JOTD's v1.5 source plus the patch lists |
| `whdload/simulation*.s`, `simulation-patches.i` | fixed-time simulation; `simulation-verify.s` holds the VERIFY assertions and fixtures |
| `whdload/render.s` | sub-unit rendering |
| `whdload/include/lvo/`, `whdload/whdload/README.md` | NDK aliases for the KickEmu sources, and the [notes](whdload/whdload/README.md) shipped with them |
| `whdload/readme-history.txt` | release notes added to the archive ReadMe |
| `amiga/` | run the game in FS-UAE: `run.sh`, `run-a1200.sh`, `run-68030.sh`, `env.sh` |
| `tools/` | tracing, state capture, checks and release packaging ([testing.md](docs/testing.md)) |
| `docs/` | [open work](docs/open-work.md), [the game](docs/game.md), [simulation](docs/simulation-design.md), [rendering](docs/subunit-rendering.md), [testing](docs/testing.md) |

## Setup

Local inputs, in `tmp/`:

```
tmp/TestDrive2_v1.5_0588.lha     pre-installed WHDLoad game        → unpack to tmp/game/
tmp/TestDrive2.lha               WHDLoad installer (slave source)  → unpack to tmp/installer/
```

Common Amiga files and the toolchain come from the shared environment that AmigaXDev installs
(`make setup` there): `amiga/env.sh` sources its `~/.local/share/amiga/env.sh`, and the Makefile
and `tools/local_env.py` use the same defaults. Set a variable to override it; AmigaXDev's
`docs/environment.md` describes them all. The ones used here:

| Variable | Default | Used for |
|---|---|---|
| `KICKSTART` | `~/.local/share/amiga/Kickstarts/kick40063.A600` | host ROM (KS 3.1) |
| `KICKSTART_A1200` | `~/.local/share/amiga/Kickstarts/kick40068.A1200` | host ROM for the A1200/68030 runs |
| `KICKSTART13` | `~/.local/share/amiga/Kickstarts/kick34005.A500` | the slave's KickEmu image |
| `RTB` | `~/.local/share/amiga/Kickstarts/kick34005.A500.RTB` | its relocation table |
| `WORKBENCH_ADF` | `~/.local/share/amiga/Workbenchv2.04rev37.67Workbench.adf` | host boot floppy (C:, Libs:) |
| `WHDLOAD` | `~/.local/share/amiga/WHDLoad-20.0` | API headers and KickEmu sources the slave builds with |
| `WHDLOAD_BINARY` | `~/.local/share/amiga/WHDLoad-20.0/C/WHDLoad` | WHDLoad run by the emulated Amiga |
| `FSUAE_COMMON` | `~/.local/share/amiga/fsuae_common.sh` | port claim; kills only our emulator |
| `LHA` | `~/.local/share/amiga/lha-compressor/src/lha` | LHa for UNIX (release archives) |
| `AMIGA_TOOLCHAIN` | `~/.local/opt` | `bin/m68k-amiga-elf-{gdb,objdump}`, NDK includes |
| `VASM` | `~/.local/vasmm68k_mot` | assembler (else `vasmm68k_mot` on PATH) |

FS-UAE with the Barto gdb stub is taken from `~/.local/fs-uae` on PATH. Scratch output
(traces, dumps, screenshots) goes to `tmp/`.

```sh
mkdir -p tmp/game tmp/installer
(cd tmp/game && lha xq ../TestDrive2_v1.5_0588.lha)
(cd tmp/installer && lha xq ../TestDrive2.lha)
```

## Build and run

```sh
source amiga/env.sh
make -C whdload                                                     # whdload/TestDrive2.slave
WHD_ARGS=CUSTOM2=1 SLAVE="$PWD/whdload/TestDrive2.slave" amiga/run.sh   # A500
amiga/run-a1200.sh                                                  # expanded A1200 (68EC020)
amiga/run-68030.sh                                                  # A1200 with a 25 MHz 68030
```

The run scripts play in real time with sound; `SLAVE=/absolute/path` runs another build. Start
a race, or leave the title screen for the attract demo.

`make -C whdload verify` builds the test slave: `CUSTOM3` makes runs reproducible, `CUSTOM4`
slows drawing, and `CUSTOM5` selects scripted input and forced-event fixtures plus 129 assembly
assertions ([simulation-design.md](docs/simulation-design.md#verification-hooks)). The normal
build has none of them. Testing and the regression checklist: [testing.md](docs/testing.md).

## Release

`python3 tools/package_release.py` rebuilds JOTD's installer and the Retroplay preinstalled
archive from their v1.5 copies in `tmp/` into `dist/TestDrive2-<ver>.lha` and
`dist/TestDrive2_v<ver>_0588.lha`. Only the slave, the ReadMe (gaining
`whdload/readme-history.txt`), the game icon (gaining `CUSTOM2=1`) and the installer's
`source/` change. The preinstalled archive contains the game: do not publish it with the repo.
