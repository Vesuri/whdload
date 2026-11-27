# Development

## Inputs

`inputs.sha256` pins two archives:

- `StuntTrackRacer.lha`: Codetapper's v1.0 install package from whdload.de (the slave, the
  Install script, which makes the DIC image, the icons and a save file; no source).
- `StuntTrackRacer_v1.0_NTSC_1142.lha`: the Retroplay install (`Disk.1`, a 468480-byte DIC
  image of the start of the disk, and the slave as `StuntTrackRacerNTSC.Slave`).

`make unpack` installs both; the variant boots the Retroplay drawer `StuntTrackRacerNTSC`.

## The build

The v1.0 slave shipped without source. `src/StuntTrackRacer.s` is a reconstruction from its
disassembly that builds it byte for byte (`release/slaves.sha256` records it): the labels
and comments are new, the instructions are the slave's. Its hunk ends in a zero word, which
the source writes out: vasm pads a code hunk with `nop`. `-devpac` (no optimisation)
matches; the slave has no relocations.

The enhanced framerate is built from Stunt Car Racer's files: `game_build` (game.sh) runs
its `tools/ulblob.py --define NTSC=1` into the ignored `tmp/include/`, and `INCLUDES` adds
its `src/` for `relocs.s`. A change to that game's blob or table changes this slave: build
and check both. To check the blob's patches against this program, extract it with that
game's `tools/scr_extract.py Disk.1 OUT --ntsc` and pass `--original OUT` to `ulblob.py`.

## Driving it

`make serve WARP=1 WINDOW=none INSTANCE=<name> &`, then `make server INSTANCE=<name> CMD=...`.
It reaches the main menu within about 25 s of warp. Stunt Car Racer's `tools/scr.py` drives
it too (`python3 ../StuntCarRacer/tools/scr.py serve`, then `fields`, `keys`, `peek`): from
the menu, RETURN, a typed name (the slave does not skip the name entry), then RETURN four
times reaches a practice race on the Little Ramp. Drive the verify build on
`SETUP=a1200-030` with `WHD_ARGS='CUSTOM3=1 MMU'` to look for missed references.
