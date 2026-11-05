# Four-times-rate simulation: physics feasibility

Static code analysis of running the simulation four times as often with quarter-sized
steps, plus measurements of its CPU cost and of the opponents' motion (§9). Nothing here is
implemented.

## Finding and scope

A roughly 59.7 Hz simulation with one quarter of the original time per update
is technically plausible. It is a substantial physics conversion, not a timer
change or a global scaling constant. The player integrator is identifiable and
has useful fractional position storage already. The difficult parts are the
player/car-table interface, filters and load transfer, collision response, and
the AI's existing multiple update rates.

There is enough code evidence to design a conversion. There is not yet enough
to claim that a complete set of safe patches has been identified, or that handling
would match. The CPU cost is measured and small on the machines the option runs on (§9).

Evidence: disassembly of the original hunk 0 from the SPS 686 Disk.1 (`python3 -m amigaxdev.disasm dis`
on an extracted hunk). Original hunk SHA256:
`74e51f8d758ec53a06f709aa3bf64d457676bc30c6d1c24df906e3c5d5446a73`.
All addresses below are **game: hunk-0 offsets**. Binary/disassembly artifacts
stay ignored. Register arithmetic is fixed point with intermediate truncation;
equations below describe its structure, not a promise of bit-exact floating-point
substitutes. Physical names inferred from dataflow are identified where necessary.

## 1. The actual driving path

SOFT enters at `007ee`. Mode `268da == 1` calls the demo director and jumps over
the player's physical update. Normal driving takes `00850` onward:

| Code | Work |
|---|---|
| `0085c..00bf8` | Effects dispatch, controller mode, steering, throttle/brake state |
| `00bf8..00dac` | Bank/gradient and speed-squared terms applied to velocity; load calculation |
| `00dac..01824` | Four wheel-related state blocks, grip modifiers, slower thermal/wear/pressure-like recurrences |
| `01824..01dac` | Wheel positions, road samples, differences from previous samples, load-transfer state |
| `01dac..02b7e` | Wheel-relative velocities, slip/grip limits, drivetrain, forces and moments |
| `02b7e..02d1c` | Translation/yaw integration, low-speed rules and small per-tick losses |
| `02d1c..03138` | Track coordinates, wall/obstacle contacts, collision effects |
| `03138..035ce` | Camera publication, race/lap time, lap crossing, pit state; field update at `035c8` |
| `03620..03af0` | Nearby-car audio, race flags and input/event dispatch |

`020d26` performs the field update, including AI movement, sorting, contacts,
a batch of four car controllers, and replay recording. It is not merely a
function that advances all cars using identical player physics. The player has
the detailed four-wheel model; other cars have a separate simpler model.

`02254e/022556`, called about 33 times per tick, are not a per-car physics
integrator: they compute **wrapped relative distance**.
The measured cost of this path is in §9.

## 2. Preserve native units; change integration intervals

Use `h = 1/4`, with one original update defined as one time unit. Keep speeds,
forces, angles, geometry, gear ratios and lookup-table inputs in their original
units. Rescaling the stored velocities themselves would force changes to speed
thresholds, squared-speed terms, slip calculations, AI prediction and audio.

Important player fields can be classified directly from their consumers:

| State | Representation / evidence |
|---|---|
| `098aa`, `098ae` | Two signed world-position longs; their high words supply the camera; movement adds a sign-extended velocity shifted left 9 |
| `098b2`, `098b4` | Signed velocity components; combined into speed/direction and integrated into the position longs |
| `098b6`, `098b8` | Magnitude and direction of those components, via `005f38` and `004edc` |
| `098ba`, `098bc`, `098be` | Heading, angular increment/rate in original-tick units, and previous angular-rate value |
| `09846` | Steering command; added to front-wheel slip angles; limited to ±3200 |
| `09afc`, `09b00` | Throttle and brake state respectively, from held input bits and their downstream use |
| `09a78..09a7e` | Four persistent load-transfer states; paired sums feed body attitude and wheel loads |

### Translation and yaw

At `02c62..02c88`, ignoring the existing ±12 dead zone:

