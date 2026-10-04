# Higher-rate simulation for duel v1

The W4 choice uses the existing priority-4 simulation process. CUSTOM2 shortens
its deadline from six to three video fields; the priority-minus-1 drawing task
continues to sample current state. No drawing routine owns elapsed game time.
The mode is optional and the original mode remains the default.

## Units and rates

On PAL, three fields are nominally 0.06 seconds (16.67 updates/second).
Continuous quantities use half the old six-field increment:

- Player distance uses speed /128 rather than /64. Acceleration, braking,
  tyre scrub, clutch decay and free-engine RPM rise use half their old rates.
- Steering input, heading/yaw relaxation, lane centring, verge drag and heat
  gain/cooling use half rates. Spatial collision impulses remain whole.
- Opponent/traffic motion, AI acceleration/braking and lane changes use half
  rates. AI speed retains its old units for lookahead and speed comparisons.
- Dashboard phases and distance-driven audio/effect phases use half increments.
  Gear envelopes use elapsed fields; police/crash script counters retain their
  original six-field units. Odd signed word rates alternate floor/ceiling halves.
- Clock and average-speed accumulators carry fractions of 3/5 per update.
  The original clock advanced one nominal tenth every six fields and ran at
  5/6 real time. The new weighting also keeps time and speed sums in matching units.

Road-unit loops, limits, thresholds, event impulses and existing field-based
input/audio timers retain their units. `simulation-patches.i` identifies each
operand and hook. `audit_simulation.py` checks direct hook entries, not all
indirect jumps or semantics; return adjustments also received manual review.

## State formerly advanced by drawing

The four visual phases advance on simulation ticks. The rare high-speed effect
has its own random generator and six-field event/animation cadence. Drawing reads
its cached state. Gameplay RNG excludes beam-position entropy under CUSTOM2 bit 0.
The main task's camera position and needle caches remain drawing snapshots;
their differing ages across CPUs do not represent physical trajectory changes.

## Recovery

The original nonfatal crash and engine-damage path blocks the simulation while
it draws animation and waits for acknowledgement. CPU speed changes when it
applies a penalty and resumes motion. CUSTOM2 bit 0 replaces those paths with 240-field
recovery (4.8 nominal PAL seconds): neutral engine, stopped player, one life loss
unless the trainer is enabled, and one 20-second penalty. Opponents, traffic and
race time continue. The ordinary drawing task displays the recovery message.
Terminal damage/fatal crash/last life retain the original race-end path.
This changes the original crash presentation and acknowledgement behaviour.

## Verification

Normal builds contain the optional shipping simulation (CUSTOM2 bit 0) and
unused-blitter-IRQ suppression (bit 1). CUSTOM2=3 enables both. VERIFY adds:
CUSTOM3 for reproducible original-mode RNG; CUSTOM4 for deliberately slow drawing;
CUSTOM5 bit 0 for an input tape (accelerate, steer both ways, brake, coast, accelerate)
and bit 1 for one engine-damage event (CUSTOM5=3); bit 2 forces a fatal crash
(CUSTOM5=5 without the trainer). Bit 3 runs original/patched shape pixel twins
(CUSTOM5=9 with CUSTOM2=3). Fixtures run in the slave, never through
memory/register writes by the debugger. Private data tests execute the assembly
half-rate and timer helpers on dummy allocations before the game starts.

`check_units.py` reads 18 rate/counter assertions. `check_timing.py` checks deadlines
and the clock against consecutive video fields. `check_recovery.py` checks life
loss, penalties, stationary recovery, idle engine pitch and recovery length.
Cross-machine comparisons use VBL data captures and `compare_state.py`.
Evidence and exact capture builds remain local in ignored `tmp/prof/`.

Finer integration changes handling and AI decisions. In the initial demo at
field 999, the original trajectory has distance 15390991 and speed 8828952;
the higher-rate trajectory has 16216065 and 9129516 (about +5.4% distance and
+3.4% speed). Those are integration changes, not CPU divergence. Original and
higher-rate screenshots are therefore not a pixel-equality oracle. PAL is the
validated timing target; NTSC is not yet validated.
