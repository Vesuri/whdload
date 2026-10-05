# Profiling the original Test Drive II

> **Read this before running, driving or tracing the game, or quoting any performance number.**
> Everything here was measured on this machine (macOS, x86_64 FS-UAE in `/path/to/fs-uae`
> with the Barto gdb stub, `m68k-amiga-elf-gdb` 2026 toolchain), 2026-10-03/04.

**Slave 1.6b (2026-10-05):** the three features are one option, "Enhanced framerate"
(`CUSTOM2`, any nonzero value; enable it by default with the icon tooltype `CUSTOM2=1`).
Commands and results below that name `CUSTOM2=1`/`2`/`3`/`4`/`5`/`7` predate 1.6b, when each
feature was a separate bit; per-feature A/B runs now need a temporary build.

**Current runtime requirement (1.6c):** WHDLoad 20.0 or later. The API and
KickEmu source baseline is pinned in the repo. `WHDLOAD_BINARY` selects a runtime
without altering the shared installation; see [compatibility.md](compatibility.md)
for 20.0 provenance and 68060 startup checks. Historical results below used 19.2.

## TL;DR

```sh
tools/profile_demo.sh                 # → tmp/prof/run/{trace.bin,code.bin,report.txt,first.png,last.png}
FIELDS=50 tools/profile_demo.sh tmp/prof/x
CHIP_KB=1024 FAST_KB=2048 EXTRA_ARGS= tools/profile_demo.sh tmp/prof/fast   # same with fast RAM
```

It boots the WHDLoad install in warp, waits for the **attract demo** to start driving (the demo
plays itself, so no input is needed), records a cycle-exact trace of `FIELDS` PAL fields (default
80, max 100), dumps the memory holding the code, checks the first and last traced fields are both
in-game, and writes the report. About 1–2 minutes of wall time; a trace is ~5.4 MB per field.

## 1. The machine

`amiga/run.sh` boots a **Kickstart 3.1 host** (FS-UAE `A500` model, 68000) from a directory DH0
plus the Workbench 2.04 floppy for `C:`/`Libs:`; DH0's startup-sequence runs
`WHDLoad TestDrive2.slave PRELOAD SPLASHDELAY=0 NOREQ` on DH1 (a fresh copy of
`tmp/game/TestDrive2` plus the WHDLoad binary). The slave is a **kick13 kickemu**: WHDLoad boots
a real Kickstart 1.3 (`DH0:devs/Kickstarts/kick34005.A500` + `.RTB`) inside its own memory and
the game's `duel` is LoadSeg'd under that, as on an original 1.3 machine.

| Variable | Default (run.sh) | profile_demo.sh | Meaning |
|---|---|---|---|
| `CHIP_KB` | 1024 | 512 | chip RAM |
| `FAST_KB` | 2048 | 0 | fast RAM at `$200000` |
| `EXTRA_ARGS` | — | `--slow_memory=1536` | extra FS-UAE options |
| `CPU` | 68000 | 68000 | |
| `WARP` | 0 | 1 | warp only changes wall time, never the emulated cycle accounting |
| `SILENT` | 0 | 1 | `--audio_driver=dummy` |
| `DEBUG` | 0 | 1 | open the gdb stub on `$DEBUG_PORT` (per-directory, from `fsuae_common.sh`) |
| `RECORD` | — | — | FS-UAE input recording file, see §7 |

**Profile the stock-A500-equivalent machine**: 512 KB chip + 1.5 MB slow RAM and no fast RAM
puts every CPU access on the chip bus, exactly as on an A500 (the slave's 512 KB "expansion"
memory lands in slow RAM at `$C00000`, and slow RAM is contended like chip). WHDLoad needs more
than 1 MB in total (base 512 KB + exp 512 KB + the 256 KB 1.3 image + itself + PRELOAD), so a
literal 512+512 A500 cannot run the WHDLoad install; 1.5 MB slow costs nothing in speed.

With fast RAM the frame rate barely changes (6.6 vs 7.2 fps, different demo positions), so bus
contention is not the limit — see §6.

## 2. Driving it: `tools/td2.py`

