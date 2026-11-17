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
15 seconds of warp, and raw key `01` starts a game on hole 1 (`make serve`, then `make server
CMD='gdb monitor key 01 1'` and so on). For anything repeatable use the harness below.

## Harness

| Tool | Does |
|---|---|
| `tools/boot.sh` | boots a server (`tools/zanygolf.py serve`): warp, deterministic, nothing in port 0, no window; run options pass through |
| `tools/route.py STEPS` | drives it: `stop`, `f N`, `key RAW N`, `click N`, `play`, `mouse DX DY N`, `shot`, `prof`, `gdb`; the route `hole1` reaches hole 1 in play (the credits and title, 1, then clicks until frames are shown) |
| `tools/zanygolf.py frames N [DX DY K]` | counts the frames shown in N fields from the flips of the copper list's plane pointer, optionally moving the mouse every field; no breakpoint, so it works on every CPU, MMU cores included |
| `tools/bench.py OUT [FIELDS [DX DY ...]]` | traces FIELDS fields (default 120) in 2-field chunks with the mouse moving and writes `OUT/report.txt`: frame pacing, tiles a frame, cycles by range and a per-frame split |
| `tools/profile.py TRACE...` | the call-profile reduction the bench uses (below) |

```sh
SETUP=a1200-030 tools/boot.sh && python3 tools/route.py hole1
python3 tools/zanygolf.py frames 240 5 3; python3 tools/zanygolf.py quit
SETUP=a1200-030 EXTRA_ARGS=--uae_mmu_model=0 tools/boot.sh && python3 tools/route.py hole1
python3 tools/bench.py tmp/prof/030-move; python3 tools/zanygolf.py quit
```

On `a1200-030` the route takes about 20 seconds and the bench about a minute.

Traps:

- **Stop the CPU before driving it.** The server resumes the CPU after a command when it was
  running before, and the boot leaves it running: in warp hundreds of fields then pass
  between two commands, the route stops being repeatable and trace chunks stop being
  contiguous. `route.py`'s `stop` (the first step of `hole1`) fixes it for the rest of the
  session. The bench checks that each chunk starts 2 fields after the previous one by the
  game's field counter in the chunk's chip snapshot.
- **The interrupt handler runs twice a field** (VERTB and COPER), so the toggle at
  `FILE1` $21e2 flips twice a field and the counter at $145c counts fields.
- **The trace needs a CPU without an MMU model.** The `a1200-030` preset's 68030 has one and
  records no instructions; `EXTRA_ARGS=--uae_mmu_model=0` gives the same cycle-exact 68030,
  and the frame rates agree (13.5 and 13.75 frames a second).
- **Data-cache figures need a CPU without an MMU model too.** With MMU emulation FS-UAE
  leaves chip RAM data-cacheable for the MMU tables to forbid, and WHDLoad sets none without
  its `MMU` option, so `DCACHE` on the `a1200-030` preset caches chip data, which no 68030
  board does (34 frames a second against 21.25 without the MMU model).
- **amigaxdev.callprofile's single call stack does not fit.** The game's user stack ($9570)
  is below the interrupts' supervisor stack ($7fff0), so no interrupt frame ever pops;
  `tools/profile.py` keeps one stack per CPU mode. Most game code is threaded and reached
  by `jmp`, so the call tree is flat anyway: the bench reports by address range instead.
- The click that leaves the pause screen is lost when it comes before the screen takes
  input, which depends on the machine; `play` clicks until frames are shown.
