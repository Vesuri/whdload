# Powerdrome

Performance and timing improvements for the PAL release: one **Enhanced framerate** option
(`CUSTOM1=1`, default off) enables fast planar rendering in Fast memory and fixed-step
gameplay timing together on a 68020+ with real Fast memory; otherwise the game stays
original. The original slave is Galahad/Fairlight's v1.0 (2003), which shipped without
source; `src/original/` reconstructs it byte for byte (game.conf `AUTHOR`, `UPSTREAM`).
The repository's rules and shared docs are in the root `AGENTS.md` and `docs/index.md`;
this file and `docs/` here hold only what is specific to this game.

Read `docs/open-work.md` first.

| Doc | Read it for |
|---|---|
| `docs/open-work.md` | where the work stands, its limits, what a release still needs |
| `docs/development.md` | builds, runs, captures, the release matrix and the checks |
| `docs/internals.md` | the game, the slave, timing and the measured machine configurations |
| `docs/timing-implementation.md` | the fixed-step timing design and its evidence |
| `docs/performance-implementation.md` | the Fast memory renderer and its evidence |
| `docs/practice-profile.md` | the original Practice departure profile |
| `docs/loader-equivalence.md` | the original and development loaders compared |
| `docs/gameplay-coverage.md` | the coverage replay routes and their checks |
| `docs/accelerator-cache-testing.md` | 030/040/060 and WHDLoad cache results |
| `docs/raster-improvements.md` | the rasteriser changes and their measurements |

The slave source is `src/` (`Powerdrome.s` and its modules; `original/` is the
reconstruction). Every build includes `tmp/build/mouse-sine.i`, which `tools/mouse_sine.py`
generates (game.sh `game_build`). The rest of `tools/` is the development harness and never
ships: `powerdrome.py` is the gdb-stub server, `fixed_window.sh` the capture runner,
`release_matrix.py` the release measurements and the `check_*.py` scripts the gates.