```sh
WARP=1 python3 tools/td2.py serve > amiga/.run/serve.log 2>&1 &   # boots run.sh with DEBUG=1
python3 tools/td2.py shot  "$PWD/amiga/.run/now.png"   # 1-field trace, keep its screenshot
python3 tools/td2.py wait 2                            # let it run 2 s (wall)
python3 tools/td2.py stop | cont
python3 tools/td2.py gdb 'info registers'              # any gdb command (halts, resumes after)
python3 tools/td2.py profile 80 "$PWD/tmp/prof/x.bin"
python3 tools/td2.py quit                              # kills gdb and our FS-UAE only
```

The server holds one gdb attached to the stub and serves one command per connection on
`amiga/.run/td2.sock`. Rules learned the hard way:

- **Attach within 20 s of launch.** `--remote_debugger=20` with no trigger means the stub waits
  20 s for a connection and then stops servicing the port for good (the socket stays in LISTEN,
  gdb then times out on `vMustReplyEmpty`). `serve` connects as soon as the port listens; the
  CPU is then halted at the reset PC `$F800D2` and `serve` continues it.
- **Emulated time does not advance while gdb has the CPU stopped**, so stops (and the lldb
  attach of §3) do not perturb any measurement.
- **gdb splits command arguments at spaces**, and this repo lives in `…/Test Drive 2`: `dump
  binary memory` must write through a space-free path (`/tmp/…`, then move it). `td2.py profile`
  quotes its own path.
- **The stub is read-only.** `M`, `P` and `G` packets get an empty reply (verified with
  `set debug remote 1`): gdb `set var`/`set {int}addr`/`set $d0` are silently dropped. Do not
  build input injection or patches on gdb writes.
- `shot` works because every field of a `monitor profile` trace carries a PNG of the display
  (`barto.Field.shot`). It is the only screenshot route: macOS denies this process screen
  capture (`screencapture -l` → "could not create image from window"), and CGEvents posted to
  FS-UAE's pid (Accessibility granted) never reach it — neither Amiga keys nor the F12+S
  screenshot chord. The user can take one with F12+S; it lands in
  `$FSEMU_SCREENSHOTS_DIR` = `amiga/.run/shots/`.

## 3. ⚠ The profiler records no PCs unless you fix its window (lldb)

`monitor profile N "" FILE` records, per instruction, `[PC words] (0xffffffff-cycles) d0-a7 sr`,
but only PCs inside `[baseText, baseText+sizeText)`. With a `--remote_debugger_trigger` that window
is the triggered program's first hunk (how other programs profile their own exes). Under WHDLoad no
host process maps onto the game, so we run **without** a trigger — and in this FS-UAE build the
window then reads `baseText=0x0100007f, sizeText=0` (127.0.0.1 in network order has landed in
`baseText`). The window is empty but non-zero, so records are written **with no PC at all**:
a trace looks like 100% "stopped CPU" while the registers visibly change.

`td2.py profile` repairs it before every capture by attaching lldb to our FS-UAE process:

```
slide = `image list -o -f fs-uae`                # e.g. 0x2f92000
memory write -s4 (0x32dea04 + slide) 0           # baseText
memory write -s4 (0x32dea08 + slide) 0x7fffffff  # sizeText
```

`0x32dea04` is this binary's link-time address of `baseText`, found from the stub's own code:
the `GDBSERVER: enabled` setup stores `0` / `0x7fffffff` there (`objdump -d` near the reference
to that string, around `0x5a49e`), and the profile command loads both and passes
`base, base+size` to `start_cpu_profiler` (around `0x5f380`). **A different FS-UAE binary needs
these addresses re-derived** the same way; `fix_profile_window` asserts the read-back and fails
loudly otherwise. lldb attaching works because the binary is not hardened; it stops the process
for a moment, which (like a gdb stop) costs no emulated time. Attaching to this x86_64 binary
under Rosetta takes from 25 s to several minutes, so `td2.py` attaches one asynchronous lldb on
the first capture of a session, with symbol preloading off, and reuses it.

To trace a moment in the game, use `td2.py until '<addr> if <cond>'`: it leaves the emulator
stopped at the hit, so the next `profile` starts there. A `gdb continue` resumes the emulator
afterwards, and warp mode runs far past the hit before the capture starts.

## 4. Catching the demo

