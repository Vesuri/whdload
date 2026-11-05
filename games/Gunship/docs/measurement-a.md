# Measurement base (plan A — complete)

Authoritative code: `src/GunshipHD.s` plus `verify.i`.
Build in the game directory with `make slave`; `make verify` builds the
separate diagnostic slave. Outputs and assembler listings stay in `tmp/build/`.
The normal slave retains interface 16 and version 1.2. All new instruments and
CUSTOM2 handling are excluded from it. No performance patches are enabled.

## Rebuild comparison (A1)

`tools/check_rebuild.py` checks all 119 pristine installer/preinstalled files and
accounts for the 232-byte difference from the shipped slave:

- 160 fewer bytes in the shared KickEmu/SDK prefix. The rebuild uses the installed
  WHDLoad SDK, whose KickEmu includes changes after the shipped February 2020 build
  (filesystem/control/cache-support changes). This is a dependency update, not a
  game optimization or a byte-identical rebuild of the old SDK.
- 72 fewer bytes from removing three 24-byte build date strings.
- The entire remaining 780-byte game-specific code and patch-list tail is identical
  after resolving twelve PC-relative operands to their corresponding SDK/string
  symbols. The checker validates those target addresses and rejects any other
  differences; it does not merely omit differing bytes.

Both shipped and rebuilt slaves boot and reach flight using the existing route.
Their uncontrolled flight captures differ because timing feeds mission generation.
They must not be advertised as fixed-window state-equivalent. The exact source
patches and instruction bodies are unchanged; the newly controlled diagnostic
baseline is measured independently.

## Deterministic mission (A2)

Use the VERIFY slave with `WHD_ARGS=CUSTOM2=1`. CUSTOM2 is the nonzero seed;
zero applies none of the instruments or deterministic patches. Currently only
0658 is instrumented. Other versions cannot produce a valid diagnostic marker.

The menu RNG at scrnmule:+0250 is a right-shifting LFSR with feedback $B40C0000,
seed at +024C. It mixes two input-counter longs on every call and folds the
range-reduction quotient back into the state. Its VBL audio caller (+0312E) also
consumes the sequence. The diagnostic replacement preserves the LFSR and range
reduction, removes input-counter entropy, and gives that audio caller its own
state. Thus changing the time spent in menus cannot consume mission randomness.
The game RNG at gamemule:+07A6A uses feedback $94820000, seed h4:+03CC, and similar
input-counter entropy. It is initialized from CUSTOM2 and its two entropy XORs
are disabled. The separate flight-audio RNG at +04B1C remains untouched.

The mission header through +0093 matches byte-for-byte on all five CPU setups.
An extra 137-field menu dwell leaves it unchanged; seed 2 changes the mission.
Results: `tmp/a-final/mission-identity.json`.
Its following pointers relocate normally and are not mission identity fields.

## Instruments (A4/A5)

The live `GSVFY001` marker publishes nine game hunk bases, completed-swap count,
tick-entry count, overflow count, the tick-checkpoint PC, log address and capacity.
A zero-filled PRELOAD copy may also exist; the reader requires one initialized
live marker rather than taking the first byte match.

Tick snapshots stop at `verify_tick_ready`, after replaying the LEA displaced at
+0563A and before the next increment. The preceding tick's AI/weapon work has
completed. Entry one has no completed predecessor. The snapshot reader preserves
hunks 0, 2, 4, 5 and 6, the mission header, alive flags, and (in current runs) the
entire fast-RAM image to retain pointer-backed allocations. Debugger access is
read-only. Use `tools/compare_states.py LEFT RIGHT` as the regression gate for
changes in C; it returns nonzero on differences. It intentionally does not hide
unexplained clocks, RNG or pointer differences across CPUs. Cross-CPU simulation
equality is a C acceptance test, not a claim about the currently coupled game.

Two independent 68000 boots at ticks 100, 101 and 102 have byte-identical entire
8 MiB fast-RAM captures, including all pointer-backed allocations. The strict
hunk/mission/alive comparisons also pass. Adjacent ticks differ, including player
data after excluding the tick counter (`tmp/a-final/repeatability-*.json`,
`negative-control.json`). Use `--whole-ram` for the strongest same-machine gate.

