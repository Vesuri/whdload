# Phase 5: timing and state model

The original has a five-field CLI simulation loop, but it is **not independent
of drawing**. The shifter/clutch handshake, a collision input traffic collision origins, road widths and the shared RNG
cross the task boundary. Phase 8 must address these dependencies; copying TD2's
six-field constants is incorrect. This is analysis, not a gameplay patch.

## Evidence and reproduction

The pinned VERIFY slave with CUSTOM3=1 and native emulator from phase 4 are used.
Normal 1.5b and the hardware A/B package are unchanged. Runtime/game pins are
checked by the runner before each boot. All captures are PAL, deterministic,
no-input first Porsche attract race, anchored at h4+$F6. No guest memory/register
writes or host UI input are used. Native keyboard input is used separately for
event diagnostics. Screenshots are navigation aids, not timing evidence.

From the harness, with the shared environment loaded:

```sh
TD_SETUP=a500 WHD_ARGS=CUSTOM3=1 SLAVE="$PWD/tmp/phase4/base-a500-1/slave.slave" \
  python3 tools/timing_capture.py tmp/phase5/NEW-frames --fields 201
TD_SETUP=a1200 WHD_ARGS=CUSTOM3=1 SLAVE="$PWD/tmp/phase4/base-a500-1/slave.slave" \
  python3 tools/timing_late.py tmp/phase5/NEW-late --fields 100
python3 tools/timing_map.py
python3 tools/timing_trace.py
python3 tools/timing_late_report.py
```

Outputs must be fresh. Each runner owns boot and shutdown and refuses an active
server. `timing_capture.py` now captures both the data hunk and 62 bytes around
the saved main-race frame at every root+$18BA boundary, before increment. The
original `a500-fields` / `a1200-fields` runs contain 1800 data-only samples via
`state_fields.py`; `a500-frames` / `a1200-frames` contain 201 data/frame pairs.
Use a window inside the same race: the saved frame is not valid after race exit.
The two late traces advance 600 fields from the anchor, then profile 100 fields.
They demonstrate differing execution, not equivalent performance workloads.

Phase-4 `base-a500-1` and `base-a1200-1` traces independently establish executed
writers and task-stack contexts. `timing_trace.py` retains selected instruction
registers/fields. `timing_map.py` decodes states and emits direct a4-relative
writer candidates from the disassembly. Its static candidates include inline
strings/tables; only the reviewed writers in internals.md are semantic claims.
Indirect array, interrupt and frame-local writers are documented explicitly.

## Equal-field comparison

Sample 0 is the first pre-increment VBL after the race anchor. Both machines have
period 5 and advance the saved deadline by exactly five at samples 5,10,15,...200.
The CLI's vehicle call is h4+$130 -> $43B0 -> $3F26; h4+$134 -> $1C3A is road
segment processing, **not** the speed integrator. The 100-field phase-4 traces
contain 20 of each on both CPUs, at trace fields 4,9,...99. Road Drawer has a
separate stack and lower priority; it snapshots the vehicle under Forbid/Permit
at $B00..$B68 and publishes via h3+$175E/root+$7AAA.

| Observation | A500 | A1200 / 68EC020 |
|---|---:|---:|
| First gear becomes 1 (sample) | 65 | 65 |
| Clutch clears (sample) | 100 | 85 |
| Speed/position/RPM first differ | 85 | 85 |
| Gear becomes 2 | 190 | 165 |
| Gear becomes 3 | 520 | 485 |
| Gear becomes 4 | 1220 | 1175 |
| RNG first changes (sample) | 598 | 546 |
| RNG-changing sample intervals in 1800 fields | 111 | 213 |
| Final longitudinal Q16.16 value | 36582039 | 37583243 |
| Final speed Q16.16 value | 8786299 | 8863321 |

Gear selection sets clutch -22786(a4) at $255A. The renderer acknowledges each
buffer at $3AF8, through -29900/-29899(a4). The CLI's $472 routine requires both
acknowledgements and the shifter position before $5CE clears the clutch. The
trace shows acknowledgements at fields 75/87 on A500, 66/72 on A1200, then clutch
clear at 99 vs 84. This explains the first physical-state divergence: the same
CPU-independent deadline does not imply CPU-independent vehicle behavior.