```
X_raw += Vx * 512
Z_raw += Vz * 512
```

Since the high word is the world coordinate, one native velocity unit represents
1/128 world unit of travel per original tick. The fine-step position operation
is therefore `X_raw += Vx * 128`, likewise for Z. This part is especially tractable:
there are already 16 fractional position bits, so no new position format is needed.
The velocity dead zone remains in native velocity units, not divided by four.

`02ba2`, `02bc2` add the rotated force/mass results to the two velocity components;
`02bfc` adds the moment/mass result to angular rate. These continuous increments
need multiplication by h. Earlier additions at `00c8e`, `00cb4`, `00d80`, `00da0`
and `00da6` also update these same states; changing only the final three stores
would miss bank/gradient and aerodynamic contributions.

`02c34` adds angular rate to heading. That also needs h. Angular rate must retain
its existing units because `01db6` and `01e46`, among other sites, use it to
calculate wheel velocities. Word-sized fractional changes need independent
signed remainders or wider shadow accumulators; blindly using arithmetic shifts
biases negative values and loses small positive changes. Retain precision before
native multiply/divide narrowing wherever practical.

### Why squared speed is not a quadratic timestep term

`00ce6..00d5e` squares the speed and uses it for aerodynamic drag/load terms.
With speed units unchanged, this **does not get divided by 16**. The force law
stays the same; its contribution to a velocity increment gets h at integration.
Static load/grip calculations using that force must retain their magnitude.

A genuine direct term `a * dt^2` in a position recurrence would get h² = 1/16.
In this engine's visible translation path, that dependence instead emerges from
the combination of the velocity and position integrations. The exponent of a
state variable in a formula is not the exponent of its timestep.

### Update order changes the original handling

The player uses the updated velocity for position integration. With constant
native acceleration increment A and no rounding, one old tick gives:

```
v1 = v0 + A
movement = v0 + A                 # omitting the position-unit conversion
```

Four ordinary quarter-step semi-implicit Euler updates instead give the same
final velocity but total movement `v0 + 5*A/8`. Thus even correctly scaled
constants do not reproduce the original acceleration/braking distance.

There are two legitimate specifications: integrate the inferred continuous model
more finely, accepting the difference; or preserve the coarse game's response.
For the latter, in this simplified constant-force case, adding `3/2` of each
fine-step velocity increment to the velocity used for displacement restores the
old endpoint. That is a derivation, **not a proposed unconditional patch**:
collisions, sign-change rules and state-dependent forces cannot be included
blindly. The same issue applies to yaw. The desired handling contract must be
settled before implementation; exact state equality every fourth step is not
a general acceptance criterion for nonlinear dynamics.

## 3. Controls and filters need different conversions

### Keyboard/joystick steering and pedals

`0095a..009da` increments/decrements steering by `09af2`, applies centering
`09af0` in manual mode, then clamps it. Those rates are speed-dependent
(`0214c..02192`). Scale their **per-time application**, not the steering angle
limit or the speed used to calculate sensitivity.

`00a08..00b64` mixes throttle/brake ramps, cruise control, unsigned overflow,
release decay and saturation. Constants 16384 and 8192 participate in one
compound update, so separately quartering literals without checking carry and
clamp behavior is unsafe. A replacement should express the ramp in native pedal
units per time, retain fractional changes, and preserve the intended saturation
and controller-mode transitions.

The joystick is polled from the player update (`00948 -> 009d9a`). Keyboard state
is interrupt-fed. Mouse movement is sampled by the VBL path (`00b424..00b484`)
and accumulated into a target. Do not divide a mouse delta merely because it
arrives more often: it already represents movement since the last sample. Raising
SOFT alone would also leave mouse sampling tied to the display interrupt.

### A derivative hidden inside mouse steering

At `00900..00916`, the controller subtracts:

```
lateral_now + 13 * (lateral_now - lateral_previous)
```

