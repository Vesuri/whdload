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

On a 68020 and up, `make run` and `make serve` add `CACHE` to the WHDLoad options, as the
installed icon will (`game_prepare` in `game.conf`). Without it the boot to the race takes
2.4 times as long, mostly the loader unpacking in Chip RAM: on the a1200-030 2221 fields
instead of 930. They also add `CUSTOM1=1` (Enhanced framerate; a 68000 ignores it) unless
`ENHANCED=0` or `WHD_ARGS` sets `CUSTOM1`. `WHD_DEFAULTS='PRELOAD SPLASHDELAY=0 NOREQ'`
boots without either; `tools/matrix.py` does that, so a cell runs only the options it names.

With Enhanced framerate the scheduler's counters are at $1C0 (`internals.md`, "Enhanced
framerate"): `do x1c0,6` reads the next tick's field, ticks, frames drawn, fields dropped,
and the period word. `CUSTOM3=n` makes n of every n+1 race loop passes leave out the
drawing, for the per-pass check: `statelog N FILE tick` on the a500 and on a 68020+ with
`CUSTOM1=1 CUSTOM3=2`, then `tools/statecmp.py A B --skip DBD8,DBDC --align 10` (the two
long words are the map marker's position in each screen; the a500 logs one more pass at the
green light). `shown 40` checks that nothing draws into the screen on display: with the option, the only
change is the map's position marker, which the original draws there too (`internals.md`,
"Enhanced framerate").

## Tools

| Tool | Does |
|---|---|
| `tools/vroom.py` | the game server (`serve`, the shared commands) and the commands below |
| `tools/statecmp.py A B [--skip ADDR,...] [--align N]` | compares two `statelog` files: the first frame whose state differs, and where; `--align` first shifts B by up to N rows to where its first row matches |
| `tools/matrix.py [--full \| CELL ...]` | `bench` on the a500, a1200, a1200-030 (`MMU`) and a1200-040 (`CACHE`), then the a1200-030 with `MMU CUSTOM1=1 CUSTOM2=1` and the a1200-040 with `CACHE CUSTOM1=1`, one boot at a time with a deadline: the bench line, WHDLoad dumps and a screenshot per cell, in `tmp/matrix/<time>/`. The check after a finished change, not after every edit; `--full` adds the a1200-fast and the a1200-040 with `DCACHE`, for one-off decisions |
| `tools/dmaregions.py TRACE [N]` | the CPU's chip memory accesses in a Barto trace of a 68000: instruction fetches, data reads and writes, and the data accesses by 4 KB block (the screens as one) |
| `tools/eacensus.py TRACE LO HI [N]` | the executed instructions in a Barto trace with a memory operand or an immediate in [LO, HI): the census before a block moves to fast memory |
| `tools/reloc.py [--write [--out FILE]] [--no-seeds LO-HI] IMAGE PROFILE...` | the race block's relocation census (`internals.md`, "Fast memory"): IMAGE is chip memory from 0 at the program's entry (`BOOT_BREAK=0x3658`, `gdb dump binary memory`), the PROFILEs aprof profiles of whole sessions and Barto PC sets (.pkl). Prints the tables found, the immediates kept as numbers, the PC-relative edge crossings and the undecoded long words into the block to review; `--write` writes `src/reloc_<variant>.i` (the data disk with `--no-seeds 3600-4400`, its different init code). Run it again when a patch changes the program's memory |
| `DEFINES_<build>=-DENH_PROTECT=1` (`BUILD=<build>`) | the race block left in chip memory, from $B000, protected between `Fix`es: any access by a missed reference ends in a WHDLoad dump. A 68030 with `MMU` (on the 68040, with 8 KB pages, the protection crawled through the title) |
| `DEFINES_<build>=-DENH_NOBLOCK=1` | only the stack moves to fast memory: the A side of a measurement of the block's move |
| `tools/smc.py TRACE.bin ...` | finds self-modifying code in Barto traces: CPU writes onto instructions executed anywhere in the traces |
| `tools/smcscan.py MEMORY.bin [--exec TRACE.bin ...]` | a static scan of a memory dump for writes into code (absolute, PC-relative, or through a `lea` of a code address) |

`tools/vroom.py` commands:

