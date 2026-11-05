# Ferrari Formula One game-time model and performance design

Current qualification (2026-10-14): emulator release qualification and calibrated
030/040/060 analysis pass; see STEP5_CAPACITY.md's release closure,
manifest/release-qualification.json and the tracked RELEASE_QUALIFICATION.md.
The opt-in local RC1 is reproducible. Human playtesting and real Amiga hardware
are deferred; historical measurements below retain their original scope.

Step 4 evidence and design, SPS 0481, PAL. Complete within the analysis scope described below.
Scope: 68000, 68020 and 68020 + Fast. 030/040/060 remain deferred.
No normal slave or game source has been modified. Diagnostics stay in ignored
`tmp/dev/`. The automatic no-input demo is the performance workload; warp is
used through startup and verified off before elapsed-time measurements.

## What a native tick means

The race is update-coupled. The calendar and session clock routine at resident
hunk 9+$372 ($22c3a in the calibrated layout) adds **one tenth of a second per
call**. Ten unpacked bytes hold year, month, day, hour tens/units, minute
tens/units, second tens/units, and tenths. This is not a binary or packed-BCD
counter. Carries occur at 10, 10, 6, 10, 6 and 24 as appropriate. The companion
hunk-10 weights are 316224000, 26784000, 864000, 360000, 36000, 6000, 600,
100, 10, 1. Calendar month/year handling must retain the native implementation.

The race calls it at race hunk 160+$1362/$1370 ($65dca/$65dd8), once for calendar
$226c0 and once for session $226ca, after drawing. Countdown and a session-specific
14:59 boundary can suppress an increment; preserve those branches. The calendar
is not to be replaced by host time. Repairs, travel and session changes intentionally
advance it in larger jumps.

Independent corroboration comes from the lap display: race hunk 174+$3ec
($6aac4) divides the lap count by 600 for minutes and by 10 for seconds/tenths.
Lap counters at $22398 advance inside the car update and reset at native lap
boundaries. Thus **10 native ticks/second** is the candidate for real-time race
clocks without changing the arithmetic of a tick. The manual's real-time claim
supports that choice. The original PAL A500 throughput and the slave's two waits
do not define a physically meaningful timestep.

This establishes clock units, not metres per coordinate unit. Speed at $2275a
is used as a per-tick displacement magnitude, resolved through native sine/cosine
helpers, then added to local coordinates. A separately verified km/h-to-distance
calibration has not been established. Do not invent one or rescale the original
integrator from a plausible-looking dashboard value.

## Time sources and modal boundaries

| Domain | Code/evidence | Native behavior and design consequence |
| --- | --- | --- |
| Display fields | resident hunk 30+$44 VBL server; counter in hunk 32+$1a ($24ad2) | Increments independently of the race. Mouse sampling also runs here. The 16-bit counter is reset by menu code; a new scheduler needs its own monotonic counter. |
| Race world | race hunk 167, $67120..$68634 | Eight cars, 7 down to 0, once per main loop. No elapsed-time read in this update. Preserve ordering, fixed-width arithmetic and RNG order. |
| Calendar/session | resident hunk 9+$372; race call sites above | One tenth per eligible loop, irrespective of the time drawing took. Keep clock mutation in the logical tick, separate from clock text drawing. |
| Ordinary menu time | file:$0f7bc h160+$6e8/$6fe/$750; file:$1ce80 h191+$6b4..$6d4 | Reads the VBL counter, requires six fields for ordinary advancement, clears it, then increments the calendar. At PAL this nominally gives 0.1 game second per 0.1202 real second. A 60 Hz assumption is an inference, not an NTSC measurement. Preserve this separate native path. |
| Accelerated time | file:$0f7bc h179+$9f4..$b8e and related callers | Consumes a requested time amount through clock calls, including batches of 13, while processing session transitions. It is scripted calendar advancement, not overdue driving ticks. |
| Pause | file:$22f30 h160+$986..$a50 ($653ee..$654b8) | ESC decodes to space; native polling loop waits for another space before continuing. Car and race-clock calls lie outside the pause loop. Audio is stopped/restarted through native calls. New simulation debt must not accumulate here. |
| Tow/race exit | file:$22f30 h160+$96c..$982; exit at $65f48 and state export from $660ac | Native K/status branch calls resident h3+$1a3a and leaves the race. Convert the high-precision condition/fuel state back through the original exit code. Rebase the scheduler before a future race. |
| Results and save/load | manual: only race statistics are saved; overlay/calendar-copy paths | A saved result is not a suspended driving simulation. Keep existing persistence and result transitions; never serialize stale scheduler debt or pointers to an unloaded race overlay. |
| Audio playback | audio.device, hardware audio DMA, native OS service | Sample playback progresses independently; RPM/boost/effect parameters are often changed by a logical tick, including code embedded in drawing. Do not make audio playback tick at render frequency. |
| Pacing/synchronization | slave fixtiming; WaitBlit; $65728 beam poll | Two WaitTOF calls cost roughly 34–36 ms per loop. IRQ/input/audio service can proceed during them; the single game task does not execute another car update. Keep display/blitter safety separate from simulation pacing. |
| Loader delays | slave fixdelay and native startup loops | Outside settled driving. They are not a calibrated physics-rate benchmark. |

