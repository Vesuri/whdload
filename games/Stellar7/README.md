# Stellar 7

A source-only WHDLoad development and profiling workspace for the supplied
English Stellar 7 install. No performance patch is enabled yet.

Read [current work](docs/open-work.md), [development](docs/development.md),
and [internals and measurements](docs/internals.md).

The original playable pack belongs in ignored `tmp/game/Stellar7NTSC/`.
`amiga/run.sh` boots it. `make -C whdload` builds the reconstructed development
loader against the vendored WHDLoad 20.0 KickEmu sources.

`python3 tools/fixed_window.py tmp/prof/base --fields 50` captures a fixed
SOL gameplay window using a verification-only menu fixture. Game data,
Kickstarts, WHDLoad executables, built slaves and captures are never committed.
