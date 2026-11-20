# Development

Only what differs from the repository's `docs/running.md` and `docs/building.md`.

## Inputs

`inputs.sha256` pins two archives, which `make unpack` installs side by side in `tmp/game/`:

| Archive | Installs | Slave |
|---|---|---|
| `Virus.lha` (whdload.de) | `Virus-install/`: installer, RawDIC imager (`Virus.islave`), README | V1.0 (15.01.99) |
| `Virus_v1.0_0004.lha` (Retroplay) | `Virus/`: `Disk.1` (184320 bytes, the whole disk), ReadMe, icons | the same bytes |

The runs boot the Retroplay drawer `Virus/`.

## The build

`src/Virus.s` is a reconstruction: the package has no source, and neither JOTD's nor
StingRay's repository holds the slave. It was disassembled from the shipped `Virus.slave`
rebuilt it byte for byte (commit 4f0c8df4). `-no-opt` keeps the shipped encodings
(`move.l #1,d0` rather than `moveq`, `lea ($1000).w`). The labels and comments are ours; the
header, code and data are the shipped slave's, including an unreferenced routine (`_clamp`,
[internals](internals.md#slave-patches)), except where 2.0b changes them (the `$VER` string
first). `release/slaves.sha256` records the current release build.

## Driving it

`make serve WARP=1 WINDOW=none &`, then `make server CMD=...`. About 15 s in warp reaches the
attract mode on the a500+. Keys go through the stub as raw hex codes:
`CMD='gdb monitor key 59 1'` presses F10, `... 59 0` releases it; with `VERIFY_EXIT=1`,
F10 leaves `OK` in `tmp/run/default/.run/dh0/whdload-exit.txt`.

## Benchmark

```sh
SETUP=a1200-030 EXTRA_ARGS=--uae_mmu_model=0 WHD_ARGS=CACHE tools/boot.sh
python3 tools/bench.py tmp/prof/demo030          # 1250 fields of the demo mode
python3 tools/report.py tmp/prof/demo030         # the report again from the reduction
```

`tools/boot.sh` boots warp, deterministic, without a window. `tools/bench.py` runs to the
demo's start (`Disk.1` `$289fe`, about 990 fields after the game's entry: the title, then the
attract screen) and traces back to back in 25-field chunks, reducing each
(`tools/reduction.py`, from Archipelagos: the 68030 core writes gap records inside ordinary
code and WHDLoad enters the handlers from its vector table in fast memory, so interrupt
frames start at the game's handlers). It reads the frame counter `$c9f4` between chunks.
The trace needs a core that records one: the 68000, the 68020, or the 68030 without its MMU
model (WHDLoad leaves the MMU alone without its `MMU` option, so the game runs the same).
The 25 s window takes a few minutes and about 7 MB of trace a field, deleted chunk by chunk.

Enhanced framerate is `WHD_ARGS="CUSTOM1=1 CUSTOM2=N"` (N 0-2: 25, 16.7, 12.5 Hz), with
`CACHE` on the a1200-030. Its checks ([internals](internals.md#game-time)), each from a fresh
`tools/boot.sh`:

```sh
python3 tools/pace.py                            # ticks and drawn frames against elapsed fields
python3 tools/gametime.py capture tmp/prof/f200_enh.bin   # the state at tick 200, then
python3 tools/callwrites.py compare tmp/re/f200.chip tmp/prof/f200_030.bin tmp/prof/f200_enh.bin
```

`compare` takes the game state's differences against the original's capture, less what the
drawing writes; `tmp/re/f200.chip` is a chip dump from the original at demo frame 200
(`python3 tools/callwrites.py capture tmp/re/f200.chip`). `tools/callwrites.py` also lists
what each main-loop call writes (`writes`), checks that leaving the drawing out keeps the
game state (`split`) and finds who reads and writes an address range (`who`), all in
Unicorn from that dump.

Other analyses, each from a fresh `tools/boot.sh`:

```sh
python3 tools/chipaccess.py                      # what the CPU's chip slots go to (trace DMA records)
FSUAE=$FSUAE_APROF SETUP=a1200-030 EXTRA_ARGS=--uae_mmu_model=0 WHD_ARGS=CACHE tools/boot.sh
python3 tools/aprof.py run tmp/prof/demo030.aprof  # exact cycles and chip-access time per group
python3 tools/gametime.py capture tmp/prof/f200_030.bin   # then the same on SETUP=a500+
python3 tools/gametime.py compare tmp/prof/f200_030.bin tmp/prof/f200_a500.bin
```

## The relocation table

`src/reloc.i` is generated: the longs in the image that hold an address in the moved block
([internals](internals.md#cpu-only-data-in-fast-memory)). After any change to the walk's knowledge
in `tools/relocmap.py` (seeds, pointer tables, ranges of lookalikes):

```sh
python3 tools/relocmap.py check                  # must print ok
python3 tools/relocmap.py inc                    # rewrites src/reloc.i (refuses if check fails)
python3 tools/relocmap.py refs | indirect | imm | dis ADDR [N]   # what it found
```

The walk reads only `Disk.1`. `check` also compares it with `tmp/re/coverage.pkl` when that
exists: the executed PCs that `tools/coverage.py` collects from traced runs, from a fresh
`tools/boot.sh` on a core that records a trace, with the original slave (`SLAVE=original`:
traced PCs must be at the game's addresses). For example the title to the demo, then play:

```sh
python3 tools/coverage.py until 63ec8 trace 1100 key 36 1 key 36 0 wander 1500
python3 tools/coverage.py dive 1000 0 mouse 0 50 dive 300 0 key 40 1 key 40 0 trace 200
python3 tools/coverage.py                        # the count by step
```

N (raw `$36`) hands the demo to the player. The game is mouse-only: RMB (`JOY1_2ND_BUTTON`)
thrust, LMB (`JOY1_FIRE_BUTTON`) fire, moving the mouse pitches and turns (up: nose up).
`NOTRACE=1` runs the same steps without tracing, to drive a build (the relocated one stops
on its `ILLEGAL` fill if a reference was missed; WHDLoad's core dump is then in the run's
`dh1`).

The tools that need the game's address find it with `tools/codebase.py` (the game's level
3 vector at `$6c`; `codebase.at` maps any address). `tools/chipaccess.py` reports CPU
accesses to the moved block's stale chip copy (there should be none). `tools/callwrites.py
capture` and `tools/bench.py` with `report.py` run the game at its original addresses: use
them with `SLAVE=original`.

## Traps

- `ws_BaseMemSize` is 544 KB, all chip memory, so WHDLoad cannot run it on a 512 KB chip
  machine: `SETUP=a500` stops with "you need chipmem up to $88000 (544 Kbyte)". The
  default setup is the `a500+` (1 MB chip).
