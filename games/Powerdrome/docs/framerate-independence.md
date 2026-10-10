# Powerdrome framerate independence analysis and plan

Status: analysis and proposed work only. No simulation changes have been implemented.
The completed renderer work remains unchanged. This is a separate proposed project.

Powerdrome is not framerate independent. Its main movement uses elapsed time, but that
elapsed time is clamped, and other gameplay operations advance once per rendered frame.
Faster CPUs and the optional fast planar renderer therefore change more than smoothness.
The recommended solution is a fixed simulation tick, independent of drawing and buffer
presentation, with an explicit treatment of every gameplay side effect currently embedded
in rendering, HUD work and the outer loop. Correcting the minimum timestep alone is an
incomplete fix.

## What success means

For the same initial gameplay state, random seed and time-stamped input sequence, supported
machines must produce the same authoritative game state at the same simulation tick,
regardless of rendering speed, view or `CUSTOM1`. Over equal unpaused real time, simulation
time must advance equally, within one tick of scheduling latency when the CPU can keep up.

Authoritative state includes player and opponent positions, speed, orientation, collision
and damage state, resources, race progression, gameplay random state and gameplay timers.
Rendering scratch, bitmap pointers, displayed frames and purely visual animation state need
not match. Smoothness and input-to-display latency can still differ across machines.
A machine unable to sustain the simulation workload cannot be guaranteed real-time play;
that capacity limit must be measured and reported rather than hidden by discarded time.

This is a stronger requirement than the existing renderer twins. Those compare two drawing
paths for the same scene input. The 30,623 successful comparisons establish drawing
correctness, not matching gameplay trajectories across CPUs.

## Evidence and confidence

Game addresses below are offsets into the code hunk. State offsets are relative to the
state base at hunk `$a6e`. Evidence consists of the supplied game, existing captures and
read-only inspection of their saved code. No new emulator run or implementation experiment
was performed for this document.

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

### Why extracting a simulation tick is substantial work

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
| Remove or lower only the minimum delta | Small patch; directly addresses fast displacement | Leaves controls, resources, effects and randomness dependent on frames; large steps remain problematic | Useful diagnostic experiment, not completion |
| Cap the entire loop at 25 Hz | Small containment measure for the lower clamp | Slower machines still update less often; limits smoothness; per-frame behaviors remain inconsistent | Not the requested solution |
| Convert every operation to variable elapsed time | Can retain one update per drawing pass | Nonlinear control/decay, random events, integer truncation and collisions need different conversions; results still depend on integration step size | Possible, but harder to prove comprehensively |
| Fixed simulation tick, independent rendering | Same update count/order and integer arithmetic per simulated second; clear replay checks | Requires separating interleaved code, input, effects and transitions | Recommended |

Use one fixed tick duration across CPUs and renderer options. Do not pick a different rate
based on hardware. Start the design investigation with **25 Hz / 40 ms** as a candidate:
it matches the existing minimum step and is an integer eight game-clock units in PAL.
This is a convenient candidate, **not proof of the intended original game speed**.

A500 rendering has varied around 10–16 fps in the existing routes; executing all unchanged
per-loop operations at 25 Hz would speed some responses relative to those routes. Before
freezing the rate, compare original A500 control response, resource consumption, impact
recovery and race timing. Evaluate a lower common tick if necessary, or calibrate specific
per-tick constants/counters to an agreed reference. Rates that do not divide the source
clock need a rational accumulator, not a rounded interval that drifts. Do not select 50 Hz
solely because PAL displays 50 fields per second; it doubles the update budget versus 25 Hz.

The intended gameplay pace has no unique answer in a frame-dependent original. The proposal
is to use the original A500 as the gameplay-feel reference, document unavoidable choices,
and then make the selected behavior consistent across supported hardware.

## Recommended architecture

### Separate timekeeping, simulation and presentation

Keep the native clock/input interrupt lightweight. Do not move physics into the VBL interrupt.
A main-task scheduler samples a monotonic time source, accumulates unpaused elapsed time,
runs due fixed ticks, and renders the most recent complete state when appropriate.

The clock audit must distinguish hardware elapsed time, logical simulation time, race/event
timers and presentation timestamps. Do not globally repurpose `$f96` before identifying all
its readers, writers and pause adjustments. Simulation decisions based on deadlines must
observe the time at the current logical tick during catch-up, not the same final wall-clock
time for every overdue tick. Otherwise weather, rescue or opponent decisions can still
vary with rendering cost despite a fixed movement delta.

Conceptual scheduler, not an implementation recipe:

