# Development

Only what differs from the repository's `docs/running.md` and `docs/building.md`.

## Inputs

`inputs.sha256` pins three archives, which `make unpack` installs side by side in `tmp/game/`:

| Archive | Installs | Slaves |
|---|---|---|
| `Vroom.lha` (whdload.de) | `VroomHd/`: installer, imager slaves, source (`.src/`), no game data | v1.4 (03.06.2006) |
| `Vroom_v1.4_1295.lha` (Retroplay) | `Vroom/`: `Disk.1`, `Vroom.Slave` | v1.4, the same bytes |
| `Vroom&DataDisk_v1.4_1295&1296.lha` (Retroplay) | `Vroom&DataDisk/`: `Disk.1`, `Disk.2`, `Vroom.Slave`, `DataDisk.Slave` | v1.4, the same bytes |

Variant `Vroom` boots `Vroom/Vroom.Slave`, `VroomData` boots
`Vroom&DataDisk/DataDisk.Slave` (the package's `VroomData.slave`). Both drawers' `Disk.1`
are the same image.

## The build

`src/Vroom_hd.asm` and `src/Vroom_Data_hd.asm` are the package's `.src/` files (the import
commit has them unchanged, with the imager sources). The setup commit made these commented
edits, after which both built byte-identically to the shipped slaves:

- Barfly's `BOPT`, `SUPER` and `INCDIR` are commented out;
- the date Barfly's `WDate` wrote into the info text, `(03.06.2006)`, is a string;
- `BLITWAIT` is `BLITWAIT_V14`, whdmacros.i's macro as it was before its 03.09.07 change,
  which the shipped bytes use;
- `and`/`cmp`/`sub #imm,Dn` are written `andi`/`cmpi`/`subi`: Barfly emits the immediate
  forms, vasm the Dn forms.

`VASM_FLAGS` stand in for Barfly's optimiser (`BOPT O+`): `-opt-allbra` sizes branches,
`-opt-clr` turns `move #0` into `clr`, and `-hunkpad=0` pads the code hunk with zeros as
Barfly did (vasm pads with `nop`).

The fixes since then are in `src/fixes.i` and `src/smc.i`, which both sources include.
`ws_Version` is 16, for `PL_PA` and `PL_PSS`.

## Driving it

`make serve WARP=1 WINDOW=none &`, then `make server CMD=...`. The title (race car and
scroller) waits for the right mouse button; the menu is driven with the mouse and the left
button. Left alone, the title runs a demo race after about 20 s in warp.

## Tools

| Tool | Does |
|---|---|
| `tools/vroom.py` | the game server (`serve`, the shared commands) plus `decrunch <n> [<s>]`: stop after each file decrunch and report its destination and length |
| `tools/smc.py TRACE.bin ...` | finds self-modifying code in Barto traces: CPU writes onto instructions executed anywhere in the traces |
| `tools/smcscan.py MEMORY.bin [--exec TRACE.bin ...]` | a static scan of a memory dump for writes into code (absolute, PC-relative, or through a `lea` of a code address) |

`smc.py` decodes only instructions in chip memory, so it misses writers in the slave. The
original slave's scaler stores are one such case; they surfaced only as garbage graphics with
`CACHE`. A memory dump comes from `make server CMD="gdb dump binary memory $PWD/tmp/mem.bin 0
0x80000"`; with `BOOT_BREAK=0x3658` in `make serve`'s environment, the dump is taken as the
program starts, with the patches applied.

## Traps

- WHDLoad's dump files are hidden (`.whdl_*`): list them with `ls -a`.
- `make serve` takes a few seconds to open its socket; wait for
  `tmp/run/default/.run/game.sock` before sending commands.
- Between demo races the screen is black for a while; check at more than one time.
