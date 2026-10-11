# Powerdrome framerate independence analysis and plan

Project status: Phases A–D and E1 are complete. Phase E2 stopped at the steady A500 handling gate; Phase E remains incomplete.
See the [current handoff](open-work.md) for completed checks, open gates and resume priorities.

Status: completion-plan Phases A–D are complete; Phase E has not started. Normal
CUSTOM3 includes the 20 ms PAL movement minimum and paced cockpit liftoff. The broader
20 ms world scheduler and periodic gameplay changes are compile-only prototypes with
bounded A500/030 validation. Weather scheduling, sound calls, fade colour arithmetic,
effect publication and palette restoration pass the latest paired tests; displayed pixels,
mode lifecycles, braking/impulse calibration, opponent state and release gates remain open.
See [open work](open-work.md) for the authoritative handoff and resume order.

Powerdrome is not framerate independent. Its main movement uses elapsed time, but that
elapsed time is clamped, and other gameplay operations advance once per rendered frame.
Faster CPUs and the optional fast planar renderer therefore change more than smoothness.
The selected first approach is to lower the movement minimum to 20 ms on PAL and move
frame-counted gameplay work onto a separate elapsed-time cadence calibrated against the
original Amiga 500. Preserve the existing elapsed-time movement path initially. A complete
fixed-step simulation remains a possible later step if this smaller approach cannot meet
the measured gameplay-speed requirements.

## What success means

The immediate target is A500-paced movement, controls, resource consumption and effect
lifetimes across supported hardware, with native or fast planar rendering. Measure these
against matched original A500 routes over equal unpaused elapsed time. The A500 is the
reference platform; its exact update rate varies with the scene, so calibration must use
representative routes rather than assume a single original target FPS.

Use a 20 ms logical base tick derived from elapsed time for scheduling frame-counted work.
This is not a requirement to execute the entire movement simulation 50 times per second.
Run each extracted periodic operation every N base ticks, using an A500-calibrated period
that is identical across CPUs. Counting N rendered frames or N variable-duration movement
calls would preserve the very dependency this change is meant to remove.

The smaller approach does not promise bit-identical trajectories: movement and collisions
still run at variable intervals and can differ through integration, integer rounding and
input sampling. It must demonstrate matching real-time pace within explicit measured
bounds. Identical authoritative state after every fixed movement tick remains the stronger
acceptance criterion for a future full simulation split if needed.

Authoritative state includes player and opponent positions, speed, orientation, collision
and damage state, resources, race progression, gameplay random state and gameplay timers.
Rendering scratch, bitmap pointers, displayed frames and purely visual animation state need
not match. Smoothness and input-to-display latency can still differ across machines.
A machine unable to sustain the required update workload cannot be guaranteed real-time play.

This is stronger than the existing renderer twins. Those compare two drawing paths for the
same scene input. The 30,623 successful comparisons establish drawing correctness, not
matching gameplay pace across CPUs.

## Evidence and confidence

Game addresses below are offsets into the code hunk. State offsets are relative to the
state base at hunk `$a6e`. Evidence consists of the supplied game, existing captures and
read-only inspection of their saved code. Subsequent prototype runs and their measured
limits are recorded in [timing implementation](timing-implementation.md).

