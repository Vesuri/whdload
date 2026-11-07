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
complete. Step 6 cut A500 interrupt time: the 68000 build masks Kickstart's unused
blitter-finished interrupt and runs an exact faster pass of the music driver's channel
update, freeing 4–7% of the A500's cycles in gameplay; the step 7 baseline on the three
validation machines measures 10–17% more A500 presentations from it, and its
regression checks pass. Remaining, in order (`docs/open-work.md`): encounter
coverage, final build checks, playtesting and the release.

Launch the separate experimental build from this directory:

```sh
make play60                      # the default machine: A500, 15 Hz
make play60 SETUP=a1200-fast     # 60 Hz
```

The launcher resolves `AMIGA_SETUP` before selecting by `CPU` (default 68000),
enables `CUSTOM1=1` and uses
normal controls and sound. `make slave` builds all three variants, and
`make slave VARIANT=Stellar7-Sim68000` (or `Stellar7-Sim60`) builds one. The resulting files are
`tmp/build/release/Stellar7-Sim68000.Slave` and `tmp/build/release/Stellar7-Sim60.Slave`.
For real hardware, copy the appropriate variant; the slaves do not switch
rates at runtime. Scripted tests use the existing VERIFY fixtures.

To try 20 Hz on the 68000, use `make play60 SIM68000_SUBSTEPS=4`.
Without that override the next launch rebuilds the selected 15 Hz default.

Build the installer archive, Stellar 7 Enhanced 2.0b (not yet published), with
`make dist`: the repository's
`dist/Stellar7Enhanced-2.0b-20261107.lha` and its checksum. It includes both CPU builds
and an installer choice, and the installed icon of a fixed-rate build enables it with
`CUSTOM1=1`; original English NTSC disks are required.

Read [current status and remaining work](docs/open-work.md),
[build and validation instructions](docs/development.md), and
[internals and measurements](docs/internals.md).

`make unpack ARCHIVES=<directory>` installs the original playable pack into ignored
`tmp/game/Stellar7NTSC/`; `make run SLAVE=original` boots it unchanged. `make slave
VARIANT=Stellar7` builds the reconstructed development loader against the shared WHDLoad
KickEmu sources (`$WHDLOAD`).
That normal build retains the earlier opt-in five-Hz timing prototype; it
does not contain the fixed-rate conversion.

Game data, Kickstarts, WHDLoad executables, built slaves and captures are
never committed. Local evidence referenced by the documents remains in
ignored `tmp/`; the repository contains source and validation tools.