The executable has no `timer.device` string; the installed KickEmu does contain
its own timer support. Direct native CIA access found in the game is the mouse
button read. The complete hunk/relocation audit finds the field-counter consumers
above, rather than a race delta-time or boot-rate calibration. This is scoped
source evidence, not a claim that the OS never uses a timer or CIA.

Garage work, transport, results and save/load are retained as native modal code.
Their clock call/copy and time-jump paths were audited statically. They are not
claimed as newly validated interactive playthroughs. A design that changes those
paths requires additional native-route tests before release; the selected design
keeps them outside the driving scheduler.

## Logical state, units and update ownership

Absolute addresses below are calibration values. Patch identities are the
resident/race hunk and relative offset in `tmp/step4/active.dis` and the annotated
per-overlay disassembly; resolve and byte-check them in the actual loaded overlay.

| Quantity | Representation and native writers | Consumers and required cadence |
| --- | --- | --- |
| Track position | $6a60a eight segment words; $6a61a/$6a62a signed lateral/longitudinal words; committed at $68532/$68546/$68584 | Track and collision tests, AI and projection. One native update per tick; 512 local longitudinal units trigger section transformation. Keep curve transforms and rounding order. |
| Speed and displacement | $2275a eight words; working $32fbe; acceleration/braking in h203, vector generation at $6dc38; displacement $6f13c/$6f14c | Movement, AI distance comparisons, RPM and damage. Magnitudes stay in native units; do not multiply collision thresholds by elapsed time. |
| Heading | $6a66a/$6a67a; fixed-point working accumulators $32fb4/$32fb8; commit $6855a/$68568 | Trig lookup masks to 1023: 1024 units/revolution. Preserve fractional accumulator and wrapping. |
| Steering/AI | $1c6a2 and h169 state; player copy at $67492; AI average at $6773c..$67752 | Native mouse/AI modes differ. AI filters and decision count stay per tick; renderer does not run controllers. |
| Countdown/status | $66f94 decrement $67174; $2268e status; $32f30 contact recovery counters | Each tick, with native start, out-of-race and recovery branches. A countdown value is a tick count, not a field count. |
| Gear/RPM | $66c3c manual gear; $6f0e8 gear bytes; $6f270/$6f0f4/$6f0f6 RPM values; h203 $6d6c8..$6d944 | Keyboard edges change gear once; automatic shifts and RPM recalculation stay with the appropriate car update. Do not replay one key edge during catch-up. |
| Boost setting | $1bf52, 0–9; key decoder $654ce | User setting, not a rate. Retain per-event changes and the corresponding logical input timestamp. |
| Boost-related filtered state | $66c76; $6bbfc..$6bcc2 computes target from RPM/boost/condition, dead band ±5 and steps ±9; also writes audio parameters | **Runs inside the drawing block today but feeds h203 wear/failure calculations.** Must run exactly once per logical tick. It is not safe to skip it with polygons or call it on every interpolated frame. Native units retained; no unproved temperature-in-degrees claim. |
| Fuel | $22376 eight longs, expanded from setup by ×10000 and exported by ÷10000; h203 consumption paths | Per-car update and native refill/exit writers. Retain the fixed-point remainder and original boost/engine dependence. |
| Conditions/wear | $66c3e..$66c72 longs; most setup values expanded by <<14; h203 $6ea3e and probabilistic decrement helper $6ec94; exit $660ac..$661a6 | Engine/system/tyre condition magnitudes and gauges, not generic elapsed-time floats. Keep the nine-way rotating update index $6ef52 and probability/RNG sequence per tick. Preserve native setup/export, contact and failure writers. |
| Damage/contact | h167 wall response $6988c; h203 collision/friction paths; Q14 conditions and status arrays | Impulses, speed exchange/projection and event damage remain native. No fine-step scaling is selected. The controlled contact fixture tests a native wall-response path, not every possible crash. |
| Calendar/session/lap | Ten-byte clocks above; $22398 lap words; flags and native copy/reset functions | Once per eligible logical tick. Drawing their digits must not increment them. Calendar jumps and reset/copy events are separate domains. |
| RNG | Resident h35, 56-word XOR state and two cycling pointers | AI, condition failure and other native calls keep their order. Separate title/boot RNG activity explains cross-machine seed differences. No extra random calls from interpolation. |
| Wheel/instrument animation | $6c942/$6c944 phases, masked to 2047 in h197; gauge state and frame modulation byte $1be42 | Some phases currently advance in drawing. Move advancement to ticks and render a snapshot; phase consumption can be per presentation. Frozen visual phases in a logic-only diagnostic are not game-state equivalence claims. |
| Render scratch | $6a63a..$6a669 projection/sort workspace; race projection arrays, bitplanes and draw-bank indices | Recompute for each presentation. References to the excluded projection block are in rendering hunks 170, 195 and 197. It must not be compared as authoritative car position. |
| Demo/passenger | $1bee8/$1c1c2/$1c1c4; takeover in resident h12+$a8 | Automatic controls use the same native car update. Mode transitions reset the new scheduler's input/pose history. No replay system was established; none is assumed. |