from its target. `009842` is the current lateral coordinate; `009884` is the
previous value saved at `02d54`. Four-times-more-frequent position samples make
the difference approximately four times smaller. Retaining the same prediction
horizon requires **52 times the fine-step difference**, or an explicitly
normalized derivative/history. Dividing this coefficient by four would be the
opposite of the required conversion. Integer position quantization makes the
history/precision choice material.

### First-order relaxation

`0233a..0234e` implements approximately:

```
y = y + (target - y)/64          # 09b02 toward 09b04
```

`02376..02384` similarly moves `09a30` toward its target by 1/32. If these filters
run every fine tick, preserve their time constants with:

```
k_fine = 1 - (1 - k_old)^(1/4)
```

For the first filter that is `1 - (63/64)^(1/4)` ≈ 1/256.5. The difference
from 1/256 (0.2%) is irrelevant next to quantization: both
states are words updated with `asr.w` (`02346`, `02382`), so the native filter
stops up to 63 (resp. 31) units short when approaching from below and reaches
the target from above, a one-sided dead band. Applying `asr.w #8` per fine tick
would widen it to 255 units and change the steady state. The filter state needs
fractional bits (a long shadow); the exact gain is secondary. Targets that
change during the interval still yield a different sampled system.

`02260..0227a` is different again: a **slew limiter** of ±250 per update on the
engine-speed-like state `09a2e`. Its fine limit is ±62.5 with fractional carry;
the nearby gear thresholds and torque polynomial at `022da..02312` remain in
native units. Gear decisions need an explicit cadence/hysteresis policy.

### Load transfer: one coefficient has more than one role

`01a58..01ae0` and `01ae6..01b6a` update paired states from previous forces.
For the first pair, ignoring integer narrowing and later one-unit decay:

```
e = (99d8 / 5) - q_sum
f = 9ad8 / 32768
k = (floor(9ad4 / 2) + 16383) / 32768
q78 += k * f * e
q7a += k * (1 - f) * e
q_sum = q78 + q7a
attitude = q_sum * 2048 / 9ad4
```

The paired sum is a relaxation, while the distribution and conversion into
attitude have other roles. Changing setup parameter `09ad4` to scale its update
would also change the physical response through the division by the same value.
The fine integration coefficient must be separated from the original setup
parameter. The second pair has an analogous recurrence using `/8`, `09ad6`,
`09ada`, and attitude factor 6144.

The code also reads the previous force sums before calculating the new ones:
this is a discrete feedback loop with a one-update delay. A fourth-root scalar
filter alone does not establish equivalence of the whole coupled system.
The four road-sample differences at `01914..019f2` feed this calculation too.
They are **per-sample height-like changes**, not clearly established forces;
normalizing their time dependence requires deriving the full recurrence.
This is one of the remaining substantive physics-analysis tasks.

`01be0..01c56` and `02cd0..02d12` reduce nonzero states by exactly one toward
zero per update. Those are constant losses, not percentage damping. They need
fractional/time-gated application. The conditional low-speed yaw sign-change
rule at `02c08..02c2e` is yet another discrete rule; it cannot be converted as
an ordinary exponential decay.

## 4. AI movement and the player interface

At `020d38..020d7a`, the field loop uses each car record as follows:

```
record[14] += record[84]         # lateral rate plus lateral acceleration
record[8]  += record[14]         # lateral position
record[10] += record[16]         # heading
track_fixed -= record[12]       # track word + fractional byte
```

The track representation has its fractional byte at **+5**, with the integer
word at +6: `track_fixed = (word(+6) << 8) | byte(+5)`. The SUB/SUBX chain performs
the fractional subtraction and lap carry. Quartering its displacement needs
fractional remainder and unchanged wrap/lap logic, not only a change to the
integer coordinate. The lateral-rate and heading integrations also need h.

But controller evaluation is already slower. `020f4a..020f7e` processes **four
records per SOFT**, advances a cursor by four 86-byte records, and handles the
player separately at the wrap. For the normal 32-opponent field, that gives one
controller visit per opponent every eight original ticks. `020fe8..0210aa`:

- calls a controller through record +38;
- derives lateral acceleration using target, lateral position and rate;
- derives a heading increment using another relaxation;
- changes longitudinal speed using drag/turning deductions and record +18.

