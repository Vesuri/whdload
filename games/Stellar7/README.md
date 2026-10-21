# Stellar 7

A source-only WHDLoad development and profiling workspace for the supplied
English NTSC Stellar 7 install.

The experimental SIM60 conversion runs **15 Hz on 68000 and 60 Hz on
68020+**, with fixed real-time game speed and no interpolation. Rendering
uses the latest completed state and runs independently of simulation timing.

**The conversion is unfinished.** Input during catch-up belongs to each tick's
recorded time. Selected-rate rendering optimization and regression checks pass.
Fast-CPU measurements identify drawing and blitter work as the main presentation
limit in the sampled scenes. Extended combat maintains the selected average
simulation rates, although slow machines still show substantial response delays.
The buffer-reuse correction now waits for the native display handoff before
starting another draw, while simulation continues. Its fresh performance matrix,
extended-combat, input, lifecycle and both launcher checks pass. Step 5 is
complete; broader gameplay, physical-control, pace and audio playtesting remain
open in step 6.

Source the shared environment and launch the separate experimental build:

```sh
source amiga/env.sh
amiga/play60.sh
```

The launcher resolves `AMIGA_SETUP` before selecting by `CPU` (default 68000),
enables `CUSTOM1=1` and uses
normal controls and sound. Build both variants with `make -C whdload sim`, or
use `sim68000` / `sim60` separately. The resulting files are
`whdload/Stellar7-Sim68000.Slave` and `whdload/Stellar7-Sim60.Slave`.
For real hardware, copy the appropriate variant; the slaves do not switch
rates at runtime. Scripted tests use the existing VERIFY fixtures.

To try 20 Hz on the 68000, use `SIM68000_SUBSTEPS=4 amiga/play60.sh`.
Without that override the next launch rebuilds the selected 15 Hz default.

Build the current experimental installer archive with `make dist`. The `.lha`,
checksum and verification report are written to `tmp/dist/`. It includes both
CPU builds and an installer choice; original English NTSC disks are required.

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