A completed call to $67120 is not a complete logical tick. A tick must also
include input/event handling, post-update boost/audio work, clock/status updates
and other native once-per-loop state changes. The main-loop entry $65174 after
the previous drawing pass is the completed-loop comparison boundary used here.

## Measurement protocol and rejected experiments

`capture_step4.py` boots each arm afresh, turns warp off at car update 120, checks
it at update 125, and takes read-only snapshots after complete loops 125, 150,
175 and 225. Differences in the free-running field counter measure emulated
elapsed time, never debugger or host wall time. No external input is applied to
these ordinary runs. Step-3 breakpoint-free 1,000-field windows independently
provide equal-elapsed-field comparisons.

Normal-release CUSTOM1=0/1 comparisons and equal-size diagnostic control/slow/
logic comparisons use identical native initialization within each pair. Slow
adds three WaitTOF calls after the draw barrier starting with tick 126. The
corrected logic arm omits the main drawing and final instrument pass but preserves
the boost/audio routine, clocks, inputs, publication/barrier work and camera
calculation. Its measured cost includes residual drawing of gauges/clock digits:
it is a conservative executable prototype, not a pure CPU cost or final tick kernel.

The first omission experiment skipped $6bbfc and changed condition/engine state.
It is retained as rejected evidence (`a500-logic`), not included in capacity claims.
The corrected v2 comparator checks the previous inventory plus complete resident
settings/globals, car working state, engine data/work and boost/audio controls.
It excludes only the identified projection block from the old mixed car/render
range. Full rendered pixels and visual scratch are expected to differ in an
omission arm. This exception is not used for normal or slow-render equivalence.

The contact fixture supplies one identical penetration at the native collision
input boundary, then leaves the native response to run. It is an explicitly
synthetic stress test with no user input, not evidence of a naturally occurring
demo collision or validated human driving controls. A preliminary attempt to
perturb the earlier position did not reach the required handler and is excluded.

## Measured coupling and capacity

All 21 accepted driving runs advance both native clocks by exactly **100 tenths
for 100 completed loops**. Twelve paired comparisons pass at 51 checkpoints:
CUSTOM1 on/off, normal/delayed drawing, normal/corrected drawing omission, and
rendered/omitted drawing after the synthetic wall contact, on all three profiles.
The six ordinary-release anchors are byte-identical across the full 512 KiB dump
to their previously validated step-3 anchors. The comparator also detects a
changed speed byte, a later tick and the rejected first omission experiment.

