# Reproducible action flight (plan step 2)

Tool: `tools/replay_flight.py`; input tape: `tools/flight.tape.json`.
Commands below run from the game directory (`games/TFX`); output paths are relative to it.

```
tools/build.sh
python3 tools/replay_flight.py --clock-relative --output tmp/step2-validation
```

Each output directory must be new. The default is two cold boots on each of 040,
020, 030+68882 and 060. `--machines 040` selects a subset. `--runs 1` is a probe,
not a reproducibility pass. The debugger requires local socket access; run outside
an execution sandbox that denies that access. Do not run two captures concurrently
in this worktree. The shared launcher owns the emulator PID and debugger port.

## Method

Use the native FS-UAE from `FSUAE` (default shared `FSUAE_ARM` installation), PAL,
AGA, Kickstart 3.1, WHDLoad 20.1, JIT off, deterministic mode and warp. Disable both
host input ports, including their modes. Use the rebuilt slave and both rebuilt
FPSP files. CUSTOM4=18 selects skip-intro plus action mode. FPU machines run
CUSTOM3=3 (`tfx.020`); the no-FPU 020 regression runs CUSTOM3=0 (integer `TFX`).

The 040 explicitly uses 40 MHz, its integrated FPU and MMU, enabled data cache,
2 MB chip and 32 MB Z3 fast memory, with the preset's extra 8 MB Z2 RAM removed.
This is an emulator approximation of Apollo RAM, not its physical bus timing.
The 030 explicitly adds the 68882 absent from the shared preset. The 020 is a full
68020 so that the common 32 MB Z3 fixture is addressable. The 060 keeps its preset
50 MHz clock, integrated FPU and MMU. Actual generated settings are retained per
run in `debug.uae`. No hardware-performance conclusions follow from these runs.

The run (`game.sh`) supports HDF=1: it packs disposable boot and game directory copies
as FFS hardfiles using the shared `xdftool`. HDF_SEED holds the two pristine images
saved **before** boot; every repetition copies those same bytes to writable runtime
images. Seeds are scoped to the new output directory and CPU, because the WHDLoad
startup command differs for the integer build. Never reuse a seed after changing
the slave, FPSP, game, or startup command. Original extracted game files are never
mounted writable. All images and copyrighted input bytes remain ignored locally.

After 1500 complete fields (plus the initial partial field), the game waits
at enrolment. The tape enters neutral pilot names A/B/C, pressing Return between
fields. Action mode then starts the flight. Before the final Return, the tool
locates the live executable by relocation-free instruction signatures AND validates
its LoadSeg BPTR chain and allocation headers; archive/PRELOAD copies are rejected.

The anchor is the patched `@PlayLevel` swap call: `tfx.020:$019fc`, integer
`TFX:$018a6`. The first hit is flight checkpoint 1. Right joystick is pressed at
hit 10 and released at hit 20; checkpoints are 1, 10, 20 and 30. This visibly banks
the aircraft. Inputs are gdb-stub `monitor key` / `monitor input` events, not debugger
memory writes or host GUI events. Every breakpoint stop checks the live PC.

