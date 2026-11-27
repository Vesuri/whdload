# Development

Only what differs from the repository's `docs/running.md` and `docs/building.md`.

## Inputs

`inputs.sha256` pins two archives, which `make unpack` installs side by side in `tmp/game/`:

| Archive | Installs | Slave |
|---|---|---|
| `VroomMultiplayer.lha` (whdload.de) | `VroomMultiplayerHd/`: installer, imager slave (no source), slave source (`.src/`), no game data | v1.6 (03.06.2006) |
| `VroomMultiPlayer_v1.6_2158.lha` (Retroplay) | `VroomMultiPlayer/`: `Disk.1`, `VroomMultiplayer.Slave` | v1.6, the same bytes |

The Retroplay `Disk.1` is the slave's "v1" (its boot block holds $3658 at $1F8). The "v2"
(NTSC) version is not among the inputs.

## The build

`src/VroomMultiplayerHD.asm` is the package's `.src/` file (the import commit has it
unchanged). The setup commit made these commented edits, after which it builds
byte-identically to the shipped slave:

- the date Barfly's `WDate` wrote into the info text, `(03.06.2006)`, is a string;
- Barfly's `DBRA.b` is `DBRA`;
- Barfly's encodings: `move.l #$8C,d0` as `moveq #$73,d0; not.b d0`, `move.b #$FF` as
  `st`, `clr.l d0` as `moveq #0,d0`, and the immediate forms `addi`/`andi`/`cmpi` where vasm
  would emit the Dn forms.

`VASM_FLAGS` stand in for Barfly's optimiser (`BOPT O+`), as in `games/Vroom`.

## Driving it

`make serve WARP=1 WINDOW=none &`, then `make server CMD=...`. Left alone, the title runs a
demo race (San Marino) after about 25 s in warp on the a500.