Each value below is emulated elapsed milliseconds per complete loop, averaged
from loops 125 to 225. These are elapsed costs with interrupts, DMA contention
and residual synchronization, not exclusive CPU timings. The field-counter
endpoints have roughly one field of phase uncertainty over the entire 100-loop
window (about 0.20 ms per mean loop). Capacity arms have one fresh boot per cell;
the repeated breakpoint-free performance baselines remain in step 3.

| CPU | Ordinary fix on | Ordinary fix off | Diagnostic control | Delayed drawing | Corrected drawing omission |
| --- | ---: | ---: | ---: | ---: | ---: |
| 68000 | 285.65 | 251.00 | 254.00 | 300.48 | 87.14 |
| 68020 | 180.29 | 143.63 | 143.63 | 200.32 | 52.68 |
| 68020 + Fast | 180.49 | 140.42 | 140.22 | 200.32 | 52.28 |

The three diagnostic arms use CUSTOM1=1 and equal-size slaves, differing in one
mode byte. Their initialization is matched to each other; do not pair their
states or seeds with a differently sized ordinary slave. Slower drawing changes
elapsed time, but leaves the sampled logical state, clocks and RNG identical at
the same completed loop. The normal/slow comparisons also preserve the original
mixed state/projection block; only drawing-omission comparisons exclude the
proven rendering workspace.

Conversely, the ordinary-release step-3 windows give different clock advancement
in the same **1,000 fields = 20.0319 emulated seconds**:

| CPU | Fix on: game seconds | Fix off: game seconds |
| --- | ---: | ---: |
| 68000 | 7.0 | 8.0 |
| 68020 | 11.1 | 14.0 |
| 68020 + Fast | 11.1 | 14.3 |

These windows begin at completed car update 125, not the completed whole-loop
boundary. The Fast fix-off endpoint includes a clock increment in a partially
completed loop; its 143 tenths and 142 completed car calls are not evidence of
clock corruption. Together the matched-loop and equal-field observations prove
that the current driving clocks follow work completed, not elapsed real time.
No elapsed-field input tape is needed for this autonomous demo; human controls
will require one for scheduler acceptance.

For the contact pair, tick 126 supplies player 0's working lateral coordinate
as `-left_track_width - 80`, at the original collision input boundary. Each run
is required to hit the native wall handler at $6988c; hitting the pit route is
rejected. Five checkpoints, including immediately after that tick, match.

| CPU | Rendered contact arm, mean ms/tick | Omission contact arm, mean ms/tick | First contact tick: rendered / omitted fields |
| --- | ---: | ---: | ---: |
| 68000 | 246.39 | 87.54 | 13 / 4 |
| 68020 | 140.82 | 53.49 | 7 / 2 |
| 68020 + Fast | 139.82 | 52.88 | 7 / 2 |

The first-tick field measurement is coarse (about ±1 field); this is one native
wall response amid eight-car traffic, not a worst-case guarantee for all crashes.
The condition, speed, positions, progress, clock and RNG comparisons continue
for the following 99 ticks.

Let `L` be the corrected omission cost and `R = control - L` the estimated
incremental presentation cost. At 10 ticks/s, `(1000 - 10L) / R` estimates the
remaining drawing rate. This subtraction is a planning approximation: omitting
drawing also changes contention and interrupt timing, and still retains some UI
work. It is not a measured shipping scheduler or a proof of additive CPU costs.

| CPU | Tick demand at 10 Hz | Estimated remaining presentations/s | Existing fix-on FPS floor |
| --- | ---: | ---: | ---: |
| 68000 | 87.1% | 0.77 | 3.494 |
| 68020 | 52.7% | 5.20 | 5.541 |
| 68020 + Fast | 52.3% | 5.43 | 5.541 |

The 68000 fails this combined real-time-and-rendering budget by a large margin.
The 68020 profiles have substantially more tick headroom but also fail the
current rendering floor in this conservative projection and lack a measured
worst-case margin. **Do not enable a 10 Hz mode on any profile yet.** First split
the residual UI work, recover measured arithmetic/blitter cost, and demonstrate
sustained bounded debt together with the rendering floor. Reducing tick frequency
to fit the CPU would knowingly slow the clocks, not solve correct game speed.

## Native pause and startup observations

