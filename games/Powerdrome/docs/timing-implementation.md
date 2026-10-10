# Timing implementation and validation

Work in progress. `CUSTOM3=1` currently enables the isolated four-clock-unit minimum
movement interval (20 ms on the measured PAL setup) and 100 ms cockpit-departure steps. It is independent of `CUSTOM1` and off
by default. This is not yet a finished framerate-independence feature.

The separately compiled `TIMING_PERIODIC=1` development prototype schedules control and
resource updates at an 18-unit / 90 ms interval. `TIMING_ORIENTATION=1` additionally tests
steering integration at that cadence. It does not yet schedule
opponent recovery/randomness, collision damage, weather or all animation counters. Do not
ship or describe this prototype as complete. No cache policy changes are made.

## A500 calibration

The stock original-loader Practice capture `tmp/prof/timing-a500-original` uses 512 KiB chip,
1,536 KiB slow and no fast RAM. Its first 500-field window contains 105 sampled presentations;
the first-to-last sampled interval spans 9.12 seconds and 104 updates, or 11.404 updates/s.
Resource consumption is one unit per update in this route. The remainder of the 30-second
capture includes the ship resting after contact; it must not be treated as sustained driving.

The unmodified-game control fixture `tmp/prof/timing-a500-controls` uses the same A500 memory
configuration and the coverage loader with timing/fast rendering disabled. In its first
500 fields, 113 complete sampled intervals span 9.84 seconds: 11.484 updates/s. Resource
consumption is 220 units, or 22.358 units/s, with different controls than the Practice route.
The full 60-second window includes full view, maps, pause and other transitions and averages
8.1 rendered fps; it is not an appropriate universal gameplay cadence.

An initial **90 ms cadence (11.111 updates/s)** is 2.56% / 3.24% below those two ordinary
A500 update rates. It is 4.5 logical 20 ms ticks, implemented with a retained time remainder
rather than rounding to four or five ticks. This is a measured reference choice, not a claim
that the original game had one intended constant frame rate. Other modes need their own
baseline evidence before their timing can be accepted.

## Initial acceptance bounds

