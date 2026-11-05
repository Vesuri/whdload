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
| Movement and geometric collision checks | 20 ms |
| Controls, orientation, resources, engine decisions, opponents | 90 ms |
| Repeated contact penalties, damage and age counters | Control epochs |
| Fall/impulse displacement | Integrated over each world step, split at effect boundaries |
| Weather generation | 80/140 ms according to effect state |
| Weather visual publication | 20 ms after its generation boundary |
| Cockpit liftoff movement | 100 ms per native movement step |

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

## Inputs, pause and sessions

Input edges and axes are timestamped using the unpaused clock and consumed by
logical control deadlines. The scheduler does not repeatedly sample a new physical
input for every catch-up step. Queue/accounting checks detect lost or duplicated
work, release ordering and overflow.

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
