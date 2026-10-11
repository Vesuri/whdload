# Stellar 7

A source-only WHDLoad development and profiling workspace for the supplied
English NTSC Stellar 7 install.

The experimental conversion uses a 60 Hz simulation timestep independently
of rendering, with integer remainders to preserve movement precision.
It is playable, but **the conversion is unfinished**. The active performance
plan will select one lower fixed tick rate for every machine, based on A500
heavy-combat measurements. The complete native/SIM60 baseline is recorded
in internals; the game still runs at 60 Hz.
Live input is still sampled during catch-up rather than preserved by tick;
heavy A500 combat can accumulate simulation debt. Broader gameplay and
original-reference pace validation also remain open.

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
does not contain the new 60 Hz conversion.

Game data, Kickstarts, WHDLoad executables, built slaves and captures are
never committed. Local evidence referenced by the documents remains in
ignored `tmp/`; the repository contains source and validation tools.
