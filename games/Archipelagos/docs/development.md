# Development

Only what differs from the repository's `docs/running.md` and `docs/building.md`.

## Inputs

`inputs.sha256` pins three archives, which `make unpack` installs side by side in `tmp/game/`:

| Archive | Installs | Slave |
|---|---|---|
| `Archipelagos.lha` (whdload.de, 01.01.2018) | `Archipelagos_Install/`: installer, RawDIC imager, source, manual | v1.1 (20.12.2015) |
| `Archipelagos_v1.2_0627.lha` (Retroplay) | `Archipelagos/`: SPS 627, the European release | v1.2 (31.08.2023) |
| `Archipelagos_v1.2_NTSC_0628.lha` (Retroplay) | `ArchipelagosNTSC/`: SPS 628, the US release | v1.2, the same bytes |

The install package's own v1.2 (01.01.2018, "imager adapted to save level 1 data too",
issue #3786) changed only the imager; its slave is still v1.1. The 0628 data has one file
the 0627 data lacks, `Archipelagos_064000`.

## The build

`src/ArchipelagosFiles_WHD.s` is the package's `Source/ArchipelagosFiles_WHD.s` (the import
commit has it unchanged) with these commented edits, and builds byte-identically to the v1.2
slave in the Retroplay archives (`release/slaves.sha256`):

- the v1.2 changes, reconstructed from a disassembly diff of the v1.1 and v1.2 slaves,
  which differ in nothing else: the version string, and `WaitRaster` (called only by
  `KillSys` on quit) waiting for VPOSR's V8 bit to set and clear instead of for line 303;
- seven `cmp`/`add`/`and #imm,Dn` written as `cmpi`/`addi`/`andi`: StingRay's assembler
  emits the immediate forms, vasm the Dn forms. With these the v1.1 source also rebuilds
  the v1.1 slave byte-identically.

`-devpac` (no optimisation) matches: the source sizes its branches. `-pic`: no relocations.
StingRay's `INCDIR SOURCES:INCLUDE/` stays; vasm finds `WHDLoad.i` through `-I`.

Both variants build the same slave. `Archipelagos` boots the 0627 drawer,
`ArchipelagosNTSC` (with `NTSC=1`) the 0628 drawer; `release/release.json` ships one
`Archipelagos.slave` in the install package, which handles both.

## Driving it

`make serve WARP=1 WINDOW=none &`, then `make server CMD=...`. Keys go through the stub:
`CMD='gdb monitor key 40 1'` presses space, `... 40 0` releases it (raw codes; F10 is 59).
From boot, about 12 s in warp reaches "Press any key"; space gives the archipelago screen,
space again starts archipelago 1. `VERIFY_EXIT=1` and F10 test the quit path.

## Traps

- `SLAVE=` is relative to where make started: inside the game directory,
  `SLAVE=tmp/game/Archipelagos_Install/Archipelagos.slave` boots the v1.1 slave.
- On NTSC the v1.1 slave never quits: F10 leaves it spinning in `WaitRaster`, waiting for
  line 303 of a 262-line frame. Compare quit behaviour only against v1.2.