Freeze these before evaluating the periodic candidate. They supplement, not replace, the
[plan](framerate-independence.md#numerical-gates).

- Steady straight-line movement: within 5% across CPUs over matched collision-free elapsed
  intervals. Report integer displacement and measured raw/applied delta; do not use FPS alone.
- Acceleration/braking: time to chosen speed thresholds within 10% of the A500 route or one
  90 ms cadence interval, whichever is greater. Use matching timed controls and initial state.
- Resource consumption: within 10% of the matched A500 route while eligibility/controls are
  equal. Across CPUs, periodic invocation counts must match elapsed-time accounting within
  one boundary event; any conditional resource difference must be explained by input/state.
- Effect/recovery duration: match the selected A500 baseline within 10% or one periodic
  interval, whichever is greater. A baseline for each conditional effect is still required.
- Renderer correctness: zero pixel/register/CCR/scratch/guard mismatches. Timing-off hooks
  must remain native. Pause and mode transitions must not produce catch-up bursts.

These bounds do not excuse untested paths or turn coordinate discontinuities into distance.
`timing_report.py` reports sampled coordinate travel and the largest jump for diagnosis;
track-origin changes, resets, rescue and coordinate wrapping make it unsuitable as a lap
or unqualified total-distance metric.

## Tools and binary boundaries

`TIMING_STATE=1` adds read-only `PDTIME` samples to `tools/fixed_window.sh` in `SWAP_ONLY=1`
mode. It records clock, native delta, loop counter, speed/resources, position, controls and
selected incident state at each presentation. `tools/timing_report.py CAPTURE` summarizes
these samples and, for the periodic prototype, its initialized `PDTIME01` diagnostics.
All captures and binaries stay under ignored `tmp/`.

`whdload/timing.s` checks the native comparison and MOVEQ before patching the two immediate
values. `whdload/periodic.s` is excluded unless explicitly compiled with `TIMING_PERIODIC=1`.
Its tentative hooks preserve full instruction boundaries: `$ca44` for elapsed accounting,
`$ca74–$ca7b` for the returning control call, and `$d922–$d929` / `$d9a0–$d9a7` for resource
mutation while retaining the normal HUD drawing call. The prototype retains excess periodic
debt above its per-pass work budget; complete input and mode-transition handling is pending.

## Movement clock ownership during nested presentations

The movement block multiplies signed speed by the current delta, divides by 24 and
multiplies the result by the direction vector. Read-only probes at `$ccee`, `$cd2c`,
`$cd3a` and `$cde2` check this arithmetic and the saved previous position separately
from collision response. `tools/check_timing_movement.py` does not interpret coordinate
resets as distance or claim trajectory equivalence from correct multiplication.

`timing-movement1-a500` and `timing-movement1-030-twins`, using the fixed-seed boost
prototype, verify 32 and 56 complete movement calculations respectively, with no wind
adjustment in this route. The first reset incident occurs at field 128 on A500 versus
143 on 030. The extra incident control invocation follows that reset; it is not the
first source of the differing trajectory.

A specific elapsed-time ownership defect is visible on the 030: movement occurs at
fields 128 and 139, separated by 220 ms, but the latter uses a delta of four native
units, or 20 ms. Native presentation `$7f7a` stores its timestamp at `state+$218` and
its most recent interval at `state+$21c`. Intermediate failure-flash presentations call
that same routine, overwriting the interval before ordinary movement resumes. The
20-ms minimum alone therefore cannot make movement account for elapsed gameplay time.

The separately compiled `TIMING_MOVE_CLOCK=1` prototype measures time between movement
updates using the PAL VBL clock minus paused fields, independent of presentation calls.
It retains the first pre-entry native interval and the 20..250-ms clamp, then replays
the original signed speed multiplication. `PDMCLK01` exposes the raw interval, applied
interval, update count and cumulative time discarded above the upper cap. The current
`PDMCLK02` extends that block with the guest-observed post-multiplication CCR. It is off
by default, requires the input/pause prototype, and leaves other shared-clock consumers
unchanged. The checker verifies consecutive clock differences, the clamp, explicit
upper-cap losses and the delta actually used by movement. It does not establish correct
integration through multiple historical control changes, collision substeps or other
mode transitions; those remain separate requirements.

`timing-moveclock1-030-twins` passes 52 complete movement calculations and clock updates,
with 51 clean renderer comparisons and unchanged raster code. It records 490 ms lost
above the retained upper clamp and no time added by the lower clamp. This bounded run
proves interval ownership and arithmetic, not the movement-equivalence gate. Presentation
latency still feeds into discrete collision timing, and applying the latest speed over
a long interval is not equivalent to integrating historical controls throughout it.
The A500 counterpart verifies 33 intervals and records 1,460 ms lost above the cap. These
first captures use `Powerdrome-timing-moveclock1.slave`; review subsequently corrected
X-flag preservation around the bookkeeping in `Powerdrome-timing-moveclock2.slave`.
The initial results establish clock arithmetic, not the original wrapper's full CCR contract.

The corrected wrapper passes `timing-moveclock2-pause-030-twins`: 76 movement intervals,
49 excluded paused fields, no upper/lower-clamp time difference, five legitimate input
events, 15 brake events and 56 fuel updates. Its 75 renderer comparisons are clean, with
unchanged raster code. Movement timestamps additionally agree with independently counted
unpaused VBLs within one field of probe placement.

`timing-moveclock3-reg-030-twins` verifies 52 complete register/stack/CCR contracts, as
well as the clock arithmetic, and adds 51 clean renderer comparisons. The wrapper saves
and restores X before replaying native MOVE/MULS. Its guest-side MOVE CCR diagnostic
observes the expected flags, including zero products; earlier debugger-only snapshots
reported Z clear in those cases. Use the guest record for the CCR oracle. The current
`Powerdrome-timing-moveclock4.slave` differs from that verified binary only in the diagnostic
marker version byte; an exact binary comparison confirms identical executable code.
`timing-moveclock4-reg-a500` verifies all 33 corresponding arithmetic, clock and
register/stack/CCR contracts, still recording 1,460 ms of upper-cap loss and no lower-cap
addition. These ordinary failure/incident effects already exceed the retained cap; lost
time cannot be dismissed as an artificial debugger stall. Handling that time safely,
with historical controls and collision work in the right order, is required before the
broader movement-independence gate can pass.

Reproduce with the engine/heat build switches plus `TIMING_MOVE_CLOCK=1`, 250 fields and
probes `$ccee/$ccf6/$cd2c/$cd3a/$cde2/$fc9e/$fcea/$fec6`. The pause route uses `CUSTOM5=8`,
300 fields and additionally `$be12/$bef2/$d058/$d9a0`. The normal build excludes this clock
prototype. No rendering-rate or full framerate-independence claim follows from these
instrumented correctness runs.

## Complete-world extraction pilot

`TIMING_WORLD=1` is a development-only extraction experiment, not the final movement
rate. It requires the input and engine prototypes and excludes `TIMING_MOVE_CLOCK`.
Its temporary 90-ms world step tests whether controls, movement, track transitions,
collision response and opponents can execute together before drawing. The final plan
still calls for 20-ms movement timing with slower A500-calibrated periodic operations;
freezing all visible motion at 90 ms is not the release deliverable.

The repeated region begins at the existing logical control/orientation entry and ends
at `$cedc`, immediately before the pre-render helper and scene/HUD/timer drawing. Each
owed control now receives its own movement/collision/opponent pass rather than batching
all controls before one movement. Draws with no owed update skip that region. The
existing 32-update budget and retained periodic debt remain; movement uses exactly 18
native units per complete world update instead of dropping time above a frame clamp.
Brakes are serviced at logical control boundaries, preserving queue order; response
calibration must be repeated because movement-boundary brake servicing is disabled here.

The wrapper holds no extra native call frame while the world body executes. Native
stack unwinding remains unchanged. Temporary counter/random-state ownership is restored
at common mode destinations `$bf32/$bfb0`, covering known exits from rescue (`$ce32`),
pit handling (`$f83c`), incident recovery (`$fe90`), opponent completion (`$d616`), lap
completion (`$f9e6`) and related notification helpers (`$9234/$92c8`). Native local
unwinds that return within a helper remain untouched. This is not an exhaustive
transitive mode-exit audit or completed debt/input rebasing policy: an interrupted world
update and its remaining scheduled work still need explicit lifecycle handling. Native
incident animations and shared-clock readers also remain inside the region and require
further decomposition.

The logical control phase temporarily owns `state+$5e`. Native `$53f6/$8ae6` share a
private world random stream during the region; the outer/drawing stream is saved and
restored around it. `TIMING_WORLD_SEED=-1` copies the natural seed at initialization;
`TIMING_WORLD_SEED=54321` is a compile-only test override. Boost heat retains its separate
stream. Incident drawing inside a world update is not yet fully separated from world
randomness, and outer weather/effect generation remains outside this extraction.

An audit finds only two native gameplay reads of `state+$21c`: player multiplication at
`$ccf2` and opponent multiplication at `$d56c`. Other decoded references with the same
negative displacement are library-vector calls, not reads of game timestep state.
The pilot restores the interval before both groups. Recovery animations also call the
opponent updater at `$fe40/$ffc2`; these calls immediately precede a fresh `$e8` test,
without consuming returned registers/flags. They are removed under the world option so
animation frames cannot advance opponents. The recovery loop changes the shared counter,
so the logical phase is restored before the scheduled opponent pass as well.

`PDWORLD1` records active ownership, saved outer counter, logical time, started-update
count, outer/world/initial RNG seeds and the current world phase. Read-only probes at
`$ccee/$cde2/$cedc` check ordered world boundaries; `$d56c` checks opponent intervals.
`tools/check_timing_world.py` verifies contiguous 90-ms epochs and compares complete
sampled state histories across CPUs. Passing this pilot establishes an extraction
boundary, not completed F1–F8, all opponents/modes, or the final physics rate.

`timing-world5-a500` and `timing-world5-030-twins` pass 56 and 55 complete epochs. Their
**55 common sampled player/engine/RNG states match exactly**, including speed, segment, position, damage,
temperatures and sampled RNG state. All 96 boost draws and their logical timestamps
match, as do 55 common engine states through both thermal failures. All 224/220 observed
opponent multiplications use the logical interval. The 030 adds 52 clean renderer twins.
This does not compare complete opponent state arrays or every authoritative game field.
The one-update endpoint difference is reported rather than concealed. Earlier world3
runs fail the opponent interval check because recovery still advanced opponents per
animation frame; they are not accepted substitutes for these corrected results.

`timing-world6-pause-030-twins` validates the build with common mode-destination cleanup:
56 complete world epochs, 224 opponent interval reads, 50 excluded paused fields, five
input events, all 15 brake events and 56 fuel updates. It adds 77 clean renderer twins.
Pause preserves fractional time and pending work. These captures do not exercise every
mode-destination branch; stack/boundary checks pass, but live pit/rescue/restart lifecycle
validation remains open. Both fixed-seed and natural-seed variants build; the normal
slave remains byte-identical to the preceding release checkpoint and excludes the pilot.

Build with `TIMING_PERIODIC=1 TIMING_ORIENTATION=1 TIMING_INPUT=1 TIMING_ENGINE=1
TIMING_WORLD=1`. The matched boost captures additionally set `TIMING_HEAT_SEED=12345`
and `TIMING_WORLD_SEED=54321`; normal defaults retain natural initial randomness.
Use `CUSTOM5=10`, 250 fields, and probes `$ccee/$cd2c/$cd3a/$cde2/$cedc/$cfec/$cff8/
$de0a/$dfae/$dffc/$fc9e/$fcea/$fec6/$d56c`. Select `CUSTOM4=1` for renderer twins.
The current frozen build is `Powerdrome-timing-world6.slave`; the matched boost pair uses
world5, which differs in mode-exit cleanup. The pause route uses `CUSTOM5=8`, 300 fields,
world/movement/opponent probes plus `$d058/$d9a0/$be12/$bef2`.

### 20-ms world integration (`TIMING_WORLD20`)

The next development stage adds `TIMING_WORLD20=1` to the complete-world build flags.
Its world cursor advances four native clock units (20 ms) after each complete update.
Controls, orientation, resources, engine decisions and opponents retain their 18-unit
(90 ms) deadlines. A slow update runs on the first world boundary at or after its
logical deadline, alternating 100/80 ms service intervals without cumulative drift.
Input sampling still uses the ideal control timestamp. The 32-step outer-frame limit
retains unassigned elapsed time; this is a work budget, not permission to discard debt.

Geometric track/contact checks run every world step. The repeated contact feedback and
fixed speed penalty at `$fb64`, damage accumulation at `$fb84`, and the `$288` age update
at `$cde2` run only on slow-update steps. Their timing and collision coverage still need
validation beyond the simple throttle/brake route.

The scalar displacement division at `$ccf6` carries its signed remainder modulo 24.
The three direction-vector shifts at `$cd32` carry remainders in 0..4095, preserving the
native signed arithmetic-shift convention. This avoids repeatedly throwing away distance
when movement is subdivided. Integrator remainders reset on world initialization;
additional teleports and mode changes still need an explicit lifecycle audit.
`PDW20T01` records the initialized flag, slow-update decision, world cursor and fast/slow
counts. `PDW20I01` records the scalar and three axis remainders.

`tools/check_timing_world20.py` independently checks continuous 20-ms world epochs,
90-ms control deadlines, opponent intervals and the allocator's retained-time ledger.
`tools/check_timing_integrator.py` reconstructs scalar and vector arithmetic from the
initial remainder state and before/after guest probes. It rejects unexpected scalar
changes (including wind); it is deliberately scoped to the no-wind test route. The
existing native-movement checker remains unchanged for builds without these carries.

The remainder-enabled 030 capture, `timing-world20-2-030-twins`, verifies 253
complete movements, 506 remainder observations, 211 scalar carries and 298 axis carries.
It has 56 slow updates, 224 opponent interval reads, no outstanding allocator debt or
unfinished assigned steps at the endpoint, and 74 clean completed renderer twins with
unchanged raster code. These instrumented runs establish correctness within the route,
not rendering throughput or original-A500 distance calibration. The matched A500 run,
`timing-world20-2-a500`, verifies 255 movements, 510 remainder observations, 213 scalar
carries and 302 axis carries. All **253 common sampled player/engine/RNG states match**
at equal world times across the two CPUs. Both have 56 identical fuel updates and all
15 brake events, ending stopped with no outstanding movement debt. The two-step endpoint
difference is retained explicitly; comparison covers only their common logical window.

The matching pause regression, `timing-world20-2-pause-030-twins`, excludes 48 observed
paused PAL fields and consumes five legitimate input edges without paused gameplay or
leaked throttle. It verifies 255 movements, 510 remainder observations, 56 fuel updates,
15 brake events, exact time accounting and 75 clean renderer twins. The pause verifier
recognizes the live 20-ms world marker when selecting the scheduler period; its existing
90-ms pilot regression still passes. No pending movement debt remains at either endpoint.

The route uses `CUSTOM5=7`, 250 fields, the driving anchor `$bc7c`, and world/movement
probes `$ccee/$cd2c/$cd3a/$cde2/$cedc`, plus `$d56c/$d058/$d9a0/$de0a/$dfae/$dffc/
$fb64/$fb84/$fc9e`. Freeze the coverage build before restoring the normal slave. The
normal build remains unchanged and excludes this stage.

Falling displacement at `$cd5c–$cd60` and impulse displacement/decay at `$cd96–$cdc0`
remain unscaled: neither path is exercised by this simple route. This stage is not yet
safe to use as evidence of whole-game timing correctness. Wind arithmetic, mode clocks,
incident presentation and the remaining calibration/matrix gates also remain open.

### Next extraction steps (`coupled-20`)

1. Implemented in the bounded `TIMING_WORLD20` prototype: give the complete world its
   own 20-ms cursor and retained debt. Service controls and
   orientation at the calibrated 90-ms rational cadence, without advancing future inputs
   or applying all accumulated controls before movement. Draw only after complete updates.
2. Implemented but collision coverage pending: keep movement and geometric contact/track
   checks together on that cursor. Split contact
   detection from damage counters, fixed speed deductions and repeated sound/flash events;
   otherwise running collision code at 50 Hz would multiply those responses.
3. Separate falling/impulse velocity integration from their 90-ms age/decay updates. Scale
   displacement and retain integer remainders; scheduling the counters alone is insufficient.
   Keep opponents on their measured logical cadence while auditing incidental callers.
4. Assign logical versus display time to shared-clock reads and all mode exits. Decompose
   blocking incident presentations, and define pause/pit/rescue/restart rebasing so elapsed
   gameplay is neither dropped nor charged across excluded mode time.
5. Repeat this seeded incident/failure comparison, then response/straight-distance bounds,
   pause and mode routes, capacity/debt measurements and the complete CPU/render matrix.
   Retain the 90-ms pilot as a diagnostic reference, not as a reduced final objective.

## Cockpit liftoff: confirmed frame-driven movement

The cockpit departure routine at hunk `$1020e` is separate from ordinary driving.
It computes initial position increments by dividing a displacement by eight, then sets
`d7=8` and executes **nine** iterations (`DBRA` includes zero). At `$102d0–$102e6`, each
iteration adds the three increments to position, adds 37 to the forward increment, and
adds 10 to the speed field. There is no elapsed-time multiplier in this movement block.
Its final speed is 90 after the nine updates. Rendering and presentation between updates
therefore determine how quickly the launch completes on different CPUs.

The existing original A500 launch trace places cockpit-departure entry at field 122 and
first ordinary gameplay at field 190: 68 PAL fields, or **1.36 seconds**, including setup
and final handoff. It contains ten renderer entries. Re-reading the instruction trace finds movement at
fields 145, 150, 155, 160, 165, 170, 175, 180 and 185, followed by departure return at
190: exactly five fields per step. The separate 1.36-second figure includes setup. Fresh read-only captures at `$102d0`, with departure entry/return probes, separate the
initial setup/drawing interval from the nine movement steps:

| Native timing, same development fixture | First step | Last step | Return | Step interval |
| --- | ---: | ---: | ---: | ---: |
| A500, no fast RAM | field 22 | field 62 | field 67 | 5 fields / 100 ms |
| 68030/25, fast planar enabled | field 10 | field 34 | field 37 | 3 fields / 60 ms |

These are `timing-liftoff-a500-native` and `timing-liftoff-030-native`, both under
`tmp/prof/`, with `CUSTOM3=0`. The nine position/speed samples match exactly; the 030
executes the sequence **1.667 times as fast**. From first movement to return, A500 takes
900 ms and 030 takes 540 ms. Initial setup is a separate interval and is not deliberately
slowed by the proposed correction.

Departure must preserve the native step sequence, final position and speed while pacing
its progression using elapsed time. The tentative 90 ms ordinary-control cadence must
not be applied to this animation without its own A500 calibration. The earlier external
pit animation at `$14764` is a separate 17-position sequence and also needs a mode-specific
check. Neither path is fixed by lowering the ordinary movement-delta minimum.


`TIMING_DEPARTURE=1` builds a separate opt-in prototype with a 20-clock-unit / 100 ms
presentation deadline for each native departure step. Its first deadline starts at the
first movement; subsequent deadlines retain lateness instead of adding 100 ms to each
observed completion. Rendering and all nine native position/speed updates remain in order.
The prototype waits only in this finite departure animation; it does not cap regular
track rendering. CPU-specific rendering overrun remains possible on slower configurations.
The first isolated prototype passes on both A500 and 030: all nine sampled native
position/speed states match, all nine intervals (including the final return) are 100 ms,
and first-movement-to-return is 900 ms. The guarded build also passes A500 and 030 with
both native and fast rendering selected, including exact final speed/position increments
at the handoff to normal driving. It checks the native instructions before patching.
These results are `timing-liftoff-a500-paced2`, `timing-liftoff-030-native-render-paced2`
and `timing-liftoff-030-fast-render-paced2` under `tmp/prof/`. Cockpit pacing is now included
in the experimental `CUSTOM3` option; `TIMING_DEPARTURE=0` isolates the minimum-delta
experiment for development. The full framerate-independence feature remains incomplete.

Reproduce a departure capture with `ANCHOR=0x1020e`, `SWAP_MARKER=0x102d0`,
`COVERAGE_PROBES='0x1026c 0x10322 0x10336 0xca3e'`, `TIMING_STATE=1`, `SWAP_ONLY=1`
and `FIELDS=100`. Use the normal Practice fixture (`CUSTOM5=2`) and select CPU/memory as
in the development guide. Build the prototype with
`make -C whdload verify VASMFLAGS='-DTIMING_DEPARTURE=1'`, freeze that slave under `tmp/`,
and compare `CUSTOM3=0/1`. `tools/check_departure.py REFERENCE CAPTURE...` checks the nine
states and A500 timing. New event samples also check final speed and the ninth position
increment at return. `tools/check_timing_layout.py --off-capture CAPTURE` audits complete
instruction boundaries, direct branch entries and disabled-mode bytes. Timing hooks are
native in both initial/final A500 and 030 disabled snapshots. This structural audit does
not replace runtime checks of wrapper register, stack and condition-code contracts.

## Periodic controls and brake input ownership

`TIMING_PERIODIC=1` schedules controls/resources every 18 clock units (90 ms).
`TIMING_ORIENTATION=1` schedules the corresponding orientation integration and makes the
braking jitter at `$d028` use logical control parity instead of rendered-loop parity.
The first control phase is odd, matching the native first driving loop. Parity advances
once per control update, including each catch-up update. Other rendered-loop consumers,
including collision damage at `$fbe6`, still need classification and extraction.

The native A500 response fixture applies fourteen inter-step braking intervals over 48
PAL fields: approximately **68.57 ms per brake step**. Braking therefore has a separate
14-unit / **70 ms** prototype cadence (`TIMING_BRAKE=1`); acceleration and resources retain
their 90 ms cadence. The VBL callback at `$5786`, after native input sampling, accounts for
held brake time in four-unit increments. It alternates three/four PAL fields between due
steps, retaining the fractional remainder. Pressing starts one immediate event; releasing
clears held-time phase but **does not discard already owed events**. The main movement
context applies at most 32 owed steps per pass and retains excess debt. Native eligibility,
damaged-brake amount and zero-speed clamping are retained at application. Physics is not
executed in the interrupt handler.

With historical input enabled, the prototype now records each owed brake event in a
separate 256-slot timestamp queue. Before a logical control update, it services only brake
events at or before that update's timestamp (brake first on equal timestamps). Before
movement, it services intervening events up to the frame's accounted clock, bounded strictly
below the next unprocessed control timestamp. Thus a capped catch-up pass cannot apply a
newer brake event ahead of an older deferred control. The queue retains unread events,
reports overflow explicitly, and shares the input scheduler's unpaused PAL clock. This
ordering correction passes the matched joystick route described below. Engine, fuel and
damage eligibility remain evaluated at application; broader state-transition chronology is open.

The route holds brake on fixture fields 100 through 149. Its independent count oracle is
`1 + floor(49*4/14) = 15` owed steps. Captures `timing-brake2-a500`, `timing-brake2-030` and
`timing-brake2-030-twins` under `tmp/prof/` each apply **15/15**, finish with no pending debt,
and stop the ship. `tools/check_timing_brake.py CAPTURE...` checks those conditions. The
030 twin run completes **77 staged comparisons**, with zero pixel/register/CCR/scratch/guard
failures and unchanged raster code. The same-build A500 `CUSTOM3=0` capture preserves every
declared timing-hook range in its initial/final snapshots.

These are bounded prototype checks, not full F5/F7 acceptance. The newer input prototype
passes the dedicated pause route below; other mode transitions still need explicit lifecycle
handling. Joystick behavior, damaged brakes and engine/fuel transitions need dedicated routes. The
separate compile-time brake option is excluded from normal builds.

## Logical resource updates and remaining engine timing

With `TIMING_INPUT=1`, the resource mutation body `$d92a–$d9a0` now runs after each
logical control call, before advancing its timestamp. The native body still computes fuel
use from speed, doubles consumption for boost, adds the native extra consumption/heating
when `$44e != $450`, clamps depletion, and stops engine audio on exhaustion. Its only
external calls in the depletion path are the returning DMA-audio stop helper `$17b0c`.
The wrapper preserves all data/address registers and condition flags. The normal HUD call
at `$d9a4` stays in the render path, without repeating resource mutations there.
The standalone periodic prototype without historical input retains its older batch path.

This corrects reuse of one rendered frame's final speed/boost state across multiple owed
resource updates. It does not settle ordering relative to variable-step collisions, or
establish A500 consumption calibration. `timing-resource1-a500` and
`timing-resource1-030-twins` validate 55 and 56 logical resource calls respectively. All
**55 complete common fuel updates match exactly** in timestamp, speed, boost, settings,
and before/after fuel. Each subtraction independently matches native word arithmetic;
there are no intervening fuel writes in the sampled sequence. All 55 common speed/input
updates and all 15 brake timestamps also match; the 030 passes **61 clean renderer twins**.
The binaries are frozen as `Powerdrome-timing-resource1.slave` under ignored `tmp/`.

`tools/check_timing_resource.py CAPTURE...` consumes `PDRESOURCE` records from the read-only
`$d9a0` probe. It checks the native low-word multiplication/shifts, minimum consumption,
boost and unequal-setting charges, continuous fuel state and cross-CPU logical sequence.
The short route keeps the engine running with ample fuel; it does not exercise exhaustion
or unequal-setting heat. The whole-game ordering relative to collision/engine transitions
and A500 consumption calibration remain open.

`timing-resource2-pause-030-twins` passes 56 continuous fuel updates, 49 excluded paused
PAL fields, five legitimate input events, 15 brake timestamps and 75 clean renderer twins.
No resource, control or movement probe executes during the native pause interval.
`timing-resource1-pause-030-twins` is an invalid, interrupted capture: a truncated debugger
request left GDB waiting for the rest of its command script before capture began. The
local socket and pipe transport now handle complete requests and short writes; dedicated
transport regression checks pass. It is not evidence of a game timing failure or a pass.

Engine heat from boost (`$cfe8/$cff4`) already follows logical controls, and extra resource
heat (`$d974/$d978`) follows the extracted resource call. Without the separate
`TIMING_ENGINE=1` experiment, **cooling is still frame-based**:
`$dfae–$dfb6` selects every fourth rendered loop, then `$dfb8–$dff8` subtracts
`20 - (speed >> 4)` from each undamaged engine, with a minimum temperature of 80.
Overheat checks at `$de04–$dfae` run once per rendered HUD update. They compare temperatures
with 180/225, update previous-temperature fields, issue warnings/sounds, set damage bits,
halve target speed when an engine fails, and stop propulsion when both have failed.
HUD warning blinks at `$dc5a` are a separate presentation concern.

`TIMING_ENGINE=1` (requiring `TIMING_INPUT=1`) now reuses the native `$de0a–$dffc`
engine decision/cooling body after each logical resource update. It schedules cooling every
four logical control ticks (360 ms at the current 90 ms cadence). Its initial control phase
uses the native loop counter's low word, preserving the original modulo-four phase as well
as parity. The default periodic build still excludes this experiment.

Failure presentation is deferred to the native HUD boundary at `$de04`. The call-site
hooks retain damage-bit writes, message pointers and target-speed halving while queuing
flash, cockpit redraw and message events in their original order. A 16-entry main-context
queue records type, logical timestamp and message pointer; overflow is explicit. The native
failure helper `$e0c0` calls `$10338` and **presents through `$8056`**, so it must not execute
inside logical catch-up. The display service runs those calls after ticking and prevents
recursive queue draining. `$13514` still schedules message expiry using the rendered-loop
counter; message lifetime and failure-flash duration remain separate unfinished timing work.
Sound decisions retain native main-context calls.

`timing-engine2-a500` and `timing-engine2-030-twins` pass 55 and 56 sampled engine updates.
Every overheat decision and cooling subtraction matches native arithmetic; the common
55 logical cooling phases match across CPUs. The existing 55 common speed/input and fuel
updates also match, and the 030 validates 61 clean renderer twins. Those short runs do not
trigger thermal failure, so they do not validate deferred-event delivery. The A500 uses
frozen `Powerdrome-timing-engine2.slave`; the 030 uses `Powerdrome-timing-engine3.slave`, whose
additional presentation-kind diagnostic is inactive on this short route.

The initial native RNG words differ (0x46fc A500, 0xa59c 030). Boost draws separate random
heat increments for both engines. These checks validate cadence and decisions against each
run's observed inputs, not temperature equality from unmatched random histories. The isolated boost stream below addresses heat ownership; matched-seed captures test its
resulting temperature history separately from these earlier runs.

`CUSTOM5=10` supplies sustained native dual-button boost at field 10, release at 700, and
ends at 800; it writes no physics or temperature state. Its purpose is to exercise thermal
failures and prove that each failure produces and delivers flash/redraw/message exactly
once, in order, outside logical ticking. `tools/check_timing_engine.py --require-failures`
checks those conditions, plus native damage/target/propulsion decisions and cooling.
`timing-engine3-heat-a500` and `timing-engine3-heat-030-twins` each pass **178 logical
engine updates and both thermal failures**. Each run delivers all six presentation events
in order, with an empty final queue and no overflow. The 030 additionally passes **211
completed staged comparisons**, with zero reported failures and unchanged raster code.
These are instrumented correctness runs, not performance measurements. Additional required
cases include unequal engine settings, fuel exhaustion, repairs and mode changes. A native A500 response
reference and matching random histories are needed before engine timing is accepted.

`timing-engine3-pause-030-twins` passes 56 engine and fuel updates, excludes all 48
observed paused PAL fields, preserves five input events and all 15 brake events, and
retains the logical remainder. The pause verifier now checks engine entry and decision
probes as well as control/orientation/resource probes. The run adds 78 clean staged
comparisons with unchanged raster code. It does not cover pausing during an engine failure.

### Boost random-state ownership

Both native generators (`$53f6` and `$8ae6`) update the same word at `state+$62`, using
`seed = (seed * $7ab7 + 1) mod 65536`. The former returns a shifted word; the latter
scales its low 15 bits to the supplied bound. The shared stream includes boost heat
(`$cfe4/$cff0`), failure audio (`$e0e4`), camera shake (`$100e6/$100f8`), rendered effects
(`$16dec/$16e14`), and frame-counted effect generation (`$bcf0/$bd0c`). Scheduling heat
alone therefore does not isolate it from unrelated random consumption.

The explicit engine prototype now gives the two boost heat draws a private stream.
It reuses native `$8ae6` with a temporary private seed field, then replays each original
heat addition. Both return registers and arithmetic flags retain the native contract.
The hook audit verifies the reused body touches only that seed and d0/d1; the native VBL
handler establishes its own game-state base, so interrupt input does not use the temporary
base. The private stream advances only when native boost requests heat. This deliberately
changes the coupling between heat and the remaining shared random calls, while preserving
the generator and heat distribution. Other gameplay and cosmetic consumers still need
classification and separation; this is not complete RNG independence. Native control
`$cef6` also has direct callers at `$fcea` and `$fec6` in incident handling, in addition
to the scheduled main-loop call at `$ca74`. Those paths still need chronology/input
ownership tests; isolating heat randomness does not by itself schedule every control call.

At scheduler initialization the private seed copies the current native seed. A compile-only
`TIMING_HEAT_SEED=0..65535` override provides repeatable tests; its default `-1` preserves
natural initial variability. `PDHEAT02` marks the initialized live state and records initial seed, current seed and draw count.
`tools/check_timing_heat.py` checks every observed seed/output against the native formula,
consecutive draw counts and left/right order, and final state. Across matched-seed captures
it compares consumption at equal logical timestamps; `--compare-engine` also requires
identical temperature, damage, target-speed and propulsion histories. Reset/repair/mode
lifecycle behavior remains part of the open transition audit.

The fixed-seed build uses `TIMING_PERIODIC=1 TIMING_ORIENTATION=1 TIMING_INPUT=1
TIMING_ENGINE=1 TIMING_HEAT_SEED=12345` and the `CUSTOM5=10` boost fixture. Capture 800
fields from `$bc7c`, with heat probes `$cfec/$cff8`, engine probes `$de0a/$dfae/$dffc`,
and presentation probes `$e0c0/$10d0c/$13514`. The frozen artifact is
`Powerdrome-timing-heat2.slave`. `timing-heat2-a500` passes 96 consecutive heat draws,
178 engine updates and both thermal failures. `timing-heat2-030-twins` independently
passes 138 heat draws, 178 engine updates, both failures and 185 clean renderer twins.
**The full matched-seed comparison fails:** the first 29 sampled engine states agree,
including the first failure at logical time 2,610 ms. The next A500 engine state has
speed 13 and temperatures 211/235, versus speed 369 and 204/228 on 030. At logical time
2,700 ms the A500 consumes an extra heat pair outside the recorded logical engine update;
the 030 consumes that pair at the following logical time. Incident/control chronology
must be resolved before calling these histories equivalent. The strict checker retains
this failure; passing per-run arithmetic and renderer checks do not override it.

The 300-field `timing-heat2-incident-a500` repeat confirms the source: at field 128,
`$fc9e` observes speed 407; `$fcea` observes speed zero and calls native `$cef6` while
logical control is inactive. That extra boost pair precedes the next scheduled control.
This happens before the queued failure flash, so flash duration alone does not explain
the initial divergence. The repeat passes 96 random draws and 67 engine arithmetic
updates. Incident calls, movement integration and collision outcomes must be assessed
together; suppressing the extra random calls just to make the trace match would conceal
the different gameplay event.

The earlier `timing-heat1-a500` stopped
before field measurement because its diagnostic did not distinguish the loaded state
from a loader copy; it is not validation evidence.

### Native A500 fuel and joystick-response calibration

`timing-resource1-a500-native` uses the same frozen input fixture with `CUSTOM1=0 CUSTOM3=0`.
All timing-hook bytes remain native in both snapshots. Over fixture fields 20–240 (4.4 s),
`tools/timing_fuel_compare.py` brackets one resource update at each interval endpoint:

| Route | Fuel used, bounded units |
| --- | ---: |
| Native A500 | 121–123 |
| Periodic A500 | 126–128 |
| Periodic 030, twin rendering | 125–127 |

Both candidates pass the frozen 10% resource bound: their maximum differences are seven
and six units, below 12.2 allowed units. Wall-clock endpoint bounds differ slightly even
though the complete common logical resource sequence matches exactly. This short-running,
eligible-engine route does not certify fuel exhaustion or all settings.

The same reference **does not establish acceptable high-speed joystick braking**. Its
post-command speed settles at 108, versus 53 for both periodic candidates. The original
joystick enters native automatic boost before braking; at around fixture field 100 the
sampled speeds are 329 native, 316 periodic A500 and 329 periodic 030. Matching 15 owed
brake events across CPUs is not equivalent to matching native A500 response. The separate
70 ms brake cadence was calibrated on the lower-speed mouse route and needs assessment
against this route's native invocation times, overspeed damping and entry speed before
further tuning. No braking threshold below 100 is reached by the native reference during
the held-input interval, so the current threshold tool reports missing thresholds rather
than a pass. Acceleration to 130 passes; acceleration to 120 remains inconclusive with
its 60–100 ms error bound against a 90 ms tolerance. The acceptance bounds are unchanged.

The native traces identify an actual cadence difference, not simply a lost input edge:
mouse braking has 15 control calls at fixture fields 101–149 (14 intervals in 48 fields,
68.57 ms on average). Joystick braking has eight calls at fields 100, 103, 107, 111, 120,
128, 136 and 144; its last three intervals are 160 ms. Above cruising speed the native
routine also halves the excess speed after each brake decrement. The changing rendered
frame duration therefore affects both operations. A single fixed braking cadence cannot
reproduce both native responses within the current bounds. The reference-policy choice
between consistent representative A500 handling and reproducing scene-dependent slowdown
is pending; do not silently relax the bounds or claim this calibration complete.

## Response measurements and next required correction

`tools/timing_response.py REFERENCE CAPTURE...` normalizes observations to the input
fixture's native VBL epoch, combines presentation and control/movement-boundary samples,
and includes PAL-field quantization in its crossing intervals. It reports conservative
error bounds against the frozen 10% / 90 ms tolerance. An inconclusive bound is not a pass.
Use `COVERAGE_PROBES='0xd058 0xccee' TIMING_STATE=1` for the finer boundary samples.

The native A500 reference is `timing-brake2-a500-native`. Its sampled stop threshold is
980–1,000 ms after the brake command. With timestamped input, `timing-input1-a500` reaches
zero in 1,000–1,020 ms and `timing-input1-030` in 980–1,000 ms. Acceleration to 130 is
1,320–1,340 ms on both, versus 1,380–1,400 ms native. Those bounds pass the frozen criteria.
Acceleration to 120 remains inconclusive at PAL-field resolution: the conservative error
bound reaches 100 ms against the 90 ms limit. The slower twin-rendered stop is not observed
within the tool's strict held-brake window, although all 15 owed brake events are applied
and the ship stops. Do not turn those unresolved bounds into a complete response claim.

## Timestamped control inputs

`TIMING_INPUT=1` (with `TIMING_PERIODIC=1 TIMING_ORIENTATION=1`) enables the input prototype
and implies `TIMING_BRAKE=1`. Its PAL VBL callback records input changes in a
256-slot ring, leaving one slot empty to distinguish full and empty. Each 16-byte record
contains a clock value, buttons/modifiers, external mouse deltas, raw joystick bits and
the native mouse/joystick mode. `PDINPT02` diagnostics include private logical axes; the
reporting tools also accept older `PDINPT01` button-only captures. The consumer applies only records whose
timestamp is at or before the current logical control update. The speed-control reads at
`$cf66` and `$cf7a` use that snapshot; live input memory is not temporarily overwritten.
A full ring preserves unread records and increments an explicit overflow counter. Overflow
invalidates validation; a final release policy and capacity/stall tests remain required.

Input timestamps and the periodic scheduler share **four units per unpaused PAL VBL**.
The ordinary movement delta still uses its original native clock path. This prevents a
slow frame from applying a new throttle press to an older owed control update. In
`timing-input1-a500`, `timing-input1-030` and `timing-input1-030-twins`, **19 early logical
acceleration updates match the timestamp-based oracle exactly**. Each consumes the same
three button edges once, with no overflow or pending records. All retain 15/15 brake steps.
The twin run validates **74 completed staged scenes**, with zero reported failures and
unchanged raster code. `tools/check_timing_input.py CAPTURE...` checks this bounded route.

### Mouse and joystick axes

Native mouse samples accumulate into state `$42a/$42e` in VBL (`$56d4/$56fe`). Controls also
write those values during collision damping (`$d082/$d086`) and joystick response
(`$d266–$d380`), so replaying old absolute samples would overwrite logical corrections.
The prototype queues external deltas and maintains separate logical axes. Its control
reads and damping writes use those logical axes only while the scheduled control call is
active. Other callers retain live input behavior. Mode, fire and direction tests within
that call use the matching historical sample. Live input memory is never temporarily
replaced with old values.

The joystick response reuses the original `$d26c–$d380` instruction body with a private
input structure. The body contains only local branches and references to five input
fields; it has no external calls or stack-relative data. The hook audit verifies that
contract. It retains the native nonlinear response and automatic boost behavior. Startup
samples and normalizes joystick input rather than inheriting stale native mouse buttons.

The mouse fixture (`CUSTOM5=7`) adds three native input deltas: +40 at PAL field 160,
−80 at 190, and +40 at 220. It no longer forces absolute axis values every VBL.
`timing-axes1-a500` and `timing-axes1-030-twins` each pass **56 logical mouse-state updates**
against an independent timestamp/delta oracle, including exactly six events consumed once,
19 matching early acceleration updates and 15 brake steps. The 030 run validates **77
completed staged scenes** with zero reported failures and unchanged raster code. These
bounded tests do not establish collision-damping or live-input equivalence.

The joystick fixture (`CUSTOM5=9`) selects joystick with native menu key 7, then Race
with key 4. It supplies the native sampled joystick byte at `$d3d0`, preserving the native
controller. Fire/up, fire/down, release, left, right and release have the same timed edges
as the mouse fixture. `tools/check_timing_joystick.py` checks historical event ownership
and the original horizontal response arithmetic at each logical update. Joystick fire/up
invokes automatic boost, so the one-second brake hold is not required to stop this route;
all 15 owed brake steps must still be applied. Response calibration against an unmodified
A500 joystick run remains separate work.

`timing-order1-a500` and `timing-order1-030-twins` pass 55 and 56 sampled logical
joystick-state updates respectively, exactly six input events and 15 timestamped brake
steps, without overflow or residual debt. All **55 complete logical speed/input updates**
in their common interval match exactly, including the braking transition and release;
both finish at speed **53**. The one-update endpoint difference reflects a capture stopping
inside a rendered frame; the checker permits at most one unmatched final logical update.
The 030 validates **61 clean staged scenes** with unchanged raster code. Both use frozen
`Powerdrome-timing-order1.slave`. `tools/check_timing_order.py` checks this complete common
sequence and rejects the earlier unordered prototype at its first braking transition.
`tools/check_timing_brake.py` independently checks every queued timestamp against
`(epoch + 101 + ceil(k*14/4))*4`, for brake events k=0..14.

These results establish ordered controls/braking in the bounded route, not whole-game
chronology. The older brake-only captures leave resource updates batched separately; the resource
extraction described above tests those at each control tick. Collision/damage state
can change between movement frames, and movement still integrates a variable elapsed
interval. Queue capacity/wrapping, overload behavior and other state transitions require
further tests before release.

Mode/menu initialization writes input fields at `$b6e4`, `$b714`, `$eab2`, `$ebd0`, `$100c2`,
`$11c6e`, `$1237e` and `$140a4`. In-flight mode changes, menu save/restore, collision
corrections, both-axis joystick input, held input at entry, queue wrapping/overflow and
live input still require dedicated validation. The gameplay joystick toggle is at `$c946`.
This is not a claim of complete input determinism or completed F5/F6.

## Pause ownership

The input prototype hooks native pause entry `$be12` and the native clock restore at `$beec`.
Paused VBL callbacks increment a separate excluded-field counter and do not enqueue input
or accrue brake time. Both scheduler and input timestamps use `VBL_count - paused_fields`,
so pending events and the fractional control phase survive without rewriting the queue or
resetting deadlines. The native clock restore is replayed with its original register/CCR
behavior. No custom cache policy or interrupt masking is introduced.

`CUSTOM5=8` is a development-only native-key fixture: the same initial throttle/brake run,
then pause, changing throttle/brake while paused, and resume. `timing-pause1-a500` and
`timing-pause1-030-twins` each exclude **49 PAL fields**, enter/exit pause once, consume five
legitimate input edges, and apply only the original 15 brake steps. No gameplay updates run
inside the pause, no paused throttle leaks into resumed play, and logical phase/debt
accounting remains exact. `tools/check_timing_pause.py CAPTURE...` verifies those properties.
The 030 run completes **75 clean staged comparisons**, with unchanged raster code.
The pause test uses the frozen `Powerdrome-timing-input3.slave` artifact under ignored `tmp/`.

The expanded-axis queue also passes `timing-axes3-pause-030-twins`, using frozen
`Powerdrome-timing-axes3.slave`: **48 actually paused PAL fields**, five legitimate input
events, 15 brake steps, exact logical remainder and **78 clean staged comparisons**.
The ordered-brake build also passes `timing-order1-pause-030-twins` with the same
48 excluded fields, five input events, 15 exact brake timestamps and 78 clean twins.
The native pause-entry timing determines the excluded count; the verifier compares it with
the observed entry/exit boundaries rather than assuming a fixed pause duration.
The normal build remains byte-identical to the preceding checkpoint: these new input
hooks and fixtures are confined to explicit development builds.

Pits, rescue, restart, title playback and other session changes still need their own timer
and input-lifecycle handling. These prototypes remain excluded from normal builds; normal
`CUSTOM3` currently enables only the movement-minimum and cockpit-departure corrections.

The resource, opponent, collision/falling/impulse and weather work remains open. In particular,
scheduling a velocity decay counter alone cannot fix an unscaled displacement: the whole
fall/impulse increment must advance at its selected logical cadence or be integrated over
the elapsed interval. Keep native mode/rendering consumers of the shared loop counter until
each gameplay read has an explicit replacement.
