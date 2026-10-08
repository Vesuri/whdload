# Fixed-time simulation (duel v1)

Enhanced framerate (`CUSTOM2` nonzero) keeps the game's own priority-4 simulation process
(see [game.md](game.md)) and changes how often it steps and how each step integrates. Code:
`whdload/simulation.s`, patch list `whdload/simulation-patches.i`.

## Period

A step lasts `sim_p` PAL fields, chosen from AttnFlags before PatchSeg (`sim_configure`):

| CPU | `sim_p` | Rate | Why |
|---|---|---|---|
| 68000/010 | 6 | 8.33 Hz, the original | the A500 draws ~7 fps: no CPU is spent on steps nobody sees |
| 68020+ | 2 | 25 Hz | the measured chip-bus rendering cap |

Each step is 1/`sim_n` of an original step, `sim_n` = 6/`sim_p` (1 or 3). After PatchSeg,
`sim_set_deadline` writes `moveq #sim_p` into the two deadline instructions. The drawing task
samples the latest state; rendering never owns elapsed game time. CPUs with the same period
produce identical state; the two periods are different integrations of the same game.

## Rates and integration

- Continuous rates are divided by `sim_n` with signed 32-bit division and a private fractional
  carry per accumulator, so small and negative rates do not vanish: `sim_n` calls with a
  constant rate sum exactly to the original increment, including INT_MIN and INT_MAX. Word
  quantities use the same division.
- Scaled: player acceleration, braking, clutch drag, tyre scrub, steering forces, heat, lane
  centring, verge movement, traffic, and physical AI motion (each AI record has its own speed,
  lane and position carries). Not scaled: road-unit loops, collision impulses, limits and
  thresholds. Fuel is distance-derived already.
- The original integrates the post-force velocity in one coarse Euler step; plain subdivision
  would give less acceleration travel and more braking travel. Player and physical AI
  displacement therefore add (`sim_n`−1)/2 times the current continuous velocity change, so
  constant force reproduces the coarse-step distance (up to integer quantisation). Player
  distance keeps its low bits until the final division by 768. Throttle and drag lookups get
  the matching velocity reference without changing velocity or RPM.
- Heading, yaw and clutch relaxation use Q16 `sim_n`-th roots of the original retention
  factors, with carries. Clutched free RPM uses the matching affine rise, so the decays and
  rises compose to the original map within one word unit; unclutched rise has its own carry.
- The race clock and average-speed sums gain 1/5 of a nominal tenth per field: race time
  follows real PAL time (the original ran at 5/6).
- Dashboard and background phases advance with simulation time, not with drawn frames. The
  renderer's rare high-speed visual event uses a private RNG at its original six-field
  cadence; gameplay RNG has no beam-position term in the enhanced mode.

## Original-cadence decisions

Police and crash script counters, automatic gear decisions, gear-lever travel and clutch
release keep their six-field cadence. An original gear command skips a whole player-physics
step; the replacement holds the controller for six fields. Gear audio envelopes use elapsed
fields.

The demo AI record is a full-step predictor, re-seeded from player state on every call, whose
speed and distance outputs the caller discards. It keeps the full prediction; only its
applied lane movement is divided. Scaling the prediction shortened its horizon and crashed
the demo early. Prediction units and integration units must be told apart even within one
original routine.

## Recovery

The original nonfatal crash and engine-damage path blocks the simulation while it animates
and waits for acknowledgement, so the CPU speed decided when motion resumed. The replacement
is field-timed: 240 fields (4.8 s) with the player stopped and the engine idling, one life
lost (none with the `CUSTOM1` trainer) and one 20-second penalty, while opponents, traffic
and the clock keep running and the renderer shows the message. Terminal damage, a fatal crash
or the last life take the original race-end path; a fatal crash overrides a recovery in
progress.

## Handling against the original

Six fine updates are not a byte-exact replacement for one coarse update: forces depend on
changing state, finer collision checks see different contacts and AI decisions cross
thresholds between old samples. Measured on the 6 000-field attract demo and the straight
acceleration/braking tape (VERIFY `CUSTOM5=17`, 1 000 fields):

| Period | Demo first crash | Demo speed / travel, field 999 | Straight speed / travel, field 399 | Stop after braking |
|---|---|---|---|---|
| Original | field 3474 | — | — | field 492 |
| 6 (68000) | 3474 | +0.00% / +0.00% | +0.00% / +0.00% | 492, +0.00% |
| 2 (68020+) | 3464 | +0.72% / +0.99% | +1.75% / +1.59% | 494, +1.84% |

Period 6 reproduces the original speed exactly up to the first crash (travel within
+0.0003%: the patch carries sub-unit motion the original drops); after it, the state differs
by design (recovery and clock). PAL is validated; NTSC is not (see [open-work.md](open-work.md)).

## Verification hooks

`make -C whdload verify` adds `CUSTOM3` (reproducible RNG), `CUSTOM4` (deliberately slow
drawing) and `CUSTOM5` fixtures, all run inside the slave without debugger writes:

| `CUSTOM5` bit | Fixture |
|---|---|
| 0 | field-based joystick tape: accelerate, steer left/right, brake, coast, accelerate |
| 1 | one forced engine-damage event (`CUSTOM5=3`) |
| 2 | forced fatal crash during a recovery (`CUSTOM5=5`, trainer off) |
| 3 | sub-unit rendering with zero fractions (see [subunit-rendering.md](subunit-rendering.md)) |
| 4 | straight acceleration/braking tape (`CUSTOM5=17`); does not follow road bends |

The VERIFY build also runs 129 assembly assertions before PatchSeg (107 simulation, 22
rendering): signed division and carries, clocks and counters, gear-hook return boundaries,
relaxation roots, coupled clutch RPM, constant-force integration, gear holds and the demo
prediction. `CUSTOM5=16` runs them without scripted input. See [testing.md](testing.md).
