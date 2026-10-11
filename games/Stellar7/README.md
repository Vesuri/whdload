# Stellar 7

A source-only WHDLoad development and profiling workspace for the supplied
English NTSC Stellar 7 install.

The experimental SIM60 conversion targets **60 Hz fixed simulation with no
interpolation**, independent of rendering. Separate 68000 and 68020+ paths
may improve performance while preserving the same timing and gameplay.

**The conversion is unfinished.** The default is restored to N=12 (60 Hz),
with release and VERIFY bytes matching the retained N=12 reference. Fresh
baseline and regression validation through the updated shared toolchain passes.
Input history, sustained A500 performance and broader gameplay validation remain open.

Source the shared environment and launch the separate experimental build:

```sh
source amiga/env.sh
amiga/play60.sh
```

`make -C whdload sim60` builds `whdload/Stellar7-Sim60.Slave` without launching.
The launcher enables `CUSTOM1=1` and uses normal controls and sound.
Scripted gameplay tests use the existing VERIFY input fixtures.

Read [current status and remaining work](docs/open-work.md),
[build and validation instructions](docs/development.md), and
[internals and measurements](docs/internals.md).

The original playable pack belongs in ignored `tmp/game/Stellar7NTSC/`.
`amiga/run.sh` boots it. `make -C whdload` builds the reconstructed development
loader against the shared WHDLoad 20.0 KickEmu sources (`$WHDLOAD`).
That normal build retains the earlier opt-in five-Hz timing prototype; it
does not contain the fixed-rate conversion.

Game data, Kickstarts, WHDLoad executables, built slaves and captures are
never committed. Local evidence referenced by the documents remains in
ignored `tmp/`; the repository contains source and validation tools.