The [performance plan](performance-plan.md#simulation-and-rendering-are-coupled) contains the
original timing trace and per-update findings. [Internals](internals.md#display-and-timing)
describes the clock and title demo. The [coverage report](gameplay-coverage.md) supplies
scenario evidence; the [raster report](raster-improvements.md) supplies measured rendering
rates. Static findings below identify code behavior, not proof that every branch was taken
in a particular capture. The inventory is a starting map, not a complete state-write audit.

### Clock and movement

`$59b6` reads CIA-A TOD, differences the previous reading and adds four times that difference
to the game clock at `$f96`. On the recorded PAL setup, this is four game-clock units per
20 ms field: 200 units per second. Clock sampling occurs from both interrupt and main code.
The routine also has native rollover handling; replacing it requires a deliberate audit
of width, rollover, interrupt interaction and all clock adjustments.

At `$7f7a`, presentation samples the clock, subtracts `state+$218`, updates that timestamp,
clamps the interval to **8–50 units**, and stores it at `state+$21c`. The next main-loop
iteration uses this value. Player movement at `$ccf2` multiplies speed by this interval and
divides by 24; opponent movement at `$d56c` uses divisor 26. These divisors are native
movement scaling constants, not evidence of an intended 24 or 26 Hz simulation rate.

The minimum interval represents **40 ms** on the tested PAL setup; the maximum represents
**250 ms**. A frame completed in 20 ms still advances displacement using 40 ms. A 500 ms
stall advances at most 250 ms in the corresponding step. Updating the timestamp before
clamping means the discarded excess is not carried forward as simulation debt.

The initial trace had 70 movement entries and 70 renderer entries; 69 completed iterations
had deltas from 12 to 32 units, so that slower route did not hit the clamp. It does not
establish correct timing on faster configurations.

| Evenly spaced update rate | Actual interval | Native used interval | Displacement time / real time |
| --- | ---: | ---: | ---: |
| 2 Hz | 500 ms | 250 ms | 0.50 |
| 10 Hz | 100 ms | 100 ms | 1.00 |
| 20 Hz | 50 ms | 50 ms | 1.00 |
| 25 Hz | 40 ms | 40 ms | 1.00 |
| 50 Hz | 20 ms | 40 ms | 2.00 |

These are arithmetic consequences of the clamp at constant speed, not measured lap-speed
ratios. Real frame intervals vary; acceleration, rounding and collisions also change the
trajectory. A mean FPS cannot reconstruct the full delta distribution. The measured fast
030/25, 040/25 and 060/50 presentation rates of 30.12, 41.57 and 42.99 fps exceed the
25 Hz threshold, making the clamp directly relevant to the accelerated configurations.
Future measurements must log actual raw and applied deltas, not infer them only from FPS.

### More than the movement timestep is tied to frames

| Location | Established behavior | Required treatment |
| --- | --- | --- |
| `$cf86–$cf90`, `$cfca–$cfd4` | Speed approaches a target by one eighth of the difference per invocation | Tick-owned control response; calibrate its real-time rate |
| `$d00a`, `$d01e`, `$d25e` | Speed deductions in particular control/engine states lack explicit frame-delta scaling | Audit branches and assign deductions to simulation ticks |
| `$d93a–$d9a0` | Resource at `state+$1ba` is decremented per HUD/update invocation, with a minimum decrement of one and conditional extras | Extract resource mutation from drawing; preserve fractional rates if converted |
| `$d96c–$d978` region | Resource/control branch also increments `state+$196/$198` | Audit meaning and dependencies; do not classify the HUD routine as cosmetic |
| `$cd60` | Falling-state counter increments per update | Tick-owned counter with calibrated duration |
| `$cdb4–$cdc0` | Impulse counter/decay includes halving components | Tick-owned decay; repeating it at a new frequency changes its time constant |
| `$cde2–$cdf0` | `state+$288` increments and invokes a helper at a threshold of `$3c0` | Determine purpose and reset behavior before selecting a time domain |
| `$bc86`, `$ca44` | Outer loop increments long `state+$5e`; update entry tests its low-bit parity | Preserve simulation-step cadence of dependent work, not rendered-frame cadence |
| `$bcaa`, `$bcea–$bd16` | Effect delay `state+$4d2` counts down, then random calls choose effect and next delay | Advance generation once per appropriate logical tick |
| `$bd1a–$bd52` | Work involving `state+$4c6` is gated by the low four bits of the loop counter | Audit the helper calls; preserve intended periodic timing independent of frames |
| `$53f6` | Shared random seed `state+$62` advances on calls | Separate gameplay consumption from draw frequency |
| `$112ec/$112f0` | Renderer decrements effect counter `state+$4ce` and invokes an effect helper | Split effect evolution from drawing |
| `$112f4/$117c8–$117d4` | Renderer sets `state+$4d0`, invokes cleanup and clears it | Determine transient draw bookkeeping versus persistent effect state before moving |
| `$f0dc` and `$f10e–$f110` | Timer display work reads the game clock and subtracts a timestamp | Preserve timer semantics; decide which values belong to logical versus wall time |
| `$107d6` | Title camera recording advances by its step, initially two samples per frame | Separate animation cadence if whole-game timing independence is claimed |

For example, ignoring integer rounding, speed error after n invocations of the one-eighth
response is `(7/8)^n` of its starting value. After one second this is about 26.3% at 10 Hz,
3.55% at 25 Hz and 0.126% at 50 Hz. Merely fixing movement delta leaves substantially
different acceleration responses. Similarly, a minimum resource decrement of one consumes
at least 10, 25 or 50 units per second at those invocation rates, when that branch remains
active. These examples illustrate the mechanism; they are not complete driving models.

### Why extracting periodic gameplay work needs care

The regular route mixes several responsibilities:

```text
Outer loop $bc4a
  Ancillary work
  Combined routine $ca3e
    controls and speed $cef6
    player movement and camera state
    rescue and possible pit/session transition
    other world helpers, collision work and opponents $d3d6
    optional pre-render helper
    scene rendering $10df2
    HUD drawing AND resource/gameplay work $d8ea
    timer/display work $f0dc
  conditional session transitions
  clock sample AND buffer presentation $8056 / $7f7a
  loop counter, effect generation and periodic work
  input and command handling
```

The saved code additionally shows a nonlocal exit at `$ce32`: it adjusts the stack before
branching to session-end handling at `$bf32`. Rescue can enter pit handling from inside
`$ca3e`. A scheduler cannot safely call that entire routine repeatedly as an ordinary
returning subroutine. All exits and their caller/stack assumptions must be mapped first.
The exact split also needs the ancillary calls around `$bc4e` and every transitive helper,
not just the labelled player movement block.

Skipping `$10df2` alone is unsafe because effects mutate there. Skipping `$d8ea` removes
resource/gameplay updates. Repeating `$8056` for catch-up ticks swaps buffers, samples time
and invokes display work. A correct split must extract responsibilities rather than broadly
suppress whole functions that happen to contain drawing.

## Design options

| Approach | Advantages | Limitations | Decision |
| --- | --- | --- | --- |
| Lower only the minimum delta to 20 ms | Small change directly addressing fast displacement | Leaves frame-counted behavior dependent on drawing | First isolated experiment |
| Lower minimum plus elapsed-time periodic updates | Retains native movement integration; restores A500-paced side effects without forcing the whole loop to one frequency | Needs careful extraction, calibration and event ordering; does not guarantee identical trajectories | Selected first approach |
| Cap the entire loop | Small containment measure | Limits smoothness and remains inconsistent below the cap | Not selected |
| Convert every operation algebraically to variable time | Can retain one update per draw | Nonlinear decay, rounding, random events and collisions require different conversions | Use only where justified by the audit |
| Fixed movement simulation independent of rendering | Supports identical tick-by-tick integer state | Requires a broader separation of interleaved code and transitions | Escalation if the smaller approach fails its gates |

## Selected architecture

### Movement minimum experiment

Change the minimum interval at `$7f7a` from eight to four native clock units for the tested
PAL timing. Keep the existing maximum of 50 units in the first isolated experiment, so its
effect can be measured independently. Do not replace every interval with four: a 100 ms
frame still needs its measured 100 ms displacement interval. Record raw/used deltas and
actual elapsed movement before claiming success. With the current PAL presentation wait,
this covers movement rates up to 50 updates/s; verify the actual interval floor on each path.

The native 250 ms maximum and next-frame delta lag remain limitations of this first step.
Test stalls explicitly and report lost movement time. Do not call the result fully independent
under arbitrary stalls. If normal supported gameplay exceeds that bound, the follow-up must
retain movement time and safely subdivide movement/collisions, or adopt fixed movement ticks.
No large unchecked movement step should be introduced just by deleting the upper clamp.

### A500 cadence for frame-counted operations

Keep the native clock/input interrupt lightweight. A main-task scheduler converts raw
unpaused elapsed time to logical 20 ms ticks with a retained remainder. Use raw elapsed time,
not the clamped movement interval, and sample/account for each elapsed interval exactly once.
Do not run gameplay in the interrupt and do not repeat drawing to service a due operation.

For example, a period of N=5 is 100 ms or 10 invocations/s; N=4 is 80 ms or 12.5/s;
N=3 is 60 ms or about 16.67/s. These are examples, not selected A500 calibration values.
Measure original per-operation counts and response curves on a stock A500 with native
rendering. Choose the common cadence for operations formerly executed together, retaining
their order and native once-per-two/every-sixteen-update subdivisions. Assign a different
period only where the original timing or measurements justify it.

If the chosen A500 reference rate lies between integer N values, use a rational phase
accumulator or an agreed nearby period after measuring the resulting error. Do not round a
period independently each frame or choose N according to the current machine's FPS. Keep
calibration constants fixed across hardware and document the reference routes and measured
error, including resource consumption and time to reach target speed.

Extract mutations, not entire mixed routines. Controls/resource changes/effect evolution
run when due; HUD pixels, scene geometry and current control-state reads remain available
when needed for movement or drawing. Code that computes collision inputs cannot simply be
skipped because it shares a function with a periodic effect. Operations sharing state must
keep a defined logical order, including during catch-up.

At a 100 ms cadence, a 50 Hz renderer normally services one periodic update per five draws;
a 10 Hz renderer services one per draw; a slower frame may owe more than one. Due updates
must be counted and retained, not represented by a boolean that drops all but the first.
For coupled operations, process due epochs in chronological order rather than running all
resource changes first and all control changes afterward.

This still leaves a coupling question: applying several historical speed changes and then
moving the ship once at the final speed is not equivalent to advancing movement between
those changes. Measure the resulting distance and control response. If it exceeds the A500
matching bounds, split the elapsed movement interval at periodic-event boundaries, with
matching input and collision handling. If that becomes a de facto full simulation split,
use the stronger fixed-tick design rather than hide the increased scope.

A work budget must not silently discard accumulated periodic updates. Pause, menus, loading
and pit/session transitions need explicit stop/rebase rules so returning to play does not
consume resources or apply a burst of old commands. Distinguish hardware elapsed time,
logical periodic time, race timers and presentation timestamps. Audit `$f96` readers and
writers before changing that shared clock; due-event decisions during catch-up must see
the relevant logical instant rather than the same final wall-clock time for every event.

### Fallback architecture if required

If the smaller approach cannot produce A500-paced gameplay across rendering rates, extract
a complete movement/gameplay tick from drawing. Choose its rate from A500 response and
capacity measurements, not the existing clamp alone. A main-task accumulator then runs due
complete ticks and draws the latest complete state independently. Full simulation requires
explicit handling of the mixed routines and nonlocal exits mapped above. Optional visual
interpolation is separate work and must not feed display positions back into gameplay.

### Input and random state

Sample physical controls at their normal interrupt rate, then preserve time-stamped values
or edges until their logical tick. Catch-up must not apply today's latest mouse position
retroactively to every earlier tick. Held accelerator/steering state can persist across
ticks; pause, rescue, view changes and session-end commands must trigger once per event.
Audit native mouse deltas, keyboard queue semantics and modifier snapshots separately.

The coverage tape currently queues inputs against VBL time and waits for the native queue
to empty. That is useful scenario automation but does not guarantee identical consumption
at equal ticks on different machines. Future deterministic tests need a tick-indexed replay
with exact mouse/button/modifier samples and declared handling of queue overflow.
Use both deterministic replay tests and normal live-input checks.

Inventory all `$53f6` callers and any other random generators. Drawing must not consume the gameplay random stream. With the same gameplay events and
inputs, periodic random advancement must match; variable-step collision differences can
still produce different conditional events and must be measured. Move draw-triggered
gameplay events to their scheduled cadence, then
render their stored results. If cosmetic draws share the gameplay stream, cache the needed
visual choices per tick or give presentation its own state after assessing compatibility.
Simply restoring the seed after drawing is insufficient if drawing also mutates persistent
world/effect state. Tests should fix the seed in a test build; production should retain
normal variability without making render frequency part of gameplay random consumption.

### Effects, HUD and transitions

Split each mixed routine into logical mutation, event emission and drawing. Audio events
should occur once per logical transition, with an explicit policy for multiple events during
catch-up; avoid retriggering sounds on each redraw. Weather duration/generation, damage
feedback and impulse decay belong to an audited time domain. Render-local save/restore
bookkeeping may remain per draw. Snapshot the state required by native fallback rendering
without letting a fallback execute an extra gameplay update.

Preserve the dependencies among player, collision, opponent and post-update resource work
when moving periodic mutations; validate any deliberate change in their ordering. Handle race end, rescue, pit return and restart as
explicit exits from ticking. Reset or carry accumulator, input queue, random state and
periodic counters according to a documented transition table. Pause must not cause a burst
of missed gameplay on resume. Pit/departure animations, title playback, repair timing and
menu timeouts need their own timing audit; racing independence alone must not be described
as whole-game independence.

### Patch and option boundaries

Implement the new timing mode independently of `CUSTOM1`, so it can be tested with native
or fast drawing. Use a separate WHDLoad option only after checking the current option map;
no option number is assigned by this plan. The timing option should initially be off by
default, with the existing native timing available for comparison and rollback. Do not
change standard WHDLoad CACHE/DCACHE behavior or introduce a cache policy.

Prefer narrow, documented hooks and standalone new routines over copying the entire game
update function. Verify instruction boundaries, relative branches, register/CCR contracts,
nonlocal exits and writable data. Use fixed-point/integer arithmetic suitable for 68000;
avoid FPU requirements. New state needs a documented size and allocation/failure path.
Resource scaling must carry fractions rather than round every decrement upward or lose
small decrements. Smaller movement steps also change integer division remainders and can
alter the original trajectory; audit residual accumulation and calibrate against the chosen
reference. Preserve explicit signedness, overflow and saturation behavior. At maximum speed,
check that one movement interval cannot skip required collision or track-segment transitions. If collision
substeps are necessary, use the same deterministic subdivision rule on every CPU.

## Step by step implementation plan

F1/F2 are in progress; F3 is built and under validation. F4/F5 have an isolated
control/resource prototype, with remaining mutations still under audit. F6 is in progress
with bounded pause, pit, retune and result-exit checks; F7/F8 completion gates remain open.
Implementation is authorized; the smaller A500-calibrated approach remains selected.

| Step | Shortcut | Deliverable and completion gate |
| --- | --- | --- |
| F1 | `timing-map` | Identify clock ownership, frame-counted mutations, shared counters, RNG calls, movement dependencies and exits. Classify which operations can be scheduled separately. |
| F2 | `timing-baseline` | Capture original A500 response/resource/effect rates on representative routes and native/fast accelerated comparisons. Freeze target cadence, N or rational periods, and numerical matching tolerances. |
| F3 | `delta-20` | Isolate the four-unit minimum change. Verify raw/used deltas and equal-time movement across CPUs, including rounding, zero/one-field intervals and retained upper-clamp limitations. |
| F4 | `periodic-split` | Extract frame-counted mutations from drawing and shared helpers. Initially service them at their original invocation points to verify extraction without intentional timing changes. Preserve dependent computations and nonlocal exits. |
| F5 | `a500-cadence` | Schedule extracted work on elapsed 20 ms base ticks with A500-calibrated periods, retained remainder/debt, ordered catch-up, input ownership and RNG separation. Measure speed-integration error and split movement intervals only where needed. |
| F6 | `timing-modes` | Validate pause, pits, rescue, repairs, restart, qualifying/race transitions, weather, departure and title playback. Freeze or rebase timers explicitly; document any remaining frame-driven mode. |
| F7 | `timing-matrix` | Meet A500-paced response/resource/effect and movement gates across CPUs and render rates; retain drawing twins. Quantify residual variable-step differences and stalls. Escalate to complete fixed simulation only if these gates cannot be met. |
| F8 | `timing-release` | Independent opt-in timing option, disabled-mode equivalence, memory/hook checks, release isolation and reproducible documentation. State the measured support envelope and remaining limits. |

F1/F2 establish what to schedule and at what rate. F3 should produce an independently
reviewable result before the broader extraction. F4 is the main structural risk. Compare
its intermediate form using identical native delta sequences and inputs in test builds,
because wrapper overhead itself can change wall-clock deltas. Reuse those checks after F5
changes the scheduling. No new fixed-rate movement engine is presumed by this plan.

Estimate remaining effort after the mutation map and A500 measurements. Report completed
gates and measured errors rather than inventing a percentage or assuming all per-frame
behavior is a safe counter to skip.

## Measurement and acceptance

### Required logs and comparisons

Record hardware elapsed units, logical time/tick, raw delta, applied movement interval,
accumulator debt, base ticks and periodic invocations per render, input events consumed, gameplay RNG state, simulation
and rendering costs separately, and authoritative state at movement/periodic boundaries. Count resource
changes, collisions, opponent updates, weather events, mode transitions and audio triggers.
Keep binary traces, memory dumps and screenshots under ignored `tmp/`.

Create an explicit state schema including opponent arrays and mutable gameplay data outside
the main state block. Compare normalized values, not relocated pointers or all RAM. An
excluded field needs a reason and a read/write audit proving it cannot influence later
simulation. Hashes provide compact comparisons; on mismatch retain the first differing tick
and a field-by-field snapshot. Extracted periodic routines should match exactly on identical input state and logical
event sequences. Whole-world comparisons use the F2 bounds while movement remains variable
step; publish trajectory differences rather than claiming exact cross-CPU state parity.

The existing renderer twin must surround drawing only. It must never run resource updates,
RNG-driven gameplay or simulation twice. A frozen logical state drawn natively or through
fast planar staging should retain current pixel/register/CCR/scratch/guard guarantees.
Compare at equal logical ticks, not equal rendered-frame indices or merely final screenshots.

### Numerical gates

- **Base time:** 10, 60 and 600 unpaused seconds contain 500, 3,000 and 30,000 base ticks
  of 20 ms. Preserve fractional time and define endpoint/initial phase precisely.
- **Periodic accounting:** for integer N, the cumulative due count is the number of base
  ticks divided by N, rounded down after accounting for the initial phase. With N=5,
  10 seconds owes 100 invocations, regardless of drawing rate. Actual N comes from F2.
  Rational periods need an equally explicit cumulative-count oracle.
- **A500 match:** freeze numerical bounds for acceleration/braking curves, distance over
  equal time, resource consumption and effect/impact-recovery durations from repeat baseline
  measurements. Set bounds before evaluating the candidate, not after observing its error.
  Report per-route results and natural A500 variation rather than claiming one universal FPS.
- **Render independence:** use identical time-stamped controls at 10, 15, 25 and 50
  presentations/s where feasible, variable intervals and both renderer settings. Compare
  periodic counts exactly and gameplay response within the frozen bounds. Test steady speed
  separately from acceleration, collisions, afterburner and engine failure.
- **Stalls:** test 100, 250 and 500 ms delays. Periodic debt must remain accounted for,
  without duplicated input or effects. Report the first experiment's lost movement time
  above the retained 250 ms clamp. Strong stall independence requires safe subdivision or
  the full simulation follow-up; it is not an achieved property of `delta-20`.
- **Capacity:** measure extraction/scheduling cost and average/worst catch-up debt on every
  supported CPU. Debt must not grow without bound during ordinary gameplay. Rendering can
  slow, but target periodic rates must not silently become CPU-specific.
- **Coverage:** repeat opponents, views, natural weather, collisions, rescue/pits, pause and
  session transitions, including at least ten minutes and a restart. Test clock/phase wrap
  with isolated synthetic cases. Drawing twins must still report zero mismatches.
- **Compatibility:** timing-off behavior retains native hooks and established captures;
  `CUSTOM1=0/1`, missing fast RAM and unsupported scene fallbacks all use the selected timing
  policy. Deterministic replay and debug instrumentation remain absent from release builds.

Start with a stock PAL A500 reference, then 68000/fast, 020, 030/25, 040/25 and 060/50.
Use the same A500-derived periodic cadence everywhere. If NTSC is supported, verify the
actual TOD frequency and convert time appropriately: a 20 ms tick must not become one
NTSC field (about 16.7 ms). Physical-board testing remains excluded as requested.

## Decisions to resolve from measurements

1. Select representative original A500 routes and freeze the periodic reference cadence,
   preserving native slower subdivisions. A500 is the chosen reference; N is not yet known.
2. Classify which mutations can be separated safely and which need interleaved movement.
3. Decide logical time ownership, pause/transition rules and input/event ordering.
4. Reserve an independent timing option and publish the initial upper-clamp limitation.
5. Judge the smaller approach against the frozen gameplay bounds before undertaking full
   fixed-step simulation. Whole-game claims also require the animation/mode checks.

No part of this plan requires a chunky renderer, new custom cache handling or changes to the
validated planar raster algorithms. The essential change is who advances gameplay, how often,
and which logical instant every update observes.