```text
sample elapsed unpaused time into accumulator
while a complete tick is due and the per-pass work budget permits:
    select held controls and queued edges for this tick
    run exactly one gameplay tick with constant movement interval
    advance logical tick/time and consume that interval
    stop immediately on a mode transition
if still behind:
    service essential input/OS work and continue catch-up
else if a presentation is due:
    draw the latest completed state, update HUD imagery and present once
else:
    wait without advancing gameplay
```

A per-pass tick budget prevents an unresponsive unbounded loop; it must not silently discard
the remaining elapsed time. Transient stalls should recover by reducing rendering. Sustained
overload must be observable and must fail the real-time support gate for that configuration.
Choosing time dilation or intentionally dropping time later would be an explicit compromise,
not framerate independence. Blocking menus, disk loads and pause are mode boundaries with
an explicit clock rebase, not ordinary stalls to replay as movement on return.

At 25 Hz, a 50 Hz renderer may draw the same state twice. Start without interpolation;
correctness is easier to establish that way. Optional interpolation can later improve
smoothness using previous/current positions and orientation in presentation-only data.
It must never feed interpolated values back into collisions, opponents or race logic.
Native/faster rendering and full/inset/effect fallback must all consume the same tick state.

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

Inventory all `$53f6` callers and any other random generators. Gameplay random advancement
must be identical for equal ticks. Move draw-triggered gameplay events to the tick, then
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

Keep player, collision, opponent and post-update resource ordering stable within a tick
until a deliberate change is validated. Handle race end, rescue, pit return and restart as
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
check that one tick cannot skip required collision or track-segment transitions. If collision
substeps are necessary, use the same deterministic subdivision rule on every CPU.

## Step by step implementation plan

All steps below are **not started**. Each produces a reviewable result before the next gate.
The shortcut names can be used to request a step. This plan authorizes no implementation.

| Step | Shortcut | Deliverable and completion gate |
| --- | --- | --- |
| F1 | `timing-map` | Enumerate authoritative state writes, clock readers/writers, input consumption, RNG calls, render side effects and all update exits. Classify each by time domain. No reachable unknown gameplay mutation may remain on a supposedly draw-only path. |
| F2 | `timing-baseline` | Add isolated measurement/replay tooling; capture equal-time state on 000/020/030/060 with native and fast rendering. Quantify clamp use, response/resource rates and update-only cost. Freeze reference behavior, tick duration and tolerance choices before production patches. |
| F3 | `tick-split` | Separate update, mixed HUD/effect logic and presentation while retaining one tick per legacy loop for the first comparison. Prove the split alone preserves native state, call order and visible output on identical inputs; handle nonlocal exits explicitly. |
| F4 | `tick-clock` | Add accumulator, logical clock, constant movement delta and render-independent scheduling. Demonstrate exact tick counts, no time loss on recoverable stalls, bounded debt, pause/rebase correctness and no extra buffer swaps. |
| F5 | `tick-behavior` | Finish input event ownership, RNG separation, resource/control calibration, periodic counters, weather and audio/event ownership. Equal tick replay must give identical authoritative state across render cadences and views. |
| F6 | `timing-modes` | Cover pit/departure, rescue, repairs, restart, qualifying/race transitions, title demo and menu timing. Document any deliberately excluded mode; do not claim whole-game independence with frame-driven animations left unaddressed. |
| F7 | `timing-matrix` | Run correctness and real-time capacity matrix, native/fast renderer comparisons and long scenarios. Retain existing planar twin checks using one shared simulation tick. Meet the numerical gates below. |
| F8 | `timing-release` | Final option/help text, diagnostics removal from release, memory and hook audit, disabled-mode equivalence, reproducible docs and commit. Keep timing mode opt-in until its support envelope is accepted. |

F1 and F2 determine patch scope; F3 is the highest structural risk. F4 depends on F3 rather
than attempting to repeatedly call the current combined routine. F5 may refine the split,
so F3 equivalence checks must be rerun after such changes. F3 comparisons should replay the
same captured native delta sequence and inputs in test builds: added wrapper overhead can
change wall-clock deltas even before intentional timing changes. This isolates the split
from incidental timing differences. F6 and F7 complete the claim;
a passing straight-line movement demonstration alone does not finish this project.

This is a substantial reverse-engineering and compatibility task, not a clamp-only patch.
The existing renderer and input harness reduce setup work, but do not supply the missing
simulation boundary or a state-equivalence oracle. A reliable time estimate should follow
F1/F2; the main uncertainty is how many hidden drawing and transition dependencies they
expose. Progress should be reported as completed gates plus numbers, not a speculative
percentage of the whole effort.