A second static dependency is wall collision at $1236: $1240/$127A read the
renderer snapshot -22372(a4), written by $B10, rather than the current lateral
position. The renderer also writes road-edge widths ($1CFA/$1D00), traffic
collision origins ($184C/$18EC), and lane-offset returns ($181E/$183E). Their
CLI consumers include traffic collision/avoidance, verge losses and steering
limits. Moving only saved-x is insufficient: enhanced simulation needs its own
road-width and road-relative traffic geometry computation and timed lane motion.
A delayed renderer can delay the crash decision. Preserve the original
behavior with CUSTOM2=0; enhanced mode needs a simulation-owned collision input.

## Race time, average and score

The race frame's -36(a5) long starts at 1, and -44(a5) speed sum at 0. Once the
first nonzero gear sets latch -52(a5), $14A..$156 adds integer mph and increments
the sample count on each loop, including stopped/police ticks. The latch stays
set until crash recovery at $68/$70; the accumulated count and sum are retained.

At sample 65 both counts are 2; at sample 125 both are 14. Thus 60 PAL fields
add 12 units: the result-screen seconds divider at $366..$36C is 12, while these
60 fields last nominally 1.2 seconds. The displayed race clock runs at **5/6 of
PAL time** during active counted ticks. Startup in neutral is excluded; this is
not a wall clock since boot. Overrun/blocking can only slow counted time further.
NTSC's nominal 60/5=12 ticks per second explains the 12 divider, but NTSC has not
been run or validated.

Average = signed integer division of speed sum by count ($38E..$396), including
its initial denominator bias and penalties. There is no distance/VBL-derived
average. At sample 200 counts are both 29, sums 768 vs 969: integer averages
26 vs 33 mph, reflecting the clutch difference.

Crash adds 240 to the count at $272, with no speed numerator contribution: a
20-second penalty in the game's 12-unit clock, also lowering the average.
At gas/stage completion, $C60 computes, with N=count, B=stage baseline and
M=stage+4:

`score = trunc(M*1000000 / max(N-B,100)) + 100*max(100-(N-B),0)`.

$34C adds it to -26350(a4). B comes from $45E0: 700,1100,1200,1100,1500;
reference times at $45F4 are 3000,2800,3500,4000,4500, also divided by 12 at
$374..$37A. The gas result passes average, elapsed/reference seconds and score
to root+$444C. Stage advances at $3BA; root+$47EC awards two chances. No independent
consumable fuel counter was identified: station entry is position within 80 of
stage end and speed <=17, with the stage/end state controlling the transition.

## RNG contexts and later windows

All 14 direct RNG-stub call sites in the pinned original are mapped:

| Caller | Context / consumption |
|---|---|
| root+$230 | CLI, choose attract car modulo 5; VERIFY resets seed here |
| root+$4450, $46AA | CLI, stage/gas result commentary choices modulo 3 |
| h3+$162, $1DE, $252, $2C8 | CLI, intro waits; consume RNG while polling input/VBL deadlines, return discarded |
| h3+$B28 | CLI, car selection/attract carousel idle loop, then DOS Delay(5) |
| h4+$1294 | CLI road crossing via $1C3A/$132E, probability gates traffic spawn |
| h4+$130C | CLI road crossing via $1C3A/$132E, probability gates radar |
| h4+$1EEE | Road Drawer via $10F2/$1ED2, >=85 mph and fewer than 30 windscreen effects; 1/1024 spawn test |
| h4+$1F00, $1F10 | Same drawing context, successful effect's random screen coordinates |
| h4+$1F76 | Same drawing context, effect animation sprite selection |

The later 100-field traces contain 9 renderer RNG calls on A500 versus 17 on
A1200, plus one CLI traffic RNG call on A1200. Both still contain 20 vehicle
and road calls. Their stack contexts agree with the phase-4 task attribution.
Removing VHPOSR leaves a shared stream whose consumption depends on draw rate;
later traffic/radar choices are not cross-CPU deterministic. Phase 7 must isolate
visual RNG from simulation RNG, or suppress visual consumption in its fixture,
and reset at a player-race anchor. This must be explicitly tested with slow drawing.
The first 100-field phase-4 baseline remains valid: it has no in-race RNG calls.