Running this entire routine four times faster also makes decision-making, speed
changes, random trials and controller timers four times faster. Leaving it at
legacy cadence while fine-integrating cached physical rates is a possible
architecture, but the speed change currently applied on a controller visit must
first be separated from instantaneous events and expressed over its actual
update interval. Merely smoothing positions would not accomplish the requested
fine-step simulation.

Measured in a race (§9): an opponent's speed and heading rate change every 8 ticks
(3,894 of 3,937 intervals), its lateral rate every tick, and its next pose follows exactly
from its record.

Record fields are also used for lookahead. `0211c4..0211d6` uses speed/16 to choose
a future track point; `021016..021022` combines lateral position with multiples
of lateral rate. These are prediction horizons, not necessarily displacements
for the next fine tick. Preserve their time horizons independently.

### Critical dual-purpose player fields

`0223a8` publishes the detailed player into this simpler car model:

- `0223ba..0223c8` derives record +14 from the difference between the new player
  lateral coordinate and the old car-table coordinate.
- `0223cc..0223e0` also stores record +36 = +8 plus 8 × that difference (falling
  back to +8 when the difference exceeds ±2000): an eight-tick lateral prediction
  that would become a two-tick one if the difference shrinks to a fine step.
- `0223f4..022426` derives record +12 from the difference in track position,
  shifted left 8, also storing it at `0252d0`.
- The immediately following field loop uses these values to advance the player's
  car-table position to match the newly calculated player position.
- Collision prediction, relative-speed calculations and sound consume these
  fields as velocities elsewhere.

With fine steps, leaving these differences alone publishes one-quarter native
speed to those consumers. Multiplying by four instead makes the existing player
position-copy mechanism advance too far. A uniform patch to all cars is therefore
incorrect. Separate **pose synchronization** from **normalized physical velocity**,
and either bypass the generic movement for the player or give it its own path.
This is a required redesign, not optional polishing.

## 5. Contacts are the highest-risk part

### Wall and obstacle correction

`002f6e..003014` finds penetration, uses current/previous track positions to
construct a sliding correction, calls `00434e`, and retries the geometry.
The resolver applies both position and velocity changes:

- `00446c`, `00448c`: add whole-world-unit corrections to the high position words;
- `004474`, `004494`: add those corrections multiplied by 128 to velocity;
- `00447a`, `00449a`: clear the fractional position words `098ac`/`098b0`, so any
  added fractional shadow state must be cleared here too;
- `004434..00445a`: add related angular corrections to both yaw rate and heading;
- `0044fa..004532`: select damage from collision severity and orientation.

The factor 128 exactly matches the reciprocal of the normal position integration
factor in world units. Changing the integration step to h creates an ambiguity
that must be resolved from the intended contact model: a displacement-to-velocity
conversion over the new step suggests 512, while an impulse should not be divided
by four, and a continuous contact force would be integrated with h. The resolver
mixes these operations; it cannot safely receive one universal scale.

Smaller steps also reduce typical penetration. Damage/severity derived from
that penetration can shrink even when actual impact speed is unchanged. Keeping
old thresholds alone would then change crash outcomes. Conversely, applying a
single-impact effect repeatedly during sustained contact can multiply damage.
Position correction, velocity response, and impact-event severity must be separated.

### Car-to-car response

`022036..022066` tests crossing using relative position **plus relative native
per-tick velocity**. The predicted displacement for a fine contact interval must
get h, while the velocity used for impact severity at `02208e..0220b4` should
retain its physical units.

`022148..02223e` exchanges/changes car velocities. These are event responses,
not ordinary force integration. Low-severity handling also damps heading rates
(`02223e..022256`). A table prevents processing the same pair twice within one
field update (`021fec..022034`, cleared at `020f20`); four smaller updates create
four fresh opportunities for the same contact. Event identity/persistent contact
handling is therefore part of the conversion.

The player's collision bridge `021e12..021f96` reconstructs world velocities
from car-record velocities and adds heading-rate impulses, so it must agree with
the corrected player publication scheme. Collision-related random steering/view
kicks occur here as well. Their cadence must follow impacts, not arbitrary
substep count.

