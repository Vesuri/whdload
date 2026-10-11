# Powerdrome

Project status: completion-plan Phase A is complete; work is stopped before Phase B.
See the [current handoff](docs/open-work.md) for completed checks, open gates and resume priorities,
and the [completion plan](docs/completion-plan.md) for the steps that finish and ship the work.

Local reverse-engineering and performance work on the Amiga PAL release.
Start with [open work](docs/open-work.md), then [development](docs/development.md) and
[internals](docs/internals.md). The [practice profile](docs/practice-profile.md) breaks down
the ten-second departure capture and identifies its bottlenecks. The
[performance plan](docs/performance-plan.md) details planar rendering into fast RAM,
presentation and CPU-specific optimization stages.

The optional implementation is enabled with WHDLoad `CUSTOM1=1` and is off by default.
It renders planar graphics and executes the rasterizer in fast RAM, then copies the scene
to the native chip buffer. See [implementation, measurements and limits](docs/performance-implementation.md).
Build and launch the new slave with fast RAM:

```sh
make -C whdload all
FAST_KB=4096 WHD_ARGS=CUSTOM1=1 SLAVE=tmp/build/Powerdrome.slave amiga/run.sh
```

The emulator defaults to a 68000; see development for faster CPU configurations.
Without suitable fast RAM the option retains native rendering.

Game data, Kickstart, built slaves and captures are not included.
