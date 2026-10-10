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

The route holds brake on fixture fields 100 through 149. Its independent count oracle is
`1 + floor(49*4/14) = 15` owed steps. Captures `timing-brake2-a500`, `timing-brake2-030` and
`timing-brake2-030-twins` under `tmp/prof/` each apply **15/15**, finish with no pending debt,
and stop the ship. `tools/check_timing_brake.py CAPTURE...` checks those conditions. The
030 twin run completes **77 staged comparisons**, with zero pixel/register/CCR/scratch/guard
failures and unchanged raster code. The same-build A500 `CUSTOM3=0` capture preserves every
declared timing-hook range in its initial/final snapshots.

These are bounded prototype checks, not full F5/F7 acceptance. Pause/mode transitions must
explicitly freeze/rebase input accounting before this code can be enabled in a normal build.
Joystick behavior, damaged brakes and engine/fuel transitions need dedicated routes. The
separate compile-time brake option is excluded from normal builds.

## Response measurements and next required correction

`tools/timing_response.py REFERENCE CAPTURE...` normalizes observations to the input
fixture's native VBL epoch, combines presentation and control/movement-boundary samples,
and includes PAL-field quantization in its crossing intervals. It reports conservative
error bounds against the frozen 10% / 90 ms tolerance. An inconclusive bound is not a pass.
Use `COVERAGE_PROBES='0xd058 0xccee' TIMING_STATE=1` for the finer boundary samples.

The current same-build native A500 reference is `timing-brake2-a500-native`. Its sampled
stop threshold is **980–1,000 ms** after the brake command. The timed A500 is **1,000–1,020 ms**;
the timed 030 is **980–1,020 ms**. Those stopping bounds pass the response criterion.
All five measured 030 acceleration/braking thresholds pass against this reference. The
A500 acceleration-to-130 result is **1,220–1,240 ms**, versus **1,380–1,400 ms** native, and
fails the frozen acceleration gate. Some other A500 bounds remain inconclusive.

Control catch-up still uses the most recently sampled input for all owed updates. In
the matched captures, the third logical control executes at fixture field 10 on A500 and
uses the new throttle (speed becomes 96); on 030 it executes at field 9 and retains speed
90. Throttle is scheduled at field 10. Thus the same logical update sees different input
across CPUs. A slow frame can apply a newly pressed throttle to an older owed update. The next required change is timestamped input ownership: retain button/modifier
changes in the existing VBL callback, consume them at each logical control timestamp, and
have the native speed-control reads use that historical snapshot without overwriting live
input. Extend the same ownership rules to joystick and steering samples; preserve queued
edges through catch-up and explicitly handle queue capacity and mode resets. Merely tuning
the 90 ms period would hide this ordering bug rather than resolve it.

The resource, opponent, collision/falling/impulse and weather work remains open. In particular,
scheduling a velocity decay counter alone cannot fix an unscaled displacement: the whole
fall/impulse increment must advance at its selected logical cadence or be integrated over
the elapsed interval. Keep native mode/rendering consumers of the shared loop counter until
each gameplay read has an explicit replacement.
