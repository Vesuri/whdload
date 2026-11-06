# Development

WHDLoad slave patches for the original 1989 Amiga release of Accolade's *Test Drive II: The
Duel*, built on JOTD's public-domain v1.5 slave. The "Enhanced framerate" option makes game
time independent of the CPU and draws the road and cars smoothly; the game itself is
unchanged and the original remains one option away.

Slave 1.6b (an unreleased beta of 1.6) runs with WHDLoad 17.2 or later.

## Enhanced framerate (`CUSTOM2`, duel v1)

WHDLoad options have no default, so the release's game icon carries the tooltype
`CUSTOM2=1`. `CUSTOM2=0` runs the original game; v2 of the game is unpatched.

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
had passed (`intro_ddfstop_close` in `src/TestDrive2HD.s`). `CUSTOM1=1` is JOTD's
infinite-lives trainer.

## Files

| Path | What |
|---|---|
| `src/TestDrive2HD.s` | the slave: JOTD's v1.5 source plus the patch lists |
| `src/simulation*.s`, `src/simulation-patches.i` | fixed-time simulation; `simulation-verify.s` holds the VERIFY assertions and fixtures |
| `src/render.s` | sub-unit rendering |
| `src/include/lvo/` | NDK aliases for the KickEmu sources |
| `release/readme` | JOTD's installer ReadMe with this work's history entry |
| `release/TestDrive2.exoticon` | the installer's game icon with the tooltype `CUSTOM2=1` |
| `release/whdload-README.md` | the notes shipped beside the KickEmu sources in the installer's `source/whdload/` |
| `tools/` | tracing, state capture and checks ([testing.md](testing.md)) |

## Inputs

`inputs.sha256` pins JOTD's v1.5 installer `TestDrive2.lha` (with the slave source) and
the Retroplay preinstalled `TestDrive2_v1.5_0588.lha`. `make unpack ARCHIVES=<directory>`
unpacks them to `tmp/game/TestDrive2Install/` and `tmp/game/TestDrive2/`, the drawer every run
copies. Kickstarts, Workbench, WHDLoad, the toolchain and FS-UAE come from the shared
environment (AmigaXDev's `docs/environment.md`); the slave's KickEmu image is
`kick34005.A500` with its `.RTB` (`KICKS` in `game.conf`).

## Build and run

```sh
make slave                                # tmp/build/release/TestDrive2.Slave
make verify                               # tmp/build/verify/TestDrive2.Slave
make run WHD_ARGS=CUSTOM2=1               # the default machine: A500, 1 MB chip, 2 MB fast
make run SLAVE=original                   # JOTD's shipped v1.5 slave
make run TD_SETUP=a1200 WHD_ARGS=CUSTOM2=1        # expanded A1200 (68EC020)
make run TD_SETUP=a1200-030 WHD_ARGS=CUSTOM2=1    # A1200 with a cycle-exact 25 MHz 68030
```

The build is vasm with `-pic` against the shared WHDLoad tree (`$WHDLOAD`: its API headers
and KickEmu sources) and the toolchain's NDK; `src/include/lvo/` comes first. `TD_SETUP`
selects the reference machines ([testing.md](testing.md#machines)), in real time with
sound unless `WARP=1`. Start a race, or leave the title screen for the attract demo.

`make verify` builds the test slave: `CUSTOM3` makes runs reproducible, `CUSTOM4` slows
drawing, and `CUSTOM5` selects scripted input and forced-event fixtures plus 129 assembly
assertions ([simulation-design.md](simulation-design.md#verification-hooks)). The release
build has none of them. `make check` checks the release build against
`release/slaves.sha256`, compiles the tools, assembles the VERIFY build and runs
`tools/audit_simulation.py` on the installed `duel`. Testing and the regression checklist:
[testing.md](testing.md).

## Release

`make dist` repacks JOTD's installer archive into `dist/TestDrive2Enhanced-<version>.lha`
(`release/release.json`). Only the slave, the ReadMe, the game icon and the installer's
`source/` change: the new `TestDrive2HD.s` plus the files it includes, the
`release/whdload-README.md` notes and the KickEmu sources and API headers the slave is built
from, which `game_dist` in `game.sh` copies from `$WHDLOAD` into `tmp/release/whdload/`
first. Everything else, JOTD's Makefiles, `datmerger` and its source among them, is copied
byte for byte. The slave's `$VER` string (`slave 1.6b`, from KickEmu) has no date, so the
archive name has none. The
old packager also repacked the Retroplay preinstalled archive; a release here is the installer
only.
