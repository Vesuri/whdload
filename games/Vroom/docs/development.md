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
- the date Barfly's `WDate` wrote into the info text, `(03.06.2006)`, is a string
  (release 2.0b replaced the info text's version line);
- `BLITWAIT` is `BLITWAIT_V14`, whdmacros.i's macro as it was before its 03.09.07 change,
  which the shipped bytes use;
- `and`/`cmp`/`sub #imm,Dn` are written `andi`/`cmpi`/`subi`: Barfly emits the immediate
  forms, vasm the Dn forms.

`VASM_FLAGS` stand in for Barfly's optimiser (`BOPT O+`): `-opt-allbra` sizes branches,
`-opt-clr` turns `move #0` into `clr`, and `-hunkpad=0` pads the code hunk with zeros as
Barfly did (vasm pads with `nop`).

The fixes since then are in `src/fixes.i` and `src/smc.i`, which both sources include.
`ws_Version` is 16, for `PL_PA` and `PL_PSS`.
Release 2.0b adds "enhanced by Vesuri" and its version line to the info text, and
`$VER: Vroom.slave 2.0b (23.11.2026)` (`VroomData.slave` on the data disk); the v1.4
slaves had no `$VER`.

## Driving it

`make serve WARP=1 WINDOW=none &`, then `make server CMD=...`. The title (race car and
scroller) waits for the right mouse button; the menu is driven with the mouse and the left
button. Left alone, the title runs a demo race after about 20 s in warp.

## Tools

| Tool | Does |
|---|---|
| `tools/vroom.py` | the game server (`serve`, the shared commands) and the commands below |
| `tools/statecmp.py A B [--skip ADDR,...]` | compares two `statelog` files: the first frame whose state differs, and where |
| `tools/matrix.py [--full \| CELL ...]` | `bench` on the a500, a1200, a1200-030 (`MMU`) and a1200-040 (`CACHE`), one boot at a time with a deadline: the bench line, WHDLoad dumps and a screenshot per cell, in `tmp/matrix/<time>/`. The check after a finished change, not after every edit; `--full` adds the a1200-fast and the a1200-040 with `DCACHE`, for one-off decisions |
| `tools/smc.py TRACE.bin ...` | finds self-modifying code in Barto traces: CPU writes onto instructions executed anywhere in the traces |
| `tools/smcscan.py MEMORY.bin [--exec TRACE.bin ...]` | a static scan of a memory dump for writes into code (absolute, PC-relative, or through a `lea` of a code address) |

`tools/vroom.py` commands:

| Command | Does |
|---|---|
| `bench [N]` | from the next green light, the fields the first N frames take (default 500): fps, distance (at the last frame's end, through one breakpoint at $D510), fields per frame. Frames are counted from $E258, which changes once a frame (`internals.md`, "The swap"). Read-only, any CPU. In the first demo race after the boot, the same simulation on every machine, so the figure compares machines and builds |
| `statelog N FILE` | from the next green light, the race state block ($DBC0-$E073) and the race clock at each of N frame ends (a breakpoint at $D510: exact per frame, any CPU) |
| `racelog N FILE` | from the next green light, one line per field: field, frame, clock, distance |
| `meter N` | frames, fields per frame, clock and distance over N fields from now |
| `race [stay]` | from the boot, through the title (right button, given only while the title idles at $12F9E: a click during the menu's wipe leaves the menu again) and the menu (left button on START) to the green light of a player race with the menu's settings as they are (ARCADE, MOUSE, MANUAL): see `internals.md`, "Input, the menu and the race controls" |
| `drive N [GAIN] [FILE]` | a test driver for N fields: full throttle, shifting up when the speed stops rising, steering against the lateral position. FILE gets field, gear, speed, lateral, x, y every 2 fields |
| `do ACTION ...` | low-level steps with the CPU stopped: `f<N>` fields, `L1`/`L0`/`R1`/`R0` mouse buttons, `m<dx>,<dy>`, `x<addr>[,<n>]` reads (`xsp` at the stack pointer), `u<addr>=<hex>,<max>` waits, `b<addr>` runs to a breakpoint, `r<reg>[,<reg>...]` registers, `pc`, `shot=<png>`; a last `stay` leaves the CPU stopped for the next command. A failing action ends the list, and the reply keeps what came before it |
| `decrunch N [S]` | stop after each of the next N file decrunches and report the destination and length |

Run it as its own server, after `. ../../common/env.sh`:

```sh
SETUP=a1200-040 WHD_ARGS=CACHE WARP=1 WINDOW=none JOY0=none DETERMINISTIC=1 \
  python3 tools/vroom.py serve &
python3 tools/vroom.py bench 500          # once tmp/run/default/.run/vroom.sock exists
python3 tools/vroom.py quit
```

The commands that wait for a green light take the first demo race when the title is left
alone (the field counter reads about 8000 there on the a500). Between commands the CPU runs on (in warp, a
command's host time is many fields), so a sequence that must stay on one screen goes in one
`do`, or ends each command with `stay`. A player race is repeatable only from a fixed
start: serve with `BOOT_BREAK=0x3658` (the server stops at the program's entry), then
`race stay` and `drive`. Two such boots gave identical `drive` logs. The demo race needs
none of this; it is the same frame by frame on every machine.

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
- On a 68020 or higher the VBL hook at $A56C is the slave's variable (`src/smc.i`); `race`
  follows it there.
- The gdb stub cannot read the slave's memory (it reads $FF); read a register at a breakpoint
  in the slave instead.
- Breakpoints sometimes never fire while WHDLoad's MMU is on (Snoop, or the a1200-040); the
  same trace on the a500 works.
- During the slave's disk loads the gdb stub reads chip memory as $FFFFFFFF (and the
  field counter stops): a wait on a value must not take that for the value.