At each checkpoint, capture every complete allocated game hunk (including the
integer build's enlarged allocation), registers, and a one-field trace containing
the screenshot. A screenshot advances emulated time; it is part of the tape, so
never add an extra screenshot while replaying. The checkpoint ordinal is a count
of stops at the swap call, not yet an independently validated display-frame counter.
Step 3 must validate that distinction and the effect of capture fields.

The manifest records all hunk and PNG SHA-256 hashes plus emulator/slave identities.
The default paired check requires raw equality of every hunk and PNG at all four
checkpoints and exits nonzero on failure. `--clock-relative` explicitly accepts
the separately reported clock-origin comparison described below; raw results
remain in the report. `tools/compare_flight.py RUN_A RUN_B` rechecks retained bytes
and manifest hashes without launching an emulator.
It compares runs **within** each configuration, not pixel equality between different
CPU/executable configurations. Register dumps and full trace bytes are retained as
evidence but are not part of the pass predicate. Host/OS RAM is deliberately not
misrepresented as game state.

## Pitfalls found

- DETERMINISTIC=1 plus `uae_uaeboard=full+indirect` and directory drives deadlocks
  during boot in `filesys_iteration -> trap_get_bytes -> call_hardware_trap_back`.
  Native process sampling identified this before any game patch. Disk images avoid
  that path while retaining CPU caches. Disabling deterministic mode also boots,
  but is not the accepted replay method. Do not silently disable caches to fix it.
- Action mode still needs enrolment when there is no saved pilot. A blank install
  cannot boot directly to the cockpit without these three name/Return entries.
- The native debugger's registers stay cached after `monitor fields`; use
  `maintenance flush register-cache` before reading the PC/registers.
- `monitor profile` paths are relative to the emulator, whereas gdb memory-dump
  paths are relative to the harness. Pass absolute trace paths.
- Match live allocation sizes, not just file hunk lengths: the integer slave
  enlarges its final allocation for rendering data.
- Never ignore `Protocol error with Rcmd` or reuse an old screenshot on failure.
- A breakpoint at `tfx.020:$3f99e` is not the default-renderer anchor: shared
  `do_swap_screen` bypasses `@ThreeScreenSwap` when CUSTOM4 bit 2 is clear. That
  path calls `_SetPage` and `_SetLogbase` itself. The original-rendering path calls
  `@ThreeScreenSwap`.

## Validated counter

Step 3 is complete; see `frame-counter.md` for reproduction and evidence. The actual
publication instruction is tfx.020:$4c474, the COP1LC write in SetPage. Count vblank
increment hits at $4d2de alongside it. The $019fc request anchor used for step-2
checkpoints can precede publication by a vblank, so retain its name as a swap-call
checkpoint rather than using it for presentation timing. The step-3 validation
uses a neutral prefix without checkpoint screenshots; the original tape is unchanged.

The local trace emulator records the 040 MMU instruction stream, including Z3 code.
Its zero-cost dispatch records validate counts/order only, not instruction timing.
The unchanged shared emulator still lacks these records.

## Captured results and accepted exit

2026-10-20, two cold boots per configuration, checkpoints 1/10/20/30:

| Machine | Evidence under `tmp/` | PNG equality | Raw hunk equality | Clock-relative hunk equality |
|---|---|---|---|---|
| 040 / tfx.020 | `step2-040/040-{1,2}` | all 4 | all 12 | all 12 |
| 020 / TFX | `step2-regressions/020-{1,2}` | all 4 | five timer values differ | all 24 |
| 030 + 68882 / tfx.020 | `step2-regressions/030-{1,2}` | all 4 | five timer values differ | all 12 |
| 060 / tfx.020 | `step2-regressions/060-{1,2}` | all 4 | all 12 | all 12 |

The 020 and 030 second boots have an absolute clock origin one vblank later.
The difference stays constant throughout the window. It changes five longwords,
not aircraft position, orientation, enemies, buffers or any other captured byte.
The user accepted this specific clock-origin mismatch on 2026-10-20, completing
step 2. Use `--clock-relative` for the accepted baseline. No source patches or memory
writes were made to force a match. Raw byte identity is still false on 020/030;
retain that result alongside clock-relative equality. Acceptance does not cover
other state differences or replace step 3's independent counter/trace validation.

`compare_flight.py` subtracts the first checkpoint's vblank count (modulo 2^32)
from exactly these five 32-bit values, then compares every byte of every hunk:

| Build | Hunk | Timer offsets |
|---|---|---|
| TFX | code 0 | $4bba6, $4bbd0 |
| TFX | data 5 | $57bc, $9a74, $befe |
| tfx.020 | code 0 | $4d85a, $4d884 |
| tfx.020 | data 1 | $10678, $13de0, $17012 |

This is a translation of time origin, not a byte mask or per-checkpoint reset;
all elapsed intervals and changes from checkpoint to checkpoint remain tested.
The code counters increment in the vblank handler. Disassembly confirms the cached
timers are copied/subtracted in TFX:$3868/$387c/$3880 and $42cc4/$42cd6/$42cf0,
and tfx.020:$3c10/$3c26/$3c2a and $4397a/$43990/$43994. The cached current-time
globals are A4+$1a74 (TFX) and A4+$f34 (tfx.020).

An additional two-boot experiment (`step2-clock020`) waited at the instruction
immediately after the game's clock increment until the clock was exactly 2000,
before typing any names. Both stops verified the PC and clock value. This did not
remove the transition's one-vblank offset: raw state still differed, while translated
state matched at every checkpoint. That unsuccessful clock wait is not in the final
tape. Investigating keyboard/CIA phase and loading remains optional following the
user's acceptance. Avoid repeatedly rerunning until two clocks happen to match.