The pause check uses a new, balanced key-consumer fixture, separately built from
the ordinary release. It supplies raw ESC ($45) to the native decoder after the
settled demo, then supplies a second ESC after 120 native VBL counts. The native
decoder handles demo takeover, maps ESC to space and enters the actual pause loop.
On both 68000 and 68020 + Fast, all compared logical state blocks—including both
clocks and RNG—remain identical over a breakpoint-free **100-field (2.0032 s)**
paused window. Resuming completes one native update and advances both clocks by
exactly one tenth; the paused time is not caught up. Demo becomes driving mode 3
through the native takeover path. This validates the consumer/pause boundary,
not physical keyboard delivery. The earlier host-injected ESC attempt timed out
and is excluded; the old step-1 input fixture is not reused as evidence.

The no-input startup runs trace the accelerated clock helper and ordinary menu
clock call site, then turn warp off and capture 600 fields (12.0191 s). During
settling, startup has already moved into loading/countdown: active overlay
file:$0dc70 at the anchor becomes race overlays file:$22f30/$30a30. On 68000 the
calendar stays at 13:00:00.2 and session remains zero throughout this window.
On 68020 + Fast, driving starts soon enough to add 17 tenths to both clocks.
These are **startup-transition measurements, not a steady-menu clock-rate test**.
The ordinary six-field menu gate remains static evidence. Do not turn the
startup delay or suppressed countdown increments into simulation debt.

Other modal domains remain native. The accelerated helper accepts amounts in
tenths, including 150 (15 seconds), 6000 (10 minutes), 18000 (30 minutes) and
36000 (one hour); some branches advance in batches of 13. The identified callers
are file:$0f7bc h160+$3b4/$3ce/$129a/$12dc/$12f6 and h176+$eae (repair-table charge).
The full relocation reference inventory includes clock reset/copy consumers in
resident and overlay code. Preserve each native call, rounding and transition;
a race-only scheduler must neither intercept these jumps nor replay them as car
updates. Garage/repair, tow, transport, results and save/load have static boundary
coverage here, not fresh interactive-route acceptance. Runtime route validation
is required before releasing a scheduler whose entry/exit hooks touch them.

## Selected design and acceptance gates

**Superseded in part (2026-10-12):** the interval is now chosen by CPU class and
Fast memory: 20 ms only on 68020+ with Fast memory, with opponents on the native
100 ms step on a 14 MHz 68020 (Plan B); chip-only 68020 and 68000 use the native
100 ms step. See `STEP5_CAPACITY.md`. The text below records the earlier decision.

Design revised at the user's direction on 2026-10-12: use **two separate fixed
physics/game-logic intervals**, selected by CPU class:

| CPU class | Interval | Selection rule |
| --- | --- | --- |
| 68000 | Coarser interval, exact value not yet selected | Measure the adapted update and choose a cadence that leaves sufficient drawing, input and audio capacity. Do not inherit the 68020 interval. |
| 68020+ | **20 ms (50 Hz)** | User-selected design requirement, shared by stock 68020 and 68020 + Fast. 030/040/060 implementation and analysis remain deferred. |

This supersedes the earlier proposal to schedule unchanged native 100 ms ticks
on every CPU. The native tenth-second clock quantum remains measured evidence,
not the required frequency of the new physics integrator. Both CPU paths must
advance the same amount of game time per elapsed second. A coarser 68000 interval
reduces computation frequency; it must not slow movement or the game clock.

Adapt continuous rates, filters, deadlines and fractional state to each selected
interval. At 20 ms, simply calling the original tick five times as often is
incorrect. Accumulate elapsed time for native tenth-second clock increments;
retain separate native season/repair/travel semantics. Audit rotating wear work,
probability trials and RNG ordering so finer updates do not multiply event rates.
Keep contact impulses and one-shot commands distinct from integrated rates.
The inventory above is the starting point; it does not yet prove all conversions
or handling equivalence for a changed integrator.

The existing omission prototype costs about 52–53 ms per update on 68020, more
than the entire new 20 ms budget. These are costs of the old update, not a forecast
of the adapted implementation. Optimization and remeasurement are prerequisites;
50 Hz is a requirement, not a demonstrated performance result. Do not silently
relax it to 100 ms if the budget fails. Keep the original mode available until the
new path satisfies timing, handling and rendering gates.

Implementation order:

1. Extract the complete tick ownership identified above. Split clock mutation
   from text drawing and boost/audio mutation from gauge drawing. Prove that the
   disabled path and equal-size control retain native state and display output.
