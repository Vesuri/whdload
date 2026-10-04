# Fixed-time simulation for duel v1

CUSTOM2 bit 0 uses the existing priority-4 simulation process with a period of
`sim_p` PAL fields, chosen from AttnFlags before PatchSeg (`sim_configure`):
6 fields on a 68000/010 (the original 8.33 Hz, so the CPU is not spent on steps
nobody sees) and 2 fields on a 68020+ (25 Hz, the measured rendering cap).
Each step is 1/`sim_n` of an original step, `sim_n` = 6/`sim_p` (1 or 3). The
text below was written for the former one-field mode (`sim_n` = 6, still the
VERIFY unit-check default); every "six"/"sixth" in rates, Euler corrections and
relaxation roots now reads `sim_n`, and every per-field clock quantum reads per
`sim_p` fields. Field-timed rules (recovery 240 fields, gear holds, envelopes)
and six-field cadence decisions are unchanged. After PatchSeg the two deadline
`moveq`s receive `sim_p`.

Different periods are different integrations of the same game, not the same
trajectory: over 1,500 demo fields the 6-field period travels ~1.5% and the
2-field period ~0.5% less than the former one-field mode; race clocks agree.
CPUs with the same period match all 35 core variables exactly.
The priority-minus-1 drawing task samples current state independently. Rendering
never owns elapsed game time. The original mode remains the default; v2 is unchanged.

## Rates and integration

A physical update spans one sixth of the original step. Signed 32-bit division
with independent fractional carries prevents small and negative rates from
vanishing. Six calls with a constant signed rate sum exactly to the old increment,
including INT_MIN and INT_MAX. Word quantities use the same division.

Player acceleration, braking, clutch drag, tyre scrub, steering forces, heat,
lane centring, verge movement, traffic and physical AI motion use fractional rates.
Each AI record has independent speed, lane and position carries. Road-unit loops,
collision impulses, limits and thresholds retain their original units. Fuel is
already distance-derived. Dashboard/effect phases and the four background phases
advance with simulation time rather than drawings.

The original integrates the post-force velocity in a coarse Euler step. Simply
subdividing it gives less acceleration travel and more braking travel. The player
and physical AI therefore add 2.5 times the current continuous velocity change to
the velocity used for displacement. For constant force, six smaller updates
recover the original coarse-step displacement, subject to integer quantisation.
Player distance retains low bits until the final division by 768; early shifting
would lose them. Collision/gear impulses are excluded from that correction.
Throttle and drag lookup inputs receive the corresponding modified-Euler velocity
reference, without changing the actual velocity or RPM.

Heading, yaw and clutch relaxation use Q16 sixth roots of the original retention
factors, with fractional carries. Clutched free RPM uses the corresponding affine
rise, so the six decays and rises compose to the original map within one word
unit. Unclutched free RPM rise uses its own signed carry.

Six fine updates are not a general byte-exact replacement for one old update:
forces depend on changing state, finer collision checks can see different contacts,
and AI decisions can cross thresholds between old samples. The constant-rate and
constant-force invariants establish the units and integration correction; measured
handling comparisons establish the practical difference.

## Original-cadence decisions and prediction

Police/crash script counters, automatic gear decisions, gear-lever movement and
clutch release retain their six-field cadence. Original gear commands skip an
entire player-physics step; their replacement holds the controller for six fields,
rather than skipping just one. Gear audio envelopes use elapsed video fields.

The demo AI record is a full-step predictor, seeded anew from player state on
every call. Its predicted speed and distance are discarded by the caller. Scaling
those values shortened its horizon and caused an early off-road crash. The demo
therefore retains the full prediction acceleration/braking and distance, while
its applied lane movement is divided by six. Opponent and police records represent
physical cars and use fractional motion. Prediction units and integration units
must be distinguished even inside the same original routine.

The race clock and average-speed accumulators carry one fifth of a nominal tenth
per PAL field. The original one-tenth-per-six-fields clock ran at 5/6 real time.
The rare visual event uses a separate RNG and original six-field event cadence;
its renderer reads cached state. Gameplay RNG excludes beam-position entropy.
Camera and needle caches remain drawing snapshots; their age is not game time.

## Recovery

The original nonfatal crash and engine-damage path blocks simulation while drawing
animation and waiting for acknowledgement. CPU speed changes when its penalty is
applied and motion resumes. The replacement uses 240 fields (4.8 nominal PAL
seconds): stopped player, neutral engine, one life loss unless the trainer is on,
and one 20-second penalty. Opponents, traffic and the race clock continue. Drawing
shows the recovery message. Terminal damage, fatal crash and last life retain the
original race-end path. This changes recovery presentation and acknowledgement.

## Verification

Normal builds contain optional simulation (CUSTOM2 bit 0) and unused-blitter-IRQ
suppression (bit 1); CUSTOM2=3 enables both. VERIFY adds CUSTOM3 for original-mode
reproducible RNG, CUSTOM4 for deliberately slow drawing, and CUSTOM5 fixtures:

- Bit 0: accelerate, steer both ways, brake, coast and accelerate input tape.
- Bit 1: one engine-damage event (CUSTOM5=3).
- Bit 2: fatal crash (CUSTOM5=5, without the trainer).
- Bit 4: a straight acceleration/braking tape (CUSTOM5=17). This tape deliberately
  does not follow road bends; it is a handling fixture, not the demo driver.

Fixtures execute in the slave, with no debugger memory/register writes. The
59 assembly checks exercise signed division, independent AI carries, field
clocks/counters, gear-hook return boundaries, relaxation, coupled clutch RPM,
constant-force integration, gear holds and full-horizon demo prediction.
`check_units.py` reads their results. `check_timing.py` checks consecutive fields,
one-field deadlines and real-time race clocks. Use `--period 3` only for historical
captures. Recovery and terminal checks test life loss, penalty, stationary time,
idle pitch, fatal precedence and frozen terminal clocks. `compare_state.py
--assert-core` checks all 35 gameplay variables at identical VBL indices.
`audit_simulation.py` checks hook boundaries and direct incoming branches; indirect
entries and return adjustments also need manual review and runtime checks.

PAL is the validated timing target; NTSC has not been validated. Exact capture
builds and ignored measurement evidence are retained under tmp/prof. Current
release validation and handling measurements are recorded in docs/open-work.md.
