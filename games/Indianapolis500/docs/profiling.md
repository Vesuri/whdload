# Building, running and measuring

> Read this before running, driving or tracing the game, or quoting any performance number.
> Commands run in `games/Indianapolis500`; the shared workflow is the repository's
> `docs/building.md` and `docs/running.md`. It follows AmigaXDev
> `docs/playbooks/new-game-playbook-stingray.md`: macOS, x86_64 FS-UAE with the Barto gdb stub,
> and the `m68k-amiga-elf` toolchain from the shared environment.

## Host files

`make unpack ARCHIVES=<directory>` checks and unpacks the two pinned archives
(`inputs.sha256`) from `tmp/archives/`: StingRay's installer `Indianapolis500.lha` (to
`tmp/game/Indianapolis500_Install`) and the preinstalled `Indianapolis500_v3.0_0686.lha` (to
`tmp/game/Indianapolis500`, the pristine installed drawer every boot copies). Shared Amiga files
(Kickstarts, WHDLoad, the Workbench floppy, `fsuae_common.sh`, vasm, the NDK) come from the shared
environment AmigaXDev installs (`../../common/env.sh`, AmigaXDev `docs/environment.md`).

Screenshots and every capture go to the ignored `tmp/` (FS-UAE's to `tmp/shots`).

## Build

```sh
make slave                          # release: tmp/build/release/Indianapolis500.Slave
make verify                         # VERIFY: pixel/register twins, guarded shadow bitmap
make build BUILD=race               # -DDRIVING_TEST=2: native menu -> Race, accelerator held
make build BUILD=practice           # -DDRIVING_TEST=1: Practice
make build BUILD=race_verify        # VERIFY and DRIVING_TEST=2 (driving pixel twins)
make build BUILD=timing             # -DTIMING=1: private CIA elapsed samples for timing_frames.py
make build BUILD=soft               # -DDRIVING_TEST=2 -DSOFT_TIMING=1: CIA stamps in each SOFT
make build BUILD=replay             # -DDRIVING_TEST=2 -DDRIVING_REPLAY=600 (DRIVING_REPLAY=n)
make build BUILD=nomotion VASM_EXTRA=-DNO_MOTION=1
```

Each build writes `tmp/build/<BUILD>/Indianapolis500.Slave` (`game.conf` holds the defines) and
always assembles, so a define never leaves a stale build. `fixed_window.sh` keeps its own copy
of the slave it ran. VERIFY, TIMING, SOFT_TIMING and DRIVING_TEST builds are diagnostics.
`-DNO_MOTION=1` (tick wait removed, no interpolation) and `-DNO_ASYNC_CLEAR=1` isolate features
(`VASM_EXTRA`, under any new `BUILD` name). The cross-build of the unmodified source differs
from StingRay's in two harmless encoding words: vasm uses `cmp` instead of `cmpi` and pads the
hunk with `nop` instead of `$5678`. The options are `-m68000 -pic -x -devpac -Fhunkexe -nosym`
with the shared WHDLoad `Include/` on the include path (the slave includes only `WHDLoad.i`).
The upstream source has no build file; StingRay assembles it with ASM-One/BASM through
`SOURCES:` assigns. `make check` confirms the release build still gives
`release/slaves.sha256`.

## Run

```sh
make run WHD_ARGS='CUSTOM1=1 CACHE DCACHE' CPU=68030
make run SLAVE=original                    # the installed v3.0 slave
make run BUILD=race                        # a diagnostic build
WHD_DEFAULTS='PRELOAD SPLASHDELAY=-1' make run   # show the splash window and wait for Start
```

`common/run.sh` boots Kickstart 3.1 from DH0 without a floppy (`WB=0` in `game.conf`); the
startup-sequence runs `WHDLoad Indianapolis500.Slave PRELOAD SPLASHDELAY=0 NOREQ` on DH1, a fresh
copy of the install plus WHDLoad. The slave is direct (no OS): no Kickstart image is needed
inside WHDLoad. `WB=1` inserts the Workbench 2.04 floppy, which moves the load address, so
load addresses, calibrations and demo courses from such captures are not comparable with the
default ones. Compare only captures made the same way.

| Variable | `make run` default | fixed_window.sh default | Meaning |
|---|---|---|---|
| `CPU`, `AMIGA_MODEL` | 68000, A500 | same | `AMIGA_MODEL` does not choose CPU, RAM or ROM (`SETUP=custom`) |
| `CHIP_KB` / `FAST_KB` / `SLOW_KB` | 1024 / 2048 / 512 | 512 / 0 / (EXTRA_ARGS) | fast RAM at `$200000` |
| `EXTRA_ARGS` | — | `--slow_memory=1536` | extra FS-UAE options (they beat every other setting) |
| `JOY0` | `mouse` | `none` | port 0; `none` also sets the port mode to nothing, so a host mouse cannot inject input |
| `SLAVE` | the release build | — | `original` or a slave file (copied in) |
| `WHD_ARGS` | — | — | WHDLoad options, e.g. `CUSTOM1=1 DCACHE` |
| `WARP`, `SILENT`, `DEBUG`, `DETERMINISTIC`, `RECORD`, `INSTANCE` | | | the shared launcher's (`docs/running.md`) |
| `SOUND`, `WINDOW` | 1, `front`; 0, `back` with `DEBUG` or `WARP` | | audio; window in front, behind the others, or `none` (no video) |

`python3 tools/i500.py serve` boots the same way with `DEBUG=1` (`common/tools/game_server.py`);
the run directory is `tmp/run/<INSTANCE or default>/.run`. `profile_demo.sh` runs the installed
slave unless `SLAVE` is given; `fixed_window.sh` takes the slave as its second argument (default
the installed one).

**Machine settings.** Use these exactly; changing an option makes results incomparable.

- **A500:** the fixed_window.sh defaults (512K chip + 1.5M slow RAM). Hunk 0 loads in slow RAM,
  which is as contended as chip RAM.
- **68030/25 (A1200):**
  ```sh
  CPU=68030 AMIGA_MODEL=A1200 CHIP_KB=2048 FAST_KB=4096 \
  KICKSTART=$AMIGA_SHARE/Kickstarts/kick40068.A1200 \
  EXTRA_ARGS='--slow_memory=0 --uae_cpu_speed=real --uae_cpu_multiplier=0 --uae_cpu_frequency=25000000 --uae_cpu_cycle_exact=true'
  ```
  `--cpu_frequency` and `--cpu_cycle_exact` are ignored; use the `uae_` names. Leaving out
  `cpu_speed=real` or `cpu_multiplier=0` gives different results.
- **68020 (A1200):** `CPU=68EC020` with the same RAM and ROM, `--slow_memory=0`, cycle-exact.
- **Stock A1200:** `FAST_KB=0` and `--slow_memory=0`, so the game runs from chip RAM.
- **68040:** `CPU=68040-NOMMU` with the 68030 options and the frequency changed.
  - Plain `68040` emulates the MMU, and WHDLoad turns it on. FS-UAE's MMU loop then ignores the
    frequency and the chip timing.
  - `cycle_exact=false` with `cpu_compatible=false` has the same problem (the generic loop).
  - Sanity check: an 8 MHz run must be slower (22.2/33.8 fps in directors 200/650).
  - An A4000 model with the default 68000 fails ("Z3 autoconfig…"); the shared folder has no
    A4000 ROM.
- **Caches:** add `DCACHE` (or `CACHE`) to `WHD_ARGS`. Without it a 68020/68030 runs with every
  cache off.
- **Max speed** (`cpu_speed=max`, `cycle_exact=false`, `cpu_compatible=false`) is not a real
  machine: chip accesses are nearly free.

## Measure

```sh
SWAP_ONLY=1 FIELDS=100 DEMO_TICKS="opening 50 200 350 500 650 800" tools/fixed_window.sh tmp/prof/x SLAVE
tools/fixed_window.sh tmp/prof/base SLAVE        # cycle trace of 100 fields from the demo's first frame
tools/profile_demo.sh                            # quick unanchored demo trace
```

- **Anchor.** `fixed_window.sh` boots once to find hunk 0, which is cached in
  `tmp/cache/hunk-*.txt` by machine, arguments and slave. It then reboots with a breakpoint at
  the first `game:0b57e` (the end of the demo's first frame) and captures from there.
  - `SKIP_FRAMES=N` moves the window N frames later; `DEMO_TICK`/`DEMO_TICKS` select director
    windows in one boot; `ANCHOR=` changes the offset.
  - The output folder gets `slave.slave` (the exact slave used), `code.bin`, `frames.txt`, the
    logs and, for traces, `trace.bin`.
- **FPS:** `SWAP_ONLY=1` counts swaps at `game:0b2e2` (after the VERTB acknowledge) with
  read-only breakpoints, on any CPU. It agrees with the trace-based `frames.py`. Cycle-exact
  68030 traces have no usable instruction records; use `SWAP_ONLY` there.
- **Where the time goes** (68000/68020 traces):
  - `i500_report.py TRACE DUMP --base B` names every region;
  - `python3 -m amigaxdev.disasm hotspots --label game` (AmigaXDev's shared tools, under
    `. ../../common/env.sh`) lists the hottest instructions (`--label slave` with the live slave's base);
  - `blit_waits.py` gives BBUSY polling per routine;
  - `soft_cost.py` gives the cost per simulation tick from a trace. On any CPU, including
    cycle-exact 68030/040, use a SOFT_TIMING build with motion on and `SOFT_TICKS=256`
    (`soft_timing.py`). It splits each SOFT into input, player physics, publication, field
    update and the rest. In driving, use it with `ANCHOR=0x270 DRIVING_TICK=240`;
  - `render_inputs.py` lists what the frame code reads from SOFT.

  Manual runs need `SLAVE=<capture>/slave.slave` to find the live slave. Interrupts share one
  stack, so `[top] ->` edges and SOFT work that appears under other routines are not real calls.
  `amigaxdev.disasm disd` and `hotspots` take hunk 0's base as `HUNKBASE` and print offsets
  from it.
- **Gameplay state:**
  - `STATE_AT=soft STATE_ONLY=1 STATE_FIELDS=1010` snapshots hunk 0 and BSS hunks 1, 2 and 5
    at each SOFT entry.
  - `compare_state.py --simulation` compares two captures; use `--align-director` in the demo
    and `--driving` in races.
  - Align by simulation tick: the frame anchor reaches the first demo frame at a different tick
    when frame timing changes.
  - BSS hunks 1 and 2 hold renderer workspaces and differ legitimately.
- **Pixel twins** (VERIFY build): `WHD_ARGS='CUSTOM1=7 CUSTOM3=N' PIXEL_FRAMES=1000
  PIXEL_VIEWS=N`, one fixture per boot. `pixel_frames.py` checks the selector, active flag and
  director in every batch. For driving, use a VERIFY DRIVING_TEST build with `PIXEL_DRIVING=2`
  and no CUSTOM3. The VERIFY slave loads at a different address, so it needs its own calibration.
- **Motion:** `MOTION_FRAMES=100` (`motion_frames.py`) checks every rewritten camera word, car pose
  and distance bias against the formula for its snapshot (interpolated, or extrapolated and
  predicted in the cockpit); `MOTION_SHOTS=4` keeps screenshots. Use `MOTION_PATH=cockpit` for
  driving. It counts predicted and extrapolated opponent poses, poses that moved since the
  previous tick, and native car poses (built just before the hook) that differ from the latest
  snapshot. That last count must be about 0: it is how a snapshot of the wrong state shows.
- **Driving:** use a DRIVING_TEST build with `ANCHOR=0x270`. `DRIVING_TICK=240` waits for a
  cockpit frame at or after fixture CIA tick 240. `DRIVING_FRAMES=100` (`driving_frames.py`)
  records whether frames within one tick actually move; FPS alone can hide repeated frames. The
  held-accelerator fixture is a test scenario, not a full lap. Demo FPS does not show how smooth
  driving is.
- **Instant replay:** `make build BUILD=replay` races for
  600 fixture CIA ticks, then posts Esc through the race's key dispatcher and picks Instant
  Replay in the menu. Capture with `ANCHOR=0x270 DRIVING_TICK=1300 DRIVING_BREAK=0x26d4c` (the
  wait then stops at an external-view frame) and `MOTION_FRAMES=100` without `MOTION_PATH`.
  `WIPE_TICKS=1` first measures the first transition wipe after the request (ticks 1212–1274 on
  the 68040/25) in fixture CIA ticks. Never raise the menu request from an interrupt: the
  original game then deadlocks (game.md).
- **Ad hoc:** `HOLD=1` stops at the window start and leaves the emulator to
  `tools/i500.py gdb '...'`; end with `tools/i500.py quit`.
- **Frame time:** a TIMING build with `TIMING_FRAMES=30` (`timing_frames.py`) measures
  `game:26d4c` to `game:0b574` in director 200. It is not FPS.
- **Hooks:** `audit_hooks.py` (instruction boundaries, direct branches into hooks) and
  `check_disabled.py CAPTURE` (with the option off, the optional ranges are original).

## Reproducibility and traps

- Two fresh boots of the same window give byte-identical instruction and DMA records,
  screenshots and state.
  - Run captures with `JOY0=none`: `game:0b424` reads the port-0 mouse counters.
  - The trace's slow-RAM snapshot differs in 164 WHDLoad bytes, so compare fields with `barto`,
    never whole files.
- **The gdb stub ignores memory writes silently.** Never select fixtures, reset counters or
  claim coverage through gdb writes; select fixtures at boot with `CUSTOMn`.
- The stub is read-only:
  - attach within 20 s;
  - emulated time stops while gdb holds the CPU;
  - screenshots come only from traces;
  - at most 100 fields per `monitor profile`.

  `i500.py` is AmigaXDev's shared gdb server (`amigaxdev.gdbserve`). Each lldb attach to the
  Rosetta process takes about 30 s; it attaches once, at the first capture, and stays attached. `until` blocks until its breakpoint is hit; if it never is, kill our emulator by
  its pid file (`tmp/run/<instance>/.run/fsuae.pid`; `make stop`), never by name. Hardware watchpoints did not fire; use
  counted breakpoints.
- **Run captures one at a time:** parallel `fixed_window.sh` runs collide on the debugger socket.
  Don't edit a shell harness while it runs.
- The live slave is not the first slave-shaped bytes in memory: WHDLoad rewrites header bytes,
  and its `resload` long at hunk offset `$a0` is non-zero. `regions()` handles this.
- Hunk-0 recognition requires the tick load at `game:26d24` to reference this candidate's
  `game:09832`. A looser matcher once found a false hunk before the game had loaded. The check
  must use code no patch replaces: the motion hook at `game:00152` broke the earlier one.
- Delete stale `tmp/cache/hunk-*.txt` entries if calibration fails after a change.

## Release

`make dist` builds the release slave and runs `tools/package_release.py` (game.sh `game_dist`):
the SPS 0686 installed archive with `Indianapolis500/Indianapolis500.Slave` and
`Indianapolis500/ReadMe` (`release/ReadMe`) replaced, stored, dated by the slave's version
date, every other member copied byte for byte, written to the repository's
`dist/Indianapolis500_v<version>_0686.lha` with its `.sha256`. It refuses a slave with
instrument magics (`I5PV`, `I5DR`, `I5TM`) or a ReadMe without the version's history entry.
StingRay's installer archive is not repacked.