## Crash and radar semantics

`events-a500` / `events-a1200` select Porsche player mode via native keys, drive
into a wall, and stop at the same instruction boundaries. `timing_crash.py`
records the main frame and full DATA at $272 (before penalty), $32D8 (animation
entry), $2EA (acknowledgement entry), after 100 fields waiting, and $F6 (recovery).
These are natural event diagnostics, not an equal-field input tape; the precise
collision state/field can differ. The animation's seven DOS Delay(2) calls provide
nominally 14 PAL fields of scheduled delay; its drawing/OS work adds further elapsed fields.

| Natural Porsche wall crash | A500 | A1200 |
|---|---:|---:|
| $32D8 animation entry -> $2EA acknowledgement | 37 fields | 31 fields |
| Before penalty -> acknowledgement | 43 fields | 37 fields |
| Explicit count penalty | 240 | 240 |
| Count/speed-sum change in 100-field acknowledgement wait | 0 / 0 | 0 / 0 |
| Chances after recovery | 4 | 4 |

The original keeps the impact state during the blocking animation/wait, then
clears speed/RPM/gear in the recovery setup. There is no automatic timed recovery.
These measured durations are for the tested crash, not a bound for every event.
CUSTOM2 must retain the original blocking path per the plan. A field-timed
recovery may exist only in VERIFY; do not copy the older TD2 recovery design.

The radar path is different: $12A skips vehicle integration once stopped ticks
are nonzero, but $134 road processing, $164 traffic/police and counted race time
continue. $1662 increments pursuit age; >60 changes relative patrol positioning,
>90 brakes it by 1536 displacement units per tick. With player and police stopped,
$16A4 counts to 30; then $1624 accelerates the departing patrol by 1536 per tick.
The ticket is drawn by Road Drawer at $1D3A for stopped count >=30. Patrol culling
at $15EA and resets at $1604..$1610 release the player. **No fire acknowledgement
is required for this radar sequence**; phase-3 acknowledgement input was incidental.
This does not use the crash count penalty or decrement chances.

`timing_route.py` reaches natural pursuit on each preset, then `timing_radar.py`
uses Down braking only and captures 1501 consecutive VBLs, including the main
race frame. No fire is sent during the capture.

| Radar read-only capture (sample index) | A500 | A1200 |
|---|---:|---:|
| Pursuit age at sample 0 | 4 | 3 |
| Stopped counter becomes 1 | 435 | 440 |
| Stopped counter becomes 30 | 580 | 585 |
| Patrol removed / stopped counter clears | 925 | 930 |
| Vehicle-hold interval | 490 fields | 490 fields |
| Race-count gain over 1500 fields | 300 | 300 |
| Crash code / chances throughout | 0 / 4 | 0 / 4 |

Every stopped-counter increment is five fields apart, with speed zero throughout
the 490-field hold. The five-field index offset follows the one-tick difference
in initial pursuit age. Once aligned to stopped-counter onset, these script
intervals match despite different draw rates. This covers the tested early
braking case; road/input/RNG dependencies can still change pursuit onset, and a
CPU overrun could stretch the main loop. It is not a universal event bound.

## Acceptance and retained scope

`tools/check_phase5.py` passes against the raw field/frame files, crash records,
RNG call-site bytes, trace reports and unchanged slave hashes. It writes
`tmp/phase5/acceptance.json`. Both emulator sessions are shut down. The full
source of the harness tools/docs/manifests is copied to `harness-snapshot/`;
`evidence.sha256` pins the phase-5 artifacts and `provenance.json` links the
phase-4 trace inputs and original game/source revision. The empty `a500-late/`
directory is a refused launch while another server was active; it is not evidence.

The normal slave is unchanged. NTSC, hardware overlay A/B, enhanced arithmetic,
VERIFY slow drawing/tapes and cross-CPU enhanced state equivalence remain open.
This completes the analysis gate; those are later implementation/release gates.

The reproducible phase-4/5 baseline uses the retained phase-4 slave above. The
current VERIFY build has phase-7 instruments and is a different fixture; use
`verify_capture.py` for it. Do not replace historical capture binaries or pins.
