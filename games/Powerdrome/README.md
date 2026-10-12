# Powerdrome

Project status: Phase F is stopped at the stock-A1200 performance gate: two runs
measure 14.575 fps versus 15.423 native (5.50% slower). Automatic defaults and timing
promotion are implemented; remaining release gates and documentation cleanup are pending.
See the [current handoff](docs/open-work.md) for completed checks, open gates and resume priorities,
and the [completion plan](docs/completion-plan.md) for the steps that finish and ship the work.

Local reverse-engineering and performance work on the Amiga PAL release.
Start with [open work](docs/open-work.md), then [development](docs/development.md) and
[internals](docs/internals.md). The [practice profile](docs/practice-profile.md) breaks down
the ten-second departure capture and identifies its bottlenecks. The
[performance plan](docs/performance-plan.md) details planar rendering into fast RAM,
presentation and CPU-specific optimization stages.

The current build automatically enables timing on 68020+ and fast planar rendering
on 68020+ with real fast RAM. `CUSTOM1=1` selects the original renderer and
`CUSTOM3=1` selects original timing. 68000/68010 keep both native paths.
It renders planar graphics and executes the rasterizer in fast RAM, then copies the scene
to the native chip buffer. See [implementation, measurements and limits](docs/performance-implementation.md).
Build and launch the new slave with fast RAM:

```sh
make -C whdload all
CPU=68030 FAST_KB=4096 SLAVE=tmp/build/Powerdrome.slave amiga/run.sh
```

The emulator defaults to a 68000; see development for faster CPU configurations.
Without suitable fast RAM the build retains native rendering. The stock A1200
performance gate is currently failing; see open work for the measured limitation.

Game data, Kickstart, built slaves and captures are not included.
