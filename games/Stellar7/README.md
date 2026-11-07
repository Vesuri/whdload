# Stellar 7

A source-only WHDLoad development and profiling workspace for the supplied
English NTSC Stellar 7 install.

The experimental SIM60 conversion runs **15 Hz on 68000 and 60 Hz on
68020+**, with fixed real-time game speed and no interpolation. Rendering
uses the latest completed state and runs independently of simulation timing.

**The conversion is experimental.** Input during catch-up belongs to each tick's
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
regression checks pass. Encounter coverage, the final build checks and the playtest
are done, and 2.0b is released (`docs/open-work.md`).

Play the release slave from this directory:

```sh
make play60                      # the default machine: A500, 15 Hz
make play60 SETUP=a1200-fast     # 60 Hz
```

`make play60` runs the release slave, `Stellar7.Slave`, with `CUSTOM1=1` and
normal controls and sound. The slave carries both simulations and installs the one
for the CPU: 15 Hz on 68000/68010, 60 Hz on 68020+. Without `CUSTOM1` it runs
the original timing. `make slave` builds it at `tmp/build/release/Stellar7.Slave`,
beside the development variants `Stellar7-Sim68000` and `Stellar7-Sim60`. Each of
those builds one simulation into the slave, the form the scripted VERIFY tests use;
the release slave's copies are checked byte for byte against them.

To try 20 Hz on the 68000, use `make play60 SIM68000_SUBSTEPS=4`.
Without that override the next launch rebuilds the selected 15 Hz default.

Build the installer archive, Stellar 7 Enhanced 2.0b (published on GitHub), with
`make dist`: the repository's `dist/Stellar7Enhanced-2.0b-20261107.lha` and its
checksum. It ships the one slave; the installer asks for the fixed-rate simulation
or the original timing and sets `CUSTOM1=1` in the icon for the former. Original
English NTSC disks are required.

Read [current status and remaining work](docs/open-work.md),
[build and validation instructions](docs/development.md), and
[internals and measurements](docs/internals.md).

`make unpack ARCHIVES=<directory>` installs the original playable pack into ignored
`tmp/game/Stellar7NTSC/`; `make run SLAVE=original` boots it unchanged. The release
slave's loader is reconstructed from Psygore's and built against the shared WHDLoad
KickEmu sources (`$WHDLOAD`).

Game data, Kickstarts, WHDLoad executables, built slaves and captures are
never committed. Local evidence referenced by the documents remains in
ignored `tmp/`; the repository contains source and validation tools.
