# Timing design and validation

The normal slave contains the full scheduler. **Enhanced framerate** (`CUSTOM1=1`)
enables it together with fast planar rendering on 68020+ with real fast RAM.
The checkbox defaults off. Unchecked, on 68000/68010 or without real fast RAM,
both paths remain original. CUSTOM3 is no longer a user option; its internal
storage and `bit=C3` timing-range annotations retain their diagnostic meaning.
WHDLoad CACHE/DCACHE remain user-controlled.

The release matrix is complete with the accepted M3 exception;
[open work](open-work.md) records the measurements and validation limits. Steady A500 handling and unseeded natural-weather validation are deferred
by the user, not passed. Physical accelerator-board tests are also deferred.

All game addresses below are offsets into the code hunk. State-field offsets are
relative to the native state base at hunk `$a6e`. Captures and built slaves remain
under ignored `tmp/`.

## Timing policy

The scheduler targets representative A500 handling. It does not reproduce the
original game's scene-dependent slowdown. Native braking histories ending at
speed 108 versus 53, impulse histories of 800/900/1,120 ms, and pilot 1 visibility
differences are accepted policy outcomes, not exact-match requirements. Opponent
word `$54` is presentation-owned and recomputed by projection.

The original game computes displacement from elapsed time but clamps the delta
and advances several gameplay operations once per rendered frame. Keeping its
native path on slower configurations preserves those limitations. There is no
second, slower fixed-step scheduler in the release configuration.

On the enhanced path, physical PAL fields advance logical time independently of
rendering. One native clock unit represents 5 ms; a PAL field is four units.
NTSC is not supported by this timing policy. A CPU that cannot service the required
work can fall behind; retaining time debt does not guarantee real-time throughput.