## 6. Slow state, clocks, replay and effects

There is no reason to make all code run at 59.7 Hz to obtain 59.7 Hz physical
motion. Preserve original-time decisions where appropriate:

| Code / state | Existing behavior and treatment |
|---|---|
| `00dec`, `00fee`, `011f0`, `013f2` | Four wheel blocks use countdown 10 for temperature-like three-node exchange, wear and grip calculations. Retain real-time cadence; accumulate/average driving inputs if needed. |
| `016dc..0181a` | Four further countdowns reload 40; target involves a temperature ratio and a relaxation. These strongly indicate pressure-related slow state. Retain cadence unless separately rederived. |
| `0240e..0256a` | Countdown 15 governs fuel subtraction, mass update and engine thermal/damage-like state. Do not run four times as often with unchanged decrements. |
| `0330e..03398` | Fractional clock: subtract 10 from a byte accumulator, add 15 on underflow, advance tenths. Calling four times faster makes the clock four times faster. |
| `03404..03430` | Lap-crossing time correction uses constant 7 times a position fraction. Must use the actual fine interval if crossing is detected every fine tick. |
| `021178..0211c0` | AI random trial countdown and RNG calls; preserve cadence/order where feasible. |
| `026abe..026bc8` | Records 33 poses (198 bytes) per call into the replay ring, with a 300-record count. Four-times recording shortens duration to a quarter unless sampling/storage/playback change together. |
| `02c3b4` | Effect lifetimes and indirect effect callbacks; unchanged four-times invocation changes lifetime and motion. |
| `039bc..03a7c` | Caution/race-state countdowns, including byte-sized timer 75; time-based, not physics rates. |

Thermal/pressure names above are dataflow interpretations (temperature ratios,
shared ambient input, per-wheel initialization and damage flags), not recovered
original symbols. Exact physical calibration still needs annotation.

Executing slow blocks once every fourth fine tick preserves their original
counter ranges. Multiplying every timer by four can overflow byte fields and
miss units embedded in formulas. Which sampled force/temperature inputs these
blocks consume must also be specified; simply choosing every fourth sample is
not equivalent to integrating a quantity over the interval.

## 7. Scheduler and display implications, from code

Keep the CIA base timer intact. The original `009c06..009c2a` four-tick request
handshake and frame-end trigger `00b592..00b5a6` both need replacement for a
one-CIA-tick physical deadline. Changing only the reload from 4 to 1 leaves the
frame-coupled handshake and does not establish a periodic 59.7 Hz simulation.

SOFT is disabled while the renderer copies state (`007da`/`007e4`, cockpit
`0015a..00296`). A single pending interrupt bit cannot count several missed
fine ticks. A scheduler needs an explicit elapsed-tick/debt count and bounded
catch-up behavior while preserving atomic publication and avoiding reentry.
Four substeps executed in one old 67 ms burst do **not** give four-times-faster
input response; the steps must actually be distributed over CIA time.

The current motion code also hard-codes a four-CIA-tick interval (`Indianapolis500_Motion.s`).
Fine-rate snapshots require a one-tick interval, or a different presentation
policy. Ordinary previous/current interpolation at the fine rate still delays
presentation by roughly 16.75 ms rather than 67 ms. Removing it displays the
latest completed physical state with variable sample age. At 59.7 Hz on a 50 Hz
display that age varies frame to frame, which is visible; §9 picks the field rate instead.
Faster simulation does not itself make the PAL renderer draw more frames or remove other
latency.

## 8. Recommended implementation boundary and remaining analysis

The most contained design is a **two-cadence simulation**, keeping existing
state units:

1. Each fine step (one per PAL field, §9): sample eligible controls, integrate the
   player's physical motion with h, resolve its wall contacts, publish a coherent state.
   Opponents need no fine step: their motion between controller visits is exactly known
   (§9).
2. Each fourth fine tick: run the selected original-time decisions, timers,
   thermal/wear updates, replay sampling and effects. Keep the opponent-controller
   round-robin schedule's time base, while converting its physical outputs into
   correctly timed rates rather than speeding up the decision loop.
