# Development

Only what differs from the repository's `docs/running.md` and `docs/building.md`: the inputs
and how they are installed, game-specific tools, captures and traps.

## Inputs

`inputs.sha256` pins two files in `tmp/archives/`:

- `Powermonger.lha`: the whdload.de install package v1.4.1, with the slave and the docs.
- `PowerMonger.ipf`: an image of the original disk.

The slave is a DIC install, so it needs a plain sector image, `Disk.1`. `make unpack` runs
`game_unpack` in `game.sh`. It builds `tmp/game/Powermonger` from the install package and
decodes the IPF with `tools/ipf2adf.py`. That tool uses the SPS capsimg library at
`$AMIGA_SHARE/capsimg/capsimg.so` (set `CAPSIMG` to use another one). All 1760 sectors decode
with valid checksums.

AmigaXDev's setup does not install capsimg. Build it from FrodeSolheim's `capsimg`
repository (`./bootstrap`, `./configure` in `CAPSImg/`, `make`) and copy `capsimg.so` to
`$AMIGA_SHARE/capsimg/`. Its structures are packed (`#pragma pack(1)`), which
`tools/ipf2adf.py` follows.

A cracked image is not tested and not pinned. The slave accepts both decruncher variants of
`RUN_PROG`, but a crack changes the program that the patches expect.

## Build

`game.conf` sets `VASM_FLAGS` to Wepl's winstalls flags. The template's flags include
`-devpac`, which turns off vasm's optimizations: the slave then keeps absolute references, and
WHDLoad refuses it with "Slave is illegal, contains relocations". `src/.date` holds the
version date that the source includes with `INCBIN` in the info text. Wepl's build writes it;
here it holds the shipped date, 10.02.2025, so the build equals the shipped slave.

## Running

`WB=0` boots without the Workbench 2.04 floppy, for a setup without `$WORKBENCH_ADF`. The
game does not need it.

## Builds

| `BUILD` | Defines | For |
|---|---|---|
| `release` | none | the slave that ships |
| `quick` | `QUICKSTART=1` | scripted runs: no name entry, a random land, a constant random seed |

## Tools

- `tools/ipf2adf.py`: the IPF decoder for `make unpack`.

## Traps

- The game seeds its random numbers from the beam position, so compare runs only with the
  QUICKSTART build.
