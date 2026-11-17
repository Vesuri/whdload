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

The source was first made to build byte-identical to the shipped slave (SHA-256 above),
before any change of ours; `SLAVE=original` runs the shipped one, and
`release/slaves.sha256` holds the hash of the current build. The shipped slave was
assembled with optimisations: PC-relative `lea` and
`pea` for labels (so no relocation hunk), short branches, `moveq` for `clr.l`, `abs.w` for
`4` and `TDREASON_WRONGVER`. game.conf therefore leaves out `-devpac` (which turns vasm's
optimisations off) and adds `-pic`, so any relocation fails the build. Three edits to the
source, each commented in place, cover the rest:

These edits keep Bored Seal's code assembling as it shipped; new code follows them (`-pic`
holds for it too).

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
| `tools/route.py STEPS` | drives it: `stop`, `f N`, `key RAW N`, `click N`, `press`, `release`, `title`, `play`, `mouse DX DY N`, `shot`, `prof`, `track`, `frametrack`, `gdb`. The route `hole1` reaches hole 1 in play (it waits for the title's state, presses 1, then clicks through the hole's intro, and the pause screen when one comes, until the ball is active); `putt` then plays one putt (`internals.md`, "Game time") |
| `WHD_ARGS=CUSTOM1=N` | the slave's debug option (`internals.md`, "Slave patches"): every game starts on hole N+1 (N 0-9); `route.py hole1` then reaches that hole, e.g. `WHD_ARGS=CUSTOM1=9 tools/boot.sh && python3 tools/route.py hole1` for hole 10 |
| `make build BUILD=verify` | the slave with `VERIFY`: after every frame `NewDraw` checks each cell of the back buffer against its tile in the hole block. Low memory (fill $cc..) counts: $1f0 cells that differed, $1f4 frames checked, $1f8 the first difference (frame, row, column), $1e0/$1e4/$1e8 frames drawn at the same origin, scrolled, from nothing. With ExpMem it also runs the game's draw-list phases after `NewList` on the same input and compares what both wrote: $1d0 lists that differed, $1d4 lists checked, $1d8 the first difference, $1dc course-piece entries, $1cc lists that filled up. It also draws each shape with `NewShape` and then the game's drawer on the same buffer and compares the planes and variables: $1c0 shapes that differed, $1c4 shapes checked, $1c8 the first difference, $1b8 and $1bc rows inside 0-319 and across an edge, $1b4 status-line shapes (not compared). Run it with `BUILD=verify tools/boot.sh`; frames are several times slower |
| `tools/zanygolf.py frames N [DX DY K]` | counts the frames shown in N fields from the flips of the copper list's plane pointer, optionally moving the mouse every field; no breakpoint, so it works on every CPU, MMU cores included |
| `tools/zanygolf.py track N FILE` | a line a field for N fields: the field counter, whether a frame was shown, the game clock, the ball's position and velocity; every CPU |
| `tools/zanygolf.py frametrack N FILE` | a line a frame for N frames, at a breakpoint on the flip: the field counter, the clock and the object table $5c7a-$5d29; not on MMU cores |
| `tools/thread.py START [END]` | lists the threaded code at `FILE1` offsets as 65xx-style instructions (the primitives read so far by name, the rest with their 68000 body) |
| `tools/bench.py OUT [FIELDS [DX DY ...]]` | traces FIELDS fields (default 120) in 2-field chunks with the mouse moving and writes `OUT/report.txt`: frame pacing, tiles a frame, cycles by range and a per-frame split |
| `tools/profile.py TRACE...` | the call-profile reduction the bench uses (below) |

```sh
SETUP=a1200-030 tools/boot.sh && python3 tools/route.py hole1
python3 tools/zanygolf.py frames 240 5 3; python3 tools/zanygolf.py quit
SETUP=a1200-030 EXTRA_ARGS=--uae_mmu_model=0 tools/boot.sh && python3 tools/route.py hole1
python3 tools/bench.py tmp/prof/030-move; python3 tools/zanygolf.py quit
INSTANCE=a500 SETUP=a500 tools/boot.sh && INSTANCE=a500 python3 tools/route.py hole1 putt 'track 900 a500'
```

On `a1200-030` the route takes about 20 seconds and the bench about a minute. Instances
(`INSTANCE`) run side by side, so the machines of a comparison can run at once.

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
- **Frame flips do not tell where the game is.** The title draws frames too, and a key or
  click that comes before a screen takes input is lost; when that is depends on the
  machine (the credits take about 1350 fields on `a1200-030` and 2200 on `a500`). The
  route waits for the state at `FILE1` $0ea8 and the drawing flag at $0ea0 instead
  (`internals.md`, "Game time"). After the click on the hole's intro the game loads the
  hole for about 400 fields with interrupts off, and the field counter stops.
- **A screenshot during a load breaks it.** `shot` traces a field; taken while the game
  loads with interrupts off (after the title's 1, after the intro's click: the field
  counter stops) the load never finishes, with the shipped slave too. Take screenshots
  once the counter moves.
- **A click during a load is lost**, and the intro and play are both state 4 with drawing:
  `play` tells them apart by the ball's active flag at $0fda.
- **The flip patch moved the flip.** `FrameCap`'s `jsr` covers $14a4-$14a9, so the harness
  marks a frame at $14ac (`SWAP` in `zanygolf.py` and `bench.py`); `bench.py`'s tile counts
  are the game's renderer's and read 0 under `NewDraw`.
- **The verify build needs more than the stock A500's memory.** Its ExpMem (the saved
  buffers of the shape check) leaves too little of the `a500`'s 512 KB slow RAM for the
  preloaded files and the title never comes; use `a500-1.5m`, the same 68000.
- **Four boots at once can fail one** (`boot failed`, no detail in the server log);
  three at once have not failed.
- **One run's frame rate is not a build's.** The boot runs in warp until `hole1`'s `stop`,
  for as long as the host takes, so each run reaches the hole at another point of its
  animations. On `a500`, hole 2 (`frames 240`, still and moving) gave 20 and 25 frames a
  second with the committed slave, and 25 and 20 with the next, each run alone
  (17.11.2026); hole 1 moved between 30.25 and 47.5 when two runs shared the host. Compare
  builds over several runs, or not by frame rates at all.
- **Per-frame timers carry the frames drawn before a putt.** Friction applies every fifth
  frame from the hole's start, so the same putt on two machines takes different paths
  unless the timer at $5cd2 has the same value at the release; change the hold before
  the release until it does (37 fields on `a500` against `putt`'s 30 on the 68030).
