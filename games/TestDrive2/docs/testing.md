# Running, tracing and testing

How to run the game in FS-UAE, trace it cycle-exactly, capture game state and check a slave
change. The inputs and the build are in [development.md](development.md); the shared run
options in the repository's `docs/running.md`. All output goes to the ignored `tmp/`; never
commit traces, dumps or screenshots.

## Machines

`make run` (the repository's `common/run.sh`) boots a Kickstart 3.1 host (`KICKSTART`)
from a directory DH0 plus the Workbench 2.04 floppy (`WORKBENCH_ADF`) for `C:` and `Libs:`.
DH0's startup-sequence runs `WHDLoad TestDrive2.slave PRELOAD SPLASHDELAY=0 NOREQ` on DH1, a
fresh copy of `tmp/game/TestDrive2` plus `WHDLOAD_BINARY`, in `tmp/run/<instance>/.run`. The
slave is a KickEmu slave: WHDLoad boots Kickstart 1.3 (`kick34005.A500` + `.RTB`, copied to
`DH0:devs/Kickstarts`) and LoadSegs `duel` under it. The slave needs WHDLoad 17.2 or later.

`make run` builds and runs the release slave; `SLAVE=original` runs the installed v1.5 slave
and `SLAVE=path` any other. The default machine (`game.conf`) is an A500 (68000) with 1 MB
chip, 2 MB fast at `$200000` and 512 KB slow RAM; `CPU`, `CHIP_KB`, `FAST_KB`, `SLOW_KB`,
`EXTRA_ARGS` (extra FS-UAE options), `WHD_ARGS` (e.g. `CUSTOM2=1`), `WARP`, `DEBUG`,
`DETERMINISTIC`, `SOUND`, `WINDOW` and `RECORD` are the shared run options.

Reference machines (`TD_SETUP`, `game.sh`; `tools/fixed_window.sh` uses the first by default,
with the variables below):

| Machine | Settings |
|---|---|
| A500 (`TD_SETUP=a500`) | `CPU=68000 CHIP_KB=512 FAST_KB=0 SLOW_KB=1536`: every CPU access is on the chip bus, as on an A500. WHDLoad needs more than 1 MB in total, and slow RAM is contended like chip RAM, so this matches a stock A500's speed |
| Expanded A1200 (`TD_SETUP=a1200`) | `AMIGA_MODEL=A1200 CPU=68EC020 CHIP_KB=2048 FAST_KB=4096 SLOW_KB=0 KICKSTART="$KICKSTART_A1200"` |
| 68030/25 MHz (`TD_SETUP=a1200-030`) | the A1200 settings with `CPU=68030 EXTRA_ARGS='--uae_cpu_speed=real --uae_cpu_multiplier=0 --uae_cpu_frequency=25000000 --uae_cpu_cycle_exact=true'`. This is an accelerated A1200, not an A4000 |

`make run TD_SETUP=a1200 WHD_ARGS=CUSTOM2=1` plays the patched slave on the expanded A1200,
`TD_SETUP=a1200-030` on the 68030.

Each capture keeps the effective emulator configuration in `OUT/fsuae.log`; check CPU,
frequency and timing mode there before reading anything into a frame rate.

## Driving the emulator: `tools/td2.py`

```sh
WARP=1 python3 tools/td2.py serve > tmp/serve.log 2>&1 &   # boots common/run.sh with DEBUG=1
python3 tools/td2.py shot "$PWD/tmp/now.png"     # 1-field trace, keep its screenshot
python3 tools/td2.py wait 2                      # let it run 2 s (wall)
python3 tools/td2.py stop | cont
python3 tools/td2.py until '<addr> if <cond>'    # run to a breakpoint and stay stopped
python3 tools/td2.py gdb 'info registers'        # any gdb command
python3 tools/td2.py profile 80 "$PWD/tmp/prof/x.bin"
python3 tools/td2.py quit                        # kills gdb and our FS-UAE only
```

The server holds one gdb on FS-UAE's Barto stub and serves one command per connection on
`tmp/run/<instance>/.run/td2.sock`. It is AmigaXDev's shared server (`amigaxdev.gdbserve`)
through the repository's `common/tools/game_server.py`; run it and the tools from the game
directory. The tools find AmigaXDev's package through `tools/_amigaxdev.py`, and
`python3 -m amigaxdev...` needs `. ../../common/env.sh` first.

- **Attach within 20 s of launch.** With no trigger, the stub stops servicing its port for
  good after 20 s. `serve` connects as soon as the port listens, finds the CPU halted at the
  reset PC `$F800D2` and continues it. `BOOT_BREAK` arms a breakpoint while still at reset.
- **Emulated time does not advance while gdb has the CPU stopped**, so stops do not perturb
  measurements.
- **The stub is read-only**: memory and register writes (`M`, `P`, `G`) are silently dropped.
  Input and patches come from the slave, never from gdb writes.
- **gdb splits arguments at spaces**: `dump binary memory` paths must have none. The shell
  tools dump straight into `OUT`, the Python ones through a private temporary directory.
- `shot` is the only screenshot route: every trace field carries a PNG
  (`barto.Field.shot`). macOS denies this process screen capture and FS-UAE ignores posted
  key events. F12+S in the emulator window saves to `tmp/shots/`.

## The profiler window fix (lldb)

`monitor profile N "" FILE` records only PCs inside `[baseText, baseText+sizeText)`. Without a
`--remote_debugger_trigger` (WHDLoad has no host process to trigger on) this FS-UAE build
leaves `baseText=0x0100007f, sizeText=0`: every record has no PC, and a trace looks like 100%
stopped CPU while the registers change. `td2.py profile` repairs it before each capture:

```
slide = `image list -o -f fs-uae`
memory write -s4 (0x32dea04 + slide) 0           # baseText
memory write -s4 (0x32dea08 + slide) 0x7fffffff  # sizeText
```

`0x32dea04` is this binary's link-time address of `baseText`: the `GDBSERVER: enabled` setup
stores `0`/`0x7fffffff` there (near that string's reference, around `0x5a49e`) and the
profile command passes both to `start_cpu_profiler` (around `0x5f380`). **Another FS-UAE
binary needs these addresses re-derived**; `fix_profile_window` asserts the read-back. Under
Rosetta the lldb attach takes 25 s to minutes, so `td2.py` attaches once per session.

## Traces

`tools/profile_demo.sh [OUT]` boots in warp, polls `shot` until `tools/ingame.py` sees the
attract demo driving (sky blue above the dashboard), traces `FIELDS` fields (default 80, at
most 100; ~5.4 MB per field), dumps the code memory, re-checks the first and last field are
in-game and writes `report.txt`. The demo content differs per run (a sign scene draws 4.3 fps,
open road 7.2), so **never compare two `profile_demo.sh` runs**: use the fixed window.

```sh
python3 tools/td2_report.py OUT/trace.bin OUT/code.bin --base 0xc00000   # routines, inclusive/self
python3 tools/frames.py     OUT/trace.bin OUT/code.bin 0xc00000           # fps, blitter waits, interrupts, DMA
python3 -m amigaxdev.disasm hotspots --label duel OUT/trace.bin OUT/code.bin 0xc00000 HUNK 0f114,0789c
python3 -m amigaxdev.disasm disd OUT/code.bin 0xc00000 HUNK 0x0f114 0x0f2c0
```

Use `--base 0x200000` with fast RAM (the code is loaded into fast RAM when there is any, else
slow RAM at `$C00000`). Keep `SLAVE` pointing at the exact slave that made a capture
(`OUT/slave.slave`): the slave's size bounds its region, and a different build can hide the
COP1LC write and report zero frames.

- **Regions** are found by byte-matching the dump against the installed files (16-byte windows
  vote for a base): `duel` hunk 0 (`duel:OFFSET`), the full `$7A70` data hunk, Kickstart 1.3
  copied to RAM (`kick:ROMADDR`) and the slave (`slave:OFFSET`).
- **Contexts**: the recorded `sr` is stale, so the report keys call stacks on which stack SP
  is in (drawing task, simulation process, supervisor, OS tasks).
- **Attribution**: a `jsr`/`bsr` followed by SP − 4 pushes a frame named after the callee
  (through `jmp abs.l` trampolines; `jsr d16(a6)` is named after the library LVO), giving
  inclusive time. Self time goes to the nearest preceding function start (`link a5` or an
  observed call target); a function without `link` merges into its predecessor, so check
  `hotspots` before trusting a big self number.
- **Frames** are counted at the slave's COP1LC write; **blitter waits** are cycles on
  `btst #6,2(a6)` polls; **interrupts** at Kickstart's level-3 handler `$FC0D14` and its BLIT
  (`$FC0D38`) / VERTB (`$FC0D4A`) branches; **DMA** from the per-field DMA records.

Trace format (AmigaXDev's `amigaxdev.barto`), little-endian uint32: `fields`, `nsections`, section bases,
16 bytes of stack bounds; ROM, chip and slow-RAM snapshots (no fast RAM, hence the separate
dump); base clock, cycle unit. Per field: custom registers (520 bytes), AGA colours (1024),
DMA records, resource records, `cycles`, `idle`, instruction words, screenshot. An
instruction record is PC words (< `0xffff0000`), then `0xffffffff − cycles`, then d0–a7 and
sr; a PC of `0x7fffffff` marks cycles between instructions. A PAL field is 142 102 CPU clocks.

## The fixed window: `tools/fixed_window.sh OUT [SLAVE]`

The only frame-rate instrument. It boots with `DETERMINISTIC=1`, stops when the first race's
clock is initialised (watchpoint on the store at `duel:0bbf8`, recorded in `OUT/anchor.txt`),
runs to `duel:05a4c` (dashboard drawn, gameplay loop not started) and traces `FIELDS` fields
(default 100). It copies the slave to `OUT/slave.slave` and runs that copy. A calibration
boot first finds the loaded hunk address and caches it in `tmp/prof/` by machine, arguments
and slave; `BOOT_HUNK` supplies a known address (checked against the dump).

| Option | Effect |
|---|---|
| `STATE_FIELDS=N` | dump the data hunk at N successive VBL entries before the trace (`OUT/state`) |
| `RENDER_FRAMES=N` | record N completed main/mirror views: rows, scanline buffers, car draw coordinates (`OUT/render`) |
| `SIDEWAYS_FRAMES=N` | record drawn/raw heading and lane per view and the mountain offset (`OUT/sideways`); `SIDEWAYS_RECOVERY=1` adds recovery state and 1 000 VBL states |
| `STATE_ONLY=1` | stop after those captures: no trace, no frame rate |
| `SWAP_ONLY=1` | count buffer swaps over the window with read-only breakpoints instead of tracing (68030, and A1200 with blitter priority: those CPU traces are empty or corrupt) |
| `WATCH_STATE=1` | after the trace, verify the state writers with hardware write watchpoints |
| `SERVE_WAIT=S` | boot timeout (default 180 s; 100 MHz emulated CPUs need ~1700) |
| `ANCHOR=0x…` | diagnostic: a different hunk offset to stop at |

For reproducible runs build `make verify` and pass `WHD_ARGS=CUSTOM3=1`: the
VERIFY patch removes the beam position from the RNG, so two boots give identical screenshots.
Frame rates from windows that follow `STATE_FIELDS` samples describe that later interval.
Treat differences under ±0.15 fps as noise and run each arm at least twice.

## Checks

| Tool | Checks |
|---|---|
| `check_units.py OUT [--base 0x200000]` | the 129 VERIFY assembly assertions (needs `CUSTOM5` set; `CUSTOM5=16` adds no input) |
| `check_disabled.py OUT [--render-only]` | with `CUSTOM2=0`, the 77 optional ranges (10 sub-unit) keep the original v1 bytes; needs `CUSTOM5` bit 0 off |
| `audit_simulation.py tmp/game/TestDrive2/data/duel` | hook boundaries, overlaps and direct incoming branches (73 hooks); indirect entries need manual review |
| `check_timing.py OUT/state --min-fields N [--period 6\|2] [--fatal-end]` | consecutive fields, deadline spacing, race clock against PAL time with penalties |
| `check_recovery.py OUT/state [--trainer\|--damage]` | one life loss (none with the trainer), one penalty, 240 stationary fields at idle pitch |
| `check_terminal.py OUT/state` | the forced fatal crash takes the original terminal path |
| `compare_state.py A/state B/state [--assert-core]` | raw state at identical VBL indices; `--assert-core` requires all 35 core variables to match |
| `state_report.py`, `state_writers.py`, `state_watch.py`, `task_state.py` | inspect state, find writers in a trace, confirm them with watchpoints, read the Exec task nodes |
| `subunit_cost.py OUT` | sub-unit patch cycles in a normal-build A500 trace, against the 3% budget |
| `subunit_report.py OFF/render ON/render [ZERO BASE --initialised] [--check-cars]` | zero-fraction byte identity, road/colour boundaries, car coordinates |
| `subunit_geometry.py ORIG/render [SUB/render]` | independent geometry model, then world-boundary continuity |
| `sideways_report.py OUT/sideways […] [--until F]` | per-frame steps and reversals of mountains, heading and lane |

Compare game time only through state, never screenshots: different machines reach different
demos. Sample 0 of a capture can fall inside the demo's borrowed-state transaction
([game.md](game.md)); explain any other mismatch.

## Regression checklist

Run what the change touches; a release runs all of it. `S` is the slave under test,
`C="CUSTOM3=1"`.

1. `make check`: the release build matches `release/slaves.sha256`, `make verify` assembles
   and `audit_simulation.py` reports no errors.
2. VERIFY, `WHD_ARGS="CUSTOM2=1 $C CUSTOM5=16" STATE_FIELDS=100 STATE_ONLY=1`: `check_units.py` passes.
3. VERIFY, `CUSTOM2=0 $C CUSTOM5=16`: `check_disabled.py` passes.
4. Simulation: 1 800-field state captures (`CUSTOM5=1` tape, `CUSTOM5=3` damage) on the A500
   and the A1200 pass `check_timing.py` and `check_recovery.py`; same-period machines match
   with `compare_state.py --assert-core`; the 6 000-field demo and the `CUSTOM5=17` tape
   reproduce the handling table in [simulation-design.md](simulation-design.md);
   `CUSTOM5=5` passes `check_terminal.py`.
5. Rendering: zero oracle (`CUSTOM5=8` in both arms, `RENDER_FRAMES=90`) with
   `subunit_report.py --initialised`; `sideways_report.py` on a demo capture; `subunit_cost.py`
   on normal-build A500 windows at the anchor, after `STATE_FIELDS=1000` and after
   `STATE_FIELDS=640` (first hill crest).
6. Frame rate: two fresh normal-build fixed windows per arm. Current first-race figures:

   | Machine | Original (`CUSTOM2=0`) | Enhanced framerate |
   |---|---:|---:|
   | A500 | 6.1 fps | 7.1 fps (simulation 6.5% of CPU) |
   | Expanded A1200 | — | 16.7 fps |
   | 68030/25 MHz | — | 25.0 fps (`SWAP_ONLY=1`) |

7. Startup under the oldest and newest WHDLoad available (`WHDLOAD_BINARY`).

## Input

The attract demo drives itself, and VERIFY tapes cover scripted driving. FS-UAE input
recordings also work (`make run RECORD=file`, forces `--deterministic=1`, written on
SIGTERM). The stream is big-endian uint32: per frame `0x80000000|frame`,
`0x10000000|rand checksum`, `0x08000000|state checksum`; events `0x40000000|line` then
`0x20000000|state<<16|event`. A rand-checksum mismatch invalidates playback, a state mismatch
only notifies, so events can be spliced into an idle recording. This binary's events:
`JOY2_LEFT/RIGHT/UP/DOWN` = 60/61/62/63, `JOY2_FIRE_BUTTON` = 68.

## Traps

- Read-only Kickstart files are copied with their mode; FS-UAE then exposes them
  write-protected and WHDLoad loops on DOS error 223. `common/run.sh` does `chmod -R u+w`.
- The WHDLoad splash stays up while PRELOAD reads the data; that is not a hang.
- FS-UAE's default `Cache/Logs/fs-uae.log.txt` is shared by every FS-UAE instance and
  block-buffered; ours is `tmp/run/<instance>/.run/fsuae.log`.
- A trace that has left the demo (Accolade logo) genuinely idles; check screenshots and that
  PCs are present before trusting a trace.
- Never `pkill fs-uae`: `fsuae_common.sh` kills only this checkout's emulator.
- Background suites must run under `nohup`, or captures die with "Terminated: 15".
- An updated slave can load at a different address: the calibration cache is keyed by slave
  hash, but it ignores `WHDLOAD_BINARY`; delete the cached `tmp/prof/hunk-*.txt` when
  switching WHDLoad versions.