The frame hook at +044CA runs after the OS swap and back-buffer toggle. Each
8-byte row stores VBL (long), simulation tick (word), buffer index (word).
The 8192-row log stops when full and increments an overflow counter; the host
rejects overflow. All 128 combinations of initial CCR flags and count boundary/
overflow cases pass the assembled-code test, including registers, stack, X flag
and guard bytes. The hook replays the displaced clear. It is excluded from
normal builds and active only with a nonzero diagnostic seed.

## Measurement contract and current matrix

`monitor fields N` advances N+1 fields in the pinned emulator; a Barto capture of
N fields also advances one unrecorded lead-in field. The original 24-chunk
"500-field" route therefore actually advanced 524 fields. Current measurements
request N-1 per chunk and assert exactly 500 elapsed game VBLs. Barto records 476
fields within that window, separated by the 24 lead-ins: its cycle percentages
are sampled, not a continuous 500-field trace. Completed-frame counts and pacing
come from the continuous slave log; aprof covers the entire window on 020+.

The retained take-off inputs remain F1 ten times, four fields down/six up, then
400 fields. The setup still uses the original route. This controls mission and
input timing but does not claim matched simulation ticks across CPUs before C.

| CPU | Completed fps | ticks/s | BBUSY | level-3 | swap incl wait |
|---|---:|---:|---:|---:|---:|
| 68000 | 5.1 | 2.5 | 21.39% sampled | not attributed | not attributed |
| 68020/14 | 10.5 | 5.3 | 44.1% | 16.7% | 14.6% |
| 68030/50 | 10.9 | 5.5 | 45.6% | 15.5% | 14.6% |
| 68040/25 | 15.3 | 7.6 | 66.3% | 5.4% | 13.4% |
| 68060/50 | 15.3 | 7.6 | 66.3% | 5.4% | 13.4% |

Completed swap counts agree with instruction counts at +044CA (51/105/109/153/153).
The older report's +04496 counts swap starts; on the 020 this differs by one at
the window boundary. Use completed swaps for the fps figure above.

Final captures: `tmp/a-final/matrix/`; command: `bash tools/final_matrix_a.sh`
from the harness root. Earlier exploratory captures remain under `tmp/a2/`.
During these captures another task migrated the shared harness API. `session_a.py`
retains the older mouse/button protocol and fs-uae-mouse/aprof-mouse selections
for reproducibility without reverting that task's changes to `gunship.py`.

## Benchmark scenes (A3)

Take-off is retained as above. Hover first performs take-off, reduces collective
from 40 to 37 using three F3 taps, and settles for 300 fields before its 500-field
window. The 68060 hover retained X/Y and altitude (235 internal units), zero
forward speed and level pitch throughout its endpoints; 167 completed frames,
16.7 fps. Evidence: `tmp/a3/hover-060/`.

The combat window uses `CUSTOM2=1 CUSTOM3=1`. At completed tick 100, the VERIFY
fixture places the player at map ($B000,$3E00), altitude 48, level heading north,
collective 37, and moves the existing helicopter in slot 5 to ($B000,$4000).
Its type and AI remain intact. This is an authored diagnostic starting position,
not a recorded natural flight route. After tick 104 the runner selects the cannon
and fires ten bursts (10 fields down, 40 up), totaling 500 fields. Normal input
and simulation run throughout the measured window.

`audit_scene.py` observes the military-shape screen-bounds gate at +0A494.
At tick 105, ground objects 2/1/0 in cells 75/91/108 are simultaneously in view;
the helicopter is the special object -1/shape -2 and is also in view. The game
also displays an enemy Hind radio message. Evidence: `tmp/a3/scene-audit/`,
`tmp/a3/combat-dense/flight-7.png` and `flight-9.png`. The 060 combat profile
executes about 19.3 full shapes/frame against 14.0 in take-off. The helicopter
can fly out of view later; the fixture guarantees the initial scene, not frozen AI.

Every result contains fps, ticks/s, per-frame VBL/tick/buffer rows, interval
histograms, min/max interval and standard deviation in milliseconds. Barto
records 476/495/480 fields for take-off/hover/combat; its omitted lead-in fields
can contain swaps, recorded as `swaps_outside_trace`. Only the continuous log
is authoritative for full-window frame counts; aprof completed-swap counts are
an independent full-window check on every 020+ run. In the final 68000 combat
window, 53 swaps are logged and 51 fall in the 480 recorded Barto fields; the
two swaps outside the trace are retained in the reported 5.3 fps.

## Reproduce the final acceptance runs