3. Keep rendering independent. Give the renderer snapshots with their actual
   simulation timestamps; update or bypass the old interpolation policy.

This does not require rewriting the renderer or the geometry/trigonometry tables.
It does require new patch routines, independent fractional state, initialization
and reset handling, and enough separation inside the large SOFT handler to avoid
rerunning slow/event code accidentally. Fractional state can live outside the
86-byte car records, avoiding a change to their many hard-coded strides.

Before a safe implementation, finish these code-analysis deliverables:

- A writer/reader inventory for all velocity/rate fields, explicitly classifying
  continuous integration, pose synchronization, prediction, and collision writes.
- Full recurrence equations for the load-transfer states, road-sample differences,
  their previous-force delay, and the low-speed stabilizer.
- A contact specification separating projection, impulse, continuous contact and
  damage/event accounting; audit both player and AI wall paths.
- A per-car controller contract: update interval, output units, lookahead, RNG,
  event state and all indirect handlers at record +38. Only needed if opponents are ever
  stepped finer; the design above leaves them at the original cadence.
- Precise policies for input edges, initialization/pit resets, pause/view/replay
  transitions, slow-state inputs, and lap-crossing timestamps.
- A handling contract: finer integration of the inferred model versus deliberate
  preservation of the original coarse integrator's response.

Those are concrete blockers to a complete patch, not evidence that conversion
is impossible. Translation, basic force accumulation, simple rate limits and
scalar filters are tractable now. The coupled dynamics and contacts require
more derivation. The CPU cost is measured in §9.

Relevant comparison: AmigaXDev `docs/playbooks/fixed-time-simulation.md` (from
Test Drive II and Stunt Car Racer) separates native units, fractional carries,
coarse-Euler response and prediction horizons, and explains why mixed
position/rate variables defeat blanket scaling. Those projects' constants and
damping choices do not transfer to this game.

## 9. Assessment

**Checked in the disassembly:** the position integration and ±12 dead
zone (`02c56..02c88`), the velocity/yaw additions with `asr.l #6` and `divs` by
`09adc` (`02b9a..02bfc`), the low-speed yaw rule (`02c08..02c2e`), the filters
(`0233a`, `02376`), the ±250 slew limiter, the ×13 mouse derivative, the
field-loop record offsets and 24-bit track position, the four controllers per
SOFT (`dbf` from 3, 86-byte stride, player at the wrap), the ×128 resolver
velocity, the clock, the CIA four-tick handshake and the player publication.
The Euler arithmetic in §2 (fine movement `v0 + 5A/8`, the 3/2 correction) is
right.

**Integer quantization is the general problem, not the gains.** Nearly every
fine-integrated state is a word with no fraction: `098b2/4`, `098ba/c`, record
+8/+10/+14, `09a2e`, `09a30`, `09b02`. Quartered `divs` results truncate toward
zero, so small forces vanish and filter dead bands widen. Every such state needs
a long shadow (or remainder) that every writer, including collisions, resets
and pit/initialization code, keeps consistent. For rules defined "per original
tick" (the ×13 derivative, the +36 prediction, the publication differences), the
simplest exact conversion is a four-fine-step history (difference against the
value four steps ago), not a rescaled coefficient. It keeps the horizon and
avoids amplifying position quantization by four.

**Coarse-step stabilizers.** The low-speed yaw rule averages the new yaw rate
with the previous one when the sign flips below speed 1000. That is a damping
fix for oscillation in a 67 ms integrator. At a quarter step the underlying
oscillation may not exist, and the rule then adds damping the original never
had. Rules like this need a decision, not a conversion.

**Verification changes category.** Everything so far was accepted by bit-exact
twins (pixels, per-tick state). A finer simulation cannot be twin-tested even in
principle. Acceptance would need behavioural metrics (braking distance, lap
times at fixed input, AI race order and spacing, collision/damage statistics,
replay length) and a tolerance the user agrees to. This is a large part of the
cost, and the existing tools do not cover it.

