# Stellar 7

A source-only WHDLoad development and profiling workspace for the supplied
English NTSC Stellar 7 install.

The experimental SIM60 conversion uses a **5 Hz fixed simulation timestep**
(N=1), independent of rendering and identical on every machine. Measurements
selected this rate: higher supported rates failed the A500 native presentation
threshold, while 5 Hz sustained the heavy-combat window without accumulating
pending updates. N=12 (60 Hz) remains buildable for reference checks.

It is playable, but **the conversion is unfinished**. The timestep is 200 ms;
faster rendering repeats poses between ticks until interpolation is added.
Steps 0–2 are complete; work stops before
step 3 for the user's pace playtest. Live input is still sampled during catch-up
rather than preserved by tick. Broader gameplay and original-reference pace
validation remain open.

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