From the game directory, with the shared environment (`. ../../common/env.sh`):

```sh
make slave verify
python3 tools/check_rebuild.py
python3 tools/test_verify_frame.py
bash tools/final_matrix_a.sh # five-CPU take-off; 68000/060 hover and combat
python3 tools/summarize_a.py tmp/a-final/matrix

export SLAVE="$PWD/tmp/build/verify/Gunship.Slave"
export MACHINE=a500-fast WHD_ARGS=CUSTOM2=1
export GUNSHIP_FSUAE="$AMIGA_SHARE/fs-uae-mouse/fs-uae"
python3 tools/verify_run.py tmp/a-final/state-1 state
python3 tools/verify_run.py tmp/a-final/state-2 state
for tick in 0 1 2; do
 python3 tools/compare_states.py tmp/a-final/state-1/tick-$tick tmp/a-final/state-2/tick-$tick --whole-ram > tmp/a-final/repeatability-$tick.json
done
python3 tools/compare_states.py tmp/a-final/state-1/tick-0 tmp/a-final/state-1/tick-1 --expect-different > tmp/a-final/negative-control.json
MENU_DELAY=137 python3 tools/verify_run.py tmp/a-final/mission-delay mission
WHD_ARGS=CUSTOM2=2 python3 tools/verify_run.py tmp/a-final/mission-seed2 mission
```

Each final capture retains emulator/source/slave hashes in `provenance.json`,
its actual emulator configuration and log under `.run/`, addresses in
`layout.json`, raw RAM snapshots, per-frame timestamps and interval histograms
in `result.json`, and screenshots. These are emulated machine configurations;
this does not substitute for the hardware/release checks in F.

`session_a.py` deliberately uses the pinned legacy emulator protocol. Its
`fields()` method retains the old lead-in behavior for the menu/setup route;
`verify_run.py` corrects each measured chunk and asserts the game's actual VBL
delta. Do not substitute a newer emulator without first checking that timing
contract. The machine configurations are A500/68000 with 512 KiB chip + 8 MiB fast;
A1200/68EC020 at 14 MHz, EC030 at 50 MHz, 040-NOMMU at 25 MHz and 060-NOMMU at
50 MHz with 2 MiB chip + 8 MiB fast. The 030+ configurations request data-cache
emulation. No claim about real 040 copyback safety is made before B3.

`ALL_SCENES=1 bash tools/final_matrix_a.sh` optionally runs every scene on
every CPU. The required baseline uses all five CPUs for take-off and the 68000/060
endpoints for hover/combat; an additional completed 020 hover capture is retained. The legacy aprof engine rejects the 68000 configuration, so its cost
breakdown uses Barto self-cycle samples (21.39% BBUSY, 17.99% geometry, 4.94% STOP
in take-off). Barto call stacks must not be carried across omitted lead-in fields;
only self-cycle counts are accepted from that sampled reduction.

After the captures and comparisons above, run
`python3 tools/accept_a.py tmp/a-final`. It checks the nine required
windows, provenance consistency, exact elapsed time, alternating buffers, hover
endpoints, applied combat fixture, whole-RAM repeatability and negative controls.
`tools/summarize_a.py` independently checks aprof swap counts and the documented
Barto coverage bounds. Reports are `tmp/a-final/acceptance.json` and
`tmp/a-final/matrix/summary.json`.

## Final acceptance result

Nine required windows pass `accept_a.py`; `summarize_a.py` passes the independent
swap-count/coverage checks. The final 68000/060 scene results are:

| Scene | 68000 fps / ticks/s | 68060 fps / ticks/s | Interval range, 68000 / 060 |
|---|---:|---:|---:|
| Take-off | 5.1 / 2.5 | 15.3 / 7.6 | 9–10 / 3–4 VBLs |
| Hover | 5.5 / 2.8 | 16.7 / 8.4 | 9–10 / 3 VBLs |
| Combat | 5.3 / 2.7 | 16.6 / 8.3 | 7–13 / 2–4 VBLs |

Hover endpoints retain position, altitude, zero speed and level pitch/roll on both
machines. Combat screenshots show cannon ammunition consumed. The separate
visible-target audit confirms three ground targets plus the helicopter at the
start, and the final 060 profile averages 19.295 full shapes per frame.
Normal slave output is byte-identical to `tmp/a1/rebuilt.h0` and contains no
`GSVFY001` marker. All 119 archived source/game files still match their manifests.
