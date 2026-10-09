# Stellar 7

A source-only WHDLoad development and profiling workspace for the supplied
English Stellar 7 install. An experimental fixed-step simulation mode is
available with `CUSTOM1=1`; it is disabled by default.

Read [current work](docs/open-work.md), [development](docs/development.md),
and [internals and measurements](docs/internals.md).

The original playable pack belongs in ignored `tmp/game/Stellar7NTSC/`.
`amiga/run.sh` boots it. `make -C whdload` builds the reconstructed development
loader against the vendored WHDLoad 20.0 KickEmu sources.

Run the timing prototype with
`SLAVE=whdload/Stellar7.Slave WHD_ARGS=CUSTOM1=1 amiga/run.sh`.
The provisional default is five simulation updates per second;
`CUSTOM2=1..25` selects another fixed rate. See the validation limits in
[current work](docs/open-work.md).

`python3 tools/fixed_window.py tmp/prof/base --fields 50` captures a fixed
SOL gameplay window using a verification-only menu fixture. Game data,
Kickstarts, WHDLoad executables, built slaves and captures are never committed.
