# Development

## Inputs

- [Official WHDLoad page](https://whdload.de/games/Mercenary3.html).
- [Official installer](https://whdload.de/games/Mercenary3.lha).
- [User-supplied full install](https://ftp2.grandis.nu/turran/FTP/Retroplay%20WHDLoad%20Packs/Commodore_Amiga_-_WHDLoad_-_Games/M/Mercenary3_v1.2_0356.lha).

`manifest/inputs.json` pins archive URLs and SHA-256 hashes. File manifests record
relative names and hashes only. Downloaded and extracted bytes remain ignored:

| Path | Purpose |
| --- | --- |
| `tmp/archives/` | Original archives and SHA-256 sidecars |
| `tmp/game/Mercenary3_v1.2_0356/Mercenary3/` | Pristine installed game |
| `tmp/installer/Mercenary3/` | Pristine official installer, including source |

`make check` checks every archive and extracted file against the pinned manifests,
including unexpected files. It never runs the game or inspects code.
For restoring inputs, download the exact named archives from the recorded URLs,
verify their SHA-256 hashes before extracting, then extract each into its recorded
extraction directory. Preserve any differing existing files separately first.

## Shared environment

Source `amiga/env.sh` from the repository root. `AMIGA_ENV` can override the shared
environment file, whose default is `~/.local/share/amiga/env.sh`. Missing shared
environment files fail explicitly. Shared tool and ROM paths are inherited from it;
no local copies or paths into other projects are used.

## Running

`amiga/run.sh` boots Kickstart 3.1 from a generated `DH0` that runs
`WHDLoad Mercenary3.Slave PRELOAD` on `DH1`, a disposable copy of the pristine drawer
under ignored `amiga/.run/`. The default machine is the A500-equivalent (68000, 512 KB
chip, 1.5 MB slow, no fast RAM); the slave needs 512 KB chip and WHDLoad needs other
memory beside it. Variables: `SLAVE`, `WHD_SPLASH=1`, `WHD_ARGS`, and the shared
launcher's (`AMIGA_SETUP`, `CPU`, `CHIP_KB`, `SLOW_KB`, `FAST_KB`, `DEBUG`, `WARP`,
`DETERMINISTIC`, `JOY0`, `JOY1`, `SOUND`, `WINDOW`). Defaults: mouse in port 0,
keyboard joystick in port 1.

The debugger server uses the native build:

```sh
. amiga/env.sh
FSUAE="$FSUAE_ARM" JOY0=none python3 tools/merc3.py serve > tmp/serve.log 2>&1 &
python3 tools/merc3.py gdb 'monitor fields 400'
python3 tools/merc3.py shot tmp/shots/now.png
python3 tools/merc3.py quit
```

## Building

`make original` assembles `whdload/original/Mercenary3.slave.asm` with vasm
(`-no-opt`, the shared `WHDLOAD` includes) into `tmp/build/` and requires it to equal
the shipped slave byte for byte. `BUILD` overrides the output directory.

`make slave` builds the performance slave `whdload/Mercenary3.slave.asm` into
`tmp/build/Mercenary3.Slave`, `make verify` its VERIFY build `Mercenary3.verify.Slave`.
Run one with `SLAVE=tmp/build/Mercenary3.Slave WHD_ARGS=CUSTOM1=1 amiga/run.sh`; the
profile and game-time tools take the same `SLAVE` and `WHD_ARGS` and record them.

## Profiling and game time

Both tools boot the shipped slave with the native build (`FSUAE_ARM`), `WARP=1`,
`DETERMINISTIC=1` and `JOY0=none`, stop at the game's entry and drive the same route
with the port-1 joystick through `monitor input`: wait 175 fields for the cell door,
walk 185 fields through it and outside, then turn right for 140 (500 fields, 10 s PAL).
`ROUTE` overrides it (`ROUTE='175:,185:JOY2_UP,140:JOY2_RIGHT'`).

```sh
. amiga/env.sh
python3 tools/route_profile.py                       # tmp/prof/a1200-fast-route/
AMIGA_SETUP=a1200-fast python3 tools/sim_speed.py tmp/sim/a1200-fast.json
AMIGA_SETUP=a500-1.5m python3 tools/sim_speed.py tmp/sim/a500-1.5m.json
python3 tools/sim_speed.py --compare tmp/sim/a500-1.5m.json tmp/sim/a1200-fast.json
PER_FRAME=1 AMIGA_SETUP=a500-1.5m python3 tools/sim_speed.py tmp/sim/frames.json
python3 tools/sim_speed.py --frames tmp/sim/frames.json
```

`route_profile.py` (default `AMIGA_SETUP=a1200-fast`) traces the window in `CHUNK`-field
captures (default 50), reduces each with `amigaxdev.callprofile` and deletes it
(`KEEP_TRACE=1` keeps them). It locates the live slave in fast RAM to name its code, counts
frames at the frame publication routine, and writes `report.txt`, `profile.pkl.gz`,
`route.json`, a screenshot per chunk and `sheet.png`. A run takes under a minute.

`sim_speed.py` runs the route untraced and samples position, heading, the in-game clock and
the frame and VERTB counters every `STEP` fields (default 5), or at every frame with
`PER_FRAME=1`. `--compare` tabulates machines side by side with per-segment rates.

`tools/write_audit.py` attributes every memory write in kept traces to the main-loop
call site running at the time (interrupt code separately):
`KEEP_TRACE=1 ROUTE='175:,135:JOY2_UP,40:JOY2_RIGHT' python3 tools/route_profile.py tmp/prof/audit`
then `python3 tools/write_audit.py tmp/prof/audit 175` (the kept chunks take about 2 GB;
delete them afterwards).

`tools/bus_audit.py` splits the CPU's chip-bus accesses by kind (instruction fetch, data
read, write) and region, counts misaligned longwords and compares slot use inside and
outside the bitplane lines: `KEEP_TRACE=1 python3 tools/route_profile.py tmp/prof/bus` then
`python3 tools/bus_audit.py tmp/prof/bus 175` (about 3 GB of chunks; delete them afterwards).

`route_profile.py` finds the live slave in fast RAM, or in slow RAM on the `a500` setups.
FS-UAE's screenshots can carry non-Amiga colours in the right border on the A500 setup;
they are not game output (OCS colours are multiples of 17 per channel).

Neither route tool is validated on `a1200-030`. A1's bounded probes have not confirmed
arrival at gameplay; the MMU backend also lacks the instruction recording needed by
`route_profile.py`. See the [A1 investigation](internals.md#a1-anchor-investigation) and
its prerequisite in the plan before relying on a counter-based anchor.