| Work | Logical cadence |
| --- | --- |
| Movement and geometric collision checks | 20 ms (crash depth over a 90 ms frame) |
| Mouse orientation integration | 20 ms |
| Opponent movement | 20 ms ([opponents](#opponent-movement-and-contact)) |
| Control decisions/input consumption, joystick orientation, resources, engine decisions, opponent decisions | 90 ms |
| Visible-opponent animation, contact and effects | 120 ms (measured A500 cadence with opponents in view) |
| Repeated contact penalties, damage and age counters | Control epochs |
| Fall/impulse displacement | Integrated over each world step, split at effect boundaries |
| Weather generation | 80/140 ms according to effect state |
| Weather visual publication | 20 ms after its generation boundary |
| Cockpit liftoff movement | 100 ms per native movement step |
| Pit arrival rise | 100 ms per native height step |

There is no render interpolation or additional display buffer. At lower rendering
rates, a frame shows the latest completed simulation state. The renderer uses the
original planar format; [the renderer design](performance-implementation.md)
describes fast-memory staging and chip-memory publication.

## World scheduling and integration

`timing.s` selects the complete fixture-free configuration with `TIMING_FULL=1`
by default. The individual feature symbols remain available for diagnostics.
All test fixtures default off and seed overrides default to native RNG. They are
not enabled by normal builds. `periodic.s` installs the scheduler only when the
resolved runtime timing option is enabled.

The allocator at `$ca44` accumulates unpaused elapsed time. Each pass assigns at
most 32 world steps and retains excess debt. Each completed step advances the
world cursor by four units. Nested presentations cannot replace the current
movement delta with an outer-frame delta. Nonlocal game exits restore temporary
counter/RNG ownership before rendering or leaving the session.

Control deadlines advance by exactly 18 units. Their service on world boundaries
alternates 100/80 ms without accumulating drift; input selection uses the ideal
control timestamp. Rendering frequency does not determine the number of updates.

The displacement division at `$ccf6` carries a signed remainder modulo 24. The
three vector shifts at `$cd32` carry remainders in 0..4095, retaining native signed
arithmetic-shift rounding. Subdividing movement therefore does not repeatedly
throw away fractional displacement. Initialization resets integration remainders.

Fall and impulse vectors describe displacement per 90 ms effect epoch. Their
wrappers scale by elapsed logical time and split a step at an effect-age boundary,
carrying signed remainders. Geometric collision checks run every world step;
repeated contact feedback/speed penalties at `$fb64`, damage at `$fb84` and age at
`$cde2` are limited to control epochs. Different simulation policies need not give
identical collision trajectories; there is only one enhanced physics rate here.

### Track collision

The track collision at `$fa18` runs once per world step (`$cece`). Its outcomes and how
each is owned on the enhanced path (`timing_collision.s`, `timing_world20.s`):

| Native test or effect | Depends on | Enhanced handling |
| --- | --- | --- |
| Plane distances `$ac72` (contact below 100) | position | every world step |
| Crash depth `$ad5a`: one call ≥ 819,200 below a plane | movement per call | scaled to an A500 frame |
| Impact speed `$fac8`: `$132`·normal / 7,500 > 110 | velocity | every world step |
| Repeated contact `$fa7a` within 100 clock units (`$24c`) | clock | every world step |
| Restore the saved position `$186..$18c` (`$fae2`, `$faf2`) | position | every world step |
| Wall stop at zero speed, reposition `$fb44` | state | every world step |
| Floor-tile palette flash `$fb3e` (`$16e6c`) | per call | control epochs |
| Wall flash and speed −10 `$fb64` | per call | control epochs |
| Contact count, nose-angle damage `$fb84..$fc9c` | per call | control epochs |
| Orientation candidate rejection `$cc84..$ccb2` (`$24a`) | orientation | every world step |
| Stick damping after a rejection `$d05e` | per control update | control epochs |

The crash depth is the only geometric test whose result depends on how far the ship moved
in one call. Natively a call covers one rendered frame, about 90 ms of movement on the
A500 (11.4 fps); a world step covers 20 ms, and the contact response restores the saved
position each step, so a nose-first dive never reached the depth. The ship was then held
against the floor with every candidate rejected, the stick damped instead of read, and no
crash or reposition to end it. `timing_collision_depth` compares the distance before the
step (from `$186..$18a`) plus 18/4 of the step's travel towards the plane, in 64 bits.

In a 060/50 capture that pushes the nose into the floor, the original game crashes at
field 316 and repositions (`$fc9e` → `$109d8` → `$100c2`); the enhanced path now does the
same at field 321, and the stick then answers the mouse (`tmp/floor/native-060`,
`fixed2-060`). Before, it stayed rejected for the rest of the 1,300-field capture and a
pull of 1,000 counts did not move the stick (`tmp/floor/old-060`).
`tools/check_collision_depth.py` checks the arithmetic.

The 66,000-field 060/50 coverage soak ([gameplay coverage](gameplay-coverage.md)) passes
`--require-long` with no failures both before and after these changes
(`tmp/collision/base-race`, `new-race`). Before: 2 track-collision responses, 23,214
`$fb84` entries, 11.5 instrumented fps. After: 4, 23,015 and 12.4. Both runs reach the same
2 rescues, 2 pit returns and 34 departure iterations; only the later run reaches the
weather effect (174 draws). The trajectories diverge after the first crash at field 2,430;
the tape is timed in PAL fields, and the old floor flash waited for the display inside
world steps. A soak does not attribute the extra crashes to either change.

## Opponent movement and contact

The native opponent update (`$d3d6`, every 90 ms control update) advances each opponent's
track progress `$66` by speed × interval / 26, with fuel-empty and `$4b8` halving, damage
countdown scaling and a minimum of 40, plus a random ±40 per call. It then rebuilds the
position `$10..$14`, heading `$20` and segment `$2` by blending two path nodes
(`$d626..$d69a`) and the player distance `$4c` (`$d724..$d756`). It also owns the per-call
pit, damage-countdown, hold-zone and lap work, the race finish and the nearest-opponent
engine sound.

`timing_opponent_motion.s` (`TIMING_OPPONENT_MOTION`) leaves that update as the authority
and moves the opponents between updates. Before an update it restores the progress the
previous update produced, so the native work runs exactly as before. After it, the slave
predicts the next update's advance with the native formula, without the random draw. Each
20 ms world step then advances the shown progress by 4/18 of that, plus 4/18 of the gap
between the shown and the authoritative progress, never backwards. Gaps over 1,024 units
(repositioning) are applied at once. The shown progress stops at the lap line until the
update that counts the lap, then carries across it. Position, heading, segment and
distance are rebuilt from it with the native arithmetic. Pit and retired opponents keep
the native progress. The per-opponent table is in the fast arena at `$9600`.

The visible-opponent work at `$9950` holds the contact tests. Within a distance of 100,
`$9a74..$9a94` knock the player in a random direction (`$9c84`, `$1da..$1e4`, integrated by
`timing_forces.s`), add player damage (`$9d04`), bounce the opponent (`$9b6a`) and play
the impact sound. A faster opponent within 80 progress units of another and closer than
100 loses 50 speed (`$9b1a`). This work runs every six world steps (120 ms), the cadence
measured for the A500 with opponents in view (nine animation updates in 920 ms). The
native frame order adds a visible opponent's bounce offset `$36..$3a` to the position its
update rebuilt; on world steps without that tick the slave does the same after rebuilding.

| 060/50, coverage race | 90 ms movement | 20 ms movement |
| --- | ---: | ---: |
| Frames where an opponent moved (300 frames, about 46 fps) | 73 / 299 | 299 / 299 |
| Speed per frame, mean / s.d. (world units per clock unit, pilot 1) | 24.7 / 44.4 | 25.1 / 7.0 |
| 66,000-field soak: player contacts / opponent slowdowns / track crashes | 3 / 2 / 5 | 2 / 3 / 5 |
| 66,000-field soak: native opponent updates | 58,990 | 58,992 |

The soaks (`tmp/contact/base-race`, `new-race`) follow the same route: crashes at fields
2430, 2473, 2528/2530 and 2651 in both. The new one passes all 15,693 drawing twins with no
failures. The frame samples are `tmp/contact/frames-base`, `frames-new`. The contacts are
too few to compare their rate. `tools/check_opponent_motion.py` checks the arithmetic
against the native code. The CPU cost has not been measured.

## Fine mouse rotation

`TIMING_MOUSE=1` is part of `TIMING_FULL`. It is selected by the existing
**Enhanced framerate** checkbox, with the same 68020+/real-fast-RAM gate. Set
`TIMING_MOUSE=0` only for diagnostic comparisons. The native fallback retains its original hooks; checked-option A500 and
unchecked A1200 name-screen snapshots verify this for the current build.

The mouse is a held turning command, not a direct heading offset. The native
`$d0a8` gain (136/256) and `$d11c` per-ship calibration divisors are retained.
The patch preserves their discarded fractions in Q12 (1/4096 degree per 90 ms),
without changing the native integer fields used by other control decisions.
For the measured setup, horizontal/vertical divisors are 55/38: a single mouse
count now produces a nonzero rate even when the native angle rounds to zero.
Input history and control decisions still use the 90 ms cadence; this change does
not promise 20 ms input latency.

Held mouse rotation is integrated every 20 ms, scaled by 4/18. Fractional time
conversion is carried between control epochs. Within an epoch, each candidate is
recomputed from its saved starting matrix and cumulative angle, avoiding repeated
rounding from subdividing a single turn. A private Q28 matrix preserves orientation
between epochs; the native game/renderer receive rounded Q14 matrices. Q30 sine
and cosine come from a mathematical quarter-wave table generated at build time
(23,044 bytes), with 1/64-degree entries and interpolation to Q12 angles. No native
lookup-table units or renderer format change.

The patch replaces the three-rotation call sequence at `$cc58`; native candidate
validation/acceptance from `$cc66` remains in place. Rejected candidates clear
pending fractional rotation. A control update that took contact damping (`$d05e`) uses
the native whole-degree rates: the damped stick settles at −1..−9 under `ASR`, which the
native division turns into 0 degrees, so the next candidate is the current orientation and
damping ends; a retained fraction would keep pressing into the floor. A native matrix
replacement rebases the private matrix; session/pit initialization clears it. Joystick and animation paths retain
the native rotation routines. Weather/banking/control decisions retain their
existing cadence. This is simulation rotation, not display interpolation.

`tools/check_mouse_math.py --ticks 30000` executes the actual assembly with the
shared Unicorn runtime. It checks 2,949,120 signed fractional angles, 2,056 input/
calibration combinations, both signs of sustained turns, rejection, native matrix
replacement, joystick fallback and reset. Ten-minute constant-yaw tests have less
than 0.003 degree final heading error and less than 0.011% row-length error against
the specified Q12 rates. These are isolated arithmetic tests, not a ten-minute
in-game handling test. Three in-game single-count tapes (020, 060 and a 060 draw
cap of 10 Hz after 200 world steps) match all 499 common private/native steering
states, with 126 matrix changes between control epochs in each capture. Both axes
respond in both directions and no input queue overflows. The uncapped 060 tape
spends most of the window at one display field per frame; the capped portion uses
five fields. The tape is correctness evidence, not a performance benchmark.

Uninstrumented Practice throughput is 24.089 fps on 020/fast versus 24.291 with
`TIMING_MOUSE=0` (0.833% lower), and 45.591/49.098 fps on 060/50 with NoCache/CACHE.
These are 500-field route measurements; different orientation/scene inputs mean
the comparison is not an isolated routine-cost measurement. The full older release
matrix has not been rerun for this feature. [Open work](open-work.md) records that
scope and the remaining unrelated validation limits.

## Inputs, pause and sessions

Input edges and axes are timestamped using the unpaused clock and consumed by
logical control deadlines. The scheduler does not repeatedly sample a new physical
input for every catch-up step. Queue/accounting checks detect lost or duplicated
work, release ordering and overflow.

Natively the mouse stick is one pair of words, `a6+$42a`/`$42e`: the VBL server at
`$56d2`/`$56fc` adds each field's mouse count to it, contact damping at `$d05e`..`$d086`
writes it, and `$b6e4`, `$eab2`, `$ebd0`, `$100c2` (reached from the A reposition at
`$c7e6` → `$fea6` → `$10092`) and `$140a4` reset it to zero. The controls read a
private copy instead, so the enhanced layer keeps the two consistent:

- Player movement is only the per-field mouse count, taken at the two VBL additions.
  Those counts are queued; nothing the game writes to the stick is read back as
  movement. Coverage tapes enter through the same routine.
- Contact damping sets both the private copy and the raw words.
- The five resets clear the raw words, the private copy and every count not yet
  consumed (pending or queued), with interrupts masked, so A recentres the stick.
- Every stick sum saturates at ±32767: the raw words, the pending counts and the private
  copy. Nothing wraps, and the native `NEG.W` of an axis cannot overflow.

The previous layer queued differences of the raw words. A reset was therefore queued as
an equal and opposite movement and added to a private copy that damping had already
reduced: pushing the nose into the floor, waiting, then pressing A left the stick at
full deflection the other way. `tools/check_input_axes.py --baseline <revision>`
reproduces that against an earlier `timing_input.s`.

Pause entry `$be12` and the native clock restoration at `$beec` preserve the
fractional control phase and pending work. Paused PAL fields are excluded from
both scheduler and input time. Paused input changes do not leak into resumed play.

Fresh entry initializes the session's clocks, input and integration state. Restart
and result transitions explicitly close ownership. Rescue/pit transitions separate
inactive player simulation from modal opponent work; any interrupted assigned
steps are recorded as discarded session work rather than silently lost time.
Returning from a same-session pit visit preserves the appropriate residual phase.

Opponent simulation and projection are separated. Modal pit updates and flight
updates use logical deadlines, while projection retains presentation-specific
scratch. Opponent repair start/expiry at `$d4b6/$d4fe` read the same continuous
opponent deadline. A sampled native-clock offset previously made repair completion
vary by render cadence; the continuous clock passes the corrected endurance pair.
Outside scheduled ownership the original reads remain native.

Lap/result timestamps use retained logical epochs so native lap-counter resets do
not rebase gameplay duration. Messages have explicit logical expiry ownership.
Initialized-lap pause, rescue, restart and a natural ten-lap finish have dedicated
validation evidence; menus and title-demo camera playback are not converted into
fixed-step gameplay.

## Pit departure and repair display

The cockpit departure at `$1020e` contains nine movement iterations. Its position
and speed updates at `$102d0` are originally per-frame. The enhanced path preserves
the native sequence and final speed of 90, pacing each step to the measured A500
100 ms interval. Initial setup/drawing time is separate from that movement cadence.

Between steps the enhanced path draws extra views (`DEPARTURE_INTERPOLATE`, default 1).
`$10304` (the `MOVE.W`/`CMP.W` before the view choice) enters `departure_blend` after
the step's position update. While one more view and the native view still fit before
the step's deadline, it publishes the position blended from the previous to the current
step for the time the view will be shown (`$12c..$130`, negated at `$3ac..$3b0`), draws
the view the native loop selects for that height (`$10338`, or `$1572e` at or below
−140), and presents it. It then restores the exact position and replays the two
instructions; the native view and its present at the deadline are unchanged. The frame
counter `$5e` is restored after each extra view. A view that does not fit is not drawn,
so a machine with no spare time presents the native steps only.

On the A1200 with a 68030/25 or 68060/50 and fast RAM, each departure view takes two
PAL fields (eight clock units, measured with `-DDEPARTURE_DIAGNOSTICS=1`), so one blended
view fits per 100 ms step: 20 presentations per second instead of 10
(`tmp/liftoff/interp-030`, `interp-060` against `step-030`, `step-060`). In all four
captures the nine native step states, the 100 ms step period and the final state match
the A500 reference. With and without blending, the state at all 96 common world steps
on the 030 is identical except the native frame-interval word `$21c`, which the scheduler
overwrites before every world step. More views per step would need a faster departure
view; that has not been attempted.

The pit arrival rise at `$1459a..$145bc` (`timing_pit_rise.s`, `TIMING_RISE`, default 1)
draws the ship at 15 heights from the table at `$144ae`; each step calls the `$102`
sprite (`$1461e`), the ship pieces (`$1432e`) and the pit frame (`$e296`). Natively a
step lasts as long as its drawing: five PAL fields on the A500, four on a 68020/14 and
three on a 68040/25 or 68060/50. The enhanced path starts a 100 ms deadline at the first
step (`$1459a`) and, at its end (`$145b8`, the `MOVEM`/`DBF`), draws extra frames while
one still fits before the deadline: the ship at the height blended towards the next
table entry for the time the frame will be shown, skipped when the rounded height has not
changed. During an extra frame `timing_repair_service_gate` reduces the pit frame's
service part to the HUD clock, so the frame counter, keyboard and opponents advance only
with the native steps. Deadlines retain overruns. The `PDRISE01` tag holds the last extra
frame cost, the deadline, the number of extra frames and the number of rises.

On the A1200 with fast RAM a pit frame costs three fields on the 040/25 and 060/50 and
four on the 020/14 (`tmp/rise/m7`, `m5`, `m4`). The 15 steps now span 72 fields against
the A500's 70 (`tmp/pit-anim/a500`) instead of 45 natively (`tmp/pit-anim/m7-c1`), with
nine extra frames on the 040 and 060 (24 frames, about 16.7 fps) and one on the 020. At
the rise's return (`$145c0`, `tmp/rise/r7` against `q7` with `-DTIMING_RISE=0`) the frame
counter `$5e` is the same; the remaining differences are the display buffer parity
(`$3b2..$3c0`) and clock-derived words. The later pit animations are unchanged.

The external pit animation at `$14764` is a different native sequence. Menus,
recorded title-camera progression and other presentation animations retain their
native behavior. Repair service uses elapsed logical time and suppresses late
intermediate drawing rather than accumulating extra service through rendering.
The title-camera pacing proposal was optional and was not selected.

## Weather ownership

Forecast trials, onset, expiry and fade progression execute on logical deadlines.
Native forecast and duration arithmetic is reused; ownership transfer translates
pre-existing deadlines into the logical clock domain. Native sentinels and the
expiry polling condition are retained.

Generation and visible publication have separate clocks. Drawing may occur more
or less frequently than logical effect publication, but it must not advance
simulation RNG, decrement lifetime again or change the next logical deadline.
Effect drawing temporarily uses its recorded visual seed and restores ownership.

Logical fades retain the native integer palette interpolation and gear changes.
Presentation consumes the latest pending fade state, permitting intermediate visual
steps to coalesce without changing logical progression. Both prepared Copper lists
must receive the expected palette and bitmap plane pointers. Palette restoration
has its own ownership and entry/return checks.

Sound requests are delivered directly at logical weather generation through the
native helper `$17836`, before native selection RNG. Native mute and resource
availability checks remain active. The helper may wait for audio DMA; that elapsed
time enters the ordinary debt ledger. Catch-up can issue historical requests close
together in physical time; it does not reconstruct audio during an external stall.
There is no deferred weather sound queue.

Directed full-cycle, audio, effect and fade tests are separate from natural weather.
The unseeded ten-minute race made 6,574 forecast trials without an episode, so it
cannot establish natural effect expiry or palette restoration. The user deferred
that gate. Directed visible-colour validation does not remove this limitation.

## Validation contracts and results

Correctness captures may contain extra rendering/probe work. Their presentation
rates are not release-performance measurements. Performance uses uninstrumented
500-PAL-field `SWAP_ONLY=1` windows at `$bc7c`, with complete interval counts and
cache configuration recorded. See [development](development.md) for capture setup
and [internals](internals.md) for measured throughput.

| Gate | Current accepted evidence |
| --- | --- |
| Cross-CPU logical state | Six accelerator captures: 501 common world states and 111 control/input/fuel updates match |
| Pause and sessions | Pause, fresh restart, initialized-lap pause and rescue ownership/accounting pass |
| Natural race finish | Ten-lap opponent victory has exact logical result time and native sorting/register behavior |
| Stalls | Observed 100/260/500 ms holds recover exact common state with zero endpoint debt |
| Requested render cadence | Ten 10/15/25/50 Hz/unpaced cases match 651 common world states and 144 control/input/fuel updates |
| Endurance | Corrected 600-second pair matches 30,001 common world/RNG states and 6,666 control/input/fuel updates; zero endpoint debt |
| Directed visible weather | Three phases match exact logical/Copper colours within the derived JPEG bound |
| Steady A500 handling | Deferred: acceleration passes; stopping reference and fuel comparison unresolved; straight-line speed not evaluated |
| Unseeded natural weather | Deferred: no episode in the ten-minute retry; expiry/restoration untested |
| Title demo pacing | Optional change not selected; no corrected-duration claim |

Requested 25/50 Hz cases did not sustain those rates under verifier overhead.
They establish deadline accounting and equality at common logical times, not
achieved 25/50 Hz scanout. Renderer twins compare pure drawing for the same input,
not gameplay trajectories or whole-game timing coverage.

The representative handling bounds remain: straight-line speed within 5%;
acceleration to 130 and stop within 10% or 90 ms; fuel within 10%; weather onset,
duration and fade within 10%. Deferral does not widen these bounds or count the
unverified rows as passes. Scene-dependent native histories are not exact oracles.

## Checks and diagnostics

- `check_disabled.py CAPTURE --timing` checks relocated native bytes across all
  declared rendering and timing hook ranges. M1/no-fast-RAM fallbacks and the unchecked default
  must leave those hooks native.
- `check_timing_layout.py` audits complete instruction boundaries and direct
  branches. Every timing patch carries a `TIMING_RANGE` comment.
- `check_timing_world20.py`, `check_timing_capacity.py` and
  `check_timing_integrator.py` check fixed steps, bounded allocation/debt and
  arithmetic. Capacity's exact contract is an unpaused single-epoch flight window.
- Input, brake, control-order, resource, engine and opponent checkers compare
  complete common logical histories. They do not mask unexplained state differences.
- Pause, session, rescue, lap and natural-result checkers require their corresponding
  fixtures/probes; a missing event is not silently treated as a pass.
- Weather cycle, effect, fade, palette, Copper and sound checkers have separate
  contracts. Seeded full-cycle assumptions do not apply to arbitrary unseeded races.
- `check_weather_screen.py` checks three stable phases of one directed fade,
  exact native palette arithmetic and both prepared Copper lists. The profiler
  stores JPEG images, so flat weather regions use a derived DC-quantization bound;
  this is not exact whole-screen RGB equality.
- `perf_status.py` checks completed renderer twins, registers/CCR, scratch, guards
  and unchanged copied raster code. An active unfinished draw is not a completed twin.

Diagnostic records include `PDTIME01` (allocation), `PDW20T01` (world cursor),
`PDW20I01` (integration remainders), input/pause/session ledgers, opponent/lap clocks
and weather generation/publication state. Read the installed hooks and capture
metadata to locate live records; absolute addresses vary with memory configuration.

## Remaining limits

The no-fast-RAM and 68000/68010 fallbacks remain frame-dependent. Enhanced timing
assumes PAL. General real-hardware/cache certification, deferred handling and the
unseeded weather episode remain outside the accepted validation scope. Optional
native menus, external pit animations and recorded title-camera playback have not
been made framerate independent. The release matrix and documentation status are
reported in [open work](open-work.md); a green build is not evidence that every
runtime gate passed.
