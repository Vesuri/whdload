# Development

Only what differs from the repository's `docs/running.md` and `docs/building.md`: the inputs
and how they are installed, game-specific tools, captures and traps.

## Inputs

`make unpack ARCHIVES=<directory>` takes the two archives `inputs.sha256` pins and unpacks
each with the default unpacker (no `game_unpack`):

| Archive | Drawer under `tmp/game/` | What |
|---|---|---|
| `StarWars.lha` | `StarWars_Install` | StingRay's v2.00 installer package from whdload.de: Install script, ReadMe, NewIcon, `StarWars.slave` and `Source/StarWars_WHD.s`; `make dist` repacks it |
| `StarWars_v2.0_0403.lha` | `StarWars` | the Retroplay install of SPS 0403 (V1.0) with the same slave; the run's drawer |

The installed data is `data/starwars` (the program, a hunk file) and `data/shapes/` (the
sounds, the SMUS tune, shapes and patterns). The slave in both archives is the same file
(SHA-256 `ec7927c8bbdf41e012b4906271e70d7b87bfc36bf9b6f3bfc31175ace0fa6b93`, 5244 bytes),
and both ReadMes are the same.

## Build

`make slave` assembles `src/StarWars_WHD.s` with the default flags
(`-m68000 -x -devpac -Fhunkexe -nosym`) against the shared WHDLoad 20.1 tree. The installer's
source does not assemble with vasm as shipped; three changes, each commented in place:

- `INCLUDE Sources:whdload/kick13.s` became `INCLUDE whdload/kick13.s` (common/build.sh
  passes `$WHDLOAD/Src/sources`). The `INCDIR SOURCES:Include/` line stays; vasm ignores
  the missing directory.
- `DEBUG` is commented out. The shipped slave was built without it: its `slv_CurrentDir`
  is plain `data`, without the `SOURCES:WHD_Slaves/StarWars/` prefix, and its info has no
  `DEBUG!!!`.
- An `ENDC` at the end closes `IFD BOOTDOS`, which the source leaves open; vasm refuses
  an unterminated conditional (StingRay's assembler evidently accepted it).

### Not byte-identical to the shipped slave

The build is 5556 bytes against the shipped 5244 (the code hunk is $1590 against $1458).
Comparing the code hunks (one hunk, no relocations, in both):

- The slave header matches field for field (ws_Version 17, flags $2402, 512 KB base and
  512 KB ExpMem, `keyexit` $46); only the offsets of the strings and of `_bootdos` move.
- The KickEmu part (`kick13.s` and what it includes) is $138 bytes larger: WHDLoad 20.1's
  `kick13.s` is newer than the 2016 one StingRay assembled with, and that version is not in
  the shared environment. This is the whole size difference.
- StingRay's own code, from `_bootdos` to the end, is instruction for instruction the same
  (245 instructions) apart from PC-relative displacements into the KickEmu part
  (`_dosname`, one word) and the encoding of six immediate instructions: his assembler wrote
  `andi.l #$ffff,Dn` (four), `cmpi.w #-1,d0` and `subi.l #STACKSIZE,d0` where vasm writes
  the equivalent `and.l #,Dn`, `cmp.w #,Dn` and `sub.l #,Dn` forms (same size, same
  result). The hunk ends in two zero bytes there, a `nop` here.

The patch lists and the version table (offsets, CRCs, bytes) are identical. A boot of this
build reaches the attract screen ("Pull trigger to start or wait for info", then the flight
instructions) on `a500-1.5m` and `a1200`, which is what was compared by behaviour.

## Running

The default machine is `a500-1.5m`. On plain `a500` (512 KB chip, 512 KB slow) WHDLoad
under the Workbench floppy cannot allocate the 512 KB ExpMem plus the preload and the
Kickstart image ("Can't allocate ExpMem"). `python3 tools/starwars.py serve` (with
`WARP=1 WINDOW=none`) boots through the shared gdb-stub server; `wait 15` reaches the
attract screen, `wait 45` its instruction page.
