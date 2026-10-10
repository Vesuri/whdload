# Profiling the original Legends of Valour

> **Read this before running, driving or tracing the game, or quoting any performance number.**
> This document defines the current measurement method. The harness originated in
> Test Drive II (also an OS game under kickemu), with Indianapolis 500's lldb fix.

## TL;DR

```sh
source amiga/env.sh
python3 tools/unpack.py                                   # once: decrunch AMIGA2 -> tmp/unpacked/
tools/fixed_window.sh tmp/prof/x                          # VERIFY slave, spin route, 100 fields
OUT=tmp/prof/x
SLAVE=$OUT/slave.slave python3 tools/frames.py $OUT/trace.bin $OUT/code.bin 0xc00000    # fps
SLAVE=$OUT/slave.slave python3 tools/lov_report.py $OUT/trace.bin $OUT/code.bin --base 0xc00000
```

A/B a patch: `tools/ab_window.sh PREFIX OFF_BITS ON_BITS [ROUTES [MACHINES]]`, then
`python3 tools/ab_summary.py PREFIX` (§8).

## 1. Host setup

Everything shared lives under `~/.local`, installed by AmigaXDev (`make setup`): the m68k
toolchain and gdb in `~/.local/opt/bin`, vasm at `~/.local/vasmm68k_mot`, FS-UAE with the Barto
gdb stub, and the shared Amiga files in `~/.local/share/amiga`. `amiga/env.sh` sources the
shared `env.sh` (AmigaXDev's `docs/environment.md` lists every variable), which puts the
toolchain on PATH and resolves the shared files, after setting this project's own choices:
WHDLoad 19.2 (`WHDLOAD`) and the native vasm (`VASM`). Each has an environment override:

| Variable | Default | Used for |
|---|---|---|
| `KICKSTART` | `~/.local/share/amiga/Kickstarts/kick40063.A600` | host ROM (Kickstart 3.1), boots Workbench |
| `KICK13` | `~/.local/share/amiga/Kickstarts/kick34005.A500` (+ `.RTB` beside it) | Kickstart 1.3 for the kick13 slave; also located in dumps by `lov_report.py` |
| `KICKSTART_A1200` | `~/.local/share/amiga/Kickstarts/kick40068.A1200` | the 68020 capture machine (§3) |
| `WORKBENCH_ADF` | `~/.local/share/amiga/Workbenchv2.04rev37.67Workbench.adf` | boot floppy |
| `WHDLOAD_BINARY` | `~/.local/share/amiga/WHDLoad/C/WHDLoad` | copied onto the game drive |
| `SOUND`, `WINDOW` | 1, `front`; 0, `back` with `DEBUG` or `WARP` | audio on/off; FS-UAE window in front, behind the others, or `none` (no video) |
| `FSEMU_SCREENSHOTS_DIR` | `amiga/<run dir>/shots` | FS-UAE screenshots |

Build-side overrides (`whdload/makefile`): `WHDLOAD` (WHDLoad dev tree, default
`~/.local/share/amiga/WHDLoad`), `NDK` (`~/.local/opt/m68k-amiga-elf/sys-include`), `VASM`
(a native build at `tmp/vasm-native-src/vasm/vasmm68k_mot` if present, else
`~/.local/vasmm68k_mot`), `OUT` (`tmp/build`). Run-side: `FSUAE` (executable, default
`fs-uae` on PATH; native captures use `$HOME/.local/share/amiga/fs-uae-arm/fs-uae`, §4),
`FSUAE_COMMON` (`~/.local/share/amiga/fsuae_common.sh`). The game itself is expected at
`tmp/game/LegendsOfValour` (`GAME`). Every game-derived file (archives, unpacked hunks,
builds, captures, screenshots, scratch dumps in `tmp/scratch`) stays in the ignored `tmp/`.

## 2. The game and the slave

| Field | Value |
|---|---|
| Archive | `LegendsOfValour_v1.0_0837.lha` (Retroplay, pre-installed): `LegendsOfValour.Slave` (4 488 bytes), `data/` (3.2 MB: `AMIGA2`, `charact`, `textfile`, pictures, maps). Hashes in `tmp/archive.sha256` |
| Slave | CFou! v1.0 (06.02.2005), **no source**. Decode it with `tools/slave_info.py [--pl OFF]` |
| Header | `ws_Version` 16, flags `$2402` (NoError, EmulPriv, Examine), `ws_BaseMemSize` `$80000`, `ws_ExpMem` `$C0000` (256 KB Kickstart + 512 KB), CurrentDir `data`, KeyExit `$59` (F10), no `slv_config` (v16) |
| Type | **OS game, kickemu Kickstart 1.3** (`ws_kickname` `34005.a500`, `$40000` bytes, CRC `$F9E3`); needs `kick34005.A500` + `.RTB` in `DEVS:Kickstarts` (run.sh copies them) |
| Kick patches | `slave+$60`: the stock kick13.s list (70 entries, `slave_info.py --pl 60`), applied with `resload_Patch` to ExpMem, then `jmp ExpMem+2` |
| `_bootdos` | `slave+$fa4`. `resload_Control` reads CUSTOM1 (`slave+$10fc`); assigns `LOV:`; opens and CRC16s the first 300 bytes of `AMIGA2` (result unused); `LoadSeg`s **`AMIGA2`**, or **`CHARACT`** (character creation) when CUSTOM1≠0; tells WHDLoad the segment list; patches; calls the program with `d0=1, a0="\n"`; `resload_Abort` on return |
| Stub patches | if the first long of hunk 0 is `$487A0178` (the PowerPacker stub): `jmp slave+$110c` over the stub's final `movem/rts` at stub `+$176`, and `bra.s` over the decrunch colour flash at stub `+$210` |
| Game patches | `slave+$110c`, run after the stub has loaded the real program: manual protection, **hunk 1** offsets. Version A: `h1:013e0` `cmp.l d7,d6; bne` → `move.l d6,d7; nop`, `nop nop` at `h1:0141e`, `nop` at `h1:01422`. **Version B (this AMIGA2)**: the same at `h1:013d8`, `h1:01416`, `h1:0141a` |

**The code.** `data/AMIGA2` (95 124 bytes) is a two-hunk file: a 548-byte PowerPacker stub and the
packed data (table 9,10,12,12). The stub decrunches in place and then **acts as its own LoadSeg**:
it AllocMems every hunk of the decrunched hunk file, copies and relocates it, chains them as a
segment list (`[size+8][next BPTR][hunk]`) and returns into hunk 0. `tools/unpack.py` is a port of
that decruncher and writes `tmp/unpacked/AMIGA2` (199 436 bytes, byte-exact) and `charact`.

| Hunk | Type | Size | | Hunk | Type | Size |
|---|---|---|---|---|---|---|
| 0 | code | `$199C` | | 9 | code | `$660` |
| 1 | code | `$2C2C` (protection) | | 10 | code | `$C4` |
| 2 | code | `$63FC` | | 11 | data | `$5E3C` file, `$A4DC` alloc |
| 3 | code | `$5BC` | | **12** | code | **`$179D0`** (asm, no `link`, reads VHPOSR) |
| 4–8 | code | `$B0`..`$2700` | | 13–16 | code | `$14`..`$184` (library stubs) |

Hunks 0–10 are **Lattice/SAS C** (`link a5` prologues); hunk 12 is hand-written. Docs name code
as `hN:OFFSET`. `tools/xref.py` lists relocations into a range; `tools/disd.py` disassembles a
dump by hunk offset.

**The rebuilt slave.** `whdload/LegendsOfValourHD.s` rebuilds CFou!'s v1.0 on WHDLoad 20.0's
`kick13.asm` example and the vendored 2025 `kick13.s`, with the example's options (`IOCACHE =
1024`: without it every small game `Read()` is a resload call; `CACHECHIP`, `SETPATCH`,
`SEGTRACKER`, `POINTERTICKS`, `SETKEYBOARD`, `HRTMON`, `WHDCTRL`). `slv_Version` 17.
`tools/behaviour_check.py OUT [--slave tmp/build/LegendsOfValour.Slave]` snapshots the first
start-screen button poll with the original or rebuilt slave; both give byte-identical view
planes (only the Intuition pointer colour differs).

| Build | Command | Contents |
|---|---|---|
| release | `make -C whdload` | W1–W6 always on; menu: character creation, game timing, fine turning |
| developer | `make -C whdload developer` | individual CUSTOM2 switches for W1–W6, no instruments |
| VERIFY | `make -C whdload verify` | developer + input tape, pixel twins and other CUSTOM5 instruments; never ship |

The `slv_config` string in `LegendsOfValourHD.s` is the authoritative bit map.

## 3. The machine

Kickstart 3.1 host + Workbench 2.04 floppy boot DH0, whose startup-sequence runs `WHDLoad
LegendsOfValour.Slave PRELOAD SPLASHDELAY=0 NOREQ` on DH1 (a fresh copy of the game + WHDLoad
each run: **save games written during a run are lost**). `amiga/run.sh` boots it; optional
`amiga/performance.env` (see the `.example`) selects the patch mask for interactive runs.

| Machine | Settings | Code base in dumps |
|---|---|---|
| A500-equivalent | `CHIP_KB=512 FAST_KB=0 EXTRA_ARGS=--slow_memory=1536` (fixed-window capture default) | `0xc00000` (slow RAM) |
| 14 MHz 68020 | `AMIGA_MODEL=A1200 KICKSTART=$KICKSTART_A1200 CPU=68EC020 CHIP_KB=2048 FAST_KB=4096 EXTRA_ARGS=--slow_memory=0` | `0x200000` |
| 68000 + physical fast | `AMIGA_MODEL=A500 CPU=68000 CHIP_KB=1024 FAST_KB=8192 EXTRA_ARGS=--slow_memory=0` (512K chip + 4M fast fails in the game's own startup allocator) | `0x200000` |

The A500-equivalent cannot PRELOAD the 3.2 MB of data. `lov_report.regions(dump, base)` finds
all 17 hunks, the Kickstart image and the live slave by voting for hunk 0 and walking the
segment chain (the freed decrunch buffer still holds a stale copy of every hunk).

**`JOY0=none` for every capture.** The host mouse feeds port 0 even with input grab off, and the
game is mouse-driven.

## 4. Driving and tracing (`tools/lov.py`)

Test Drive II's server: `serve` boots `amiga/run.sh DEBUG=1` and attaches gdb; then `stop`,
`cont`, `gdb <text>`, `shot <png>`, `profile <fields> <bin>`, `wait`, `until <addr>`, `quit`.
Socket `amiga/<run dir>/lov.sock`. Captures run in `amiga/.cap` (`FSUAE_RUN`), interactive
sessions in `amiga/.run`; **never stop an emulator in `.run`, and run one capture at a time**
(two parallel captures broke both debugger sessions). gdb runs in the repo root and cannot quote
file names, so dump paths are relative (`tmp/scratch/...`). `until` waits in the background
(`UNTIL_TIMEOUT`, default 1 800 s) and stops the capture cleanly on expiry; a `profile` is capped
at 100 fields.

**Native captures** (`FSUAE=$HOME/.local/share/amiga/fs-uae-arm/fs-uae PROFILE_WINDOW=guest`).
The arm64 FS-UAE (revision `b70b1180`) cannot be attached by host LLDB, so the VERIFY-only
`PROFILER_WINDOW` fixture configures the profiler from the guest: at the tape anchor, in VBL
context, it saves SR, the current process's segment-list/task-number fields and 32 chip scratch
bytes, presents a synthetic segment, and restores everything before tracing.
`profile_window_check.py` (run by `fixed_window.sh`) checks the restoration. Barto stores RAM
PCs relative to the profiler start (ROM PCs and IRQ markers stay absolute); `lov.py` saves the
acknowledged base in `trace.pc-base` and `barto.py` normalizes RAM PCs. Keep the sidecar with
its trace.

## 5. What the game does, and how it reads input and time

With no input the boot reaches the **start screen** (static 3D street, three buttons) and stays;
there is no attract demo. The start screen polls through `h6:0076c`, `h0:01524`, `h2:00000`,
`h1:01b8c`, `h12:16a4e`, `h12:0fe66`.

All input and time come through **h12's vertical-blank server `h12:06404`**:

| Offset | What |
|---|---|
| `h12:06404` | `addq.l #1,h11:0602c` — **field counter** (time source). `h12:063ac` combines its low word with VPOSR into a beam-time value; `h12:063f0` waits for the next field |
| `h12:0643e` | `move.w $dff00a,d0` (**JOY0DAT**), deltas against `h12:0002c` added to the **pointer accumulators `h11:008d2` (x) / `h11:008d4` (y)** |
| `h12:06472` | optional per-field callback through `h12:0648e` |
| `h12:06480` → `h12:05298` | buttons: left = CIAAPRA bit 6 (`h12:0529a`), right = POTINP bit 10 (`h12:052ee`), each debounced over 2 fields; state bits in **`h12:05292`** (bit 0 left, bit 1 right), read by `h12:05288` |

There are no CIA keyboard reads in AMIGA2; the keyboard comes through the OS console.

Screens (coordinates are tape window coordinates, below):
- Start screen: green = load a **character** (`Charact.__N`, written by `CUSTOM1` character
  creation), red = load a **saved game** (`Legend1.__N`), Amiga DOS. The archive has neither.
- Save-slot screen (`h8:001de`): bars 1–8 select, left die loads, middle die switches save disk,
  **right die (132,175) cancels → the game starts with the default character**.
- In game a townsman may walk up and talk; his speech blocks the game until EXIT (75,183) in the
  conversation panel. Clicking there with no conversation hits the status bar harmlessly.
- View size: the game **starts in the medium view**; nothing is saved. Computer button (15,188)
  → options dialog → second icon from the right on the top row (193,52); each click cycles
  medium → small → large → medium (`tools/tapes/viewcycle.txt`); clicking outside applies it.

## 6. The input tape (VERIFY, `CUSTOM5` bit 0, `whdload/tape.s`)

`h12:05298` jumps into the slave, which writes the tape's pointer position into the game
window's `MouseX/MouseY` (the game copies them every poll, `h1:01b8c`) and its buttons into
`h12:05292`. Tape field 0 is the first VBL after the game installs its server.

`tools/tape.py SCRIPT OUT` builds a tape from `FIELDS X Y [L|R|A|W|H]` lines (window coordinates
= (screenshot x − 75) / 2, (y − 38) / 2); `run.sh` installs it as `data/lovtape` (`TAPE=`).
- **`W`** waits on game state: the tape hooks the button hit test `h6:0076c` and holds the entry
  until the last hit-tested list has button id FIELDS (0 = any) under (X,Y). It covers every
  screen that hit-tests through h6 but **not the conversation panel**, which polls through h2:
  routes dismiss the townsman by clicking EXIT blindly every 100 fields.
- **`H`** waits until the heading `h11:08c28` reaches a value (used by `wall.txt`).
- **`A`** marks the anchor: its first field runs `_tape_anchor`, where captures break.
- The last entry must have FIELDS 0 and must not be a `W`.

`tools/tape_explore.sh SCRIPT OUT [COUNT STEP]` boots a tape and takes labelled screenshots for
route finding.

| Route (`tools/tapes/`) | Use |
|---|---|
| `spin.txt` | **benchmark**: default character, large view, EXIT pulses, 250 fields turning right, anchor |
| `wall.txt` | scene-stable benchmark: stop at heading 150 facing a wall, 1 000 fields, anchor |
| `c2p-views.txt` | visits all three view sizes; pixel-twin validation (`render_validate.sh`) |
| `turning-still.txt` | stationary pose for one-degree turning A/B |
| `timing-*.txt` | simulation-timing checks (`docs/simulation-timing.md`) |
| `load.txt`, `cancel.txt`, `walk.txt`, `street.txt`, `talk.txt`, `viewcycle.txt` | building blocks and exploration |

## 7. Fixed window and frame counter

`tools/fixed_window.sh OUT [TAPE]` builds the VERIFY slave (or uses `OUT/slave.slave` with
`KEEP_SLAVE=1`), keeps it and its listing in OUT, boots with `DETERMINISTIC=1`, finds the live
slave in a dump, breaks at `slave + _tape_anchor` (from the listing) and traces `FIELDS` fields
(100). `anchor.txt` records the tape field and the game's field counter at the anchor. Options:
`TAPE_OPTIONS` (CUSTOM5 value, default 1), `WHD_ARGS` (e.g. `CUSTOM2=63`), `STATE_ONLY=1`
(dump state, no trace), `SWAP_ONLY=1` (count frames with breakpoints, for CPUs without an
instruction trace; agrees exactly with the trace), `SELFTEST_FRAMES=N` (run VERIFY twins to
their completion breakpoint), `STATE_FIELDS` / `STATE_TICKS` / `TIMING_PAUSE` / `KEYBOARD_EXIT`
/ `TAPE_CHECKPOINTS` (simulation-timing observers), `TURNING_CHECK=1`, `BOOT_BREAK=addr`.

**Reproducibility.** `tools/compare_traces.py A B` compares every field's instruction records,
DMA records and screenshot. Two fresh boots of the spin route give **all 100 fields identical**,
so VPOSR entropy does not leak into it; re-check for any new route.

**Frame counter.** The game never writes the copper. The main loop renders into a chunky buffer
(192 bytes per row; `h12:027bc`) and shows it with `h12:05ea6`, which waits for the beam and
converts the buffer into the screen's 4 bitplanes (`h12:054ce`), or copies with `BltBitMap` on
view changes. `frames.py` counts entries of `h12:05ea6`; `swap_fields.py` watches the same entry.

## 8. Measuring a change

1. Build once; vary only CUSTOM2 (`WHD_ARGS=CUSTOM2=…`). Developer/VERIFY builds honour every
   bit; release builds force W1–W6 on (pass `--custom2 (mask|63)` to `check_disabled.py`).
2. Capture off and on, on the A500-equivalent **and** the 68020, one at a time, on `spin` and
   `wall`. `tools/ab_window.sh PREFIX OFF ON [ROUTES [MACHINES]]` does this and runs the analysis
   chain on each capture: `check_disabled.py` (off: patched ranges are original) or
   `chunky_check.py` (on), `frames.py`, `lov_report.py`, `c2p_report.py`, `render_report.py`,
   `blocks.py`, `lov_state.py`. `KEEP_TRACE=0` deletes the 0.5–1 GB trace afterwards (any window
   can be recaptured deterministically).
3. `python3 tools/ab_summary.py PREFIX` prints slave hash, fps, cycles/call and state per pair and
   writes off/on first/last comparison sheets.
4. **Scene caveat.** The original's game time depends on frame time, so a faster build reaches the
   anchor in a different state. Quote fps over the window, but compare the changed routine's
   **cycles per completed call** (`c2p_report.py`, `render_report.py`: boundary-partial calls
   excluded; main-task excludes the IRQ stack, inclusive includes it), check first/last images,
   and use `wall.txt` for a matching scene. `lov_report.py` self-time names are unreliable in
   hunk 12 (no prologues); `blocks.py` gives a 64-byte PC histogram.
5. Correctness is proven by VERIFY twins, not by A/B: `tools/render_validate.sh PREFIX [BITS]`
   calibrates each CPU, then runs C2P, wall, sprite, reciprocal and clear twins over all views
   (`c2p_check.py`, `render_check.py`). Use the native FS-UAE.

## 9. Results

Spin route, large view, 100 fields. Baseline is the original game; each row adds one patch
(developer build, CUSTOM2 mask in brackets). Per-patch cycle figures are in
`docs/performance-patches.md`.

| Build | A500-equivalent fps | 14 MHz 68020 fps |
|---|---|---|
| original (0) | 2.5 | 12.4 |
| + W1 Kalms C2P (1) | 3.0 | 14.8 |
| + W2 PUBLIC chunky (3) | 3.0 | 16.0 |
| + W3 wall unroll (7) | 3.0 | 15.8 |
| + W4 sprite rows (15) | 3.1 | 15.8 |
| + W5 reciprocal cache (31) | 3.2 | 16.0 |
| + W6 MOVEM clear (63) = release | 3.2 | 16.1 |

On the scene-stable wall route the release build runs 3.3 fps (A500-equivalent) and 15.3 fps
(68020), from 2.8 and 11.9. Differences under ~0.2 fps between rows are scene/phase noise; the
per-routine cycle savings are the evidence. The 25 fps cap and beam wait are unchanged.

Where the original spends the frame (share of all CPU cycles; A500-equivalent / 68020):
render 43.8% / 53.1% (wall columns `h12:04c1a` 26.8% / 31.8% self, per-column setup
`h12:02808` 11.7% / 14.1% self), chunky-to-planar 26.0% / 29.9%, game logic and objects
(`h5:02358`) 15.8% / 6.2% including scaled sprites `h12:05114` 12.6% / 4.9%, interrupts and OS
~9% / ~3%. No blitter waits; CPU busy 100% (no STOP).