**CPU budget (measured).** `tools/soft_timing.py`, race fixture, cockpit, 256 ticks; times
include the interrupts that preempt SOFT:

| Machine | Whole SOFT | Player physics `00bf8..03138` | Field update `020d26` |
|---|---:|---:|---:|
| 68030/25 + fast RAM, `DCache` | 0.81 ms | 0.37 ms | 0.30 ms |
| 68EC020/14 + fast RAM, `DCache` | 2.79 ms | 1.60 ms | 0.85 ms |

A tick is 67 ms. Running the whole simulation four times as often would take 5% of the
68030 and 17% of the 68020. The player physics alone at 50 Hz would take about 2% and 8%,
before the extra cost of the long shadows. CPU time does not decide feasibility on the
machines the option runs on. The A500 stays out: its demo path alone takes 0.52 field per
tick.

**Opponents need no faster simulation.** The field loop moves each car by rates its
controller set before the tick, and the controllers change them only after the movement
(§4). So when a SOFT ends, every opponent's pose at the next tick is already fixed. Checked
against per-SOFT snapshots of 1,008 race ticks (32,256 car-ticks): the next track position and
heading follow exactly from the record in 100% of cases, the lateral position in 99.95% (the
misses are contacts). Advancing an opponent by α of its own per-tick rates is the field loop's
integrator evaluated at the display time, with the controllers at their original cadence.
It is neither an estimate nor a delay.

This also explains how the presentations look in driving. Speed and heading rate change at
controller visits, every 8 ticks per car. The lateral rate changes every tick by the lateral
acceleration. Extrapolation continues the last tick's motion and corrects at the next tick,
so the cars jump:
- along the track: 0.1 m on 50% of ticks, up to 0.8 m. Part of this is the motion code
  dropping the fraction byte +5;
- sideways: on 80% of ticks;
- in heading: up to 4.1° at controller visits.

Interpolation never jumps, but it shows everything 67 ms late, and the control lag is
noticeable. The player's car is different: its next state depends on input that has not been
read yet and on the four-wheel model. Only a faster player simulation removes both the delay
and the overshoot. That is the conversion in §2–§5.

**Run the player at the field rate, not at four CIA ticks.** Without interpolation, every
frame should show a real simulated state. Frames are swapped at the PAL VBL (50 Hz).
- One player step per field (h = 59.70/200 ≈ 0.2985 of an original tick) puts every frame
  on a simulated state, whatever whole number of fields the frame takes.
- Four steps per original tick (59.70 Hz) would advance 1 or 2 steps per frame at 50 fps
  (about every fifth frame advances twice), and 2 or 3 at 25 fps. That judder would itself
  need interpolation.

The conversion work is the same for any h. The parts that stay at the original cadence keep
running from the CIA tick: opponent controllers, contacts between cars, slow state, clocks
and replay recording.

**What stays at 14.9 Hz.** The demo has no input, so its interpolation delay is invisible;
keep it. Replays are recorded per tick (33 poses, 300 records); smooth replays would need
either interpolation or a ring 3.35 times larger. Effects and the HUD stay per tick.

**Assessment.** The physics analysis is sound, the conversion is technically plausible,
and CPU time is not an obstacle. Can driving avoid interpolation and extrapolation
entirely?
- **Opponents:** yes, cheaply and exactly (above).
- **The player's car and the camera:** only with the converted player physics at the field
  rate. That rewrites the game's handling and needs behavioural rather than exact acceptance.

Ordered path:
1. Advance every opponent record by its own rates, and keep the camera and the player's
   record extrapolated. This is what `Custom1=1` now does in driving (slave.md). The
   player's record must not use its own rates: its `+12`/`+14` are the last tick's motion,
   but its heading rate `+16` matches the last tick's turn in only 281 of 1,008 ticks.
2. Not pursued (the user's decision): the player-only fine integrator at 50 Hz
   (translation, yaw, force accumulation with long shadows, wall contacts). Opponents,
   controllers and slow state would stay at the original cadence. Acceptance would compare
   braking distance, lap times at fixed input and crash outcomes.