The attract sequence loops intro → "Loading Game…" → **in-game demo** (dashboard view, a few
seconds of emulated time, sometimes much longer) → Accolade logo → high scores. Never trace the
boot or the menus: `profile_demo.sh` polls `shot` every 0.5 s (wall, in warp) and tests each
screenshot with `tools/ingame.py` (sky-blue pixels above the dashboard at 12% height), traces the
moment it matches, and afterwards **re-checks the first and last traced fields** — a trace that
ran past the end of the demo is rejected. One gap: the demo itself starts with the car at rest,
so very early traces carry a little start-line work.

## 5. Reading a trace

```sh
python3 tools/td2_report.py tmp/prof/run/trace.bin tmp/prof/run/code.bin --base 0xc00000
python3 tools/frames.py     tmp/prof/run/trace.bin tmp/prof/run/code.bin 0xc00000
python3 tools/hotspots.py   tmp/prof/run/trace.bin tmp/prof/run/code.bin 0xc00000 <duel-hunk-base> 0f114,0789c
python3 tools/disd.py       tmp/prof/run/code.bin 0xc00000 <duel-hunk-base> 0x0f114 0x0f2c0
```

(`--base 0x200000` and a fast-RAM dump when `FAST_KB>0`.)

**Code regions** (except the linked data hunk) are found by byte-matching the dump against the installed files (relocations
make an exact compare impossible, so 16-byte windows vote for a base):

| Region | Found as | In a 512K/1.5M run |
|---|---|---|
| `duel` root code hunk (hunk 0, `$1156C` bytes, file offset `$28`) | `duel:OFFSET` | `$D000A8` |
| `duel` data hunk (hunk 1, `$3A38` file-backed, `$7A70` allocated) — holds a `jmp abs.l` jump table (Aztec C) | resolved to targets | `$D11620` |
| Kickstart 1.3, **copied into RAM by kickemu** | `kick:ROMADDR` (`$FC0000`-based) | `$CB5000` |
| the WHDLoad slave | `slave:FILEOFFSET` | `$D7CF20` |

`duel` is an overlay executable (`HUNK_OVERLAY` at file `$1571C`); in the driving demo all hot code
is in the root hunk. `duel:` offsets are the **same numbering as the slave's patch lists**
(`PL_P $00588A,set_copper` = `duel:0588a`).

**Contexts.** ⚠ The recorded `sr` is stale (UAE rebuilds `regs.sr` lazily; it reads `$0004`
inside interrupt handlers), so supervisor/user cannot be told from it. The report keys call stacks
on **which stack SP is in** instead: in a 512K/1.5M run the main game task's stack is around
`$D1E000`, the supervisor stack `$D74000–$D75FFF` (interrupts), and two more task stacks around
`$CFD000` (a second game task) and `$CF8000` (OS device tasks).

**Attribution.** A `jsr`/`bsr` whose successor has SP lowered by 4 pushes a frame named after the
callee (through a `jmp abs.l` trampoline if there is one; `jsr d16(a6)` is named
`library-LVO` from the library node at `a6`); the frame pops once SP climbs back to the caller's.
That gives **inclusive** time and call counts. **Self** time is assigned statically to the nearest
preceding function start (Aztec C `link a5` prologues plus every observed call target), so code
entered before the trace began is still credited. A function without a `link` merges into its
predecessor in the self table — check `hotspots.py` before believing a big self number.

**Frames** are counted at the slave's `set_copper` (`move.l a0,$dff080`, the buffer swap JOTD
patched in at `duel:0588a`). **Blitter waits** are cycles on `btst #6,2(a6)` polls (DMACONR
BBUSY, `a6=$DFF000`) and the `nop`/`bne` around them. **Interrupts** are counted at Kickstart
1.3's level-3 handler `$FC0D14` and its BLIT (`$FC0D38`) / VERTB (`$FC0D4A`) branches. **DMA
slots** come from the per-field DMA records (58 bytes each in this build; type byte at offset 29:
1 refresh, 2 CPU, 3 copper, 4 audio, 5 blitter, 6 bitplane, 7 sprite, 8 disk).

### Trace format (`tools/barto.py`)