| Command | Does |
|---|---|
| `bench [N]` | from the next green light, the fields the first N frames take (default 500): fps, distance (at the last frame's end, through one breakpoint at $D510), fields per frame. Frames are counted from $E258, which changes once a frame (`internals.md`, "The swap"): with Enhanced framerate the drawn frames, and the line adds ticks, undrawn passes and dropped fields. Read-only, any CPU. In the first demo race after the boot, the same simulation on every machine, so the figure compares machines and builds |
| `aprof N FILE`, `aprof race FILE` | from the next green light, the aprof FS-UAE's instruction profile of N fields into FILE; `race` profiles a fresh boot through `race` to the green light instead (the load). Start the server with `FSUAE=$FSUAE_APROF SETUP=a1200-040 EXTRA_ARGS=--cpu=68040-NOMMU` (a cycle-exact CPU without an MMU model). On a 68040 it is an instruction count plus chip time (AmigaXDev's measurement method) |
| `tools/aprof_report.py FILE [N]` | an `aprof` file: the chip and slave shares, the call targets with the most inclusive time, the flat time by 4 KB block |
| `frames N FILE` | from the next green light, at each of N swaps: the frame number, the tick and a hash of each of the frame's 800 plane lines |
| `tools/framecmp.py A B [--by tick\|frame] [--lines F-L]` | compares two `frames` files frame by frame: which planes and lines differ. Lines 31-35 (the race clock) and 175-199 (the cockpit's bottom) differ between runs of the same build |
| `tools/blitsites.py MEM [--check MEM2 ...]` | writes `src/blitwait.i` from a race memory image: the blitter starts the game waits after itself (`internals.md`, "Blitter waits") |
| `shown [N]` | from the next green light, for N frames (default 40): at each swap ($D522) reads the screen still on display, and again when the VBL takes the new frame ($A404); reports the frames where it changed, with the planes and lines. Exact on any machine, slow (two 32000-byte reads a frame) |
| `statelog N FILE [tick]` | from the next green light, the race state (the block $DBC0-$E073, the score $8370, the simulation's long words in the renderer's area) and the race clock at each of N frame ends (a breakpoint at $D510: exact per frame, any CPU), or with `tick` at every race loop pass ($CD0E, drawn or not). Pointers into the race block's fast memory copy are logged as the program's addresses, so logs with and without fast memory compare. Any long word whose value falls in the copy's range is translated too: on the a1200-060 the copy is at $9DE000-$9EFFFF, and some state words hold numbers there, so against an a1200-040 log 23 of 600 passes differ by exactly the offset ($9D4800) |
| `racelog N FILE` | from the next green light, one line per field: field, frame, clock, distance |
| `meter N` | frames, fields per frame, clock and distance over N fields from now |
| `race [stay]` | from the boot, through the title (right button, given only while the title idles at $12F9E: a click during the menu's wipe leaves the menu again) and the menu (left button on START) to the green light of a player race with the menu's settings as they are (ARCADE, MOUSE, MANUAL): see `internals.md`, "Input, the menu and the race controls" |
| `drive N [GAIN] [FILE]` | a test driver for N fields: full throttle, shifting up when the speed stops rising, steering against the lateral position. A shift holds the button 4 fields and the release 4 (the race reads the controls once a tick: a shorter release can fall between two reads, and the gear never engages). FILE gets field, gear, speed, lateral, x, y every 2 fields |
| `do ACTION ...` | low-level steps with the CPU stopped: `f<N>` fields, `L1`/`L0`/`R1`/`R0` mouse buttons, `m<dx>,<dy>`, `x<addr>[,<n>]` reads (`xsp` at the stack pointer; an address in the race block reads its fast memory copy, `X` the address itself), `u<addr>=<hex>,<max>` waits, `b<addr>` runs to a breakpoint, `r<reg>[,<reg>...]` registers, `pc`, `shot=<png>`; a last `stay` leaves the CPU stopped for the next command. A failing action ends the list, and the reply keeps what came before it |
| `decrunch N [S]` | stop after each of the next N file decrunches and report the destination and length |

Run it as its own server, after `. ../../common/env.sh`:

```sh
SETUP=a1200-040 WHD_ARGS=CACHE WARP=1 WINDOW=none JOY0=none DETERMINISTIC=1 \
  python3 tools/vroom.py serve &
python3 tools/vroom.py bench 500          # once tmp/run/default/.run/vroom.sock exists
python3 tools/vroom.py quit
```

With fast memory the race block ($A924-$1B4FF) runs from its copy there: the commands'
breakpoints and reads of block addresses go to the copy, at the offset the slave leaves at
$1D6 (`internals.md`, "Fast memory").

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
