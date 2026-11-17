# Development

Only what differs from the repository's `docs/running.md` and `docs/building.md`: the inputs
and how they are installed, the build and traps.

## Inputs

`make unpack ARCHIVES=<directory>` takes the two archives `inputs.sha256` pins and unpacks
each with the default unpacker (no `game_unpack`):

| Archive | Drawer under `tmp/game/` | What |
|---|---|---|
| `ZanyGolf.lha` | `ZanyGolfHD` | Bored Seal's v1.1 install package from whdload.de: Install script, ReadMe, `ZanyGolf.inf` and `ZanyGolf.newicon`, `OSEmu.400`, `ZanyGolf.slave` and `src/ZanyGolf.asm`; `make dist` repacks it |
| `ZanyGolf_v1.1_NTSC_1482.lha` | `ZanyGolfNTSC` | the Retroplay install (1482) with the same slave as `ZanyGolfNTSC.slave`; the run's drawer |

The installed data is `data/Zany` (the loader, a hunk file), `data/OSEmu.400` and
`data/files/` (`FILE1`, the 64 KB main program, the holes, sprites, sounds and font). The
slave in both archives is the same file (SHA-256
`4e718c27c4065e2898171198d7d05161dc64b46459e1c4d8973c4787148a79d3`, 412 bytes), as are
`OSEmu.400` and the ReadMe. The Retroplay icon has `SLAVE=ZanyGolfNTSC.slave PRELOAD NTSC`;
the install package's NewIcon `SLAVE=ZanyGolf.slave PRELOAD QUITKEY=$5D`. game.conf sets
`NTSC=1` as the Retroplay icon does.

Only this one game version is known: the slave checks `FILE1`'s CRC16 ($9cc8) and refuses
anything else.

## Build

`make slave` builds a slave byte-identical to the shipped one (`release/slaves.sha256` holds
the shipped hash). The shipped slave was assembled with optimisations: PC-relative `lea` and
`pea` for labels (so no relocation hunk), short branches, `moveq` for `clr.l`, `abs.w` for
`4` and `TDREASON_WRONGVER`. game.conf therefore leaves out `-devpac` (which turns vasm's
optimisations off) and adds `-pic`, so any relocation fails the build. Three edits to the
source, each commented in place, cover the rest:

- `opt o4-`: vasm would turn `move.l #65536,d0` into `moveq #1,d0; swap d0`, which the
  shipped slave does not.
- `cmp.w #$9cc8,d0` and `cmp.b #$59,d0` are written `cmpi`: vasm encodes `cmp #,Dn` as CMP
  (`b07c`, `b03c`), the original assembler as CMPI (`0c40`, `0c00`). Same size and result.

The `incdir "include:"` line stays; vasm ignores the missing directory.

## Running

`SETUP=a500` (the default) and `a1200` both boot to the title ("Press 1-4 to start") within
15 seconds of warp, and raw key `01` starts a game on hole 1:

```sh
make serve WARP=1 WINDOW=none &
make server CMD='wait 15'; make server CMD='shot tmp/shots/title.png'
make server CMD='gdb monitor key 01 1'; make server CMD='wait 0.5'
make server CMD='gdb monitor key 01 0'; make server CMD='wait 10'
make server CMD='shot tmp/shots/hole1.png'; make server CMD=quit
```