Little-endian uint32: `fields`, `nsections`, section bases, 16 bytes of stack bounds; ROM, chip and
slow-RAM snapshots (size + bytes each; **no fast RAM** — hence the separate gdb dump); base clock,
cycle unit. Per field: custom registers (520), AGA colours (1024), DMA records (size, count,
records), resource records, `cycles`, `idle`, word count, instruction words, screenshot (size,
kind, PNG). An instruction record is zero or more PC words (< `0xffff0000`; first = PC), then
`0xffffffff − cycles`, then 17 registers (d0–d7, a0–a7, sr). `0x7fffffff` as PC marks cycles
burnt between instructions (interrupt entry). A PAL field is 142 102 CPU clocks.

## 6. Baseline (2026-10-04, 512K chip + 1.5M slow, demo, 80 fields)

**7.2–7.3 fps** (a frame every 6.8–6.9 fields). The CPU never idles (no `STOP`).

| Share of CPU cycles | What | Where |
|---|---|---|
| 13% | CPU horizontal span fill of 5 separate bitplanes (masked edges, `dbf` of 5 `move.w`), ~215 spans/frame, ~600 cycles each | `duel:0789c` |
| 11% | **CPU spinning on the blitter**: the shape blitter starts one plane (BLTSIZE) and polls BBUSY before the next | `duel:0f114` (+`0f2ea`, `0f426`, `0f612`) |
| ~9% | shape blit setup around those waits | same |
| ~11.6% | **~150 blitter-finished interrupts per frame** through Kickstart 1.3's level-3 dispatch (the game polls anyway) | `kick:fc0d14` |
| 3.9% | vertical blank interrupt chain | `kick:fc6d48` |
| ~16% | road/object projection (`muls`, table lookups) | `duel:07370`, `duel:079c6` |
| ~7% | unoptimised C masked word copy (locals in the stack frame) | `duel:09588` |
| 3.6% | `movem.l` clear of the back buffer | in `duel:0844e` |
| ~9% | other tasks (second game task `duel:0d6ae`; OS) | |
| ~2.5% | WHDLoad-only: slave `set_copper` beam wait (1.5%), kickemu interrupt stub | slave |

The blitter is busy in only **5%** of bus slots (CPU 37%, bitplanes 28%, free 26%): the game is
CPU-bound and serial, not bus- or blitter-bound. The same demo with 2 MB fast RAM ran at 6.6 fps.

## 6a. The benchmark window (A/B comparisons)

`profile_demo.sh` traces whatever moment of the demo the poll catches, and the demo content
varies (different sceneries per attract loop, traffic, signs): a run with a vector-font sign and
a rock wall ran at 4.3 fps against 7.2 for open road. **Never compare two `profile_demo.sh`
runs.** For A/B use

```sh
tools/fixed_window.sh tmp/prof/base                      # shipped slave
tools/fixed_window.sh tmp/prof/mine "$PWD/whdload/TestDrive2.slave"
```

It boots with `DETERMINISTIC=1`. The W1 harness now calibrates the loaded `duel` address
once per machine/arguments/slave combination, then reboots with the race-clock reset breakpoint
already armed at CPU reset (`BOOT_BREAK` in `td2.py serve`). This avoids missing the first race
on fast warp boots. `BOOT_HUNK` can supply a known loaded address; it is checked against the dump.
The reset at `duel:0bbf8` writes 1 to `-10146(a4)`, which displays as 0:00. A gdb watchpoint
confirms the store, then the window starts at `duel:05a4c`, after dashboard setup and before the
gameplay loop. `anchor.txt` preserves the clock and breakpoint evidence.

For reproducibility build `make -C whdload verify`, and run with `WHD_ARGS=CUSTOM3=1`
and `SLAVE="$PWD/whdload/TestDrive2.slave"` (also pass the slave as the second argument).
The v1-only VERIFY patch removes VHPOSR from the RNG. Two 68000 windows have identical field-0
and field-99 screenshot bytes and measure 5.9 fps in stage 2; a first-race 68020 window reaches
the same stage and measures 9.3 fps. These replace the old span-anchor window for future work.
They must not be compared as an optimisation A/B with the earlier desert captures.
`ANCHOR` is a diagnostic override of the hunk offset, not a substitute for the race-start window.

## 7. Input, if it is ever needed

The demo made it unnecessary, but these were established:

- **FS-UAE input recordings** (`RECORD=file amiga/run.sh`, forces `--deterministic=1`; written
  on SIGTERM). Big-endian uint32 stream: per frame `0x80000000|frame`, `0x10000000|rand checksum`,
  `0x08000000|state checksum`; events `0x40000000|line` then `0x20000000|state<<16|event`. On
  playback a rand-checksum mismatch invalidates the recording, a state mismatch only notifies —
  so synthetic events can be spliced into an idle baseline (`tmp/base.rec`: 32 015 frames,
  warp, no input). This binary's event numbers (from its event-name table, checked against
  `SPC_STATESAVE1 = 378` in its own log): `JOY2_LEFT/RIGHT/UP/DOWN = 60/61/62/63`,
  `JOY2_FIRE_BUTTON = 68`. Not yet tried end to end.
- **The slave**: `read_joydat` / `read_fire1` / `read_fire2` already intercept the game's
  joystick reads (keyboard control, v1.5); a test slave could feed them from a tape.

## 8. Traps hit setting this up

- **Kickstart copies were read-only**: `kickstarts` files are `r--r--r--` and `cp` keeps the
  mode, which FS-UAE exposes as a write-protected file; WHDLoad loops on `DOS-Error #223 (file is
  write protected) on reading "devs:kickstarts/kick34005.a500"`. `run.sh` does `chmod -R u+w`.
- The WHDLoad splash stays up while PRELOAD reads the data; that is not a hang.
- `/path/to/fs-uae.log.txt` is shared by every project's FS-UAE and is block-buffered:
  do not read the stub's state from it. Our stdout log is `amiga/.run/fsuae.log`.