## Measurement and acceptance

### Required logs and comparisons

Record hardware elapsed units, logical time/tick, raw delta, applied movement interval,
accumulator debt, tick count per render, input events consumed, gameplay RNG state, simulation
and rendering costs separately, and authoritative state after each tick. Count resource
changes, collisions, opponent updates, weather events, mode transitions and audio triggers.
Keep binary traces, memory dumps and screenshots under ignored `tmp/`.

Create an explicit state schema including opponent arrays and mutable gameplay data outside
the main state block. Compare normalized values, not relocated pointers or all RAM. An
excluded field needs a reason and a read/write audit proving it cannot influence later
simulation. Hashes provide compact comparisons; on mismatch retain the first differing tick
and a field-by-field snapshot. State parity should normally be exact between CPUs when
using identical integer code and tick-indexed input; tolerance must not hide divergence.

The existing renderer twin must surround drawing only. It must never run resource updates,
RNG-driven gameplay or simulation twice. A frozen logical state drawn natively or through
fast planar staging should retain current pixel/register/CCR/scratch/guard guarantees.
Compare at equal logical ticks, not equal rendered-frame indices or merely final screenshots.

### Numerical gates

- **Tick accounting:** at the proposed 25 Hz, 10 unpaused seconds require 250 ticks;
  60 seconds require 1,500; ten minutes require 15,000. Define the initial boundary exactly.
  A sampled endpoint can be less than one tick behind; a boundary-aligned replay must match
  exactly. Revise these counts if F2 chooses another rate.
- **Cross-CPU state:** identical authoritative state after every tick on the supported matrix,
  with identical replay and seed. Check native and fast rendering separately and against
  each other. Any intentional platform difference needs a narrowly defined exception.
- **Render independence:** replay at controlled 10, 15, 25 and 50 presentations/s where
  feasible, plus variable intervals and skipped drawing. These are test cadences, not
  shipping frame caps. Tick state and gameplay events must match regardless of cadence.
- **Stalls:** inject 100, 250 and 500 ms delays in a test build. Debt must be retained and
  recovered without one giant movement step, duplicated input or skipped collision work.
  Log recovery time and peak debt; pause is tested separately and must accumulate no debt.
- **Capacity:** provisional target is average simulation utilization below 70% of the tick
  interval, with no sustained increasing debt. For 25 Hz this leaves a 28 ms average
  simulation budget and 12 ms reserve before drawing. Measure worst-case and high-percentile
  cost as well; this proposed margin is not an achieved result or a guarantee of render FPS.
- **Gameplay:** match the chosen baseline response/resource/time curves within tolerances
  frozen in F2. Use scripted acceleration, braking, turns, engine failure, afterburner,
  collisions, recovery, rescue, opponents and natural weather, not only constant-speed motion.
- **Long runs:** at least ten minutes of matched tick replay, plus a complete native session
  transition/restart and the existing coverage routes. Check timer/accumulator rollover with
  isolated synthetic tests instead of waiting days for a live wrap.
- **Compatibility:** timing-off behavior retains native update hooks and established captures;
  `CUSTOM1=0/1`, fast allocation failure and unsupported scene fallbacks preserve the selected
  timing mode. Normal build includes no deterministic input/seed fixture or debug capture.

Start with PAL 68000/no-fast, 68000/fast, 020, 030/25, 040/25 and 060/50. If the 68000 cannot
sustain the selected tick after drawing is decoupled, document that result before claiming
support; do not silently lower its tick rate. If NTSC is supported, verify the actual TOD
source frequency and use a region-independent duration conversion. Counting two VBLs is
40 ms in PAL but about 33.3 ms in NTSC, so a VBL-count-only scheduler is insufficient for
cross-region speed equality. Physical-board testing remains excluded as requested.

## Decisions to resolve before implementation is accepted

1. Freeze the reference gameplay feel and global tick duration from F2 evidence. The current
   proposal is A500-referenced behavior and a 25 Hz candidate, not an already approved balance.
2. Choose which clock each existing deadline observes, especially during catch-up and pause.
3. Finalize the overload/support policy based on measured update-only cost.
4. Reserve the timing option independently of renderer and development fixture controls.
5. Decide whether the first deliverable claims racing-only or whole-game timing independence.
   F6 is required for the broader claim; optional visual interpolation can remain future work.

No part of this plan requires a chunky renderer, new custom cache handling or changes to the
validated planar raster algorithms. The essential change is who advances gameplay, how often,
and which logical instant every update observes.