2. Add a dedicated monotonic field counter and rational elapsed-time conversion.
   PAL is 49.9204102 fields/s here; one field is not exactly 20 ms. Keep
   fractional time, wrap-safe differences, completed ticks and pending debt.
3. Enter the new scheduler only in the active race overlay. Rebase at race entry,
   ESC pause/resume, demo takeover, tow/pit/exit, track/session changes and load.
   Calendar jumps and menus never become a backlog of driving updates.
4. Consume tick-indexed input history, including accumulated mouse deltas and
   single-use gear/boost/pause edges. Preserve VBL input sampling and native key
   decoding. Keep audio serviced between bounded batches of at most two ticks.
5. Draw only from a completed snapshot and keep collision state authoritative.
   Preserve WaitBlit/DMA ownership and safe publication. Initially present the
   latest completed pose; do not add speculative extrapolation. Add interpolation
   only if drawing can exceed tick rate, with an explicit extra-tick latency
   budget and discontinuity resets.
6. Enable the real-time mode on a profile only after sustained capacity passes.
   While temporarily behind, skip drawing and retain debt; never silently discard
   time or change the quantum. If a profile cannot sustain the workload, keep the
   new mode unavailable there rather than claiming successful catch-up.
7. Use the step-3 exact-output arithmetic/blitter opportunities to recover the
   required headroom before raising rendering targets. Re-price the complete
   tick and renderer after each accepted optimization.

Release gates: exact state/RNG equivalence for the disabled and native-step
control paths; for the adapted intervals, compare at equal simulated time with
matched input history and explicit handling/condition tolerances, including
traffic/contact and event probabilities. Also require correct
clock progression over long emulated intervals; bounded debt including contact;
no input-history loss or repeated edges; native pause/modal transitions; safe
blitter/buffer ownership; and a measured rendering rate above the corresponding
fix-on baseline without slowing game time. Use at least the measured 3.49 FPS
A500 and 5.54 FPS 68020 baselines as regression floors, not as user-approved new
simulation rates. If these cannot all hold, optimize first and keep legacy mode.

No scheduler has been implemented by step 4. The capacity projection above is a
design gate, not proof of convergence of code that does not exist. Real hardware,
Irek, full season interaction and the deferred CPUs remain outside this evidence.

## Reproduction and scope of completion

`profiling.md` lists the commands. `manifest/step4-validation.json` records the
asserted gates, exact run/input/tool/build hashes, startup/pause observations and
excluded experiments. `manifest/step4-measurements.json` contains the state-block
inventory, checkpoint hashes and measured field counts. `step4-static-audit.json`
and `step4-clock-refs.json` preserve the hunk/relocation evidence. Per-overlay
annotated disassembly and raw snapshots remain under `tmp/step4/`.

Early per-run `result.json` files inherited unused `requested_fields: 1000` and
`observer: survey` defaults. The actual step-4 driving protocol is completed loops
125–225, with elapsed fields read from snapshots; the validation manifest labels
this explicitly. Only the reused step-3 runs are 1,000-field driving windows.

Step 4 is complete as an analysis/design gate for SPS 0481 and the three selected
PAL profiles. It establishes the native clock quantum, state ownership, measured
coupling, a conservative capacity envelope, and a conditional implementation
choice. It does not certify gameplay at 10 Hz, real-hardware performance, every
modal route, physical input, Irek or the deferred CPUs. Step 5 must retain a
working legacy path and satisfy the measured capacity and transition gates before
the new mode can be enabled. No production code or normal slave changed.

Design revision provenance: the measurements and captures above are unchanged.
The original step-4 validation manifest hashes the documents as they stood before
this CPU-specific interval decision; it does not validate a 20 ms implementation.
The revised design needs the additional interval-conversion and capacity gates
specified here and in step 5.

### Accelerated release observations (2026-10-14)

Calibrated 030/040/060 emulator analysis is complete. Enabled production reaches
16.640 FPS over 300 presentations and 0.0409% error over 60 simulated seconds.
Original v1.01 observations range from 5.491–5.691 FPS (CUSTOM1=0) or
6.540–7.139 FPS (CUSTOM1=1), with only 54.9–71.4% real-time calendar advance.
These are separate native demo observations, not matched-workload speedup ratios
or physical-hardware timing predictions. See tracked
docs/RELEASE_QUALIFICATION.md and
manifest/release-original-observations.json for per-profile evidence and scope.