- Two causes made early captures look like "100% STOPped CPU": the empty profiler window (§3,
  every record PC-less) and a capture that had already left the demo for the Accolade logo,
  which genuinely idles. Check the screenshots and that PCs are present before trusting a trace
  (`profile_demo.sh` checks the screenshots; §3's assert covers the window).
- Killing a `td2.py` client mid-reply used to kill the server (BrokenPipe); it now survives.

## 9. Per-field state studies (W2)

`STATE_FIELDS=300 tools/fixed_window.sh ...` takes an initial data snapshot at the race anchor,
then 300 snapshots at successive game VBL-server entries before its ordinary trace. Its trace
therefore starts at that field offset; record it when quoting fps. `WATCH_STATE=1` additionally
runs four writer watchpoint checks after the trace; they do not change the traced window.
Use `tools/state_report.py OUT/state` and `tools/state_writers.py OUT/trace.bin OUT/code.bin BASE`.
The sampler reads the full allocated `$7A70`-byte data hunk, including the zero-filled tail,
not just its `$3A38` file payload. See the state table and transient demo-state trap in open-work.
Constant-address `watch -location *(int*)ADDR` uses the stub's hardware write watchpoints;
register-dependent `watch *(int*)($a4-OFFSET)` may instead choose software watchpoints.

## 10. Cross-machine state comparisons (W3)

Use `python3 tools/compare_state.py OUT_A/state OUT_B/state` to compare the same
relative VBL indices. It reports exact raw matches, including the shared RNG, plus
field-clock/deadline values normalised by the first sample's field counter. Absolute
field counts differ because boots take different amounts of emulated time. Do not
ignore later mismatches just because the known sample-0 borrowed-state transaction
can explain a few early differences.

The VERIFY slave additionally offers v1-only `CUSTOM4=1`: a 65,536-iteration DBF
delay before the existing copper hook, preserving registers and leaving interrupts
and scheduling enabled. This is a W3 stress instrument, not an optimisation or
shipping timing design. Use `WHD_ARGS="CUSTOM3=1 CUSTOM4=1"`. Both flags are off by
default; normal builds omit the instruments.

The 1,000-sample W3 windows trace fields 1000–1099 after sampling. Their measured
render rates are 4.3 fps (68000), 6.8 fps (68020/fast), and 2.7 fps (68000 with
CUSTOM4). Longer state-only runs use `FIELDS=1`; these provide no meaningful fps
comparison. See open-work for the simulation verdict and W4 decision boundary.

`tools/task_state.py OUT/code.bin BASE` reports the cached game process and named
Road Drawer task from their Exec structures, including signed node priorities.
The saved process SP can lie outside its initial bounds because the C runtime uses
a replacement stack; correlate it with trace SP pages, not the original bounds alone.


For rebuilt slaves, keep `SLAVE` set when running `frames.py` or `td2_report.py`
on saved captures. Their slave-region lookup uses that selected file's size;
using the installed slave's smaller footprint can miss the new copper-write
location and falsely report no buffer swaps. Use the exact build that made the
capture, retained under ignored `tmp/` if the source changes between runs.

`tools/audit_simulation.py tmp/game/TestDrive2/data/duel` checks v1 simulation
hook instruction boundaries, overlaps and direct incoming branches. It reads the
original game locally and emits only diagnostics; it embeds no game bytes.


The harness now retains `OUT/slave.slave` and runs that exact copy, including its
calibration reboot. For later analysis use `SLAVE="$PWD/OUT/slave.slave"` so a
new build cannot change the slave-region bounds for an old capture.

For W5, `tools/check_timing.py OUT/state --min-fields 1800` checks consecutive
VBL indices, one-field deadline increments/spacing and the clock against PAL
elapsed time, accounting for recorded 20-second penalties. It reports any end of
the continuous driving prefix; it does not count menu phases as active simulation.

`make -C whdload verify` additionally offers v1 `CUSTOM5=1` with `CUSTOM2=1`:
the first race uses normal player physics with a field-based joystick tape.
It accelerates, turns left at fields 100–105, right at 106–111, brakes at 200–299,
coasts at 300–399, then accelerates. There are no debugger target writes.
`CUSTOM1=1` tests infinite lives through repeated recoveries. Normal builds omit
this fixture, and v2's joystick hooks stay unchanged.


## Higher-rate simulation checks (W5)

Use the normal build with CUSTOM2=1 to test the shipping v1 mode. VERIFY adds
CUSTOM5 bit 0 for the field-based joystick tape; CUSTOM5=3 also forces engine
damage once and CUSTOM5=5 forces fatal crash 17 during an existing recovery.
The latter requires CUSTOM1 off. The fixture clears both the live demo flag and
the race stack frame's cached attract flag; clearing only the live flag skips
player life-loss handling at a terminal event.

```
source amiga/env.sh
make -C whdload verify
WHD_ARGS="CUSTOM2=1 CUSTOM3=1 CUSTOM5=3" STATE_FIELDS=1800 STATE_ONLY=1 SLAVE="$PWD/whdload/TestDrive2.slave" tools/fixed_window.sh tmp/prof/damage "$PWD/whdload/TestDrive2.slave"
python3 tools/check_units.py tmp/prof/damage
python3 tools/check_timing.py tmp/prof/damage/state --min-fields 1800
python3 tools/check_recovery.py tmp/prof/damage/state --damage
```

For fast-RAM dumps, `check_units.py` and `check_disabled.py` require
`--base 0x200000`. `check_recovery.py --trainer` expects no life loss. A fatal
fixture uses `check_terminal.py` and `check_timing.py --min-fields 900 --fatal-end`:
the active clock check ends at the fatal event, before the original menu path.
Do not report a frozen race clock after game over as simulation lag.

`check_disabled.py OUT` reads the original local v1 file and verifies its bytes
at the simulation patch ranges when CUSTOM2 bit 0 is off. It excludes the two RNG
ranges shared with CUSTOM3. An original-mode RNG comparison can differ because
the original renderer still consumes that generator; it is not an optional
simulation patch accidentally left active.

Every fixed-window capture retains `OUT/slave.slave`. Set SLAVE to that copy
when re-running trace reports: using the installed or latest slave's different
size can omit the copper write and falsely report zero frames. STATE_ONLY skips
tracing and fps reporting; FIELDS=1 captures cannot establish fps either. The
historical three-field baseline was `w5-repeat-a/b`, 5.6 fps each.


## Rendering checks (W6)

CUSTOM2 is now a v1 bitfield: bit 0 keeps the W5 simulation, bit 1 suppresses
unused blitter-finished interrupts. Compare CUSTOM2=1 against CUSTOM2=3 in the
**same build**, with CUSTOM3=1 and no CUSTOM5 fixture for fps. The shipping
rendering option changes no game code, wait, ownership call or beam wait.

The VERIFY shape twin (CUSTOM5=9, `check_draw.py`) validated the rendering
experiments that changed game code. Shipping rendering changes no game code, so
the twin was removed; it remains in git history.

For candidate costs, inspect individual instructions rather than treating every
region attributed to an earlier unframed routine as that routine. The actual
clear kernel is duel:086c0..08768; its two bulk MOVEMs are 08746/0874a. The
span interior is 07928..0793a. Projection angle accumulators are read/written at
073fc/07400/0742a/0742e. Their cycle totals can be summed from `barto.instructions`
or inspected with `hotspots.py`. These are cost bounds, never fps comparisons.

## One-field refinement

The current optional mode updates once per PAL field (50 Hz). Historical
three-field captures need `check_timing.py --period 3`. `STATE_ONLY=1` skips
profiling, screenshots and fps reporting after the requested STATE_FIELDS; use
it for long state comparisons. Normal fixed-window runs remain the only fps
instrument. `compare_state.py --assert-core` checks all 35 gameplay variables;
`--start` is only for an individually explained initial transaction sample.
VERIFY CUSTOM5=17 accelerates, brakes, coasts and restarts without steering; it
will leave a curved road. Evaluate normal attract driving with CUSTOM5 off.
An updated slave can move the loaded hunk to another allocation page; calibrate
again or supply a verified BOOT_HUNK. The harness checks the supplied address.


## A1200 and 68030 configuration studies

`AMIGA_MODEL` selects the FS-UAE model in `amiga/run.sh` (default A500).
Set `CPU` explicitly when selecting another model; its default remains 68000.
The calibration key includes the model and host Kickstart path. Each completed
capture retains the effective emulator configuration in `fsuae.log` and stdout
in `fsuae-stdout.log`. Emulator files/logs use a project-local base directory,
so other projects' emulators cannot overwrite this evidence.

For the expanded A1200 tested here:

```sh
source amiga/env.sh
export AMIGA_MODEL=A1200 CPU=68EC020 CHIP_KB=2048 FAST_KB=4096
export KICKSTART="/path/to/kickstarts/kick40068.A1200"
export EXTRA_ARGS='--slow_memory=0' WHD_ARGS='CUSTOM2=3'
export SLAVE="$PWD/whdload/TestDrive2.slave"
STATE_FIELDS=6000 STATE_ONLY=1 tools/fixed_window.sh tmp/prof/a1200-state "$SLAVE"
tools/fixed_window.sh tmp/prof/a1200-fps-a "$SLAVE"
tools/fixed_window.sh tmp/prof/a1200-fps-b "$SLAVE"
```

For the 25 MHz 68030 configuration, retain that model/ROM/RAM and change:

```sh
export CPU=68030
export EXTRA_ARGS='--slow_memory=0 --uae_cpu_speed=real --uae_cpu_multiplier=0 --uae_cpu_frequency=25000000 --uae_cpu_cycle_exact=true'
```

This is an accelerated A1200 configuration, not an A4000 hardware claim.
No A4000 host ROM was available locally. Verify the retained log's effective
CPU, frequency and timing mode before interpreting FPS as a hardware estimate.
Use state-only captures for timing/physics comparisons and separate 100-field
windows, with no preceding state samples, for rendering comparisons.


This FS-UAE binary's 68030 backend emits **zero CPU instruction bytes** in a
100-field trace (`030-fps-a`); it cannot supply the usual COP1LC instruction
count or polling percentages. `frames.py` now rejects such a trace explicitly.
Use `SWAP_ONLY=1 tools/fixed_window.sh ...` for these CPUs. This retains the
same calibration, fresh-boot race anchor and field window, but calls
`swap_fields.py`: read-only breakpoints at the slave's COP1LC write and
`duel:0231c` count swaps over 100 complete PAL fields. Only debugger convenience
variables are modified. It retains `swaps-gdb.txt`, `frames.txt`, the exact slave,
code dump and effective configuration log; it does not claim cycle costs or
trace screenshots.

The `a1200-swaps` validation gives the **exact same 100-field swap pattern**
and 30 frames over 93 fields / 16.1 fps as both ordinary A1200 cycle traces.
This independently validates the field boundaries and FPS calculation before
using the alternate instrument on the 68030. FPS comparisons still run only
through `fixed_window.sh`; the state study remains a separate capture.

The completed 25 MHz 68030 runs are `030-state` (6,000 fields, all 35 gameplay
variables exact against the 68000; elapsed-clock and recovery checks pass) and
`030-swaps-a/b` (both 49 frames over 98 fields = 25.0 fps, identical swap
patterns). The A1200 ordinary trace repeats are 16.1 / 16.1 fps. All use
CUSTOM2=3 and normal shipping slave hash
`ac3d955a3639a5c12b2a49fa8f624272335431d2b766e7a3eea14cd34193aed8`.


## Sub-unit rendering capture (2026-10-05)

Enhanced framerate (CUSTOM2=1, any nonzero value) includes fractional road/car
projection and sideways smoothing in duel v1. The historical 3/7 FPS comparison
below predates the boolean option. Those values now enable identical features.
For new FPS comparisons use distinct retained slave builds and two fresh normal
100-field fixed windows per arm. Use SWAP_ONLY=1 on A1200/68030; BLTPRI corrupts
A1200 CPU trace records.

`RENDER_FRAMES=90 STATE_ONLY=1 tools/fixed_window.sh OUT "$SLAVE"` collects
completed main and mirror geometry, full row records, scanline buffers and car
draw coordinates through read-only breakpoints. It writes ignored OUT/render;
it does not measure FPS. STATE_FIELDS can precede this capture to select a
later interval. The current sub-unit slave is required in both arms.

VERIFY CUSTOM5 bit 3 (`CUSTOM5=8`) forces road/car fractions to zero and clears
the 117-line scanline buffer before each view, **in both arms**. Compare
CUSTOM2=0 CUSTOM3=1 CUSTOM5=8 with CUSTOM2=1 CUSTOM3=1 CUSTOM5=8. Different
render cadences retain different unused scanline history in the original;
matching completed views with identical inputs and initial buffers is the
valid whole-buffer oracle. Interrupted VBL snapshots are not completed rows.
`subunit_report.py OFF/render ON/render ZERO/render BASE/render --initialised`
checks every row byte and all 117×16 scanline bytes for matched inputs. It also
writes per-frame road/colour-boundary CSVs. Use `--check-cars` on later demo
captures covering the opponent and both traffic directions to check actual
x/y draw registers and a constant-gap flat-road geometry fixture. A natural
police chase remains unrecorded; do not claim one from the traffic list.

There are 127 assembly assertions in the VERIFY build (107 simulation, 12
rendering bounds/fraction checks, 2 turned-camera straight-segment seeds and
6 tangent-cache checks). Historical captures retain their own count markers.
`check_disabled.py --render-only` checks the nine sub-unit ranges with CUSTOM2=0.
The full disabled check covers 76 ranges with CUSTOM2=0 and
CUSTOM5 bit 0 off (e.g. CUSTOM5=16 to run assertions without scripted input).
The input instrument deliberately patches two simulation entries.
`subunit_geometry.py ORIGINAL/render SUBUNIT/render` validates the independent
geometry model against completed rows before measuring held-input world-boundary
continuity. It reads captured tables/track from ignored assets.bin, with no
game bytes embedded in the tool.


### Sideways capture and cost checks

Sideways work uses the ignored `tmp/horiz/tools/fw.sh` and `hcap.py` to capture
completed main rows at 06c74 and backdrop d2 plus inputs at 08c9e. The recovery
variant also captures VBL state. `RW` records contain field, drawn heading/lane
and raw heading/lane; compare those values during lane changes, not screenshots
or individual road-row indices. `BD` records permit counting pixel steps and
nonzero-step direction reversals. Compare steering captures over the same field
prefix. The scratch scripts and retained slave builds remain in tmp/horiz.

Run a normal CPU=68000 100-field `tools/fixed_window.sh` window and then
`python3 tools/subunit_cost.py OUT`. Repeat with STATE_FIELDS=1000 for the moving
window. The cost includes all helpers, nine calls and PL_PSS NOPs; malformed
traces are rejected and the 3% budget is enforced. These cost checks do not
establish an FPS improvement. Final provenance is in subunit-rendering.md.
