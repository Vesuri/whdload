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
prototype, verify 32 and 56 complete movement calculations respectively, with no centering-field
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

## Shared-clock ownership audit

`tools/audit_timing_clock.py` cross-checks the native executable's relocation table
against decoded instructions across the complete code hunk, including sound routines.
It accounts for **85 absolute references to `$f96`: 79 read-only accesses, four stores
and two read/modify/writes**. This inventory is independent of a textual disassembly
search. It does not prove the absence of computed-pointer aliases or classify every
transitive caller; those remain explicit audit work.

The six direct writers must not be treated as interchangeable elapsed-time updates:

| Offset | Operation | Required ownership treatment |
| --- | --- | --- |
| `$5414` | Reset clock to zero | Establish a new native epoch; initialize/rebase logical session time explicitly |
| `$59f2` | Add sampled CIA TOD difference × 4 | Keep physical time advancing for waits, presentation and audio |
| `$93d2` | Restore saved value through `a3` | Audit saved-input/playback lifecycle before translating logical time |
| `$93fc` | Restore value from saved input state at `$4520` | Same; preserving VBL time alone does not reproduce this clock restore |
| `$beec` | Restore pre-pause time | Existing input prototype excludes paused fields; logical/native epochs must remain consistent |
| `$f67a` | Add a calculated gameplay time adjustment | Preserve its gameplay meaning without adding extra physics ticks |

At `$f67a`, the adjustment uses `state+$2d0`, scales by 200/8 and multiplies by a
lap-related difference. Its exact mode semantics still need runtime confirmation.
It is evidence that the native clock is not simply a monotonic VBL counter.

The directly inspected gameplay consumers establish these concrete dependencies:

| Consumer offsets | Timestamp/state | Split required |
| --- | --- | --- |
| `$d4b6`, `$d4fe` | Opponent `+$50` start time, `+$56` active flag; elapsed / 200 compared with `+$1c` | Pair the start and expiry in one logical domain; audit initialization and every caller before patching either read |
| `$d7f8`, `$d836`, `$d866` | Opponent `+$5c` lap timestamp, `+$60` duration; minimum interval 400 clock units | Logical crossing time, with session-start epoch and saved results preserved |
| `$ce00` | Rescue deadline `state+$fe` | Convert its producer and consumer together; rescue may unwind the current world step |
| `$dd36`, `$dde0`, `$e1c4`, `$e23c` | Scheduled deadlines `state+$4bc` and `+$4b8` | Logical scheduling after decomposing their nested presentation/wait paths |
| `$dd5e`, `$ddb2` | Timestamp/duration `state+$272` | Pair both reads at their logical crossing instants |
| `$e044`, `$e39e` | Session deadline `state+$ca` | Audit session setup and end transitions together |
| `$fa7a` | Previous contact timestamp `state+$28a`, threshold 100 units (500 ms) | Logical collision interval; elapsed render delay currently influences recovery routing |
| `$f108` | Display clock minus `state+$206` | Keep display derived from the selected gameplay timer domain, not raw physics cursor without an epoch conversion |
| `$c094`, `$c266`, `$f688`, `$f6ca` | `state+$22e` result timestamp/duration | Preserve mode-specific interpretation and time adjustments |

The opponent update has **seven direct native callers**: `$b76c`, `$c92c`, `$ced8`,
`$e3bc`, `$fe40`, `$ffc2` and `$1318c`. The prototype schedules `$ced8` and removes the
two recovery calls `$fe40/$ffc2`; it has not established ownership for the other four.
`$b76c` is reached by setup rendering, `$c92c` is a keyboard-handler path returning to
`$bc4a`, and `$e3bc/$1318c` sit in additional mode loops. Their exact lifecycle policies
still need confirmation. Thus replacing just `$d4b6/$d4fe` with the bare world cursor
would mix timestamp domains across callers; those two reads are not an isolated patch.
Direct `a5`-relative accesses show only that pair writes/reads `+$50`, but do not rule out
bulk initialization or saved-state restoration of opponent records.

Several consumers require a clock that progresses **while the world cursor is stopped**:
`$c518/$c532` surround a 163-unit animation wait; `$dad2/$dade` a 1,000-unit wait;
`$db26/$db32` spin for 50 units. Sound shutdown at `$17806/$17812` spins for 40 units
(200 ms on PAL), outside the earlier gameplay-only address range. Globally substituting
a frozen world clock would hang these loops. The incident animations `$fdb2–$fe8e` and
`$fea6–$1004c` additionally perform fixed position updates interleaved with rendering;
their finite loops block the current world update and are not resolved by changing the
clock reads alone. They include persistent position/speed/centering mutations, so they
cannot simply be deferred as cosmetic drawing.

Implementation order for this part of F6:

1. Audit all callers and initialization/restoration of opponent repair timestamps, then
   move the paired start/expiry reads to an explicitly logical clock. Verify active
   repairs across pause, pit and session changes, including opponent arrays.
2. Give lap, rescue and session deadlines an epoch-aware gameplay clock; apply native
   time adjustments to timer values without manufacturing simulation debt. Verify both
   producers and consumers and all nonlocal world exits.
3. Represent incident motion/recovery as timed state that can advance without blocking
   ordinary world scheduling. Separate audio/presentation waits onto physical time.
   Preserve the native final positions, speed resets and centering changes.
4. Rebase or clear input, partial steps and retained debt at each session boundary;
   preserve fractional time at pause. Then run the long mode/capacity matrix.

The normal timing option and prototype do **not** yet implement this clock split.
Passing common player states on the short fixtures is insufficient evidence for these
opponent, lap, rescue and result timer behaviors.

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
transitive mode-exit audit. The session-completion cleanup below rebases ordinary new
Practice sessions; interrupted world updates and their remaining scheduled work still
need explicit lifecycle validation. Native
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
changes (including centering assistance); it is deliberately scoped to the centering-off route. The
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

The simple throttle/brake route does not exercise falling or impulses. The separate
force integration below extends this stage. Centering-field scalar arithmetic, mode
clocks, incident presentation and the remaining calibration/matrix gates remain open;
passing these bounded routes does not establish whole-game timing correctness.

### Falling and impulse integration

`timing_forces.s`, included only in `TIMING_WORLD20`, interprets the native fall and
impulse increments as displacement per 90-ms epoch. Each eligible 20-ms movement step
integrates four native time units. It splits a step at a local 18-unit age/decay boundary,
using the old increment before that boundary and the new one afterward. Signed division
remainders preserve sub-unit displacement. For example, an impulse of 90 units contributes
20 units during each of its first four 20-ms steps; the fifth contributes 10 units before
the boundary and 5 after the vector halves. Its first 100 ms therefore contribute 95 units.

The fall hook at `$cd5c` retains the native engine/mode/age eligibility checks. It advances
`state+$1a2` once per 90 ms of eligible falling, including the native signed-word doubling
of age. The native special-case flag still decides whether falling can continue above age
50. Initialization and repair writes at `$b390/$c59e` clear the corresponding local phase
and fractional remainder. Ineligible time does not accrue falling age.

The impulse body at `$cd96–$cdc0` integrates all three components, then advances its age
and performs the native signed halves at each 90-ms boundary. It preserves the native
expiry comparison and ceases integrating immediately when the impulse expires, even if
that boundary falls inside a 20-ms step. New centering-field impulses at `$adba` and close
opponent-contact impulses at `$9c8c` reset their local phase/remainders. Continuous
centering can refresh the vector before expiry, as in the original code.

The field at `state+$d2`, and the related forward-speed reduction at `$cd00–$cd2a`, are
**centering assistance**, not wind. The C-key handler at `$c8b0` changes its strength and
shows the native centering-field message; `$ca56` calls the impulse constructor. Weather
and this input-selected assistance must not be conflated when calibrating forces.

`PDW20F01` records phases, signed remainders, initialization counts and fall/impulse
step/age counts. Read-only entry/exit probes feed `tools/check_timing_forces.py`, whose
reference advances one native 5-ms unit at a time rather than following the guest's
boundary-split chunks. `--require fall` or `--require impulse` requires actual activity;
an uneventful route cannot pass. It checks displacement, ages, phases, remainders, native
reset effects and the sampled preserved registers/stack.

The corrected failure-route captures `timing-forces2-a500` and
`timing-forces2-030-force-twins` cover 500 PAL fields with `CUSTOM5=10`. They verify 181/178
fall steps and 40/39 age advances respectively. All **501 common sampled world states
match** across CPUs, including position, speed, temperatures, damage and world RNG.
The captures complete 504/501 world updates, with no unassigned or assigned movement debt
at either endpoint. The 030 has 98 clean renderer twins and unchanged raster code.
These runs do not reach the age-50 boundary or native fall-reset paths.

The centering route (`CUSTOM5=3`) verifies 490/495 impulse steps, 54/55 decays and
109/110 native centering resets on A500/030 respectively. The 030 adds 143 clean renderer
twins. Impulse component ranges are X=0, Y=−2..0, Z=0: this establishes negative vertical
fraction/decay handling, not nonzero horizontal forces or a complete unrefreshed lifetime.
The verifier reports these ranges and zero expiries explicitly; `--require-three-axes`
and `--require-expiry` are exercised by the mixed route below. Close opponent-contact
initialization and native fall-reset paths are still unexercised.

This practice route has no opponents. `check_timing_world20.py --practice` explicitly
requires either the bounded `CUSTOM5=3` route (at most 500 fields) or `CUSTOM5=11`
(at most 750 fields), native practice/no-opponent state in both snapshots, and zero
opponent movement observations. Its default mode still
requires active opponent interval coverage. The individual time ledgers pass with 498/503
complete world steps and no outstanding movement debt.

The live-input force prototype exposed a centering chronology defect: at logical time
120 ms, the A500 advanced 28 forward units while the 030 advanced 60 with the same prior
position, direction and speed. The centering path at `$cd00–$cd2a` read live assistance
state and Shift, so a post-render C-key handler could change movement between logical
control epochs. The keyboard extraction below addresses that defect. The earlier failed
pair remains useful regression evidence; force arithmetic alone does not prove input
chronology.

Incident presentation can overwrite the shared movement delta. The world wrapper now
restores it on the no-opponent fast-step path as well as before slow opponent updates.
The earlier force trial failed the strict end-of-world interval check and is not used as
evidence that this ownership invariant held. The corrected runs pass it unchanged.

The frozen artifact is `Powerdrome-timing-forces2.slave`. Use the WORLD20 build flags,
500 fields, driving anchor `$bc7c`, and probes `$ccee/$cde2/$cedc/$d56c/$cd5c/$cd64/
$cd96/$cdc4/$b390/$b398/$c59e/$c5a6/$9c8c/$9c92/$adba/$adc0`. This probe set fits the
emulator breakpoint capacity; an earlier larger set was rejected before any measured
field and is not a valid capture. Instrumented runs are correctness evidence, not FPS
benchmarks. The normal build still excludes this prototype.

### Timestamped centering and movement modifiers

`timing_keys.s` is included only in WORLD20. It records native C/X/Z keyboard publication
at `$5816` into a 256-slot, eight-byte timestamp/key queue with one empty slot. Hardware
arrival is rounded up to the next PAL boundary, preventing a key interrupt from publishing
into an already executed world step. The input-only fixture calls the same enqueue helper
for the VBL it is about to publish. Each world step applies commands whose timestamps
have arrived: C adds 40 up to 360, X subtracts 40 with a zero floor, and Z switches assistance
off. The corresponding native post-render handlers no longer mutate assistance.

Movement has its own cursor through the existing timestamped input ring. It reads Shift
history before the slower control consumer can release those slots. The centering/orientation
read at `$ca5a` and movement read at `$cd20` use that history; the existing control read at
`$cf7a` retains its own control-time history. These are all three decoded modifier reads in
the ordinary simulation region. The BTST wrappers preserve every native condition flag
except Z, which is defined by the historical bit test, and use the existing 68000/010+
status-read convention.

Centering text is emitted once from the outer drawing path after logical updates, using
the native message helper at `$13514`; multiple changes during catch-up coalesce to the
latest level. It does not run from the logical mutation loop. Initializing a world clears
the private queue and readers; the common session/result exits disable publication. Paused
keys are excluded. Full pit/menu/restart ownership and live-keyboard coverage still require
the wider mode audit; this does not yet move every keyboard command into simulation time.

`PDKEY001` records enable/presentation flags, the movement input cursor and modifier,
queue offsets/counts/overflow and the last applied key timestamp. `check_timing_keys.py`
checks the nine C-key fixture timestamps independently, then every observed movement's
centering state and modifier against those histories. `check_timing_integrator.py
--centering` additionally checks the signed strength/mode reduction and Shift halving
before direction multiplication. Its ordinary mode still requires nonzero scalar and
axis carries; centering mode requires actual centering adjustments and reports the
observed carry counts without implying axis coverage.

The world ledger now distinguishes a completed slow control from a merely started one
at the capture endpoint. An uncompleted control is accepted only with one started but
unfinished world step, live world ownership, slow-update due set, and an unchanged input
deadline matching the last completed epoch. All completed epochs retain the strict
accounting check; an unfinished update is reported explicitly, not counted as completed.

The final centering pair, `timing-keys3-centering-a500` and
`timing-keys3-centering-030-twins`, uses the frozen `Powerdrome-timing-keys3.slave`,
`CUSTOM5=3`, 500 fields and probes `$ccee/$cd2c/$cd3a/$cde2/$cedc/$d56c/$cd5c/$cd64/
$cd96/$cdc4/$adba/$adc0`. Both publish and consume the same nine commands at the exact
fixture timestamps. All **501 common centering/modifier histories and sampled world
states match**, resolving the earlier 120-ms divergence. Final feedback displays level 9.
The A500/030 complete 503/501 movements, with 407/406 scalar remainder carries and
493/491 centering scalar adjustments. This route has zero nonzero axis carries; the
separate centering-off fraction route retains that coverage requirement.

Impulse checks pass 490/488 steps, 54/54 decays and 110/109 native resets. The 030 adds
144 clean completed renderer twins with unchanged raster code. Both retain zero unassigned
time debt; the A500 endpoint has two assigned unfinished world steps, including one
started slow control, and the 030 has none. These endpoint differences are explicit and
excluded from the completed-state comparison. They are not lost updates or evidence of
completed work. The snapshots and deadline/ownership checks prove the partial endpoint.

The final pause regression, `timing-keys3-pause-030-twins` (`CUSTOM5=8`, 300 fields),
excludes 50 observed paused PAL fields. It verifies 253 historical movement-modifier
states with zero centering commands, five legitimate input events, 56 fuel updates and
all 15 brake timestamps. The fraction audit verifies 211 scalar and 298 axis carries;
the world ledger has no outstanding debt or unfinished steps. It adds 76 clean renderer
twins, for **220 final-build comparisons** across centering and pause. This does not
exercise a centering command arriving while paused. Both the ordinary coverage build
and the normal slave still build; the normal slave is byte-identical to the prior checkpoint.

Remaining keyboard gates include the C-key upper cap, queue wrapping/overflow, live hardware
publication and keys across pause/pit/rescue/restart. Input fixtures exercise the common
enqueue logic but bypass the hardware publication wrapper. Other keyboard-controlled
settings and presentation-owned mutations still require extraction before release.

### Mixed commands, three-axis impulses and native calibration

`CUSTOM5=11` selects Practice and publishes 13 C/X/Z commands, including X at zero,
plus opposing mouse pulses on both axes and one Shift interval. It writes only native
input fields; it does not seed velocity, position or force state. The final Z allows
an unrefreshed impulse to expire. All three observed complete impulses start after a
recorded native centering reset and end at age 10.

The frozen `Powerdrome-timing-force-route1.slave` produces these 750-field captures:

| Capture suffix (`timing-force-route1-`) | Complete world steps | Slow updates | Impulse steps / decays | Centering resets | Clean renderer twins |
| --- | ---: | ---: | ---: | ---: | ---: |
| `a500` | 755 | 167 | 531 / 74 | 91 | — |
| `030-twins` | 754 | 167 | 531 / 74 | 91 | 244 |

All **754 common sampled player/engine/RNG states and centering/modifier histories match**
at identical logical times. Both captures verify all 13 producer timestamps, finish
without queue loss, allocator debt or assigned unfinished steps, and use the expected
20-ms movement / rational 90-ms slow cadence. The centering arithmetic audit verifies
396 actual scalar adjustments per capture; scalar remainder observations number 729/728.
This route has no nonzero ordinary axis carries, so it does not replace the earlier
fractional vector tests. Impulse component ranges are **X −1..177, Y −2..3, Z −341..1**.
Each capture verifies three complete integrated lifetimes of **900 logical ms**.
The force checker now enforces continuity between observed resets and steps, and requires
an observed age-zero reset before crediting a complete lifetime. No falling occurs here.

The native A500 reference uses the same frozen artifact and input route with
`CUSTOM1=0 CUSTOM3=0 CUSTOM4=0`. Its initial and final timing hooks retain native bytes.
Equivalent first-impulse-entry to expiry-decision boundaries give:

| Episode in route | Native A500 VBL ms | Timed A500 VBL ms | Timed 030 VBL ms | Timed logical ms |
| --- | ---: | ---: | ---: | ---: |
| 1 | 800 | 880 | 940 | 880 |
| 2 | 900 | 800 | 880 | 880 |
| 3 | 1,120 | 1,060 | 880 | 880 |

These are **boundary durations**, excluding the last represented movement interval.
The prototype's 45 × 20-ms integrated lifetime is 900 ms, whereas its first-to-last
entry boundary is 44 × 20 = 880 ms. Native episodes each contain ten frame-driven
increments. VBL observations have less than one PAL field (20 ms) of endpoint-difference
quantization. Logical time and physical observation time can differ while work waits
for rendering or catches up; zero debt at the capture endpoint does not prove zero
latency throughout the run. Instrumented twins are not throughput benchmarks.

The third native boundary duration differs from the timed logical duration by 240 ms
(21.4%), and from the 030 observed duration by the same amount. This exceeds the frozen
10% or 90-ms duration tolerance even allowing field quantization. Therefore **A500
impulse calibration is not passed**. The first two logical differences are within that
bound. The runs share the input tape, but native and timed trajectories are not proven
equal; this is a calibration warning, not proof that one replacement period fixes every
scene. Do not change the 90-ms period solely to fit one episode or relax the gate.

Recheck the bounded results with:

```sh
python3 tools/check_timing_keys.py --forces CAPTURE...
python3 tools/check_timing_world20.py --practice CAPTURE...
python3 tools/check_timing_integrator.py --centering CAPTURE...
python3 tools/check_timing_forces.py --require impulse --require-three-axes --require-expiry CAPTURE...
python3 tools/timing_impulse_durations.py NATIVE_CAPTURE TIMED_CAPTURE...
```

Use `CUSTOM5=11 FIELDS=750`, `ANCHOR=0xbc7c`, `SWAP_MARKER=0xbc7c`, `SWAP_ONLY=1`
and `TIMING_STATE=1`. The timed capture probes are `$ccee $cd2c $cd3a $cde2 $cedc $d56c
$cd5c $cd64 $cd96 $cdc4 $adba $adc0 $9c8c $9c92 $fc9e $1003a $10046`.
The native duration capture needs `$adba $adc0 $cd96 $cdc4`; the recorded reference also
observes `$ccee $cde2 $c88e $c89a $c8b0 $fc9e $1003a $10046`. Pass these as hexadecimal
`COVERAGE_PROBES` offsets. The timing prototype uses the same WORLD20/input/engine flags
as the centering experiment and fixed heat/world seeds 12345/54321.

Remaining force coverage includes close-opponent impulse generation, native falling
resets and both sides of the age-50 eligibility boundary. Logical clock ownership,
mode lifecycle and renderer-blocked latency remain separate F6/F7 work.

### Next extraction steps (`coupled-20`)

1. Implemented in the bounded `TIMING_WORLD20` prototype: give the complete world its
   own 20-ms cursor and retained debt. Service controls and
   orientation at the calibrated 90-ms rational cadence, without advancing future inputs
   or applying all accumulated controls before movement. Draw only after complete updates.
2. Implemented but collision coverage pending: keep movement and geometric contact/track
   checks together on that cursor. Split contact
   detection from damage counters, fixed speed deductions and repeated sound/flash events;
   otherwise running collision code at 50 Hz would multiply those responses.
3. Implemented in the force prototype, with coverage/calibration still pending: separate
   falling/impulse velocity integration from their 90-ms age/decay updates. Scale
   displacement and retain integer remainders; scheduling the counters alone is insufficient.
   Keep opponents on their measured logical cadence while auditing incidental callers.
4. Assign logical versus display time to shared-clock reads and all mode exits. Decompose
   blocking incident presentations, and define pause/pit/rescue/restart rebasing so elapsed
   gameplay is neither dropped nor charged across excluded mode time.
5. Repeat this seeded incident/failure comparison, then response/straight-distance bounds,
   pause and mode routes, capacity/debt measurements and the complete CPU/render matrix.
   Retain the 90-ms pilot as a diagnostic reference, not as a reduced final objective.

## Native countdown lap reset

At countdown completion, `$dbd8` copies native state `$206` into race-start `$22e`,
then `$dbe8` copies that same timestamp into all five linked pilots' lap-start fields.
The ordinary mode-7 route reaches this after the logical timeline has already started.
Its mode update can execute with world ownership inactive; testing only the active-world
flag would miss the reset. The separate `$da6a` branch can also enter this native reset
sequence and still requires its own runtime case.

The WORLD20 prototype hooks the six-byte `$dbd8` instruction. When the player and
opponent timelines are initialized, it rebases the stable lap epoch to:

`native reset timestamp - (retained world clock - opponent origin + 18)`

Here 18 is the 90-ms opponent period in native five-millisecond clock units. The hook
preserves registers and caller X, then replays the original memory-to-memory MOVE,
including its NZVC behavior. It does not rewrite the native five-pilot reset, race-start
value, simulation deadline, accumulated debt or random state. Unsupported/uninitialized
paths simply replay the native instruction. The 010+ installation substitutes the usual
CCR read for the helper's entry SR read; the source remains 68000-compatible.

The uncorrected 030 capture `timing-lap-reset-before-030` reaches mode 7 with 4,430 ms
of logical elapsed time. Its native reset timestamp is 70 ms ahead of the previous
logical lap-clock mapping. The corrected `timing-lap-reset-after-030` runs 2,000 PAL
fields from the same native reset with frozen `Powerdrome-timing-lapreset1.slave`.
It verifies one rebase, five native reset-loop visits, four unchanged opponent reset
stamps, and eight subsequent lap-clock reads (minimum interval and completed-lap
calculation for each of four opponents) in the rebased domain. The corresponding
`timing-lap-reset-after-a500` capture uses 68000, 512 KiB chip and 1,536 KiB slow memory
with the same frozen slave and 2,000-field window. It passes the same checks. At its
reset, logical elapsed time is 15,270 ms and the old mapping is **410 ms** behind the
native shared reset, rather than the 030's 70 ms. These runs validate each clock reset;
the different countdown/event histories do not prove matching trajectories.

```sh
python3 tools/check_timing_lap_reset.py tmp/prof/timing-lap-reset-after-030
python3 tools/check_timing_lap_reset.py tmp/prof/timing-lap-reset-after-a500
```

The 030 captures use 68030/25, 2 MiB chip and 4 MiB fast memory. All three use `CUSTOM1=1 CUSTOM3=1
CUSTOM4=0 CUSTOM5=5 NoCache`, anchor `$dbd8` and probes `$dbde $dbe8 $dbee $dbf4 $cedc
$d7fe $d86c $d7f0 $ca44 $bc44`, with early timing and opponent-state logging enabled.
The frozen prototype uses the existing full WORLD20 flags and synchronized-pit test
fixture. The normal build remains byte-identical; hook boundaries pass structural checks.

Guest-observed reset flags/registers, the alternate reset entry and
pause/rescue transitions remain to verify. The result-duration latch now uses the stable lap/race domain as described below.
The lap-reset tests alone do not establish consistent race-result timing; each result
source still requires its own finish and cleanup validation.

## Opponent preparation on logical world ticks

The WORLD20 prototype separates native opponent preparation (`$9950–$9d9e`)
from model projection (`$9d9e–$a26c`). The sole direct rendering caller at `$11228`
now performs projection only during supported human flight. Persistent animation,
contact checks and their native effect generation execute every six completed 20-ms
world ticks (120 ms), before advancing the world clock. Native repair, visibility,
player-state and mode gates remain in place. Unsupported modes retain the native path.
This is an experimental implementation, not completed F5/F6 calibration.

The logical call enters the original `$9950` register-save prologue and returns through
its matching `$a268` restore/return before projection. The rendering call constructs the
same stack frame and enters projection directly. The structural audit verifies both
native frames and complete hook instructions. The private effect-phase counter replaces
the render counter only for preparation, including native alternating damage checks;
the caller's counter is restored afterward. Other rendering effects still require audit.

The native A500 reference `timing-opanim-native-a500` observes nine animation updates
for each of four pilots, spanning 920 ms between the first and ninth updates. All 36
observed transitions pass exact native arithmetic checks. This is a visible prefix,
not a complete animation-lifetime measurement.

The synchronized 18/24-second pit fixture uses the frozen `Powerdrome-timing-opanim2.slave`
and captures `timing-opanim2-initial-a500` and `timing-opanim2-initial-030-twins`:

| Check | A500 | 68030/25, renderer twins |
| --- | ---: | ---: |
| Logical visible preparations | 147 | 205 |
| Projection-only drawing calls | 142 | 295 |
| Verified active-animation transitions | 40 | 40 |
| Pilot 1 first-nine-update span | 2,040 ms | 2,040 ms |
| Pilots 2–4 first-nine-update span | 960 ms each | 960 ms each |

Both CPUs reproduce the animation arithmetic and durations. Pilots 2–4 are 40 ms
(4.35%) slower than the native A500 prefix, within both frozen limits. **Pilot 1 fails
native calibration**: it leaves the visible segment range, causing a 1,200-ms interval
between preparations instead of 120 ms. Removing that native visibility gate solely to
pass calibration would change behavior; matching the native event history and checking
the full lifetime remain open. CPU agreement does not establish A500 gameplay fidelity.

The complete opponent comparison has 335 shared deadlines from 90 to 30,150 ms,
including 135 after both CPUs enter flight. Nine snapshots differ, solely in record
word `$54`; all other compared words, lap clocks and RNG match. `$54` is written during
projection and read during drawing. The bounded effective-address audit below supports
that ownership in the sampled route; unexecuted paths remain unaudited. The whole-record
comparison therefore remains failing; no field has been masked.
The 030 run has 64 completed clean renderer comparisons and one additional scene still
active at capture end. These instrumented runs are not performance measurements.

Both runs pass the synchronized-event, initial-pit accounting and retune checks.
A500 drains 84 old-speed updates before the 18-second retune, retains the 3,120-ms
initial return overflow, and ends with 50 ms residual opponent time. The normal build
remains byte-identical to the pre-prototype reference; this split requires WORLD20.

Recheck the captures with:

```sh
python3 tools/check_opponent_animation.py tmp/prof/timing-opanim2-initial-a500 --logical
python3 tools/check_opponent_animation.py tmp/prof/timing-opanim2-initial-030-twins --logical
# Expected failure: pilot 1 does not pass native timing calibration.
python3 tools/check_opponent_animation.py tmp/prof/timing-opanim2-initial-a500 --logical --reference tmp/prof/timing-opanim-native-a500
python3 tools/compare_timing_opponents.py --through-departure --report-only tmp/prof/timing-opanim2-initial-030-twins tmp/prof/timing-opanim2-initial-a500
```

The 50-field instruction trace `timing-opanim-projection-access-a500` starts at `$9950`
after the initial `$bc44` pit return, using the same frozen prototype and A500 configuration.
`tools/audit_opponent_projection.py` decodes 4,236 executed game instructions and evaluates
explicit memory effective addresses against all four opponent `$54` words. This includes
copied/indexed pointers and overlapping block transfers, rather than merely matching
field displacements in disassembly. All 55 observed accesses occur at the three native
writers and one reader:

| Site | Role | Observed accesses |
| --- | --- | ---: |
| `$a142` | Clear projection rejection flag | 19 |
| `$a26e` | Set projection rejection flag | 9 |
| `$1162e` | Select distant-model drawing | 10 |
| `$11644` | Choose drawing path | 17 |

All 17 reads follow a fresh projection write after that pilot's current `$11228` render
entry. All four pilots are covered; no explicit memory addressing mode is unresolved.
Other direct `$54` references at `$721c` and `$143e4` address the asset table rooted at
hunk `$6e2`, rather than an opponent record. This trace does not cover unexecuted paths,
implicit stack accesses, DMA or accesses from code outside the game hunk. It supports
render-only ownership in the measured early-flight window, not a blanket normalization
rule for every mode or capture.

```sh
python3 tools/audit_opponent_projection.py tmp/prof/timing-opanim-projection-access-a500
```

The extended `timing-opanim-projection-long-a500` instruction capture covers **300 PAL
fields (six seconds)** from the same `$9950` anchor after `$bc44`, with the same frozen
opanim2 slave and route. It decodes **5,168 distinct game instructions** and resolves all
explicit memory addressing modes. Its **382 accesses** remain confined to the same four
sites: 120 writes at `$a142`, 67 writes at `$a26e`, 78 writes at `$1162e`, and **117 reads**
at `$11644`. Every read follows a fresh projection write; all four pilots are covered
(17 / 37 / 26 / 37 reads). `$1162e` is a writer selecting distant-model drawing, not a
simulation reader.

The audit now reports a conservative opponent-deadline interval from completed-update
counts in the installed continuous ledger, requiring the same retained origin at both
snapshots. The longer A500 trace covers **25,560–30,060 ms**; the earlier 50-field trace
covers **25,560–26,460 ms**. All nine raw-record mismatches occur within the longer
interval: 25,650, 25,740, 27,270, 27,360, 27,450, 28,260, 28,350, 28,440 and 28,530 ms.
This strengthens ownership evidence for the A500 path but does not establish it for
every accelerated execution path.

The attempted 300-field `timing-opanim-projection-long-030-twins` instruction capture
terminates with **no instruction PCs**; sampled fields 0, 1, 10, 100 and 299 all contain
zero PCs. The harness correctly rejects it before terminal memory snapshots, so it is
not a successful instruction or renderer audit. Shared tooling notes also report that
hardware watchpoints can fail to fire; a counted breakpoint at the four known sites
would not rule out other aliased accesses. Accelerated effective-address coverage still
needs a usable instruction/access trace. No opponent comparison field has been masked,
and the strict full-record gate still reports nine `$54` differences and zero RNG
differences across 335 common deadlines (135 after both CPUs enter flight).

The animation-duration mismatch is separate: both corrected CPUs agree on pilot 1's
2,040-ms span. The native segment-range endpoint `state+$200` is loaded from the track
lookup at `$f85a–$f866`, following player-segment selection in the movement path; it is
not simply a stale value computed by rendering. Removing the visibility gate would
change native behavior. Match the original event/visibility history before treating the
920-ms native prefix as the same animation-lifetime case.

```sh
python3 tools/audit_opponent_projection.py tmp/prof/timing-opanim-projection-long-a500
```

Next obtain accelerated `$54` access coverage, test matched native visibility/lifetime
histories, and cover contact/damage/effect feedback, pause, repair, rescue and nonhuman mode transitions.
The preparation split alone does not complete the broader effects or timing matrix.

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

The external sequence enters at `$1475c`, loads the position table at `$144cc`, and
sets `d7=16`. Each iteration reads the next table word, draws at `$1432e`, calls the
pit presentation/update routine `$e296`, then uses DBRA to advance. There is no elapsed
scaling of the table index. Return is `$147a6`. In the current retune4 initial-pit
captures, its 16 first-to-last intervals are 60 ms eight times, 40 ms seven times and
20 ms once on 030 (780 ms total); A500 has 100 ms once, 80 ms eight times, 60 ms five
times and 40 ms twice (1,120 ms total). These corrected-build observations establish
remaining CPU dependence, not the original-game calibration target.

For native calibration, capture from `$1475c` with `CUSTOM3=0`, marker `$1479e`,
`TIMING_STATE=1`, probes `$14764 $147a6` and 100 PAL fields. The read-only register
samples verify all 17 loop indices, position-table progression and stable stack through
return. `tools/check_external_departure.py REFERENCE [CAPTURE...]` reports each interval
and compares candidate geometry against the no-fast-memory 68000 reference. The native A500 capture `timing-external-native-a500` passes: its ordered intervals
are **nine × 80 ms, five × 60 ms, three × 40 ms**, including the final interval to
return. Total first-movement-to-return is **1,140 ms**; first-to-last is **1,100 ms**.
This establishes a position-dependent reference cadence rather than assuming the
cockpit animation’s uniform 100 ms. The uncorrected 030 capture
`timing-external-native-030` preserves the same table sequence and loop stack but takes
**820 ms** through return (780 ms first-to-last), about **1.39 times as fast** as A500.
All declared timing-hook bytes remain native in its initial and final snapshots.

The full WORLD20 prototype now includes `timing_external.s`. Its `$14764` hook replays
the native two position-loading instructions; `$1479e` restores the native saved loop
registers, waits for the cumulative deadline, then reproduces DBRA and its terminal
`$ffff` low word. All 17 draws and presentation calls remain native. The initial deadline
comes from the physical native clock, with periods 16/12/8 clock units matching the
measured 80/60/40 ms sequence. An overrun is retained rather than resetting the deadline
from each observed completion. Caller registers, stack and condition flags are preserved.
The wait is at the loop tail after native presentation; it controls the next position
boundary and final return, not the exact scanout instant of the preceding draw.

This remains an opt-in prototype under `CUSTOM3` and WORLD20; the normal build is
unchanged. The paced 030 capture `timing-external2-030` preserves all 17 table steps
and the loop stack. It observes **1,120 ms** through return in debugger PAL fields,
with **1,140 ms** elapsed in the native CIA-derived clock: all subsequent field
boundaries are one field early relative to A500, while clock deadlines match exactly.
The clock changes in 20-ms units and is sampled at a different phase from the debugger’s
VBL-entry breakpoint. The initial exact-field checker rejected this result; the revised
`--require-cadence` gate explicitly checks both time sources and permits at most one
PAL field (20 ms) at every boundary. It passes this capture and rejects the unpaced
820-ms 030 capture. This is tighter than the frozen broader animation-response budget;
it does not hide dropped positions or accumulated drift. The paced A500 capture
`timing-external2-a500` also passes: **1,160 ms** through return, with all field and
guest-clock boundary errors between zero and **+20 ms**. The first interval overruns
by one field; subsequent deadlines retain that lateness instead of adding more delay.
Both CPU runs preserve all 17 positions and the native loop stack. The 030 capture
contains no staged scenes, so it is not evidence of renderer equivalence or throughput.
The full 030 pit-to-track capture `timing-external2-initial-030-twins` also passes:
7,620 ms in the pit; six old-speed updates (540 ms) drained before the retune at
6,480 ms with zero residual; 1,140 ms of departure tail served as 1,080 ms plus 60 ms
retained at first flight. Final residual is 20 ms, with no whole updates pending.
All caller register/flag, RNG ownership and record checks pass, as do **188 completed
renderer comparisons** with unchanged raster code. An additional scene is active at
the final snapshot and is not counted as complete. The full A500 counterpart
`timing-external2-initial-a500` passes: 17,080 ms in the pit, 57 old-speed updates
(5,130 ms) drained at a 15,620-ms cutoff with 50 ms residual, and a 1,510-ms departure
tail served as 1,440 ms plus 70 ms retained in first flight. Its final residual is
30 ms; no allocation hits the 32-update cap. Both CPUs retain the same native speed
mutation, **489/519/522/558 → 567/617/553/594**. Other pit callers and rendering
configuration coverage remain separate requirements.

```sh
python3 tools/check_external_departure.py --require-cadence tmp/prof/timing-external-native-a500 tmp/prof/timing-external2-030 tmp/prof/timing-external2-a500
```


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

### Current high-speed brake arithmetic audit

The current full WORLD20 build, with repair pacing/drop enabled and all repair-input,
result and initial-pit synchronization fixtures disabled, reproduces this distinction.
`timing-brakeaudit1-native-a500`, `timing-brakeaudit1-periodic-a500` and
`timing-brakeaudit1-periodic-030-twins` use the same frozen input fixture and a 300-field
window from `$bc7c`. The native run disables CUSTOM3; the candidates enable it. These
read-only control-boundary captures are not throughput measurements.

| Measured behavior | Native A500 | Periodic A500 | Periodic 030/25 |
| --- | ---: | ---: | ---: |
| Brake decrements during held command | 8 native | 15 queued | 15 queued |
| Control calls during held logical command | 8 | 11 | 11 |
| Cruise speed | 140 | 140 | 140 |
| Post-command speed | 108 | 53 | 53 |
| Brake/input queue overflow or remaining debt | Not applicable | 0 | 0 |

At native fixture fields **100, 103, 107, 111, 120, 128, 136, 144**, entry speeds are
329, 230, 181, 156, 144, 135, 126, 117. Each brake body subtracts **9**. The native
`$d038–$d058` operation first clamps negative speed to zero, then subtracts half of any
excess over cruise (integer division), yielding 230, 181, 156, 144, 135, 126, 117, **108**.
All eight brake decrements and 52 exercised clamp/damping calls pass exact arithmetic.
The last three native inter-call intervals are 160 ms.

Both corrected CPUs have **identical eleven held-command control states** at logical
2,070–2,970 ms in 90-ms increments. Entry speeds are 320, 212, 167, 145, 134, 116, 107,
98, 89, 71, 62; control exit speeds are 230, 176, 154, 143, 134, 116, 107, 98, 89, 71, 62.
The final queued brake event brings speed to **53**. The native brake body makes **no**
additional speed subtraction in either candidate: its decrement sites are NOPed, so the
faster braking is not a duplicated native decrement. All 58 sampled damping operations
on each CPU retain native arithmetic. The separate existing brake verifier proves 15/15
owed events, and the joystick verifier checks 67 logical updates and six timestamped
input events per CPU. The 030 adds **72 completed clean renderer comparisons**, with no
pixel/guard/scratch/register failures and unchanged raster code; its ending snapshot is
inside an active staged draw, so it is not a completed teardown check.

Physical observation fields differ and are retained in the audit report. Only the
hardware-independent logical timestamps and full recorded brake-control states are
compared across CPUs; deferred controls are not reassigned to their observation time.
This confirms the bounded scheduling/arithmetic behavior but **does not pass the native
high-speed response calibration**. The outstanding reference-policy choice is whether
representative normal A500 handling should define one stable cadence or whether the
original scene-dependent slowdown should also be reproduced. No period, brake strength,
acceptance tolerance or production behavior was changed by this audit.

`PDBCTL_EVENT` records speed, cruise limit, brake amount, damage, fuel, engine state,
buttons, input mode, sampled joystick and D7. Add probes
`0xcf2e 0xd000 0xd022 0xd038 0xd058 0xccee` with TIMING_STATE; candidates also use
TIMING_EARLY. The checker distinguishes native per-call decrements from the disabled
native body in periodic builds and verifies clamp/damping arithmetic independently.
It rejects unscheduled control calls rather than hiding them in cadence statistics.

```sh
python3 tools/check_brake_control.py tmp/prof/timing-brakeaudit1-native-a500
python3 tools/check_brake_control.py tmp/prof/timing-brakeaudit1-periodic-a500 tmp/prof/timing-brakeaudit1-periodic-030-twins
python3 tools/check_timing_brake.py tmp/prof/timing-brakeaudit1-periodic-a500 tmp/prof/timing-brakeaudit1-periodic-030-twins
python3 tools/check_timing_joystick.py tmp/prof/timing-brakeaudit1-periodic-a500 tmp/prof/timing-brakeaudit1-periodic-030-twins
```

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

## Session completion and fresh entry

| Boundary | Current prototype policy |
| --- | --- |
| Ordinary world update | Retain elapsed debt and input history; advance logical time only for completed updates |
| Pause/resume | Exclude paused fields; retain fractional time, pending work and input chronology |
| `$bf32` | Restore temporary world ownership; may return to gameplay, so do not close input or scheduler |
| `$bfb0` | Restore world ownership and disable centering commands; retain timing for the native ending animation |
| `$c2aa` after ending animation | Close timing and queue ownership before native cleanup and menus |
| Next gameplay timing entry | Initialize from current unpaused time; do not replay the menu/pit-setup interval |
| Rescue via `$ce1e` | Suspend flight, explicitly discard interrupted work, then start a fresh player epoch; preserve logical phase/RNG streams |
| Other pit entries and nonlocal interruption paths | Full lifecycle validation remains open |

The WORLD prototype now closes its timing state at `$c2aa`, after native result/ending
animation and before the original `$17148` cleanup call. `timing_session.s` restores
world counter/RNG ownership, disables the VBL input/brake producer, clears allocated
work and retained debt, resets input/brake queue ownership, and discards pending engine
presentation. Centering publication is disabled. The next ordinary timing entry performs
full initialization against the then-current unpaused VBL clock, including world/input
cursor, fractional integration state, forces and per-session random seeds. Pause does
not use this closure path; it retains its existing fractional-time/debt behavior.

The closure cannot be placed at `$bf32` or `$bfb0`: `$bf32` can branch back to gameplay
when `state+$43a > 4`, and the result path still calls `$ca3e` from the ending animation
at `$c1b6`. Closing at the earlier gates made that animation initialize a second session
and left input collection enabled through subsequent menus. The failed
`timing-session1-030-twins` capture exposed this boundary mistake. The corrected build
retains world restoration at the early gates, disables centering publication only at
the actual result branch `$bfb0`, and closes the scheduler after the animation.

`PDSESS01` records initialization and explicit closure counts, discarded assigned steps,
unassigned clock units, queued inputs/centering keys/engine presentation events, and the
last scheduler timestamp at closure. Counters are diagnostic and do not drive gameplay.
`tools/check_timing_sessions.py` verifies before/after cleanup accounting, inactive
menu/pit-entry samples and fresh world/input deadlines at reentry. It requires two
closures and two later gameplay entries; one exit or a static menu cannot pass.

The input-only `CUSTOM5=12` route exits Practice with native Shift-Q twice and re-enters
through the ordinary menu and pit Space handling. Its first C command while outside
gameplay is not queued for the next session. Unlike the longer repair-coverage route,
it requests Space directly on subsequent pit visits, isolating session reentry from
repair duration. Use 1,800 PAL fields on 030 or 3,600 on A500, the normal driving
anchor/marker `$bc7c`,
`TIMING_STATE=1`, and probes `$ca44 $ccee $c2aa $c2b0 $bf32 $bfb0 $12f6a $13cde`.

The frozen `Powerdrome-timing-session2.slave` passes the 030/25 fast-planar twin run
`timing-session2-030-twins`: two closures, two fresh gameplay entries, six inactive
samples, and **228 clean completed renderer comparisons** with unchanged raster code.
The new sessions start at fields 523 and 1,563. Each has exactly one initially due world
step, zero retained allocator debt, world time equal to the fresh scheduler timestamp,
and the next slow-input deadline 18 clock units later. The 8.34/8.38 seconds between the
previous scheduler timestamps and these new entries are not replayed as movement.

The same frozen artifact passes `timing-session2-a500-long` over 3,600 fields: two
closures, two fresh entries and six inactive samples. A500 entries occur at fields
1,455 and 2,899, with fresh world/input clocks and one initially due step. The excluded
scheduler intervals are 26.08/26.06 seconds. The shorter 1,800-field A500 capture ended
after the second closure but before reentry and is not counted as passing coverage.
These captures verify the lifecycle independently on each CPU, not identical input
trajectories: Shift-Q still uses the native keyboard queue, and the second A500 quit
was published during pit setup and handled upon returning to gameplay. General keyboard
ownership across modes remains open. The normal slave remains byte-identical to the
preceding checkpoint; this cleanup is confined to the explicit WORLD prototype.

The observed closures have no pending assigned work, input or engine messages; this
route therefore validates lifecycle isolation and zero-work accounting, not nonzero
discard paths. Unwinds in the middle of a world update, native pit return without session
completion, rescue, repair clocks, qualifying/race transitions and title playback still
need dedicated lifecycle tests. In particular, interrupted assigned steps before the
ending animation must not silently disappear from diagnostics. The ending animation's
own fixed frame count is also still a separate timing issue. No whole-game timer or
mode-completeness claim follows from these two Practice restarts.

## Same-session rescue boundary

The development `CUSTOM5=13` fixture selects the ordinary Race menu route, applies
native dual-button boost, releases at field 500 and requests rescue with B at field 550.
It does not write damage, temperature, position, fuel or rescue deadlines. Both engines
fail naturally and the stopped ship satisfies the native rescue gate. Subsequent pit
visits use the existing native repair sequence `1,3,8,4,6,Space`.

The frozen `Powerdrome-timing-rescue1.slave` capture
`timing-rescue1-030-long-twins` spans 5,000 PAL fields on 030/25 with fast planar twins.
It records:

| Event | Field | Evidence |
| --- | ---: | --- |
| Accepted rescue `$c7d2` | 548 | Native eligibility gate passed |
| Pit-return entry `$103a2` | 1,051 | Entered from inside an active world update |
| Six native pit inputs `$13cde` | 1,630; 2,123; 2,615; 2,845; 3,470; 4,063 | Repair keys and Space use the native menu |
| Cockpit departure `$1020e` | 4,277 | Nine paced departure steps follow |
| Interrupted world reaches `$cedc` | 4,333 | Same session and world cursor resume |
| Next ordinary allocation `$ca44` | 4,337 | Entire pit interval becomes player update debt |

The pit entry to world return spans **3,282 fields / 65.64 seconds**. The world cursor
remains at 6,244 native time units while the modal pit sequence executes; four assigned
steps remain. On return, those four finish. The next allocation produces **32 assigned
steps (640 ms)** and **65,080 ms retained debt**, or 65,720 ms combined. Only 120 ms is
allowed by the observed work outside the pit plus two fields of sampling allowance.
This is a confirmed failure: the repair/departure interval is subsequently treated as
player movement time. Retaining all debt is correct for an ordinary slow render, but
not for a mode where ordinary player flight has been suspended.

The route completes **407 clean renderer comparisons** with unchanged raster code.
That does not validate simulation timing. The earlier 3,000-field capture stops during
repairs and cannot establish return behavior. No matched A500 rescue claim is made.
These captures omit the opponent multiplication probe; they cannot establish opponent
cadence during or after the pit sequence.

`tools/check_timing_pit.py CAPTURE` rejects the long capture with “Pit time became player
movement backlog.” `--report-only` prints measured boundary/debt values without converting
that known failure into a pass. The checker requires accepted rescue, pit entry from an
active world, a completed return, and the first subsequent allocation. It permits
pre-existing debt and elapsed work outside the pit; it does not test complete opponent,
repair, keyboard or result-timer behavior.

Reproduce with `CUSTOM5=13`, `FIELDS=5000`, driving anchor/marker `$bc7c`, `SWAP_ONLY=1`,
`TIMING_STATE=1` and probes `$c7d2 $ce00 $103a2 $13cde $1020e $10322 $ccee $cedc $ca44
$bf32 $c2aa $c2b0`. Use the WORLD20/input/engine flags and fixed random seeds from the
other timing prototypes. Add `$d56c` when validating opponent cadence in a subsequent run.

The next fix must distinguish an ordinary render stall from this modal transition:

1. Intercept the rescue call at `$ce1e` (the other direct `$103a2` caller at `$bc3a` is
   initial gameplay entry), record its interrupted step and pending work, and suspend
   flight input/physics ownership before entering native pit code.
2. Keep physical time advancing for repairs/audio and give pit opponent updates their
   own elapsed scheduling. Freezing the shared `$f96` clock is not a solution.
3. Rebase player deadlines/input sampling explicitly at return, preserving or explicitly
   discarding pre-pit pending work according to its ownership. Restore the intended
   counter/RNG owner and reset teleport-sensitive movement fractions. Record excluded
   modal time separately from ordinary lost work.
4. Require this debt regression to pass, then repeat both CPUs and audit repaired engine
   state, opponent arrays, queued input and subsequent rescue/pit interactions. Keep the
   normal build unchanged until the broader F6/F7 gates pass.

### Player timing correction

`timing_pit.s` now wraps the rescue call at `$ce1e`, preserving the native call depth and
the following complete `MOVE.W` instruction. Entry restores native counter/RNG ownership,
stops timed flight input, and records/discards the interrupted batch and any pending
player debt or input/presentation work. Native physical time continues through repairs,
audio and departure. The original return value and post-pit native tail still execute.
That tail skips an extra ordinary opponent update and is explicitly retired rather than
counted as a completed 20-ms simulation step. The next ordinary frame initializes player
time and input against the current unpaused VBL clock and resets movement/force fractions.

This is a new player timing epoch within the same game session. It preserves the existing
world and heat random streams and the logical control/cooling phase. An ordinary new
session still initializes those normally; the session-completion hook clears any pending
pit rebase. Nonlocal pit exits have explicit abort cleanup, but that path is not yet
runtime-validated. `PDPIT001` records entry/return/abort counts, elapsed modal time,
discarded work and retired partial updates separately from ordinary session closures.

The frozen `Powerdrome-timing-pit2.slave` passes `timing-pit2-030-twins` over 5,000 fields.
The same rescue and pit return occur at fields 1,051 and 4,333. Instead of scheduling
32 steps plus 65.08 seconds of debt, the next frame schedules **one 20-ms step and zero
retained debt**. Four assigned updates, including the interrupted update, are explicitly
discarded; its return tail does not advance the old world cursor. The next fresh input
deadline is 18 units after the new world timestamp. All **1,052 common sampled world
states before pit entry match** the failing reference, so the boundary change does not
alter the tested pre-rescue flight. The corrected 030 run completes **422 clean renderer
comparisons**, with unchanged raster code.

`check_timing_pit_lifecycle.py` additionally checks stopped player ownership throughout
2,735 pit samples, exact discard accounting, return retirement, fresh input/deadlines,
preserved world/heat random streams and preserved control/cooling phase. It verifies
that the interrupted flight tail does not advance opponents a second time. Run both it
and `check_timing_pit.py` on the corrected capture. Include `$ce1e`, `$ce28` and `$d56c`
in the probes; the full corrected set is `$c7d2 $ce1e $103a2 $13cde $1020e $ce28 $ccee
$cedc $ca44 $bf32 $c2aa $c2b0 $d56c`.

The same artifact passes `timing-pit2-a500` over 8,000 fields. Rescue pit entry at field
1,050 returns at field 6,079: **100.58 seconds**. Seven assigned updates are explicitly
discarded. The next ordinary allocation at field 6,084 again schedules one 20-ms update
and zero debt; the stronger lifecycle/RNG/phase checks pass all 2,735 inactive pit samples.
The earlier failing reference is still rejected by the debt checker. This proves the
bounded player rebase on both CPUs, not equivalent complete post-pit trajectories.

| Corrected player boundary | 030/25 + fast planar twins | A500, no fast RAM |
| --- | ---: | ---: |
| Pit interval | 65,640 ms | 100,580 ms |
| Assigned interrupted/unstarted steps discarded | 4 | 7 |
| First new player batch | 1 step / 20 ms | 1 step / 20 ms |
| Retained pit-related player backlog | 0 ms | 0 ms |
| Native modal opponent multiplication samples | 2,728 | 2,728 |

The whole pit interval is still CPU-dependent. Repair, setup and presentation timing
must be separated/calibrated before claiming that the complete pit experience has the
same duration across hardware; the clock boundary fixes the player catch-up defect only.

The final-build ordinary-session regression `timing-pit2-session-030-twins` also passes
two closures and two fresh entries over 1,800 fields, with **232 clean renderer twins**.
Together the final-build 030 rescue and restart runs validate 654 completed renderer
comparisons. The normal slave is byte-identical to the previous checkpoint. The timing
hook layout audit passes, including the ten-byte rescue call replacement; the existing
native C3-off snapshots retain original bytes at that range.

### Repair animation pacing: measured baseline and next correction

The native item-0/item-1 branch of `$147a8` performs two 33-step drawing loops. The first
runs from `$148d0` through `$14962`; the second from `$14970` through `$14aa6`, with its
drawing body at `$14a18`. Word position increments are applied once per iteration. The
second stage also performs a sound/display sequence before counter 31, so a longer
post-draw interval there must not be treated as ordinary movement work.

Read-only `PDREPAIR_EVENT` probes record D4–D7, the five position/item words at
`state+$46e/$470/$472/$474/$47c`, native clock/VBL counters and mode/pit/lap words.
`timing_repair_loops.py` requires all counters 32 through 0 in both stages before crediting
a complete invocation. The initial entry timestamp comes from the stopped anchor snapshot;
later entry/exit probes separate drawing-body duration from intervening waits. Unfinished
trailing stages are reported explicitly. The presentation marker `$e296` only drives the
capture tool; its derived frame rate is not a performance benchmark for this experiment.

`timing-repairloop2-native-a500` uses the frozen playercontract1 slave with
`CUSTOM1=0 CUSTOM3=0 CUSTOM4=0 CUSTOM5=13 NoCache`, no fast RAM, and 1,000 fields from
`$148d0`. All declared C3 hook bytes remain native in both snapshots. The corresponding
current WORLD20 030 capture is `timing-repairloop2-before-030-twins`.

| Item / direction | Native A500 stage 1 | Native A500 stage 2, including wait | Native A500 full invocation | Current 030 full invocation |
| --- | ---: | ---: | ---: | ---: |
| 1 / 0 | 3,760 ms | 4,500 ms | 8,260 ms | 6,120 ms |
| 1 / 1 | 3,820 ms | 5,020 ms | 8,840 ms | 6,200 ms |
| 0 / 0 | 3,400 ms | 4,500 ms | 7,900 ms | 5,240 ms |
| 0 / 1 | 3,500 ms | 4,460 ms | 7,960 ms | Incomplete |

Each invocation retains all 66 recorded word-geometry states across CPUs. Native ordinary
drawing-body samples are 100–120 ms; the current 030 samples are 40–80 ms. The native
second-stage wait before counter 31 is **1,140 ms** in both directions, producing a
1,240-ms post-draw interval. On 030 that wait is 1,100/1,180 ms. These sound/display waits
must retain their native event ordering. The 2,000-field extension
`timing-repairloop3-native-a500` completes all four invocations with no trailing samples
and reproduces both item-1 measurements exactly. Item-0 pauses are 1,100/1,160 ms. Its
ordinary second-stage drawing totals are therefore 3,400/3,300 ms; item 1 totals are
3,360/3,880 ms. All declared timing hooks remain native in both extended snapshots.

```sh
python3 tools/timing_repair_loops.py tmp/prof/timing-repairloop2-native-a500 tmp/prof/timing-repairloop2-before-030-twins
python3 tools/check_timing_layout.py --off-capture tmp/prof/timing-repairloop2-native-a500
python3 tools/timing_repair_loops.py tmp/prof/timing-repairloop3-native-a500
python3 tools/check_timing_layout.py --off-capture tmp/prof/timing-repairloop3-native-a500
```

Next steps for this correction:

1. Native A500 measurements of both item variants and directions are complete for this
   route, with all 33 positions per stage and separately measured sound/display pauses.
2. The opt-in elapsed-deadline pilot is implemented and passes the 030 cadence/geometry
   gate below. It retains native step order and lateness, and shifts the stage epoch by
   the separately measured sound/display pause.
3. A500 cadence, native register/stack/nonlocal-exit contracts and opponent-time
   accounting remain to verify. Apply the existing calibration bounds; do not count a
   CPU overrun or partial sequence as a pass.
4. Extend to the other repair-animation branches and complete pit/lifecycle regressions.
   These two loops alone do not cover every repair or the full F6/F7 scope.

`TIMING_REPAIR=1` enables this isolated pilot in a WORLD20 build; its default is zero,
and installation still requires `CUSTOM3`. Unsupported build combinations are rejected.
The pre-message-correction measurements use frozen playercontract1 with the repair
pilot omitted. The corrected full timing baseline is now pitmessage1, described below;
it intentionally changes pit message ownership. The normal slave is unchanged.

For completed step `k=1..33`, the current deadline is `epoch + native_cumulative[k]`.
The eight 33-word tables come directly from the complete native A500 stage observations,
in five-millisecond clock units, excluding the separate second-stage pause. They preserve
the measured 100/120-ms step pattern instead of flattening each stage into equal intervals.
The tables total 528 bytes. Their final values equal the existing measured stage totals;
all 264 source entries have been checked against the independent native field capture.
Deadlines retain lateness and never add a fresh period to a late completion. Four whole
instruction hooks preserve the native save/presentation-call/restore depth and continue
at the native loop tails. Only human active-pit paths for these two item variants are
paced; unsupported modes keep the native path. The repair state clears on stage completion
and pit abort. The full hook boundary/direct-entry audit passes.

The earlier uniform prototype used `epoch + floor(k*T/33)`. Its frozen measurements
below remain valid evidence for that implementation. The current per-step schedule is
not a calibration pass: the A500 runtime result below still fails, and 030 regression
remains open.
`check_repair_pacing.py --native-steps` requires every deadline to match the native step
reference; without that option it checks the earlier uniform prototype. The native-step
mode rejects the old uniform capture, and the timing tolerances are unchanged. Both the
normal slave and the repair-disabled full timing build remain byte-identical to their
respective pre-schedule artifacts.

The native sound/display work still executes in its original order before counter 31 of
stage two. The helper then enforces its measured A500 minimum, preserving longer native
waits, and shifts the epoch by the actual pause. This keeps both absolute deadlines and
pre-pause lateness without interpreting the pause as owed movement. Clock sampling
clobbers D0/D1, so the minimum-wait deadline is held in saved D2.

The frozen repairpace3 slave passes `timing-repairpace3-030-twins` over 2,000 fields.
All **264** recorded word-geometry/deadline samples agree, every stage initializes and
completes exactly once, and all four full invocation durations equal the native reference:
**8,260 / 8,840 / 7,900 / 7,960 ms**. Every stage and full invocation passes the strict
10% and 90-ms bounds, including a conservative 40-ms two-capture endpoint allowance.
The A500 counterpart **fails** calibration, as detailed below. Renderer diagnostics
remain clean with unchanged raster code, but this pit window adds **zero** staged scenes;
it is not new scene-equivalence or FPS evidence.

```sh
python3 tools/check_repair_pacing.py tmp/prof/timing-repairloop3-native-a500 tmp/prof/timing-repairpace3-030-twins
python3 tools/perf_status.py tmp/prof/timing-repairpace3-030-twins
```

The 2,000-field `timing-repairpace3-a500` preserves all 264 geometry/deadline observations,
but its invocation timing exceeds the native A500 reference by **120–860 ms**. Passing
030 results therefore do not establish the required cross-CPU cadence. A matched-config
run with the repair pilot disabled (`timing-repairpace3-off-a500`, frozen playercontract1)
shows most of the cost is already present in the full timing prototype:

| Item / direction | Native A500 | WORLD20, repair pilot off | WORLD20, repair pilot on |
| --- | ---: | ---: | ---: |
| 1 / 0 | 8,260 ms | 8,840 ms | 8,960 ms |
| 1 / 1 | 8,840 ms | 8,940 ms | 8,960 ms |
| 0 / 0 | 7,900 ms | 8,700 ms | 8,720 ms |
| 0 / 1 | 7,960 ms | 8,780 ms | 8,820 ms |

Waiting cannot recover the extra body time. Even without the new pacing, these cases are
100–820 ms slower than the native reference. Equal-spaced deadlines also remove some of
the headroom provided by cheaper native iterations before expensive ones, so they cannot
be assumed free on A500. The complete-step cycle attribution below separates graphics work, display waits and
opponent service. Extend this across the stage before choosing an optimization; a short
window cannot explain all four invocation overruns. Do not relax calibration bounds,
disable the A500 gate or enable this pilot by default.

The paired 50-field instruction profiles `timing-repair-cost-native-a500` and
`timing-repair-cost-world-a500` use the same frozen playercontract1 slave, A500 memory
configuration, emulator and Kickstart hashes, and repair-entry anchor. The native run has
CUSTOM1/CUSTOM3 off; WORLD20 has both on, with no fast memory and repair pacing disabled.
The whole-window profiles spend respectively **40.30% / 38.66%** of recorded cycles in
the blitter-wait helper. This is substantial existing drawing cost, not proof that timing
patches added that cost. Routine averages at the trace edges can include incomplete calls.

`tools/repair_step_profile.py` instead pairs the ordered native boundaries from `$148d0`
through `$1495e`, excluding the opening and closing partial steps. Each measured segment
includes intervening interrupts and stopped time on the A500 CPU-backend scale of
142,102 cycles per PAL field. Both captures contain eight complete first-stage steps,
counters 31 through 24; counter 32 is an incomplete opening prefix and counter 23 an
incomplete tail. Their segment means are:

| Complete-step segment | Native A500 | WORLD20 A500 |
| --- | ---: | ---: |
| Body bitmap composition, through `$148e0` | 47.308 ms | 46.442 ms |
| Moving parts, through `$14956` | 3.776 ms | 3.864 ms |
| Presentation preparation, through `$e334` | 19.878 ms | 20.214 ms |
| ScrollVPort interval, `$e33a–$e34a` | 7.866 ms | 8.526 ms |
| WaitTOF interval, `$e35a–$e364` | 5.038 ms | 5.067 ms |
| Bitmap copy, `$e364–$e378` | 20.659 ms | 20.681 ms |
| HUD/input, `$e378–$e3bc` | 2.971 ms | 3.112 ms |
| Opponent service, `$e3bc–$e3c0` | 2.108 ms | 3.373 ms |
| Whole complete step, including remaining small segments | 109.959 ms | 111.619 ms |

The eight WORLD20 steps total **13.277 ms** more than their native counterparts.
Opponent service accounts for **10.121 ms** of added time in this subset, while body
composition is slightly faster. This corrects the impression from the whole-window
opponent percentage: a small share of total cost can still explain much of the local
increase. Native opponent calls take 2.088–2.124 ms; the scheduled calls take
2.837–4.908 ms. Counting entries to the native opponent body at `$d3de` finds eight
updates in the native subset and ten in WORLD20: counters 27 and 24 each service two
updates. Thus the extra service time includes required elapsed-time catch-up, not only
wrapper overhead. The six single-update WORLD20 calls still take 2.837–2.880 ms;
matching body paths and state is necessary before attributing this remaining difference
solely to the scheduler.

The paired 200-field `timing-repair-stagecost-native-a500` and
`timing-repair-stagecost-world-a500` captures complete 32 first-stage steps, counters
31 through zero, excluding the same opening partial step. Native averages **114.353 ms**
per step and WORLD20 **117.890 ms**, totaling **113.172 ms** of extra time. WORLD20
executes 42 native opponent-body entries versus 32, with ten steps serving two updates;
opponent service adds **44.764 ms** over this subset. Body composition averages
47.176 / 46.516 ms and bitmap copying 20.658 / 20.698 ms respectively. This covers
one first-stage item/direction, not the remaining seven stages.

The last five native steps, counters 4 through zero, take approximately **100 ms**;
WORLD20 continues taking approximately **120 ms**. The trace identifies a message
lifetime mismatch: the native expiry path at `$e2ac` executes from counter 4 onward,
changing the message pointer drawn at `$e330` from hunk `$3d20` to `$3bd5`. WORLD20
keeps drawing `$3d20` through counter zero and never takes that expiry path in the
measured stage. Presentation preparation alone adds **36.499 ms** across the 32 steps;
display waits then contribute additional phase-dependent differences.

At the repair anchor, native `state+$5e` (frame counter) is **665** and `state+$64`
(message deadline) **692**, a remaining difference of 27. WORLD20 has counter **585**
and deadline **839**, a difference of 254. `$e2a6` compares those fields directly;
`$e388` increments the counter once per presentation. Thus this message still has a
frame-dependent lifetime and the matched repair entry does not have matched remaining
message time. The expiry/drawing difference is observed, not inferred from aggregate
profile percentages. Its origin must be traced through message creation and temporary
counter ownership before selecting a correction. Do not shorten messages merely to
make an animation timing test pass, or treat all measured overhead as scheduler cost.

Display phase also matters. Native complete steps cluster near 100 and 120 ms; the
ScrollVPort interval ranges from 0.053 to 14.280 ms. WORLD20 has a 111.133-ms first
complete step and subsequent steps spanning 99.873–121.807 ms. These observations
motivate checking refresh-boundary crossings across the whole stage, but do not yet
prove that missed refreshes explain the full 100–820-ms unpaced invocation penalty.
No display wait has been removed and these captures are not rendering FPS evidence.

#### Experimental late-presentation extraction

`TIMING_REPAIR_DROP=1` requires `TIMING_REPAIR=1` and defaults to zero. It suppresses
only late pictures in supported human repair stages; the normal build is unchanged.
At step entry, lateness of at least one PAL field relative to the preceding deadline
selects a dropped picture. Stage endpoints and stage-two counter 31 (the first frame
after the native repair/sound event) always draw. EC=0 and DA=0 retain native drawing.

The native buffer audit rules out suppressing only sprite draws: `$7f7a` exchanges the
display/drawing bitmaps and `$e372` restores the background from `state+$3d2` into the
new drawing bitmap. That source is the separate pit background (`$06ae` in this route),
not a copy of the currently displayed ship. A skipped sprite frame followed by an
ordinary presentation could therefore expose an empty background.

The prototype instead retains the native `$1432e` part-bank pointer updates and every
repair geometry mutation, while gating `$176c6` during the selected drawing interval.
The normal clipping call preserves its original return-slot depth, including its native
clipped-out return. The `$e2fc` gate runs after native message expiry and refuel updates;
when suppressing a picture, it samples the clock and bypasses drawing, buffer exchange,
display waits and background copying. The `$e378` gate clears suppression before native
counter/timeout/input/opponent/keyboard service, skipping the HUD draw for that picture.
All native E296 register-save frames remain at their original depth. Pit abort also
clears suppression. This is an extraction prototype, not a demonstrated full state or
pixel-equivalence contract: skipped drawing-register outputs, HUD scratch fields,
clipped calls, input/result histories and nonlocal exits still require verification.

`PDRDROP1` reports suppression activity, selected dropped steps, suppressed bitmap calls,
service-only continuations, rendered steps and last entry lateness. The read-only
`check_repair_drop.py` pairs all 264 post-step observations and checks exact accounting,
endpoint protection, nine suppressed bitmap calls per dropped step on this measured
route, and cleared suppression after every step.

The first guarded run (`timing-repairdrop2-a500`) preserves all **264 native geometry
and deadline observations**: **234 steps draw, 30 presentations drop**, suppressing 270
bitmap calls. All 30 drops rejoin native service and all step exits have suppression
cleared. Whole invocation times are **8,260 / 8,840 / 7,960 / 7,980 ms** versus native
**8,260 / 8,840 / 7,900 / 7,960 ms**. Three cases pass; item 0/direction 0 is 60 ms long,
whose conservative 100-ms error still exceeds the unchanged 90-ms gate. It is a failure,
not a rounded pass. All eight individual stage durations pass.

The current candidate retains stage-one lateness across the stage transition: only a
completed supported first stage can supply its intended endpoint as stage two's epoch.
This one-shot bridge clears on consumption, fresh stage-one initialization and pit abort.
The deliberate stage-two pause remains separately excluded, including any longer native
wait. `--continuous-stages` checks this epoch transfer independently. The A500 `timing-repairdrop3-a500` run **passes all four complete cadence cases and all
eight stage gates**, retaining all 264 native word-geometry/deadline observations and
all four exact stage-epoch transfers. Whole durations are **8,240 / 8,840 / 7,860 /
7,940 ms**, versus native **8,260 / 8,840 / 7,900 / 7,960 ms**. Maximum absolute whole
error is 40 ms; with the unchanged conservative endpoint allowance, all errors are
40–80 ms and also within 10%. Accounting remains 234 drawn / 30 dropped, 270 suppressed
bitmap calls and 30 service-only continuations, with suppression clear at every post.
Drops per stage are 2/5, 0/1, 4/6 and 6/6. No input or game-state fixture was added.

The 030 `timing-repairdrop3-030-twins` counterpart also passes all 264 geometry/deadline
samples, all four exact stage-epoch transfers and all eight stage/four invocation gates.
Its complete durations exactly match native: **8,260 / 8,840 / 7,900 / 7,960 ms**.
It draws all 264 presentations, with zero suppression or service-only continuations;
this exercises the normal path, not the drop path. Renderer diagnostics show zero new
staged comparisons during this pit window, no new failures and unchanged raster code.
Selecting CUSTOM4 here does not provide new 3D renderer equivalence evidence.

Read-only paired chip-memory snapshots in `timing-repairdrop3-buffers-full-a500`
cover all **264 steps across all eight stages**. All **30 dropped steps** preserve both
32,000-byte screen buffers and the separate 32,000-byte pit background exactly, including
bitmap descriptors and drawing/display roles. Every dropped entry has an idle blitter
(DMACONR busy is word bit 14); all **180 native part-bank selections** still occur.
The **234 rendered steps** exchange drawing/display descriptors normally, with 221
changed displayed pictures. The native outer service counter advances exactly once in
every one of the 264 steps. There are no busy-entry exclusions or incomplete pairs.
The same capture passes all geometry, deadline, stage-transfer and cadence gates, with
the same durations and drop counts as the earlier A500 run. This is endpoint buffer
preservation, not independent native-render pixel equivalence or proof against transient
writes. The shorter `timing-repairdrop3-buffers-a500` capture also passes its 34 pairs.

`REPAIR_BUFFER_STATE=1` with TIMING_STATE and probes `$148d8`, `$14962`, `$14a20`,
`$14aa6` saves paired full chip snapshots around each logical repair step. The checker
requires exercised drawn and idle-blitter dropped paths, validates each planar descriptor,
compares all three bitmaps on idle-entry drops, and checks part-bank updates and the native
outer service counter. `--complete-route` additionally requires all 264 pairs. Busy-entry
drops are reported and excluded from pixel claims. These instrumented runs are not FPS
measurements. Skipped drawing-register/HUD scratch state, broader input coverage,
full opponent-record equivalence, native exits and broader branches remain open.

`timing-repairdrop3-service2-a500` covers all **264 repair steps**, including all **30
suppressed pictures**. Each step reaches `$e3bc` / `$e3c4` around opponent service, then
`$e3d0` / `$e3d6` around keyboard availability polling, exactly once and in that order.
Drawing suppression is clear at each post. All **264 keyboard results are empty**;
this proves polling continuity, not key consumption or input-triggered exits.
The opponent-ledger check passes **1,772 movement samples and 298 pit service restores**
across the 2,000-field window. It verifies the unchanged epoch/phase, elapsed-time
accounting, logical movement delta, scheduled clock values, RNG/counter ownership and
exact bounded service: each pit call serves the smaller of the total owed updates and
32 additional updates, retaining the remaining elapsed debt. Six lap-gate and six
lap-duration reads use the retained stable epoch. No opponent repair-clock or lap-start
reader is exercised. This covers the ledger and ownership, not complete-record trajectory
agreement or a rescue-return cycle.

The capture uses `ANCHOR=0x148d0`, `FIELDS=2000`, `SWAP_MARKER=0xe296`, `SWAP_ONLY=1`,
`TIMING_STATE=1`, `TIMING_EARLY=1`, and probes
`0x148d8 0x14962 0x14a20 0x14aa6 0xe3bc 0xe3c4 0xe3d0 0xe3d6 0xd56c 0xd4bc 0xd504 0xd7fe 0xd83c 0xd86c`.
Other CPU/slave/input settings match the A500 repairdrop3 route. These reduced probes
intentionally omit the geometry-stage entry/return sites; use the separately completed
buffer/pacing capture for those gates. The earlier `timing-repairdrop3-service-a500`
attempt stopped before its first field after the debugger rejected its larger breakpoint
setup and supplies no runtime evidence. Existing 030 pause and A500 rescue ledger checks
still pass with the added repair-only verifier mode.

A separate input-only fixture, `TIMING_REPAIR_INPUT_TEST=1`, is compiled only with
VERIFY, COVERAGE_INPUT and TIMING_REPAIR_DROP. It publishes one ordinary `x` into the
native keyboard ring on the first eligible dropped step, after the coverage tape finishes
and while the native queue is empty. It changes no physics, clock, mode or repair geometry
fields. Pit entry has already disabled the private world-key queue; this fixture targets
the native pit consumer. It is a directed main-context input publication, not a test of
hardware interrupt concurrency. The test remains absent when its build flag is zero.

The complete A500 `timing-repairinput1-a500` route passes all 264 service/poll pairs:
**236 drawn / 28 dropped**, with 263 empty polls and **one nonempty poll**. At field 150,
a dropped step publishes `x` (120), advancing the native writer from slot 1 to 2 while
the reader remains at 1. Native `$581e` reports availability; `$5838` returns exactly 120
and advances the reader to slot 2. `$e422` / `$e426` pass it to `state+$10e`. The original
key-reader call restores its caller's stack depth, and the repair post restores its
24-byte MOVEM frame with suppression cleared and the native queue empty. There is exactly
one observed consumption across the complete route. This does not prove special-command
handlers, nonlocal exits, wrapping/capacity or competing producers. The test changes the
run's drop count, so it supplies service/input evidence rather than a new timing or FPS
claim. With the fixture disabled, both the full repairdrop3 slave and the normal slave
remain byte-identical to their frozen references; requesting it outside the required
development configuration is rejected.

Build the repairdrop3 coverage configuration with the additional
`-DTIMING_REPAIR_INPUT_TEST=1` and freeze it as a separate test slave. Reuse the A500
2,000-field repair service configuration with probes
`0x148d8 0x14962 0x14a20 0x14aa6 0xe3bc 0xe3c4 0xe3d0 0xe3d6 0xe3e6 0xe3ec 0xe422 0xe426`.
PDRKEY_EVENT records the publication metadata, current native queue indices/capacity,
command latch, D0 and SP. The checker requires the publication to begin on a dropped
step, follows its ordered native call/return/latch boundaries, and rejects repeated or
missing consumption. It also runs the full repair-service checker.

The drop-disabled build was
byte-identical before the additional stage-bridge correction; the normal build remains
byte-identical afterward. A build requesting DROP without REPAIR is rejected.

```sh
python3 tools/check_repair_drop.py tmp/prof/timing-repairdrop3-a500
python3 tools/check_repair_drop.py --allow-no-drops tmp/prof/timing-repairdrop3-030-twins
python3 tools/check_repair_buffers.py --complete-route tmp/prof/timing-repairdrop3-buffers-full-a500
python3 tools/check_repair_service.py tmp/prof/timing-repairdrop3-service2-a500
python3 tools/check_repair_input.py tmp/prof/timing-repairinput1-a500
python3 tools/check_timing_opponent_continuity.py --repair-only --stable-lap-domain tmp/prof/timing-repairdrop3-service2-a500
python3 tools/check_repair_pacing.py --native-steps --continuous-stages tmp/prof/timing-repairloop3-native-a500 tmp/prof/timing-repairdrop3-a500
```

#### Logical flight-message publication and expiry

The WORLD20 prototype now uses one logical counter domain for ordinary human-flight
message publication and expiry. Both queued text presentation and native `$da50–$da64`
expiry run **outside** temporary world ownership, so changing a publisher alone is
incorrect. The prior `timing-flightmessage-before-a500` trace observes ten publications,
eight with different render and logical phases; at field 227 the publisher uses render
counter 103 while the last logical phase is 110. The consumer also uses the render
counter. Thus these ordinary messages are frame-counted even though controls are timed.

The shared counter selector now chooses the extended logical message phase
when timing has started, WORLD20 has initialized, no pit owns the context, and the
native mode is human flight. `$13536` and `$c990` publish into that domain; the existing
`$d8ca` opponent-message hook uses it in flight too. Native additions of 15/30/45 phases
remain in place. The `$da54` CMP/BGT pair compares against the same selected domain and
rejoins the original alive/expired successors. All registers and stack depth are preserved;
MOVE/CMP define their native flags, with X unchanged. Pits keep the previously corrected
saved-outer-counter behavior; unsupported modes select their native counter. The new
hooks are inside WORLD20 and CUSTOM3, not the normal minimum/liftoff-only build.

The frozen `Powerdrome-timing-flightmessage2.slave` uses the full timing/repair prototype,
fixed test seeds and **no** initial-pit synchronization or input/result predicate fixture.
The input-only CUSTOM5=11 centering route runs for 850 fields from `$bc7c`:

| Check | A500 | 68030/25, renderer twins |
| --- | ---: | ---: |
| Logical message publications | 13 | 13 |
| Publications differing from the render counter | 11 | 13 |
| Expiry branch and register/SP checks | 204 | 241 |
| Unrefreshed native clears | 2 | 2 |
| Observed age at each clear | 45 logical phases | 45 logical phases |

Both unrefreshed messages expire at **4,050 ms of logical control time** on both CPUs.
This is elapsed simulation time, not a claim of identical physical display latency or
original A500 message-duration calibration. The 030 completes **294 clean renderer
comparisons**, with unchanged raster code and no pixel/guard/scratch/register failures;
its final snapshot is inside another staged draw and is not a teardown check.

`timing-flightmessage2-pit-a500`, built with the existing synchronized pit fixture,
regresses all three differing-domain pit publications, their native MOVE/ADD boundaries,
register/SP preservation and following outer consumers. Normal-build bytes remain
identical. The legacy engine-only prototype still builds, and WORLD20 without ENGINE
is rejected by its existing dependency guard. The hook-layout checker verifies complete
instructions and native bytes at all sites in both C3-off reference snapshots.

The lap hook at `$10c16` now preserves the message deadline in the selected logical
flight domain. The native three-instruction MOVE/SUB/MOVE sequence still determines
D1 and CCR, including subtraction's X; the wrapper saves that CCR and restores only
state+$64 before returning. The following native clear of state+$5e remains in place.
The same domain predicate is shared with publication and expiry. Unsupported contexts
retain the original rebase. This hook is WORLD20/CUSTOM3-only.

The 030 natural-lap route gives paired read-only observations at `$10c16`, `$10c22`
and `$10c2a`. In `timing-messagelap-before-pair-030`, the native rebase changes deadline
**1,045 → 693** while logical phase remains **352**. The corrected
`timing-messagelap1-pair-030` preserves **1,044 → 1,044** at phase **352**, with the native
D1 subtraction result, all other D/A registers, stack depth, speed and movement delta
unchanged. The native counter still clears to zero. The one-phase arrival difference
means these runs are not full trajectory equivalence evidence. Both captures enter from
the existing rescue route; the captured message's publisher precedes the window, so
this does **not** establish its lifetime or correct pit-to-flight deadline conversion.
The corrected ten-field window completes two clean renderer twins; its final snapshot
is inside another draw, not a teardown check.

The corresponding A500/native-renderer run `timing-messagelap1-pair-a500-long` passes
one lap boundary with deadline **849 → 849** and phase **352**, retaining the same
native register/stack/subtraction contract. Its message flag is zero, so it covers an
inactive deadline, not a live message lifetime. Use 100 fields on A500: the initial
ten-field attempt reached the boundary but failed the harness's minimum-presentation
requirement and has no final snapshots; it is not a completed validation run.

The corrected ordinary-flight regression `timing-messagelap1-flight-030` (850 fields,
C5=11 without the synchronized-pit fixture) passes **13 publications, 240 expiry
branch/register checks and two clears at 45 logical phases**. It completes **293 clean
renderer twins**, with unchanged raster code. The shared domain-predicate refactor therefore
retains the bounded publication/expiry contract. Normal-build bytes remain identical;
the expanded hook-layout check also passes against both snapshots of the C3-off reference.

Reproduce with the full timing/repair build plus `TIMING_PIT_SYNC_TEST=1`, C5=13,
the documented 030 configuration, TIMING_STATE/TIMING_EARLY, anchor `$10c10`, ten fields
and probes `0x10c16 0x10c22 0x10c2a 0x13536 0x1353c 0x13558 0xda54 0xda5a 0xda64`.
The anchor precedes the entry probe; anchoring at `$10c16` skips its initial observation
and is insufficient for the checker. The abandoned C5=11 anchor attempt supplied no
lap evidence. `check_message_lap.py` verifies register and memory contracts; guest CCR
edge cases remain a separate requirement.

```sh
python3 tools/check_message_lap.py --expect-native-rebase tmp/prof/timing-messagelap-before-pair-030
python3 tools/check_message_lap.py tmp/prof/timing-messagelap1-pair-030
python3 tools/check_message_lap.py tmp/prof/timing-messagelap1-pair-a500-long
python3 tools/check_flight_message.py tmp/prof/timing-messagelap1-flight-030
```

The rescue return also needs an explicit change of message-counter domain. In
`timing-messagehandoff-before-030`, departure publishes a message through `$13536`
while the pit opponent scheduler owns the native counter: its temporary counter is
1,343, but the saved outer source is 999, correctly producing deadline 1,044 after the
native +45. At first resumed flight the outer counter is 1,018, so **26 counts remain**.
The logical clock resumes at phase 293. Previously deadline 1,044 survived unchanged;
71 observed expiry branches leave the message alive until a new publication replaces it
at phase 352, already past its intended remaining count.

`timing_message_resume` now translates the deadline once during the existing rescue
reinitialization, after selecting the resumed control phase and before clearing the
pit-rebase flag: `deadline = phase + (old_deadline - outer_counter)`. The -1 sentinel
is preserved explicitly. Human-flight mode guards retain native behavior elsewhere;
initial pit entry and ordinary frames do not call the conversion. Registers and CCR
are protected by the containing `timing_frame` save frame. Negative remaining counts
stay expired instead of being clamped into a fresh positive lifetime.

The corrected `timing-messagehandoff1-030` observes **1,044 → 319** at the phase-293
handoff, preserving those **26 remaining counts**, and the native expiry/clear occurs
at phase **319**. The checker verifies the pit publication, paired first-update
register/stack contract, 32 expiry branch/register decisions and one native clear.
It stops tracking that message at the next publication rather than mixing lifetimes.
The completed 500-field capture adds **117 clean renderer twins**, with unchanged raster
code; the final in-progress draw is not a teardown proof. The normal build remains
byte-identical, and the option-off hook audit still passes.

The same build on A500 (`timing-messagehandoff1-a500`) exercises an already inactive
message. At retune its deadline is 849; no publisher changes it before first resumed
flight. The outer counter reaches 904 and the logical phase resumes at 293, so the
conversion yields **849 → 238**, preserving **-55 remaining counts**. The message stays
inactive until a later publication. The check verifies the paired register/stack
contract and rejects revival; it makes no claim about the unobserved original publisher
or an active A500 message lifetime. The different 030/A500 message histories are not
matched trajectory evidence.

Use the lap-correction synchronized-pit configuration (C5=13), ordered pre-anchor
probe `$c7d2`, anchor `$1408a`, 500 fields and probes
`0x14090 0x140d0 0xce28 0xca3e 0xca4a 0x13536 0x1353c 0x13558 0xda54 0xda5a 0xda64`.
The pre-anchor probe selects rescue departure instead of the initial pit departure.
This establishes count-domain ownership, not original A500 pit-message duration:
those pit counts are still tied to native presentations and need their own cadence
calibration. Other result/nonlocal handoffs, the sentinel branch, wrap and guest CCR
edge cases remain separate runtime requirements.

```sh
python3 tools/check_message_handoff.py --expect-leak tmp/prof/timing-messagehandoff-before-030
python3 tools/check_message_handoff.py tmp/prof/timing-messagehandoff1-030
python3 tools/check_message_handoff.py --inactive tmp/prof/timing-messagehandoff1-a500
```

The message deadline is also mutated outside its ordinary publisher. A static audit of
explicit state+$64 operands identifies these additional contracts (indirect aliases are
not excluded by this inventory):

| Native sites | Deadline operation | Timing ownership still needed |
| --- | --- | --- |
| `$b116`, `$c196` | Store -1 sentinel | Initialization/ending lifecycle |
| `$c772` | Extend by 15 after calling `$13514` | Suppressed-publication and extension cases |
| `$10c16–$10c1e` | Subtract state+$5e at player lap completion | Preserve a continuous logical deadline |
| `$e2ba`, `$13ac0` | Publish native counter minus 1 | Pit expiration/sentinel semantics |
| `$13ada`, `$13af4`, `$14138`, `$141aa`, `$141ec`, `$14210` | Publish native counter plus 30 | Pit modes and flight handoff |
| `$14156` | Publish native counter plus 45 | Pit mode and flight handoff |
| `$da50`, `$e2a2` | Read for flight/pit expiry | Paired consumer domains |

The native control phase remains 16 bits, but message deadlines now use a private
32-bit extension (`PDMSGCLK`: valid word +8, last native phase word +10, extended phase
long +12). Each world step adds the unsigned word difference from the previous observed
control phase. Repeated movement steps in the same phase add zero; `$ffff → 0` adds one.
Initialization takes the outer counter's high word and the selected control phase's low
word. Ordinary new timing epochs invalidate this clock; rescue reinitialization preserves
it. Rescue deadline conversion uses the extended upcoming phase, not a zero-extended
word. Native control cadence and phase-mask behavior remain unchanged in production.
The containing world/frame wrappers preserve registers and CCR around clock maintenance.

`TIMING_MESSAGE_WRAP_TEST=1` is an explicit VERIFY/WORLD20-only fixture. It selects
initial control phase **65,401** to exercise rollover quickly; it is absent by default
and is not a gameplay policy or an A500 handling calibration. At 90 ms per increment,
a natural full word rollover spans **98.304 minutes**, so ordinary ten-minute runs do
not provide this evidence. The fixture changes initial control-phase bits and therefore
cannot certify unchanged full gameplay trajectories.

`timing-messagewrap1-030` passes **13 publications, 241 expiry branch/register checks
and two native clears at exactly 45 phases**. The second unrefreshed message publishes
at extended phase **65,523** and expires at **65,568**, when the native phase is **32**.
The completed 850-field window adds **294 clean renderer twins**, with unchanged raster
code. The A500/native-renderer counterpart `timing-messagewrap1-a500` passes
**13 publications, 203 expiry checks and two 45-phase clears**, including the same
**65,523 → 65,568** rollover-spanning lifetime. These are directed message checks,
not full gameplay equivalence. The 030 final active draw is not teardown evidence.
`PDMSGPHASE_EVENT` records the
three clock fields beside each domain sample; the checker requires matching low words,
a monotonic extended phase, and a publication-to-clear lifetime spanning rollover.
Older captures without the new clock retain their original bounded phase checks.

The fixture-free synchronized-pit build also passes
`timing-messageclock1-handoff-030`: the extended clock preserves the rescue message's
26 remaining counts, clears at phase 319, passes 32 expiry/register checks and adds
117 clean renderer twins. That run does not cross rollover. Explicitly disabling the
wrap fixture produces byte-identical output to omitting it; enabling it without VERIFY
is rejected. The normal build remains byte-identical and the option-off hook audit passes.

Use the ordinary full timing/repair build with `TIMING_MESSAGE_WRAP_TEST=1`, C5=11,
anchor `$bc7c`, 850 fields and the ordinary flight-message probes above. The fixture
must not be used as a throughput benchmark. Thirty-two-bit signed-clock rollover,
negative sentinels and rollover combined with rescue, lap/session resets or other
publishers remain separate requirements.

```sh
python3 tools/check_flight_message.py --require-wrap tmp/prof/timing-messagewrap1-030
python3 tools/check_flight_message.py --require-wrap tmp/prof/timing-messagewrap1-a500
python3 tools/check_message_handoff.py tmp/prof/timing-messageclock1-handoff-030
```

This is a bounded flight-message correction. The direct `$c990` publisher and flight
`$d8ca` context still need directed runtime coverage. Broader lap contexts and
wrap combined with mode changes, pause/rescue/result handoffs, other publishers and unsupported modes
remain to audit before release. The current checker explicitly rejects extended-clock resets instead of counting them as covered. Runtime guest CCR edge cases and native
A500 lifetime calibration also remain open. Pit expiry is still in its outer counter domain.

Use TIMING_STATE, TIMING_EARLY and probes
`0x13536 0x1353c 0x13558 0xda50 0xda54 0xda5a 0xda64 0x134ba` with the usual 850-field
C5=11 A500/030 configurations. Do not probe `$da58` in the corrected build: it lies inside
the replaced comparison/branch pair. PDMSGDOMAIN_EVENT records timing/pit/world ownership,
last logical phase, opponent ownership, message flag and native mode. PDMESSAGE/PDMREG
provide independent native deadline, clock, register and stack observations.

```sh
python3 tools/check_flight_message.py tmp/prof/timing-flightmessage2-a500
python3 tools/check_flight_message.py tmp/prof/timing-flightmessage2-030-twins
python3 tools/check_pit_message.py tmp/prof/timing-flightmessage2-pit-a500
```

#### Pit message counter ownership correction

The read-only `timing-message-ledger-world-a500` capture directly establishes the leak.
At `$d8ca`, the scheduled opponent body uses counter 508 and writes deadline 538;
the next outer `$e2a6` reader has counter 198 and sees that unchanged deadline. Two
further fully paired publications reproduce the mismatch. A stopped snapshot at the
first setter independently has active opponent ownership, phase 503 and saved outer
counter 198. Selecting the live `PDPOPP01` inside the installed slave is essential;
the preload cache also contains an uninitialized copy of the same diagnostic tag.

WORLD20 now replaces the six-byte native MOVE at `$d8ca` with
`timing_pit_message_counter`. During scheduled pit ownership, with no active world
body, it publishes the saved outer counter to `state+$64`. The native following
ADD #30 remains unchanged. Other contexts replay the existing native counter source.
The helper preserves D0/A0 and the caller's stack, and its final MOVE recreates NZVC
while preserving X. It does not change the opponent phase, update count, RNG or clocks.
The new hook is installed only with the experimental WORLD20 build and CUSTOM3;
the normal build remains byte-identical to its reference.

The frozen pitmessage1 build passes `timing-pitmessage1-a500`: **three** complete
entry/MOVE/ADD observations all use the correct outer deadline and preserve all
D/A registers and SP, plus the sampled movement delta and speed. Three subsequent
outer readers observe those deadlines. For example, phase 508 now publishes
**198 + 30 = 228**. The final observed publication sets **200 + 30 = 230**; the native
strict-greater expiry path runs at outer counter 231, at field 152 (2,520 ms after
that publication at field 26). The earlier leading publication is only partially
observed at the capture anchor and is excluded from the three complete contracts.

The complete 2,000-field `timing-pitmessage1-repairs-a500` regression preserves all
**264 native word-geometry states**, with all four invocations complete and no trailing
partial invocation. With repair pacing still off, the changed message lifetime removes
400–960 ms per invocation relative to the earlier unpaced WORLD20 build:

| Item / direction | Native A500 | Earlier WORLD20 | Corrected message ownership |
| --- | ---: | ---: | ---: |
| 1 / 0 | 8,260 ms | 8,840 ms | 7,980 ms |
| 1 / 1 | 8,840 ms | 8,940 ms | 7,980 ms |
| 0 / 0 | 7,900 ms | 8,700 ms | 8,300 ms |
| 0 / 1 | 7,960 ms | 8,780 ms | 7,880 ms |

These unpaced durations still fail the strict calibration gate. They demonstrate that
message ownership was a material contributor to the animation cost; they do not establish
elapsed-time message equivalence or repaired animation cadence. The corrected baseline with uniform pacing (`timing-pitmessage-pace1-a500`)
preserves all 264 word-geometry/deadline observations, but only item 1/direction 1 passes
both stage and whole-invocation gates. Whole durations are **8,420 / 8,840 / 8,420 /
8,080 ms**, respectively **160 / 0 / 520 / 120 ms** above native. Several individual
stages pass, but the remaining cases must not be counted as calibrated. The current
per-step schedule above tests whether retaining the measured cheap/expensive-step order
avoids waiting away the headroom needed for later drawing. It does not change message
lifetime, opponent cadence, required native updates or the separate minimum pause.

The native-step candidate `timing-pitmessage-pace2-a500` passes all **264** exact
word-geometry and native-cumulative-deadline observations, including stage ownership
and pause exclusion, but still fails overall calibration. Whole invocation times are
**8,420 / 8,820 / 8,420 / 8,120 ms** versus native **8,260 / 8,840 / 7,900 / 7,960 ms**.
Only item 1/direction 1 passes both stage and whole-invocation bounds. The per-step
schedule has not removed the A500 throughput constraint; do not infer an improvement
from matching its deadline arithmetic. The pilot remains off by default.

The next correction must reduce drawing work or allow presentation to fall behind the
logical animation while preserving every native state update. The native call audit
identifies two substantial costs: `$176c6` draws each masked bitmap with two graphics
calls (mask then image), and `$15878` copies the complete 320×200 bitmap at each pit
presentation. Neither can simply be skipped: `$1432e` also refreshes mutable part-bank
pointers, and `$e296` combines drawing with message/refuel state, the outer counter,
input polling, scheduled opponents and native nonlocal exits. A presentation split must
preserve those operations and original stack depth, and must validate both bitmap buffers
at displayed boundaries. Whole-stage timing, all 264 logical states, opponent continuity,
input/result paths and image checks are required before treating reduced drawing as a fix.
Do not remove blitter/display waits without proving the corresponding ownership contract.

```sh
python3 tools/check_repair_pacing.py --native-steps tmp/prof/timing-repairloop3-native-a500 tmp/prof/timing-pitmessage-pace2-a500
# Geometry/deadline assertions pass; final cadence assertion deliberately reports failure.
```

This fixes an escaping deadline's counter domain, not its remaining frame dependence.
Elapsed-time calibration of message lifetimes, ordinary world message ownership,
other writers, inactive/native fallback paths, guest CCR runtime coverage, 030
validation and repair-duration calibration remain open. Debugger SR is
not used as guest flag evidence. The hook-boundary audit passes; no decoded direct
branch enters its interior. The full repair pilot remains disabled by default.

```sh
python3 tools/check_pit_message.py --expect-leak tmp/prof/timing-message-ledger-world-a500
python3 tools/check_pit_message.py tmp/prof/timing-pitmessage1-a500
```

```sh
python3 tools/repair_step_profile.py tmp/prof/timing-repair-cost-native-a500 tmp/prof/timing-repair-cost-world-a500
```

`PDREPR01` records active stage, epoch, total units, latest deadline/completion time,
stage/step counts, excluded pause time and lateness. The per-step implementation appends
its selected table pointer after the unchanged diagnostic prefix. The read-only `$14a20` continuation
probe distinguishes the enforced minimum pause from the drawing body. These checks cover
only the two item variants, not all repair branches, nonlocal result exits or complete
pit duration. The pilot is not enabled by default until the remaining gates pass.

### Continuous opponent time across flight and rescue

The WORLD20 development build gives opponents an independent 18-unit (90-ms) deadline
from the first timed race world update. `timing_pit_opponents.s` intercepts the native
`$d3d6` entry for the ordinary `$ced8` call and the pit updater's `$e3bc` call. Other
callers retain the native body. Ordinary flight allocates through its logical 20-ms world
cursor; rescue pits allocate against unpaused physical time. The same origin, deadline,
counter phase and residual survive entry and return. The player still discards its
interrupted batch and rebases after the pit, as described above.

Each scheduled update temporarily owns the native counter. During flight it uses the
already-live world RNG and must not replace or rewind that stream. During a pit it swaps
the private world stream in and restores the outer presentation stream afterward. Five
direct opponent clock reads at `$d4b6`, `$d4fe`, `$d7f8`, `$d836` and `$d866` receive the
logical deadline translated into the observed native clock epoch during these updates.
The epoch offset uses physical time even when the scheduled world cursor is behind it.
Other callers read the real native clock. The shared `$f96` clock is never frozen or rewritten.

Cockpit departure does not call the pit updater. Normal pit return therefore drains
updates due through a fixed native-return cutoff before continuing at `$ce28`, preserving
the original pit return registers in private storage and the original native stack depth.
The following flight allocations use the same ledger, including its residual and time
spent draining and returning. Individual allocations are capped at 32 updates without
dropping unassigned debt. Ordinary session closure disables the timeline; a fresh session
initializes a new origin and phase. Nonlocal result exits restore ownership, but runtime
coverage of their stack behavior remains open.

The frozen `Powerdrome-timing-oppcontinuous1.slave` passes
`timing-oppcontinuous1-030-twins` over 5,000 fields. At pit return it has completed
965 opponent updates since the first timed world update, with zero residual and counter
phase 1,024. The first resumed allocation accounts for **100 ms after the cutoff** as
**one 90-ms update plus 10 ms residual**. All 4,444 sampled opponent movement executions
use the 18-unit delta and scheduled counter, including 588 after return. The checker
verifies 682 paired pit counter/RNG restores and 659 resumed flight counter restores.
Sixteen lap-gate results at `$d7fe` and sixteen lap-duration results at `$d86c` match their
logical timestamps. Repair-clock and lap-start results were not exercised in this capture.

`tools/check_timing_opponent_continuity.py CAPTURE...` checks the continuous ledger at
every probe, verifies live world RNG is preserved on entry, verifies counter ownership,
and checks exact bounded service through each completed world timestamp: the smaller of
all owed updates and 32 updates, with every unserved clock unit retained as debt. It
requires a completed rescue and at least ten resumed world updates. The historical
`timing-retune4-rescue-030-twins` still passes the ledger/ownership checks. The current
`timing-playerresult4-pause-030-twins` passes 254 completed world-call checks and 364
movement samples in `--flight-only --stable-lap-domain` mode, including its initially
capped backlog. That pause window has no lap-clock reads and is not lap-domain evidence.

For current WORLD20 captures, add `--stable-lap-domain`: lap readers use the retained lap
epoch while repair readers retain their sampled physical mapping. This mode requires
unchanged epoch/reset diagnostics between terminal snapshots; a countdown reset requires
a separate reset-boundary audit. The A500 rescue counterpart below passes this stable-domain mode. These
checks do not establish full opponent-array
equivalence or native A500 calibration. `check_timing_pit.py` and
`check_timing_pit_lifecycle.py` independently verify the suspended player's boundary:
four assigned player steps are discarded, then flight resumes with one 20-ms step and
zero debt. All **1,049 common pre-pit sampled player/engine/RNG states** match the preceding
modal-only scheduler when aligned to fixture time. The current capture adds **416 clean
renderer comparisons**, with unchanged raster code. Instrumented captures are not FPS benchmarks.

Reproduce with the WORLD20 build flags above, `CUSTOM5=13`, `FIELDS=5000` on 030,
`TIMING_STATE=1`, and probes `$ce1e $103a2 $13cde $ce28 $ccee $cedc $ca44 $d56c $e3bc
$e3c4 $d3de $d4bc $d504 $d7fe $d83c $d86c $c7d2 $ced8`.

The same artifact passes `timing-oppcontinuous1-a500` over 8,000 fields. At pit return it
has completed 1,384 session updates with 50 ms residual and counter phase 1,443. The first
resumed allocation accounts for **200 ms after cutoff plus 50 ms residual** as **two 90-ms
updates plus 70 ms residual**. The checker validates 7,112 movement samples (1,580 after
return), 682 pit ownership restores, 2,814 world counter restores (1,768 after return),
and 26 results at each observed lap-clock read. Both CPU runs explicitly discard four
assigned player steps and resume player movement with one 20-ms step and zero debt.

| Current rescue handoff | 030/25 with fast renderer twins | A500, no fast RAM |
| --- | ---: | ---: |
| Pit interval through native return cutoff | 65,700 ms | 103,500 ms |
| Opponent residual at cutoff | 0 ms | 50 ms |
| Time from cutoff to first resumed opponent allocation | 100 ms | 200 ms |
| Work served by that allocation | 90 ms | 180 ms |
| Residual afterward | 10 ms | 70 ms |
| Retained pit-related player debt | 0 ms | 0 ms |

The added D5 probes establish that these CPU runs do not start with matching opponent
movement operands. At the first common sampled scheduled update, the first opponent uses
505 on 030 and 619 on A500, despite matching sampled RNG values. Those differences precede
rescue. Full opponent equivalence needs matched initialization and complete state probes;
the current ledger passes must not be presented as matching trajectories.

The 27-value `PDPOPP_EVENT` adds flush/RNG-ownership flags,
initial phase, world ownership/cursor and the actual D5 multiplication operand to the
previous diagnostics. D0 at `$d56c` is not that operand and cannot establish movement equivalence.

The same artifact passes `timing-oppcontinuous1-session-030-twins`: two ordinary session
closures and two fresh entries over 1,800 fields, with 228 clean renderer comparisons.
That route uses Practice, so it does not exercise race-opponent reinitialization.
The 300-field `timing-oppcontinuous1-pause-030-twins` excludes 48 paused PAL fields,
preserves all five input events, and verifies 255 consecutive 20-ms world steps, 56
90-ms control updates and 224 opponent movement samples. It ends with no assigned work
or time debt outstanding and adds 75 clean renderer comparisons. Run
`check_timing_pause.py`, `check_timing_world20.py`, and
`check_timing_opponent_continuity.py --flight-only` on that bounded pause route. The three
current-build 030 runs total **719 clean renderer comparisons**. The normal build remains
byte-identical to the preceding checkpoint; the prototype rebuild reproduces the frozen
artifact. The complete-instruction/branch-entry audit passes.

Full opponent-array equivalence, native A500 cadence calibration, repair-clock cases,
initial pit/setup and other direct opponent callers, nonlocal exits, broader pause/epoch
changes, capacity/overload and mode transitions remain unproven. Repair/setup/presentation duration
itself is still frame dependent. No whole-game framerate independence claim follows from
these bounded checks.


### Matched initialization exposes the initial pit gap

`TIMING_WORLD_SEED` starts at timed flight entry, after native race initialization. It
therefore cannot make initial opponents identical. Native `$bad6` reseeds `$62(a6)` from
clock-low-word `$f98`, and `$e910` subsequently generates each opponent speed from that
stream. Different clock values can produce different starting speeds without proving a
simulation-timing defect.

The explicit development flag `TIMING_SETUP_SEED=54321` now supplies a controlled input
to native initialization. It seeds before initialization's random draws at `$b9a0` and
replaces the clock reseed at `$bad6`. The game still executes its original initialization,
random generator and speed arithmetic. It neither overwrites opponent records nor changes
the native later speed retunes. The flag defaults to -1 (disabled), requires VERIFY and
WORLD20, and remains behind CUSTOM3. Both hooks preserve X/other required registers and
replay complete displaced instructions. 010+ builds use the existing MOVE-CCR adaptation.
With the flag omitted, the entire prototype is byte-identical to the preceding checkpoint;
the normal build is also unchanged.

`OPPONENT_STATE=1` adds read-only snapshots of all four **190-byte** native opponent
records at selected checkpoints. `check_timing_setup.py` verifies one initialization and
reseed, the selected seed and native random arithmetic, then reports complete-record
differences at `$e976` (initial speed generation finished) and `$ca3e` (first world entry).
Use `--require-initial-equal` to assert the first checkpoint or `--require-equal` to require
both checkpoints. It normalizes only the
known absolute lap-start field `+$5c` against its constructor's `$206(a6)` epoch; it does
not silently omit other mismatches. `compare_timing_opponents.py` compares all four records
at matching fixture-relative 20-ms world times and fails on unequal records. Its explicit
`--report-only` mode is for describing a known failing regression, not declaring equivalence.

The final fixture `Powerdrome-timing-setup2.slave` reproduces matching native initialization
on 030 and A500: seed **54,321**, native speed baseline **533**, and four speeds
**489, 519, 522, 558**. All four complete records match at `$e976` after the documented
lap-epoch normalization. Before the first timed world update they differ:

| Checkpoint fact | 030/25 + fast renderer | A500, no fast RAM |
| --- | ---: | ---: |
| PAL fields from `$e976` to `$ca3e` | 357 | 845 |
| Nominal elapsed time | 7,140 ms | 16,900 ms |
| Opponent segments at first world entry | 7, 7, 7, 8 | 9, 9, 10, 10 |
| Opponent speeds at first world entry | 502, 544, 588, 517 | 502, 544, 588, 517 |

Every record differs at words `+$02`, `+$10`, `+$14`, `+$20`, `+$48`, `+$4e`, `+$68`.
The segment and X/Z differences are gameplay state, not merely a clock offset. This
localizes the loss of matching starting conditions to the interval before timed flight.
It does not prove that opponents moved at different rates over equal elapsed time: the
setup/pit windows themselves are different lengths. Initial pit updates still use the
native `$e3bc` caller while the continuous opponent timeline has not yet started.

Reproduce with the WORLD20 flags plus `-DTIMING_SETUP_SEED=54321`, `CUSTOM5=13`, 500 fields,
`TIMING_STATE=1 OPPONENT_STATE=1`, and ordered `PROBE_OFFSETS='0xb9a0 0xbade 0xe976 0xca3e'`.
Keep the usual `$bc7c` driving anchor/marker. Use live probes `$ccee $cde2 $cedc $d3de
$d56c $ced8 $d4bc $d504 $d7fe $d83c $d86c`. The current final-build 030 capture
`timing-setup2-030-twins` passes 501 consecutive world steps, 111 slow updates and 444
opponent movement samples with no outstanding time debt and **97 clean renderer comparisons**.
The completed `timing-setup2-a500-repeat` has 502 world steps and the same 111 slow updates
and 444 opponent samples, also with no outstanding time debt. All **501 common sampled
player/engine/RNG states match**. In contrast, the strict full-record comparator rejects
these runs: **all 501 common four-opponent snapshots differ**, beginning at fixture-relative
world time 20 ms. This is a reproduced initial-pit regression, not opponent equivalence.
The final artifact rebuilds exactly; default prototype and normal bytes remain unchanged.

### Initial pit opponent timeline

The WORLD20 prototype now starts the independent opponent timeline at the initial pit
call (`$bc3a`), before player simulation begins. It carries the same origin, phase, random
stream and residual into flight. Player controls, input queues and heat updates remain
inactive throughout this first pit visit. The first flight initializes those player
systems without resetting the already-running opponents. Normal builds are unchanged.

`timing-initialpit1-030-twins` (1,200 fields) and `timing-initialpit1-a500` (1,600 fields)
use the same frozen prototype, controlled initialization and `CUSTOM5=13`. Read-only
`TIMING_EARLY=1` diagnostics start at `$bc3a`, retaining `$bc7c` as the driving marker.
All **62 common complete four-opponent records**, at matching elapsed opponent deadlines
from 90 to 5,580 ms, agree after only the audited lap-epoch normalization. Their random
states also agree. This proves the sampled active-pit prefix, not the departure handoff
or whole-race trajectory equivalence.

| Initial-pit measurement | 030/25, fast-render twins | A500, no fast RAM |
| --- | ---: | ---: |
| Complete pit visit | 7,300 ms | 17,000 ms |
| External animation, first to last of 17 positions | 780 ms | 1,120 ms |
| External last position to cockpit routine entry | 560 ms | 5,200 ms |
| Cockpit routine entry to pit return (includes setup) | 1,120 ms | 1,380 ms |
| Unserved opponent time at pit return | 1,720 ms | 6,560 ms |
| First world batch serves / retains | 1,710 / 10 ms | 2,880 / 3,680 ms |
| Capped world allocations while draining departure tail | 0 | 2 |
| Final completed-world residual | 20 ms | 80 ms |

The A500 retains 820 ms after its second capped allocation and drains the remaining
whole updates in its third allocation. `check_timing_initial_pit.py` verifies every
allocation against the production limit of 32 updates, exact elapsed-time conservation,
unchanged origin/phase, private random ownership and eventual removal of whole-step debt.
It checks 464/1,420 modal/total movement samples and 40/748 pit/flight ownership restores
on A500; the 030 counts are 248/1,064 and 40/834. The 030 also passes **192 renderer
comparisons**, with no pixel, scratch, register or guard failures and unchanged raster code.
These heavily instrumented captures are not performance benchmarks.

**Retune boundary under validation:** `$14090` calls the native opponent-speed retune
`$e8d4`, before `$1409a` enters cockpit departure. The initial-pit prototype originally
served the deferred tail in first flight, allowing historical updates to use the later
speed. The experimental `timing_retune.s` now captures a fixed unpaused cutoff at this
boundary, drains all whole opponent updates through that cutoff with the old speeds,
and then runs the native retune. Time spent doing the drain remains for subsequent
allocations; no opponent time is discarded. Player updates remain inactive.

The final `timing-retune4-030-twins` (1,200 fields) and `timing-retune4-a500`
(1,600 fields) use the same ordinary prototype with result injection disabled.

| Retune and handoff measurement | 030/25, renderer twins | A500, no fast RAM |
| --- | ---: | ---: |
| Old-speed updates drained before retune | 6 / 540 ms | 57 / 5,130 ms |
| Fixed cutoff since pit entry | 6,180 ms | 15,620 ms |
| Residual at retune | 60 ms | 50 ms |
| Remaining tail at pit return | 1,200 ms | 1,510 ms |
| First flight serves / retains | 1,170 / 30 ms | 1,440 / 70 ms |
| Final completed-world residual | 40 ms | 30 ms |
| Modal / total movement samples | 272 / 1,064 | 692 / 1,420 |
| Pit / flight ownership restores | 40 / 834 | 40 / 746 |

On both CPUs, speeds change from **489, 519, 522, 558** to **567, 617, 553, 594**.
The checker verifies every drained full record, restored caller registers and native
stack depth, outer random/counter ownership, and that the native retune changes only
record speed words using its four original random draws. All **68 common complete
four-opponent snapshots**, through 6,120 ms, and their random states match. Neither
first-flight allocation reaches its 32-update cap. The 030 passes **192 renderer
comparisons**, with unchanged raster code and no pixel, scratch, register or guard
failures. These instrumented captures establish the bounded initial-pit boundary and
handoff, not a throughput benchmark or whole-game equivalence.

The retune state occupies 44 static bytes; it makes no new allocation and does not
change the requested memory or cache policy. The ordinary seeded coverage prototype is
23,256 bytes, 476 more than the initial-pit predecessor. Each explicit result-test variant
is 23,340 bytes. All three final artifacts rebuild byte-identically, and the normal slave
remains byte-identical. An attempted non-VERIFY result-test build is rejected.

Condition codes use guest-side input/output samples in VERIFY builds. As already observed
for the movement wrapper, the 030 debugger SR can be stale. A focused instruction-step
check found the saved word unchanged (20) across the drain although the initial debugger
snapshot reported 8. The direct guest samples agree; `check_timing_retune.py` requires
those samples rather than treating debugger SR equality as a flag oracle.

The new helper also intercepts the native `$d606` race-result decision during its drain.
`$14008` has already cleared `state+$da`, so the original `$d616` path would unwind eight
bytes from an incompatible pit-helper stack. The prototype records the first winner and
delivers it from the flat pit-return context, removing the ordinary world return slot only
for rescue visits. The current revision returns immediately from the winning native
opponent body, restores counter/random ownership, and retires all assigned and unassigned
remaining work explicitly. A partial update is not counted as completed. No later
opponents are processed after the winner.

`TIMING_RETUNE_RESULT_TEST=1/2` is an explicit VERIFY-only outcome fixture for the initial
or rescue boundary. It injects the native winning decision at opponent movement entry;
it does not prove natural lap detection or final ranking arithmetic. Values outside 0–2,
non-VERIFY builds, and builds without WORLD20 are rejected. The default is zero and has
no result-injection patch.

`timing-retune4-initial-result-030` completes 1,000 fields. Exactly one winner is delivered
at the initial pit return, with the expected native result stack depth (four bytes above
native pit entry). **Six assigned updates, including the interrupted one, plus 60 ms of
unassigned time** are explicitly retired. The checker proves that no later opponent
moves, the partial update is not counted complete, caller flags and counter/random
ownership are restored, and the result gate clears pending modal ownership. Native
session cleanup at `$c2aa` and later setup at `$e8d4` are reached with opponent ownership
cleared. At field 639, fresh driving initializes both player and opponent clocks: one
first opponent update, zero inherited debt and a new origin. Mode snapshots confirm a
transition from qualifying (`state+$c0=$ffff`) to an ordinary race (`+$c0=0`, with
`+$b6/+$be/+$c4/+$c8=0`). Its **52 renderer comparisons**
pass with unchanged raster code and zero reported mismatches.

`timing-retune4-rescue-result-030` completes 6,000 fields. The injected rescue result also
stops after the first winning body and enters native results at the correct stack depth:
eight bytes above the native rescue-pit entry, including removal of the world-call return.
It retires **six assigned updates plus 80 ms unassigned time**, restores guest flags and
counter/random ownership, clears modal/input/engine ownership, and reaches native cleanup
and a fresh ordinary race with new player/opponent clocks and no inherited debt. Its
**437 renderer comparisons** pass without reported mismatches or copied-code changes.
Both forced-outcome tests therefore pass their bounded control-flow/cleanup checks. They
still do not prove natural race finishing, final standings or result-duration correctness.
The ordinary initial-pit CPU pair also passes on this revision. Ordinary rescue handoff,
pause and session-lifecycle regressions remain; an injected result does not exercise a
normal rescue return.

```sh
python3 tools/check_timing_retune_result.py tmp/prof/timing-retune4-initial-result-030
python3 tools/check_timing_retune_result.py --rescue tmp/prof/timing-retune4-rescue-result-030
```

### Retune revision lifecycle regressions

The final ordinary `timing-retune4-rescue-030-twins` completes 5,000 fields with result
injection disabled. Rescue return preserves 1,049 completed opponent updates, phase 1,050
and 50 ms residual. The next allocation accounts for 80 ms elapsed after return:
**80 + 50 = 90 ms served + 40 ms retained**. The checker verifies 4,444 scheduled opponent
movement samples (572 after return), 682 modal ownership restores, 1,691 world counter
restores (642 after return), and 16 samples each of the logical lap-gate and lap-duration
clocks. The rescue retune drains six old-speed updates (540 ms), retains 10 ms, and changes
speeds from 567/617/553/594 to 622/549/603/508 with the original native random arithmetic.
There are **414 clean renderer comparisons**, with unchanged raster code.

The final `timing-retune4-pause-030-twins` excludes **50 paused PAL fields**, accounts for
all five input events, and checks 254 consecutive 20-ms movement steps, 56 rational 90-ms
slow updates and 224 opponent reads. It finishes with zero allocator debt, unfinished
assigned steps or pending started controls. All **76 renderer comparisons** pass, with
unchanged raster code. The final `timing-retune4-sessions-030-twins` completes 1,800
fields, verifies two native closures and two fresh gameplay entries, and checks six
inactive menu/pit probes. No assigned steps, allocator debt, inputs or engine events are
left to discard at those two sampled boundaries. It adds **232 clean renderer comparisons**
with unchanged code. These results do not replace wider A500/mode/CPU validation.

### Natural result timing and ranking gate

The forced winner proves an exit decision and its call-stack handling, not a natural
finish. The `CUSTOM5=13` Race-menu fixture initially enters **qualifying**, not the race
itself: `state+$c0=$ffff`, and the natural lap-target winning decision is disabled by
that flag. The injected outcome tests qualifying cleanup followed by race setup. A
separate natural race-finish fixture is required for the ranking/duration branches. Native `$d7f2` first requires at least 400 clock units since the opponent lap
start; it then advances the lap count at record `+$22`, compares the race target at
`state+$266`, and checks that ending animation is not already active (`state+$e6`).
The body updates lap-start/best-lap fields and, for the ordinary race mode, resets track
progress before returning the winning decision. The injected movement-entry outcome
intentionally bypasses these mutations. Its delivered opponent id alone cannot establish
that the race standings identify the same winner.

The native result path calls `$f5a6` at `$c0a2`. That routine sorts the linked pilot list
headed by `state+$33c` using lap/segment comparisons, with separate repair branches at `$f5d6` and `$f5ec`.
The native second repair branch at `$f5f2` adds `state+$280` to `d0`, not `d1`; preserve
and test the actual instructions rather than assuming a symmetric abstract sort key. Links are record `+$28` / `+$2c`. In the ordinary human race, the five-node list contains
opponents 1–4 and player 0 at **state-relative `$11c`** (hunk `$b8a`); its segment and
lap words are therefore `state+$11e` and `state+$13e`. The current complete opponent
capture omits this player node. `state+$346` is a separate optional pilot pointer used
by other modes and is zero in the observed human race; it must not be used to locate
the human player record. Sorting retains the existing order for equal scores. `$c164` then takes
the first record id as the result winner. A natural-finish test must therefore capture
the player record as well as all four opponents, audit the complete linked order, and
compare lap/progress mutations and the resulting winner. Four opponent arrays alone do
not cover this gate.

Result duration also has a separate clock boundary. `$c094` reads physical `$f96` and
subtracts `state+$22e` in one result mode. Other mode branches read `$f96` at `$c240`,
`$c250` and `$c266` for result waiting and elapsed-time accounting. Deferring a historical
win through cockpit departure can let additional physical time enter the reported race
duration, even with correct opponent movement and stack delivery. Audit the mode flags
and capture the logical winning deadline alongside these reads. Use logical event time
for race-duration accounting; keep actual display/input waits on the physical clock.
`tools/check_pilot_list.py` now validates the five-node topology, reciprocal links,
mode-specific bank and record ids in the captured dumps. Its optional sorted check must
only be used at an audited native sort-completion point. `tools/check_natural_result.py`
uses ordered `$c094`, `$c09e` and `$c0a6` snapshots to compare the committed
race duration with the logical winning instant while checking all five sorted records.
`--require-logical-time` additionally requires exact duration, preserved caller registers
and stack, native MOVE.L flags, and cleared result-clock ownership after cleanup.

The baseline natural runs now reach an unforced ten-lap finish with all five reciprocal
pilot links and the native sorted comparisons intact. `timing-retune4-natural-result-030`
reports **215,140 ms** for a logical winning duration of **215,120 ms** (**+20 ms**), with
opponent 2 winning. `timing-retune4-natural-result-a500` reports **227,960 ms** versus
**227,920 ms** (**+40 ms**), with opponent 4 winning. These are independent result-clock
observations, not trajectory equivalence: the winners and complete starting histories
are not established as matching across CPUs. The 030 reaches the result with 2,415
cumulative renderer twins and no reported failures; the 200-field result window adds
no staged scenes. Do not count those cumulative twins as new window comparisons.

The experimental `timing_result.s` latches an active opponent or deferred pit opponent
winning instant before ownership cleanup, and supplies it only to the ordinary duration
read at `$c094`. Each opponent step now records its stable lap-domain instant in
`PDLAP001+$28` before native execution; the result latch uses that saved instant even
when a retune winner is delivered later. Repair/native-clock sampling remains separate.
The stable epoch follows the shared countdown reset, so lap and race durations share
the same start mapping rather than repeatedly sampling the native/VBL offset. Unclassified sources still use the native physical value. The 64-byte
result state clears its ownership flags at native session cleanup; the helper reproduces MOVE.L flags,
including X preservation, and records guest flags for verification. The global native
clock and display/input waits are unchanged. The corrected 030 natural finish
(`timing-resultclock1-natural-030`) reports **215,020 ms**, exactly its logical winning
duration, while the native physical read is **60 ms later**. All five sorted pilot
records, preserved caller registers/stack, MOVE.L flags and cleared ownership at cleanup
pass the strict checker. Its 200-field result window contains no new staged scenes;
2,391 cumulative clean twins are not additional window comparisons. The corrected A500
run (`timing-resultclock1-natural-a500`) reports **227,920 ms**, exactly its logical
winning duration, while the physical read is **40 ms later**. It passes the same strict
clock, five-pilot ordering, register/flag and cleanup checks. These CPU runs have different
winners and do not establish cross-CPU trajectory equivalence. Player-originated finishes,
other result modes and deferred-pit duration still need explicit validation. The normal
build remains byte-identical.

The current stable-domain prototype's unforced 030 run
`timing-resultdomain1-natural-030` reports **215,060 ms**, exactly the logical winning
duration, with opponent 2 reaching ten laps. At that instant, the sampled native mapping
is 60 ms ahead of the stable lap mapping and the physical duration read is 100 ms ahead.
The stricter `--require-stable-domain` gate verifies the shared countdown start, the
winning-step latch, all five ranked records, preserved registers/stack, guest MOVE.L
flags and cleared result ownership. There are 2,408 cumulative completed renderer twins
with no failures; the 200-field result window adds zero staged scenes. This is not a
performance measurement. The matching A500 run `timing-resultdomain1-natural-a500`
reports **226,290 ms**, exactly the logical winning duration, with opponent 1 reaching
ten laps. Its sampled native mapping is 120 ms behind the stable lap mapping; the
physical duration read is 90 ms behind. The same strict ranking, register/stack,
guest-flag and cleanup checks pass. A negative physical-clock offset is a difference
between the clock mappings, not a negative race duration. Different winners and event
histories mean these runs do not establish trajectory equivalence. Player, deferred-pit
and other mode-specific result durations remain open.

```sh
python3 tools/check_natural_result.py --require-stable-domain tmp/prof/timing-resultdomain1-natural-030 tmp/prof/timing-resultdomain1-natural-a500
```

The next player-result correction must account for the complete native clock path:

1. `$f7ae` calls `$f952` when player movement wraps the track segment range. `$f974`
   invokes the lap-accounting helper `$10bec` before checking the winning lap.
2. `$10bf0` reads the physical clock; `$10bf8–$10c0c` subtract and replace lap-start
   `$206`, then commit lap duration `$202`. `$f9a2` reads that duration for the lap table
   and accumulated total. The helper also updates best-lap state and lap frame counters.
3. `$f9ec–$f9f0` supplies the player-result sentinel and enters `$bfb0` after native
   stack unwinding. The player-result hook now captures a classified logical winning
   instant here; opponent-result tests do not validate this separate source.
4. The cockpit timer independently reads the physical clock at `$f108` and subtracts
   `$206` at `$f110`. Moving player lap-start timestamps into a logical domain without
   updating this consumer would mix domains in the displayed lap timer.
5. `$b796` is another direct caller of `$10bec`, outside the ordinary player-lap caller.
   State `$206` also serves other modes and waits. Gate any logical substitution by an
   audited lifecycle/domain contract; do not globally replace this shared timestamp.

A read-only 030 baseline, `timing-player-clock-before-030`, captures 300 PAL fields
from the first natural `$f952` crossing with `CUSTOM5=13` and the frozen resultdomain1
prototype. The player has lap index -1 at entry, the scheduler is started, and world
ownership is active. The native helper reads clock 6,148, subtracts the old start 976,
and stores the new clock; the negative-lap branch correctly discards that preliminary
duration. Lap index then becomes zero, with lap duration and accumulated total still zero.
These values are five-millisecond native clock units, not addresses.

All 118 sampled cockpit clock-read pairs use the physical clock and that unchanged lap
start. Physical elapsed minus elapsed retained-world time ranges from **-20 to +680 ms**,
ending at zero. The retained world timestamp is the scheduler cursor; outside a world
step it can point at the next step, so the -20-ms endpoint is not evidence of a reversed
clock. Positive differences expose display/clock versus simulation progress, and require
an explicit display-time contract. This baseline covers first-lap initialization and
HUD reads, not a completed player lap, finish, or correction.

```sh
python3 tools/check_player_lap_baseline.py tmp/prof/timing-player-clock-before-030
```

The WORLD20 prototype now includes `timing_player_lap.s`, with a private logical
lap-start timestamp and a copy of the associated native physical start. Hooks at
`$10bf8` and `$f110` select logical lap/HUD elapsed time while retaining the physical
clock in D7 and native `$206`. They replay the displaced native subtraction first,
preserve its X flag, and reproduce the final native MOVE flags. The private timestamp
starts at the natural first crossing or shared countdown reset; session cleanup and
new initial-pit entry invalidate it. The HUD uses the last completed world-step time
(the retained next-step cursor minus 20 ms outside active world ownership), clamped to
zero immediately after a reset. It does not display accumulated unserved simulation debt.

If a native writer unexpectedly changes `$206`, the HUD invalidates the private timestamp.
Lap accounting retains the native duration for that boundary and establishes a new private
start. Unsupported non-driving or nonhuman lap-helper calls invalidate the private state
and preserve native behavior. These fallbacks prevent accidental clock-domain mixing;
they do not establish framerate independence for those unaudited paths.

The frozen `Powerdrome-timing-playerlap1.slave` passes matching 300-field first-crossing
captures on 030/25 and A500, with native rendering on A500 and fast rendering on 030:

| Capture | Exact logical HUD outputs | Physical minus retained-world elapsed | Native reset fallbacks |
| --- | ---: | --- | ---: |
| `timing-player-clock-after-030` | 118 | -20..680 ms; final 0 ms | 0 |
| `timing-player-clock-after-a500` | 37 | -60..1,580 ms; final 1,500 ms | 0 |

Both preserve the native shared start, private logical start, zero initial lap duration
and accumulated total. These heavily instrumented captures are not FPS measurements.
The A500 clock/simulation-progress gap remains visible in the audit; displaying logical
progress does not fix simulation backlog or prove adequate real-time throughput.
Completed player-lap accounting is implemented but **not exercised by these captures**.
Pause/rescue, native-reset fallback, guest-observed lap/HUD flags/registers and natural
player finishes still need explicit tests. Practice initialization and a directed
player-result test are described below. The normal slave remains byte-identical and
all new hook ranges pass the structural boundary/branch audit.

```sh
python3 tools/check_player_lap_baseline.py --logical tmp/prof/timing-player-clock-after-030
python3 tools/check_player_lap_baseline.py --logical tmp/prof/timing-player-clock-after-a500
```

The corrected probes replace displaced `$10bfc` with post-hook `$10c00`, and add `$f118`
after the HUD hook. `timing-player-clock-practice-030` uses the same frozen playerlap1
prototype with `CUSTOM5=2`. Its 182 logical HUD outputs pass, with an explicitly
uninitialized opponent timeline, unchanged native/private starts and no reset fallback.
The physical-minus-retained-world gap is -60..120 ms, ending at -40 ms. This proves
Practice initialization/HUD independence from opponents, not completed Practice laps.

```sh
python3 tools/check_player_lap_baseline.py --logical --practice tmp/prof/timing-player-clock-practice-030
```

### Player lap/HUD hook register and flag contracts

VERIFY-only `PDPLC001` diagnostics record the physical subtraction's guest CCR and result,
its native clock/start operands, the final displaced MOVE's guest CCR, and separate lap
and HUD call counts. The observation helper preserves A0 and CCR; 68010+ installation
substitutes the user-mode CCR read, as for the existing timing diagnostics. This does not
change normal-build bytes. The `PDPLAP01` layout remains unchanged.

`timing-playercontract1-030-twins` uses the frozen playercontract1 slave, the ordinary
`CUSTOM5=13` route, 300 fields from `$f952`, and probes `$10bf8/$10c00/$f110/$f118`.
`check_player_lap_contract.py` independently computes subtraction flags from the original
operands, verifies final native MOVE flags, and compares all D0–D7/A0–A6 registers and SP
across each hook, allowing only the specified logical D0 result and HUD D1 low word.
It ignores debugger SR and reads architectural condition codes recorded by guest code.

The 030 run passes **one initial lap hook and 75 HUD hooks**, with native shared timestamp
semantics intact. It adds **39** completed clean renderer comparisons, with one further
scene active at the end. This initial boundary establishes the lap origin and deliberately
keeps its physical subtraction result; it does **not** exercise a completed logical lap
duration. The A500 counterpart `timing-playercontract1-a500` passes the same initial
boundary and **37 HUD hooks**, including guest flags and all register/stack checks.
Hook boundaries pass and the normal slave is byte-identical to the reference.

The natural completed-lap capture first observes `$f952` and post-hook `$10c00`, then
anchors at the next `$f952` (`PROBE_OFFSETS='0xf952 0x10c00'`). The 300-field 030 run
`timing-playercontract1-natural-030-twins` passes **one logical-duration lap hook and
82 HUD hooks**, plus **73** completed clean renderer comparisons. The duration is
**92,220 ms**; the following HUD sample confirms matching native lap duration, total,
best time and lap index. `--natural-completed-lap` requires all these observations and
native bytes at the three synthetic boundary/checkpoint/finish predicate sites. It
correctly rejects the initial-boundary-only capture. The A500 counterpart
`timing-playercontract1-natural-a500` passes one completed logical lap of **128,380 ms**,
its committed native records and **55 HUD hooks**, including registers, stack and guest
flags. This diagnostic run's observed duration differs from the earlier rescue capture;
the checks prove internal accounting, not identical trajectories or instrument-free speed.
External-reset fallback, other modes and unobserved arithmetic/flag cases remain open.

```sh
python3 tools/check_player_lap_contract.py tmp/prof/timing-playercontract1-030-twins
python3 tools/perf_status.py tmp/prof/timing-playercontract1-030-twins
python3 tools/check_player_lap_contract.py tmp/prof/timing-playercontract1-a500
python3 tools/check_player_lap_contract.py --natural-completed-lap tmp/prof/timing-playercontract1-natural-030-twins
python3 tools/perf_status.py tmp/prof/timing-playercontract1-natural-030-twins
python3 tools/check_player_lap_contract.py --natural-completed-lap tmp/prof/timing-playercontract1-natural-a500
```

### Player-result timestamp and directed validation

The WORLD20 hook at `$f9ec` captures the current player's logical world timestamp after
native stack unwinding but before `$bfb0` restores ownership. It requires active player
world timing, an initialized opponent timeline, ordinary human race mode and a recorded
shared countdown reset. It translates the world instant through that stable lap/race
epoch, then replays the native player sentinel and result branch. Result entry consumes
the pending timestamp as source 3, distinct from active/deferred opponents; session
cleanup clears both pending and active result ownership. Unclassified paths keep their
native result clock. This supports the ordinary race clock contract; it does not use an
opponent's most recent step as a player's winning instant.

The explicit `TIMING_PLAYER_RESULT_TEST=1` fixture requires VERIFY, COVERAGE_INPUT and
WORLD20. Separate negative builds reject omission of each guard with its intended
assembler error; the normal build is restored byte-identically afterward. After at least 500 ms of logical post-countdown time, it forces three counted
native decisions: admission to a lap boundary at `$f7a0`, admission past the checkpoint
predicate at `$f96c`, and the finish decision at `$f9d8`. It calls native `$f952` with its
original caller stack; native code performs the lap-record mutations and result unwind.
The no-input route's player is stationary after countdown, so waiting for a real later
boundary would not exercise this path. The fixture is disabled by default; explicit zero
and omission build byte-identically. It is not evidence of a naturally completed lap,
winning rank or player victory.

`timing-playerresult4-forced-030-complete`, using the frozen playerresult4-forced slave,
passes a 200-field result/cleanup window. Synthetic lap duration, native accumulated
player total and final reported duration all equal **500 ms**. One player source is
consumed, native sentinel/registers/stack depth survive the entry hook, duration-read
guest flags match, all five pilot records pass native sorting, and ownership clears at
cleanup. There are 79 cumulative clean renderer twins; the result window adds zero
staged scenes. The normal slave remains byte-identical and hook boundaries pass.

```sh
python3 tools/check_player_result.py tmp/prof/timing-playerresult4-forced-030-complete
```

The A500 counterpart `timing-playerresult4-forced-a500` passes the same directed
500-ms lap/accumulated/result-duration checks, source-3 consumption, sentinel/registers,
stack depth, duration flags, five-pilot sorting and cleanup. This closes the bounded
CPU pair for the synthetic branch, not natural player-victory coverage.

```sh
python3 tools/check_player_result.py tmp/prof/timing-playerresult4-forced-a500
```

### Initialized player lap clock through pause

The input-only `CUSTOM5=14` fixture selects Practice and waits for the native lap index
to become nonnegative. It then schedules native pause/resume keys 160/210 PAL fields
from that observed first-lap start, without early throttle/braking or writes to simulation
state. This event-relative start matters: the existing `CUSTOM5=8` pause can occur before
the private lap clock initializes, so its passing scheduler checks alone do not validate
private-lap preservation. Its current regression still passes 50 excluded fields, five
input events and exact remainder accounting, with 75 new clean renderer comparisons.

`timing-playerpause2-030-twins` uses the frozen playerpause2 normal timing prototype,
`CUSTOM1=1 CUSTOM3=1 CUSTOM4=1 CUSTOM5=14 NoCache`, 300 fields anchored at `$f952`, driving
marker `$bc7c`, and the normal pause probes plus `$f118/$f10e/$f9a2`. The measured native
pause excludes **49 PAL fields**. Private logical and native physical lap starts, logical
world/input clocks and lap-accounting state remain unchanged across it. All **70** observed
logical HUD outputs, including **26 after resume**, equal elapsed completed-world time;
there is no native-reset fallback and the input queues drain without overflow. The run
adds **61** completed clean renderer comparisons, with one further scene active at capture
end. These instrumented counts are correctness evidence, not a performance measurement.

```sh
python3 tools/check_player_lap_pause.py tmp/prof/timing-playerpause2-030-twins
python3 tools/perf_status.py tmp/prof/timing-playerpause2-030-twins
```

Read-only `PDPLAP_EVENT` probes expose validity, both lap starts, reset/lap/HUD counters,
last durations and fallback count at the pause boundaries and HUD output. The checker
requires an initialized lap at pause entry; it does not relax that condition for routes
that have not reached the first crossing. The A500 counterpart
`timing-playerpause2-a500` uses the same frozen slave and 300-field route, with no fast
RAM and verification rendering disabled. It excludes **47 PAL fields**, preserves both
lap starts and logical clocks, and passes **53** exact HUD readings (**16 after resume**)
with no reset fallback or input overflow.

```sh
python3 tools/check_player_lap_pause.py tmp/prof/timing-playerpause2-a500
```

The 030 and A500 rescue/natural-lap checks below pass. External-reset fallback,
other natural laps and natural player results remain open.

### Player lap clock through rescue and a natural completed lap

`timing-playerlap-rescue-030-twins` uses the frozen playerpause2 prototype with
`CUSTOM1=1 CUSTOM3=1 CUSTOM4=1 CUSTOM5=13 NoCache`. It captures 5,000 PAL fields
from the first natural `$f952` boundary, with read-only private/player clock probes at
`$c7d2`, `$e3bc/$e3c4`, `$ce28`, `$10c00` and `$f118`. The native rescue is accepted
at field 456 and the pit returns at field 4,333. The measured pit interval is **67,520 ms**;
1,364 inactive pit observations preserve both private logical and native physical lap
starts. The resumed player clock includes the pit interval rather than excluding it.

All **437** active logical HUD outputs pass, including **179 after return**, with no
external-reset fallback. The run reaches a natural completed player lap at field 4,608:
its logical duration is **92,220 ms**, and the following HUD observation confirms the
native lap duration, accumulated total, best time and lap index. The checker verifies
that all three synthetic boundary/checkpoint/finish predicate sites retain native bytes;
this is not the forced-result fixture. It also checks 32 opponent lap-clock reads against
an unchanged stable lap epoch. There are **394** new completed clean renderer comparisons,
no pending scene at the end, and unchanged raster code. These are instrumented correctness
observations, not an FPS measurement or a matched-trajectory comparison.

```sh
python3 tools/check_player_lap_rescue.py tmp/prof/timing-playerlap-rescue-030-twins
python3 tools/perf_status.py tmp/prof/timing-playerlap-rescue-030-twins
```

The checker distinguishes a legitimate observed lap boundary from an unexpected timestamp
reset: it verifies logical subtraction and native timestamp storage at `$10c00`, followed
by native duration/total/best/index accounting at `$f118`. It requires terminal snapshots
and an unchanged opponent epoch; captures with a countdown reset need separate reset
observations. The A500 counterpart `timing-playerlap-rescue-a500`, using the same frozen
slave without fast RAM or twin rendering, captures 8,000 fields. Rescue returns at field
6,132 after **103,540 ms** in the pit. Both lap origins survive 1,364 inactive pit
observations; **556** logical HUD readings pass, including **404 after return**. A natural
lap at field 6,407 records **128,300 ms**, with matching total, best time and lap index.
All 52 sampled opponent lap reads use the stable domain, with no external-reset fallback.

The full opponent continuity check also passes on A500: 1,651 updates are complete at pit
return with 30 ms residual. The first resumed allocation accounts for 120 ms after that
cutoff plus the residual as 90 ms served and 60 ms retained. There are 7,116 movement
samples (1,656 after return), 682 pit counter/RNG restores and 2,819 world restores
(1,860 after return). Different pit and lap durations across CPUs mean these are bounded
accounting/lifecycle checks, not matched-event-history or real-time throughput evidence.

```sh
python3 tools/check_player_lap_rescue.py tmp/prof/timing-playerlap-rescue-a500
python3 tools/check_timing_opponent_continuity.py --stable-lap-domain tmp/prof/timing-playerlap-rescue-a500
```

Additional natural laps and modes, external-reset fallback and natural player victory
remain unverified.

The read-only capture locator now uses the installed frame JMP to find live session
metadata in early captures: added helpers had put PDSESS01 exactly 4,096 bytes before
WORLD20, outside the former strict proximity test. The completed fixture includes the
cleanup evidence that the earlier aborted capture lacked. Wider non-forced regressions,
natural player laps/results and lifecycle coverage remain open.

Implement and test player lap storage, displayed elapsed time and final-result latching
as one consistent contract. Practice has no initialized opponent timeline, so it needs
an explicit player-clock origin rather than borrowing an absent opponent origin. Validate
ordinary race, Practice, pause/rescue and the non-driving helper caller, with natural
lap progression and a separately labelled forced-finish fixture if needed. A forced branch
alone cannot prove natural winning rank or race duration.

The earlier sampled-domain opponent-result correction was validated on this CPU pair. Broader
**result-clock** work remains open: do not infer player/deferred-pit/mode coverage from
these runs or freeze the shared native clock to hide discrepancies. Recheck this pair with:

```sh
python3 tools/check_natural_result.py --require-logical-time tmp/prof/timing-resultclock1-natural-030 tmp/prof/timing-resultclock1-natural-a500
```

The extended `compare_timing_opponents.py --through-departure` gate now samples every
completed four-opponent body from pit entry into flight. It requires consistent
opponent deadline/completion counts and at least 30 shared deadlines after **both**
pit exits. It still normalizes only the audited lap-start epoch; speed, positions,
rendering scratch and random state remain visible. It does not cover the player record.

For the paced `timing-external2-initial-030-twins` / `timing-external2-initial-a500`
pair, **72** complete snapshots at 90–6,480 ms match, including RNG. Across the longer
90–23,940-ms window, **194 of 266** snapshots differ and **151** have different RNG;
93 shared snapshots occur after both CPUs enter flight. The first difference is at
**6,570 ms**, immediately after the 030 retune cutoff (6,480 ms), while A500 does not
retune until 15,620 ms. Speed words differ for all four opponents at that first mismatch,
alongside movement and scratch fields. Thus event histories are demonstrably unequal;
these runs cannot prove whole-trajectory equivalence. The result does not establish
that retune timing explains every later difference. A controlled matching-event run is
still required to separate history differences from simulation defects.

Use `--report-only` to inspect this known mismatch; without it the extended gate fails.
The earlier prefix-only check continues to pass and must not be cited as whole-departure
coverage:

```sh
python3 tools/compare_timing_opponents.py --initial-pit tmp/prof/timing-external2-initial-030-twins tmp/prof/timing-external2-initial-a500
python3 tools/compare_timing_opponents.py --through-departure --report-only tmp/prof/timing-external2-initial-030-twins tmp/prof/timing-external2-initial-a500
```

The matching-event experiment is `TIMING_PIT_SYNC_TEST=1`, which requires VERIFY,
COVERAGE_INPUT and WORLD20. It delays only the initial-pit retune and return until
18,000 and 24,000 ms after pit entry. It does not rewrite records, seeds, counters,
logical cursors or physical time. Existing catch-up code accounts for the wait. Actual
arrival/release times are recorded in `PDSYNC01`, and `check_timing_sync.py` requires
exact release times plus agreement with the real retune cutoff and pit-exit clock.
A late arrival fails the check. This is a **test-only causal experiment**, not a proposed
production loading policy and not proof that the unsynchronized route is equivalent.

The disabled fixture rebuilds byte-identically to `timing-external2`; the normal slave
also remains byte-identical, and a non-VERIFY build rejects the flag. The synchronized
030 capture `timing-sync1-initial-030-twins` arrives at retune at 6,480 ms and releases
at exactly 18,000 ms; it arrives at return at 19,180 ms and releases at 24,000 ms.
It drains 134 old-speed updates (12,060 ms) before retuning, with zero residual.
At first flight, the 6,000-ms tail serves 2,880 ms and retains 3,120 ms; two capped
allocations are needed before only fractional debt remains. Final residual is 10 ms.
All ownership/register/flag/native-RNG checks pass, as do **64 completed renderer
comparisons**. The A500 counterpart `timing-sync1-initial-a500` arrives at retune at
15,620 ms and at return at 19,480 ms, releasing at the same exact **18,000 / 24,000 ms**
boundaries. It drains 84 old-speed updates (7,560 ms), with zero residual, and has the
same first-flight 2,880-ms service / 3,120-ms retained tail. Its final residual is 40 ms.
Both CPUs pass the synchronization, ownership, native speed-mutation and time-conservation
checks. These artificial waits are not included in ordinary gameplay or performance claims.

The synchronized comparison covers **336** common snapshots at 90–30,240 ms, including
136 after both pit exits. **All random states agree.** The first 254 complete four-opponent snapshots
agree; **82 later snapshots differ**. The first difference, at **22,950 ms**, is opponent
4’s lap-start and best-lap values (`+$5c` / `+$60`, differing low words `+$5e` / `+$62`).
The normalized values are 4,598 versus 5,114 clock units: a **2,580-ms** discrepancy,
despite identical logical movement deadlines. The current code repeatedly derives its
native-epoch offset from physical `$f96` minus unpaused VBL time. This offset changes
through the run, so logical lap reads are not in one stable elapsed-time domain. The
first active sample puts the pit epoch 40 ms after setup on 030 versus 1,080 ms on A500;
later epoch drift adds to that initial difference. The cause of the changing physical/VBL
offset is not yet established. Do not assume all of it is ordinary loading time, and
do not subtract a measured constant from reported results as a fix.

From **25,650 ms**, non-clock differences appear at record `+$36`, `+$38`, `+$3e` and
`+$54`; `+$3c` first differs at 26,550 ms. The only differing words in the whole paired
window are `$36/$38/$3c/$3e/$54/$5e/$62`. Movement-record fields and RNG therefore
remain equal in these sampled bodies, but complete-state equivalence still fails.
The native opponent drawing path calls `$9950` at `$11228`, conditionally for opponents
selected by the visible track range. `$999a–$9a04` advances persistent animation offsets
`+$36..+$3a`, increments/stores age `+$3e`, and clears active `+$3c` at its limit.
This is a confirmed render-driven mutation that must be separated from presentation.
`+$54` is also written by projection/model-selection code (`$a142/$a26e/$1162e`) and
read by drawing (`$11644`); its complete ownership still needs audit before classification
as harmless rendering scratch.

The lap-clock prototype now separates `$d7f8/$d836/$d866` from the repair-clock reads.
`timing_lap.s` captures native `state+$206` when a new opponent timeline starts, preserving
the epoch used by the native initial lap stamps at `$babe/$bbf4`. Active lap reads return
that fixed epoch plus the elapsed opponent deadline; they no longer add the repeatedly
sampled physical/VBL offset. Reads outside an active scheduled opponent body retain the
native physical value. No position, speed, random state or global clock is rewritten.
The wrapper restores X and reproduces native MOVE.L NZVC; 010+ uses the established
MOVE-CCR substitution. Its 24-byte `PDLAP001` diagnostic records the epoch, read count,
last clock and guest flags.

`timing-lapclock1-initial-030-twins` passes four minimum-interval and four lap-duration
reads at exact logical deadlines, with the native guest flags. The synchronization,
initial-pit and retune checks still pass, and 64 completed renderer comparisons report
no failures. `timing-lapclock1-initial-a500` passes the same eight clock reads, flags,
synchronization, initial-pit and retune checks. Across the paired **336** snapshots,
all lap timestamps and durations now agree, as does RNG. The remaining **39** differing
snapshots first diverge at **25,650 ms** and contain only `$36/$38/$3c/$3e/$54` differences.
No clock differences are normalized away: the comparison still subtracts only the
native setup epoch from absolute lap stamps and directly compares best-lap durations.
Normal-build bytes remain unchanged.

```sh
python3 tools/check_timing_lap.py tmp/prof/timing-lapclock1-initial-030-twins tmp/prof/timing-lapclock1-initial-a500
python3 tools/compare_timing_opponents.py --through-departure --report-only tmp/prof/timing-lapclock1-initial-030-twins tmp/prof/timing-lapclock1-initial-a500
```

This does **not** close the clock-domain audit. A separate native producer at `$dbe8`
resets each linked pilot's lap stamp from `state+$206` after the mode path clears result
flags; it is reached for `state+$43a >= 7`, after blocking presentation and input work.
It requires an explicit logical reset/rebase contract and a runtime test before this
feature can cover that mode. Pause, rescue, saved-state clock restores, native time
adjustments, first-flight paths without an initial pit and total race-result clocks
remain separate required checks. The cause of physical/VBL offset drift also needs a
measurement against hardware field time rather than assuming the interrupt counter
cannot miss fields. A read-only audit of the existing original-loader
`practice-continuous-10s` hardware trace counts **500 hardware fields, 500 native VBL
entries, 500 counter-site executions and 2,000 CIA-derived clock units** (10,000 ms).
No field lacks a VBL entry and none has multiple entries. This confirms agreement in
that bounded Practice launch window; it does not explain the synchronized qualifying
pit’s offset drift or validate the interrupted/stalled cases. The per-field audit is
saved as `clock-field-audit.json` beside that ignored capture.

Separately audit the full `$9950` call for collision/effect generation and presentation
side effects, then move persistent animation advancement to calibrated logical ticks
while leaving projection usable on every render. Preserve remaining mismatches as
failing gates until those changes are tested; matching retune/return alone is not full
input/player-state or trajectory equivalence.

```sh
python3 tools/check_timing_sync.py tmp/prof/timing-sync1-initial-030-twins tmp/prof/timing-sync1-initial-a500
python3 tools/compare_timing_opponents.py --through-departure --report-only tmp/prof/timing-sync1-initial-030-twins tmp/prof/timing-sync1-initial-a500
```

The next F6 steps are:

1. **Retune ordering:** finish wider A500 lifecycle regressions. The final initial-pit
   CPU pair, 030 ordinary rescue/pause/session restart, and both injected result paths
   now pass their bounded checks. Verify natural finishing,
   ranking (including the player record), result-clock ownership and a fresh driving
   session; the injected initial-result test covers control flow and cleanup, not these
   broader requirements.
2. **Initial pit pacing:** calibrate the external 17-position sequence against native
   A500, independently of cockpit pacing. Keep real user waiting time advancing opponents;
   do not delay CPU-only loading to manufacture matching first-flight positions.
3. **Whole-state gate:** the comparison now extends through departure, but the current
   CPU pair fails after the earlier 030 retune. Establish matching semantic-event/input
   histories and require complete-record plus RNG agreement; investigate any differences
   that remain under those conditions. Preserve elapsed pit time in production rather
   than inserting loading delays to manufacture matching starts.
4. **Lifecycle regressions:** repeat pause, rescue and session restart with the initial-pit
   hooks, then add race reinitialization (the existing restart fixture uses Practice).
5. **Other modes:** finish repairs and other pit callers, then return to the full F7
   calibration/configuration matrix and F8 release checks.

Reproduce the bounded checks with:

```sh
python3 tools/check_timing_initial_pit.py tmp/prof/timing-initialpit1-030-twins tmp/prof/timing-initialpit1-a500
python3 tools/compare_timing_opponents.py --initial-pit tmp/prof/timing-initialpit1-030-twins tmp/prof/timing-initialpit1-a500
python3 tools/perf_status.py tmp/prof/timing-initialpit1-030-twins
```

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

Resources, opponents and falling/impulses have bounded development coverage above; their
full mode lifecycles and calibration remain open alongside weather and other effects.
Fall/impulse displacement is integrated over elapsed logical time, separately from its
90-ms age/decay cadence. Keep native mode/rendering consumers of the shared loop counter until
each gameplay read has an explicit replacement.


## Bounded accelerator timing matrix

`tools/timing_cpu_matrix.sh` freezes one supplied WORLD20 coverage artifact and runs
five sequential C5=9 windows: 030/25 fast planar with twins, 040/25 native and fast,
and 060/50 native and fast. Each window counts 500 PAL fields from `$bc7c`, with
read-only movement/control/resource/opponent probes. Every run checks 20-ms world
accounting, rational 90-ms controls, scalar/vector remainder arithmetic, all 15 owed
brake events, six timestamped joystick events, and native fuel arithmetic. Fast-renderer
runs additionally require the existing pixel/register/CCR/scratch/guard comparisons.
The cross-run checks retain every existing sampled player/engine/RNG field; no differing
field is masked. These instrumented results are not rendering-throughput measurements.

The unsynchronized `timing-cpumatrix1` batch passes the individual arithmetic/accounting
checks on all five configurations and matches **111 common control/input and fuel
updates**. Its strict sampled-world comparison **fails at the first logical step**:
030 RNG is **33,537**, versus **12,305** on both 040 and 060 renderer paths. Across all
500–502 common samples in each comparison, RNG is the only differing sampled field;
this is a diagnostic finding, not permission to exclude RNG or claim world equivalence.
Full opponent records and unsampled effects are not compared by this checker.

The initial-pit histories differ before flight. The 030 pit lasts **7,680 ms** and has
completed **85** opponent updates at the initial snapshot; 040 lasts **7,040 ms** and
has completed **78**; 060 lasts **7,020 ms** and also has completed **78**. Thus fixed
random seeds alone do not establish matched gameplay history at the first rendered
flight frame. Renderer path does not change these initial counts within the tested
040/060 pairs. The unsynchronized failures remain recorded and do not pass F7.

The matching experiment uses the existing VERIFY-only `TIMING_PIT_SYNC_TEST=1`
fixture, which waits for the same 18-second retune and 24-second pit-return events.
It changes no simulation records or random seeds. `check_timing_sync.py --flight-window`
requires the actual cutoff/return times to match the requested events in **both**
endpoint snapshots and requires identical synchronization diagnostics across the window.
The original initial-pit mode of this checker remains unchanged and still passes its
established reference. Production loading/pit behavior is not changed by this experiment.

The matched `timing-cpumatrix2-sync` batch passes all five individual and cross-run
gates: **502 common sampled player/engine/RNG states**, **111 common control/input
updates**, and **111 common fuel updates** match exactly. Each configuration applies
all 15 brake events, consumes all six input events without overflow, verifies carried
scalar/vector arithmetic, and observes **584 opponent multiplication reads at 90 ms**.
Those reads include initial-pit catch-up; they are not one opponent update per player
control. Complete opponent arrays and their trajectories remain outside this comparison.

| CPU / renderer | Completed 20-ms steps | 90-ms controls | Initial → final unsampled elapsed time | Clean completed twins |
| --- | ---: | ---: | ---: | ---: |
| 030/25, fast | 504 | 112 | 80 → 0 ms | 112 |
| 040/25, native | 503 | 111 | 60 → 0 ms | — |
| 040/25, fast | 504 | 112 | 80 → 0 ms | 122 |
| 060/50, native | 502 | 111 | 60 → 20 ms | — |
| 060/50, fast | 504 | 112 | 80 → 0 ms | 124 |

Every pair of initial/final game VBL snapshots differs by exactly **500 fields**, or
10,000 ms. The table's unsampled time is `(unpaused VBL × 4 - allocator last sample) × 5`
ms, distinct from already retained allocator debt. Both endpoint debt and assigned
unfinished-step counts are zero in these runs. Therefore the complete-step count is
`(10,000 + initial unsampled time - final unsampled time) / 20`, explaining 502–504
without duplicated or discarded time. These endpoint checks do not establish worst-case
latency or long-term catch-up capacity. The three fast runs total **358 clean twins**,
with unchanged raster code; all finish inside a further draw, so they are not teardown
proofs. The unsynchronized batch separately has 365 clean twins but still fails RNG
state equivalence. The matched test fixture is not evidence that production initial-pit
histories are identical across hardware.

Reproduce with the full periodic/orientation/input/engine/WORLD/WORLD20/repair/drop
coverage build, heat seed 12345, world/setup seeds 54321, and `TIMING_PIT_SYNC_TEST=1`.
Leave the wrap, input-injection and result-injection fixtures off. The driver uses
2 MB chip, 4 MB fast, Kickstart A1200, uncached cycle-exact 030/25, 040-NOMMU/25 and
060-NOMMU/50 configurations. `CUSTOM3=1` is independent of `CUSTOM1`; native-renderer
runs have `CUSTOM1=0`. Cache selection remains a WHDLoad option.

```sh
bash tools/timing_cpu_matrix.sh tmp/prof/timing-cpumatrix2-sync FROZEN_SLAVE
```

`REQUIRE_PIT_SYNC=0` permits reproducing the unsynchronized diagnostic batch; it does
not relax the cross-state gates. The driver stops at a failed check and keeps the
completed captures. Use new output directories and never run two captures concurrently.
This bounded matrix does not complete F7: further renderer/memory combinations,
60/600-second routes, controlled render rates, deliberate stalls, long-run capacity,
full opponent/effect states and lifecycle coverage remain. A500 response/resource/effect
calibration remains an independent requirement.


### A500 and 68020 matrix extension

`CASE_SET=baseline` adds five cases using the same frozen synchronized-pit artifact.
`TIMING_REFERENCE` reuses a completed reference only after comparing its slave bytes
against the frozen matrix input. The baseline run uses the existing 030 fast reference;
no new production code or calibration constants are introduced.

| Configuration | 20-ms steps | 90-ms controls | Initial → final unsampled time | Maximum sampled step delay | Maximum retained debt | Clean twins |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A500, 512 KB chip / 1.5 MB slow, native | 504 | 112 | 140 → 60 ms | 780 ms | 160 ms | — |
| 68000, same plus 4 MB fast, native | 507 | 112 | 140 → 0 ms | 780 ms | 0 ms | — |
| 68000, same plus 4 MB fast, fast/twins | 505 | 112 | 320 → 220 ms | 1,120 ms | 380 ms | 27 |
| A1200 / 68EC020, 2 MB chip / 4 MB fast, native | 504 | 112 | 80 → 0 ms | 400 ms | 0 ms | — |
| A1200 / 68EC020, same, fast/twins | 505 | 112 | 140 → 40 ms | 580 ms | 0 ms | 69 |

The 68000 and 020 cases use their model-default CPU clocks; effective configurations
and emulator logs are retained with the captures. All five windows span exactly 500
physical PAL fields. Initial/final retained debt and final assigned unfinished steps
are zero. The 504–507 completed steps follow the same initial/final unsampled-time
identity as the accelerator table. Maximum allocations are 32 steps on all three
68000 cases, 16 on 020 native and 25 on 020 fast/twins.

`timing-cpumatrix3-baseline` passes **504 common sampled player/engine/RNG states**
and **112 common control/input and fuel updates** against the existing 030 reference.
All 15 brake events and six input events are accounted for, and independent scalar/vector
arithmetic checks pass. The new fast-renderer cases add **96 clean twins**, with unchanged
raster code; both final snapshots are inside further draws, not teardown checks.
Combining this batch with the five synchronized accelerator cases also passes the strict
comparison: **502 common simulation-state samples and 111 common control/input and fuel
updates across all ten configurations**, with **454** clean twins in the synchronized
batches. Full opponent arrays and unobserved state still require their own comparisons.

```sh
CASE_SET=baseline TIMING_REFERENCE=tmp/prof/timing-cpumatrix2-sync/030-25-fast \
  bash tools/timing_cpu_matrix.sh tmp/prof/timing-cpumatrix3-baseline FROZEN_SLAVE
```

`CASE_SET=accelerators` remains the default; `CASE_SET=all` runs all ten cases from
scratch. A supplied reference is optional. The same initial-pit synchronization caveat
and remaining F7 requirements apply. These runs show retained-time correctness even
when the slow configurations fall behind temporarily; they do not prove acceptable
interactive latency or sustained capacity over 60/600 seconds. The fast/twin workload
must not be mistaken for an uninstrumented renderer performance comparison.

### Sampled delay accounting

`tools/check_timing_capacity.py` pairs each `$cedc` world-end observation with the
actual guest VBL count (`PDINITIAL_EVENT`), allocator state (`PDSESSION_EVENT`) and
world cursor (`PDW20_EVENT`). It requires a complete unpaused single-epoch capture,
an unchanged session/discard ledger, consecutive world timestamps, and a physical VBL
window matching the configured field count. At every observed world-end boundary it
independently checks this identity, in the game's 5-ms clock units:

`physical_clock - step_timestamp = physical_clock - last_allocator_sample + retained_debt + (assigned_steps_left - 1) × 4`

The current step is observed before the world-end hook advances its cursor. Thus the
reported delay measures how far that step's timestamp trails physical time, not how
long the step took to execute. The checker reports maximum observed delay, retained
debt, allocation size and the three components at the peak. A zero endpoint debt does
not imply zero latency: elapsed time since the last allocation has not entered that
debt counter yet. Per-step maxima do not bound unobserved rendering intervals or prove
long-term capacity; fast paths here include the extra workload of drawing twins.

The earlier synchronized accelerator captures pass this ledger: maximum sampled delay
is **260 ms** on 030 fast, **220/240 ms** on 040 native/fast, and **200/200 ms** on
060 native/fast. Retained debt is zero at every sampled boundary, with maximum
allocations of 12, 10, 12, 11 and 11 steps respectively.

The synchronized A500 extension exercises the actual allocation cap. `a500-native`
reaches **780 ms** of sampled delay at field 451: **0 ms** since the last allocation,
**160 ms** retained beyond the work cap and **620 ms** in later assigned steps.
It reaches the 32-step cap, then has zero retained debt at the endpoint. With 4 MB fast
RAM and native rendering, maximum sampled delay is also **780 ms**; that peak consists
of **180 ms** since allocation plus **600 ms** in later assigned steps, with no sampled
retained debt. The 68000 fast-renderer/twin run reaches **1,120 ms** at field 458:
**160 ms** since allocation, **380 ms** retained debt and **580 ms** in later assigned
steps. It also ends with zero retained debt but still has **220 ms** since its last
allocation. These are significant responsiveness limits, not a loss of logical time
or proof that uninstrumented fast rendering has the same delays.

```sh
python3 tools/check_timing_capacity.py CAPTURE...
```


## Longer-window contact-response validation

The synchronized A500/native and 030/fast pair `timing-endurance60-2` passes a physical
60-second window on each machine. Both complete 3,004 world steps and 667 control/resource
updates. All 3,004 common sampled player/engine/RNG states and 667 control/input/fuel
states match exactly. The four extra steps service 80 ms carried into the window:
initial/final unsampled elapsed time is 80/0 ms on 030 and 140/60 ms on A500. Neither
endpoint has retained or assigned unfinished debt.

Maximum sampled world-end delay is 260 ms on 030 and 780 ms on A500; maximum retained
debt is respectively 0 and 160 ms. The 030 completes 851 clean renderer twins, with raster
code unchanged and no draw active at the final snapshot. These are instrumented correctness
measurements, not release throughput. No fall-age or impulse samples are nonzero, so this
run supplies no new evidence for those effects. The ship comes to rest after the initial
maneuver; this is predominantly stationary accounting coverage, not sustained-driving
capacity. Full opponent/effect state and a restart remain outside this comparison. The synchronized ten-minute pair `timing-endurance600-1` passes all per-run and
cross-CPU gates over exactly 30,000 physical PAL fields (600 seconds) on each machine.
All **30,000 common sampled player/engine/RNG states** and **6,666 common control/input/fuel
updates** match exactly at their logical timestamps.

| Ten-minute observation | 030/25, fast renderer with twins | A500, native renderer |
| --- | ---: | ---: |
| Consecutive 20 ms world steps | 30,000 | 30,003 |
| Logical control/resource updates | 6,666 | 6,667 |
| Fractional-remainder observations | 60,000 | 60,006 |
| Initial → final unsampled elapsed time | 80 → 80 ms | 140 → 80 ms |
| Maximum sampled world-end delay | 260 ms | 780 ms |
| Maximum sampled retained debt | 0 ms | 160 ms |
| Maximum allocation | 12 steps | 32 steps |
| Opponent multiplication reads checked at 90 ms | 25,634 | 25,638 |

A500's three additional steps service the 60 ms difference between initial and final
unsampled time. The independent physical/world/control-clock checks account for the
extra endpoint control; no counts or state values are discarded to force equality.
Both CPUs finish with zero retained debt, assigned unfinished steps and pending controls.
All six input events and three contact responses pass on each CPU. The A500 integrator
checks 29,928 scalar and 89,629 axis carries; both runs have no nonzero fall-age, impulse
or centering-adjustment observations.

The 030 completes 7,069 clean renderer twins, with unchanged raster code and no draw
active at the endpoint. Opponent multiplication reads are checked individually for the
90 ms interval, not treated as full-record opponent equivalence. This is predominantly
stationary long-window accounting evidence, not sustained-driving, active-weather,
release-throughput or whole-lifecycle proof. No restart occurs in this window.

Native contact handling at hunk `$d058–$d090` multiplies saved steering axes `$436/$438`
by 230 and shifts right eight bits when `$24a` is nonzero, then replaces logical axes
through the existing `$d082` hook. The joystick checker includes this response as well
as direct input: `PDSTEER_EVENT` observes the branch flag and both saved axes at `$d058`;
the independent arithmetic oracle verifies saved-axis continuity, the next response and
final logical axes. Both CPUs observe three damping updates, including 75 → 67 → 60 → 53.
The 650-field `timing-contact13-1` reference also passes, with 652 common world states,
144 common control/input/fuel updates and 156 clean 030 twins. The earlier
`timing-endurance60-1` log lacks these branch observations and remains insufficient evidence
for the contact gate; it is not counted as a passing run. No production behavior changed.

Use `CASE_SET=endurance FIELDS=3000 bash tools/timing_cpu_matrix.sh NEW_OUT FROZEN_SLAVE`
for the sequential 030-fast/A500-native comparison; `FIELDS=30000` selects ten minutes.
The frozen coverage slave must include the documented fixed seeds and initial-pit sync.

## Controlled simulation-stall fixture and measured recovery

`TIMING_STALL_TEST=100|250|500` adds a VERIFY-only delay at the next flight allocator entry
after at least 200 world updates. Native VBL/input interrupts continue while simulation
waits. The fixture does not rewrite simulation data, timestamps, debt or input queues;
the normal allocator must account for elapsed time afterward. It injects once per process,
so restart does not repeat it. It is not a pause or a production render-rate limiter.

All three A500/native and 030/fast pairs pass. Each observes one hold of the specified
PAL duration, resumes at the saved next-world cursor, and services elapsed work through
release. Relative to both unstalled `timing-contact13-1` references, each pair matches
652 common sampled player/engine/RNG states and 144 common control/input/fuel states
exactly. All six input events are consumed once and all three contact responses pass.
Movement, brake, fuel, input and allocator checks pass. Every endpoint has zero retained
or assigned unfinished debt. The captured 030 drawing comparisons are clean with unchanged
raster code. The 100 and 250 ms captures end with drawing still active; only completed
twins are counted, and these endpoints do not establish drawing teardown. The 500 ms
capture ends with drawing inactive.

| Requested delay | Observed delay | Capture pair under `tmp/prof/` | World steps 030/A500 | Controls 030/A500 | Clean 030 twins |
| --- | --- | --- | ---: | ---: | ---: |
| 100 ms | 100 ms / 5 PAL fields | `timing-stall100-1` | 652 / 657 | 144 / 146 | 155 |
| 250 ms | 260 ms / 13 PAL fields | `timing-stall250-1` | 652 / 655 | 144 / 145 | 153 |
| 500 ms | 500 ms / 25 PAL fields | `timing-stall500-1` | 654 / 656 | 145 / 145 | 151 |

The 250 ms request rounds up to the first PAL field at or after the requested duration.
All windows span exactly 13 physical seconds. Differences in completed work at their
endpoints are explicitly accounted for below; they are not silent drops or relaxed state
comparisons.

| Requested delay | Max sampled delay 030/A500 | Max retained debt 030/A500 | Max allocated steps 030/A500 | Unsampled elapsed start→end, 030 / A500 |
| --- | ---: | ---: | ---: | --- |
| 100 ms | 260 / 780 ms | 0 / 0 ms | 12 / 32 | 80→40 / 140→0 ms |
| 250 ms | 320 / 780 ms | 0 / 160 ms | 17 / 32 | 80→40 / 140→40 ms |
| 500 ms | 560 / 760 ms | 0 / 0 ms | 29 / 32 | 80→0 / 140→20 ms |

These maxima are sampled at world-end probes and can occur later than stall release;
they are not bounds on all rendering latency or release performance. The results support
one interruption on this matched route. Repeated/arbitrary stalls, other effects/lifecycle
states, controlled presentation rates and the ten-minute/restart requirement remain open.

### Stall evidence and build isolation

`PDSTALL1` records injection count, physical entry/release fields, logical world cursor,
allocated tick count at entry and requested milliseconds. `tools/check_timing_stall.py`
checks duration, absence of world-end observations inside the stall, exact resume cursor,
consecutive 20-ms steps through recovery and independent elapsed-time/debt accounting.
Input/resource/world comparisons remain separate required gates.

The checker follows the installed allocator's first BSR and the fixture's PC-relative LEA
to locate the live record, avoiding stale loader copies and fixed search-range assumptions.
It accepts the timing installer's SR-to-CCR rewrite for 68010+ at the saved-status prologue,
retaining exact checks on subsequent call/reference instructions. Duration uses paired
guest VBL-counter observations, not an inferred debugger-field offset.

All three variants assemble. Non-VERIFY and invalid-duration builds are rejected. An
explicit zero fixture is byte-identical to the frozen full timing prototype; the restored
normal build is also unchanged. Reproduce each pair with `CASE_SET=endurance FIELDS=650`,
then run `tools/check_timing_stall.py` on both outputs and compare them with the unstalled
reference using the world, control and resource tools. Use `--accounted-endpoints` for the
control and resource comparisons.

### Exact endpoint accounting

The optional `--accounted-endpoints` mode requires equal physical durations, an unchanged
session/discard ledger, unpaused and complete boundary controls, continuous world-clock
observations and the physical elapsed/debt identity. If `S` is the initial next-control
deadline and `E` is the final next-world cursor, the expected count is
`max(0, floor((E - 4 - S) / 18) + 1)`, in native 5-ms units. Every observed deadline must
be `S + 18*i`, and the final control cursor must be `S + 18*count`. Every common state
still compares exactly. The CPU matrix uses this mode. Legacy callers retain the old
one-update endpoint allowance unless selecting this stronger proof.

This matters for the 100 ms pair: A500 services 100 ms more logical time inside the equal
physical window and legitimately completes two extra controls. The raw batch log retains
the original one-update-limit failure; the clock-based checks and reference comparisons
are saved separately. This is a change to endpoint verification, not to game cadence,
field exclusions or gameplay tolerances. The stronger oracle also passes the ten-CPU
10-second matrix (111 common control/fuel updates), 60-second pair (667), and 500 ms pair
(145). The ten-minute, full-state, lifecycle and calibration gates remain unproven.


## Controlled render-rate fixture (runtime validation pending)

`TIMING_RENDER_HZ_TEST=10|15|25|50` is VERIFY-only and mutually exclusive with the
single-stall fixture. After at least 200 world updates, it paces allocator entry using
physical PAL fields. The first release is immediate; later deadlines advance from the
previous actual release by rational 50/Hz periods. At 15 Hz the period repeats 4,3,3 fields;
10/25/50 Hz use 5/2/1 fields. If rendering arrives late, the fixture records lateness and
releases immediately, then bases the next presentation deadline on that actual release.
Only presentation deadlines are rebased. Simulation clocks, input queues and elapsed debt
are untouched; the ordinary allocator still services all elapsed simulation work.

This is a requested pacing rate, not a guarantee that the CPU can render at that rate.
Late deadlines and actual completed-frame measurements must be reported. The experiment
must not label a run as 25 or 50 presentations/s solely because that build option was set.
It is scoped to the existing unpaused, single-epoch matched flight route. It does not
establish pause, pit or restart behavior for the fixture itself.

`PDRATE01` stores initialization/rate, pacing origin, release count, last arrival/deadline/
release, rational remainder, total waiting fields, late count, maximum/cumulative lateness
and a pending-deadline flag. The caller already saves CCR and all registers the fixture
uses. `tools/check_timing_render_rate.py` follows direct code references to the live record
and checks the aggregate identity
`last_release - origin = ceil((release_count - 1)*50/Hz) + cumulative_lateness`, the rational
phase, endpoint state and independent world/physical-time accounting. It reports allocator
release rate separately from driving-presentation markers. It derives the debugger-field
offset from paired guest VBL observations, requires that alignment to remain constant,
and reports every observed marker interval after the pacing-origin field, its histogram
and measured rate. This excludes any marker that could precede fixture entry in the same
PAL field. Aggregate counters alone do not prove presentation cadence or gameplay equality;
marker observations have 20-ms resolution and do not prove distinct displayed images.
`frames.txt` retains the separate whole-window frame report.

The presentation extractor passes a regression against the existing unpaced
`timing-contact13-1` captures: 155 intervals over 12,840 ms on 030 (12.072/s), and 111 over
12,760 ms on A500 (8.699/s), matching the independent whole-window report. Their interval
ranges are 60–240 ms and 60–800 ms respectively. These are instrumented reference
observations, not achieved controlled-rate results or release performance.

All four variants assemble and their direct record references/initial states decode.
Non-VERIFY, unsupported-rate and combined stall/rate configurations are rejected. The
explicit zero fixture is byte-identical to the existing full prototype, and the restored
normal build is unchanged. These build checks alone establish no rate-independence result.

The first runtime pair, `timing-rate10-1`, passes all arithmetic/input, pacing-accounting
and CPU-comparison checks over 650 PAL fields (13 seconds). Against both unpaced
`timing-contact13-1` references, **652 common world states and 144 common control/input/fuel
updates match exactly**. The pacing fixture starts after 200 world steps, so its rate
measurements cover the paced region rather than the whole capture.

| Requested 10 Hz observation | 030/25 fast with twins | A500 native |
| --- | ---: | ---: |
| Allocator releases / measured rate | 87 / 9.534 per second | 74 / 8.166 per second |
| Driving-marker intervals / measured rate | 85 / 9.572 per second | 72 / 8.200 per second |
| Measured marker span | 8,880 ms | 8,780 ms |
| Late deadlines / maximum lateness | 4 / 140 ms | 27 / 700 ms |
| Total lateness / pacing wait | 420 / 2,400 ms | 1,640 / 700 ms |
| Complete world steps / controls | 654 / 145 | 657 / 146 |
| Initial → final unsampled time | 80 → 0 ms | 140 → 0 ms |
| Maximum sampled world-end delay / retained debt | 240 / 0 ms | 780 / 160 ms |

The exact endpoint accounting explains the different completed-step/control counts.
Both endpoints have zero retained/assigned simulation debt and pending controls. The
030 contributes 132 clean completed renderer twins; one draw is active at the endpoint
and is not counted as complete. Raster code and all renderer failure counters are unchanged.

The marker interval histograms in milliseconds are 030 `{80:3, 100:78, 180:2, 240:2}`
and A500 `{80:1, 100:44, 120:23, 140:2, 460:1, 800:1}`. Pacing occurs at allocator entry,
whereas these markers observe the driving-loop boundary; neither requested rate nor
allocator-release spacing proves exact display spacing. These measured intervals establish
changed presentation timing with equal sampled simulation state for this route, not a
steady achieved 10 Hz, distinct displayed images, release FPS or whole-game independence.
The additional `timing-rate15-1`, `timing-rate25-1` and `timing-rate50-1` pairs also pass.
A combined comparison of all eight requested-rate captures and the two unpaced references
finds **652 identical common sampled world states and 144 identical common control/input/fuel
updates across ten captures**. Each added pair completes 652/654 world steps and 144/145
controls (030/A500), with initial/final unsampled time 80→40/140→60 ms. All finish with
zero retained/assigned simulation debt and pending controls. Their maximum sampled delay
is 260/780 ms and retained debt 0/160 ms. Each adds 156 clean 030 renderer twins, for
**600 new completed twins across the four pairs**. Each 030 endpoint interrupts another
draw; these are not completed-draw teardown tests.

| Requested rate | 030 marker rate | A500 marker rate | Pacing wait, 030/A500 | Late deadlines, 030/A500 | Maximum lateness, 030/A500 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 10 Hz | 9.572/s | 8.200/s | 2,400 / 700 ms | 4 / 27 | 140 / 700 ms |
| 15 Hz | 12.275/s | 9.039/s | 280 / 0 ms | 49 / 67 | 180 / 720 ms |
| 25 Hz | 12.275/s | 9.039/s | 0 / 0 ms | 110 / 80 | 200 / 760 ms |
| 50 Hz | 12.275/s | 9.039/s | 0 / 0 ms | 110 / 80 | 220 / 780 ms |

For each 15/25/50 request, the 030 marker histogram is
`{60:30, 80:62, 100:13, 160:1, 180:1, 240:2}` over 109 intervals / 8,880 ms;
A500 is `{80:38, 100:14, 120:23, 140:2, 460:1, 800:1}` over 79 intervals / 8,740 ms.
Allocator release rates are 12.249/s and 9.009/s, respectively. Requests of 25/50 Hz
add no wait on either machine, so they validate late-deadline behavior, not simulation
independence at achieved 25/50 Hz. The 15 Hz request adds only 280 ms of waiting on 030.
None establishes a steady requested display rate. The 10 Hz request supplies the meaningful
slower-cadence comparison for both configurations. These remain correctness-instrumented
observations, not release throughput measurements.

The `timing-rate50-native1` extension uses `CASE_SET=rate-native` for 030/25 and 060/50
with native rendering, the same frozen 50 Hz request fixture and 650-field input window.
Both per-run gates and the 652 common sampled world states pass. The original endpoint
control checker rejects the 060 capture because it assumes every completed control belongs
to a completed movement; the failed runner log is retained. Inspection proves a completed
control/resource update inside its one unfinished movement step. After the independently
verified boundary correction below, 145 common controls/resources match between these two
runs. Combining them with all four requested-rate pairs and both unpaced references gives
**652 identical common world states and 144 identical common control/input/fuel updates
across twelve captures**.

| Native-rendered 50 Hz request | 030/25 | 060/50 |
| --- | ---: | ---: |
| Allocator releases / rate | 168 / 18.556 per second | 150 / 16.592 per second |
| Marker intervals / rate | 166 / 18.568 per second | 148 / 16.629 per second |
| Marker span | 8,940 ms | 8,900 ms |
| Late deadlines / maximum lateness | 167 / 200 ms | 149 / 200 ms |
| Total lateness / pacing wait | 5,660 / 0 ms | 6,000 / 0 ms |
| Completed movement steps / completed controls | 653 / 145 | 652 / 145 |
| Assigned unfinished movement steps at endpoint | 0 | 1 |
| Initial → final unsampled time | 60 → 0 ms | 60 → 0 ms |
| Maximum sampled world-end delay / retained debt | 220 / 0 ms | 200 / 0 ms |

The 030 histogram is `{40:75, 60:86, 140:4, 220:1}`; 060 is
`{40:26, 60:113, 80:4, 120:2, 140:1, 160:1, 220:1}`. Neither reaches 50 Hz or waits
for pacing. The 060 endpoint retains no unallocated time but has one assigned movement
unfinished, so it is not a zero-outstanding-work endpoint. No renderer twins are performed
on these native paths. These configured emulator results extend measured cadence coverage;
they are not physical accelerator rankings or release-performance benchmarks.

`timing_control_window.py` now recognizes a completed control in an unfinished movement
only when independent evidence agrees: active world ownership, the control-due flag,
exactly one extra started world step, the exact started-control count, a deadline due in
that movement, an advanced completed-input clock with control ownership released, and a
unique post-control `$ccee` observation agreeing with the live clock and counters. It does
not infer an extra allowance from the observed row count. Exact deadline sequence and final
clock checks still apply to all compared rows, including resources. The combined twelve
captures, ten-minute pair and 100 ms stall pair pass. Seven in-memory corruptions (cleared
ownership/due flags, extra started-step/control counts, removed boundary probe and missing/
duplicate control rows) are rejected without modifying any frozen capture. Gameplay code,
cadences and equality tolerances are unchanged.

The matched lower-rate native-renderer pair `timing-rate10-native1` also passes. Both
machines measure **9.707 driving markers/s** over 86 intervals / 8,860 ms, compared with
18.568/s (030) and 16.629/s (060) in their native-rendered 50 Hz request runs. Across
these four captures, **649 common world states and 144 common control/input/fuel updates
match exactly**, with all per-run arithmetic, clock, input and pacing checks passing.

| Native-rendered 10 Hz request | 030/25 | 060/50 |
| --- | ---: | ---: |
| Allocator releases / rate | 88 / 9.688 per second | 87 / 9.663 per second |
| Late deadlines / maximum lateness | 5 / 120 ms | 4 / 120 ms |
| Total lateness / pacing wait | 280 / 4,880 ms | 300 / 4,320 ms |
| Completed world steps / controls | 652 / 144 | 649 / 144 |
| Initial → final unsampled time | 60 → 20 ms | 60 → 80 ms |
| Maximum sampled world-end delay / retained debt | 240 / 0 ms | 200 / 0 ms |

Both finish with no assigned/retained simulation debt or pending controls. The 060 ends
inside a presentation wait, independently checked by its pending-deadline flag and
rational phase; that wait has not yet become allocated simulation work. Its 649 completed
steps plus the increase in unsampled time account for the full 13-second physical window.
The 030 marker histogram is `{60:1, 80:2, 100:78, 140:3, 200:1, 220:1}` and the 060 is
`{60:1, 80:6, 100:71, 120:4, 140:1, 160:1, 220:2}`. This establishes equal sampled
simulation state over a measured high/low cadence change on each native-rendered CPU,
not exact 10 Hz scanout, high-rate target achievement or coverage of other effect routes.

Next steps:

1. Completed the matched high/low measured-rate comparison on native-rendered 030/25
   and 060/50. Extend beyond this same bounded timed-input route as gameplay work proceeds.
2. Report higher requested rates as unattained where measured intervals cannot support
   them; do not equate a fixture setting with achieved coverage.
3. Extend to variable presentation intervals and other response/effect routes. Preserve
   both native and fast-rendered state checks and keep rendering correctness separate
   from the measured cadence claim.


## Remaining weather and effect ownership

Static inspection identifies coupled simulation and presentation work that cannot be
fixed by pacing only the visible effect. The following offsets are game-hunk offsets;
field offsets are relative to the native state block. These are native control-flow
findings, not measured A500 cadence or completed runtime coverage.

| Native sites | Ownership/dependency to preserve |
| --- | --- |
| `$d91e → $dc5a`, `$dd0e–$dd42` | HUD/status path reaches forecast eligibility and RNG selection. `$e1a2` sets a forecast flag at `+$4c0` and deadline `+$4bc = clock + 5000`; `$dd36/$dd3c` test that deadline. |
| `$e1f8–$e25c` | Starts the transition at `+$4c6 = 15`, clears steering offsets `+$4c2/$4c4`, computes an active deadline `+$4b8` from a track-dependent duration, RNG and the clock, and may enable effects at `+$4cc`. |
| `$ddd4–$ddf8`, `$e25e–$e28e` | Expiry is checked only when the low three loop-counter bits are zero. Exit sets `+$4c6 = -15`, resets both deadlines and disables effect generation. |
| `$bc8a–$bd16` | Eligible effect generation decrements delay `+$4d2` once per outer loop, then makes RNG calls and sets lifetime `+$4ce` and the next delay. |
| `$bd1a–$bd52` | Transition `+$4c6` advances toward zero only when the low four loop-counter bits are zero. Palette helpers `$8a1a/$8a60` draw the fade, but completion helpers `$8a4c/$8a8e` also change target gear `+$450`. |
| `$d0b6–$d11a` | Active weather affects handling: RNG updates steering offsets; negative transition phase scales those offsets into controls. Transition timing therefore changes gameplay even if pixels are ignored. |
| `$112e6–$112fa` | The renderer decrements effect lifetime `+$4ce`, runs an effect helper and changes transient palette state `+$4d0`. Separate lifetime evolution from per-buffer presentation and cleanup. |
| `$a8dc/$a936`, `$b60a`, `$c2dc` | The same transition word is also used/reset by animation, initialization and mode cleanup. A global hook on every write would incorrectly merge distinct lifecycles. |

The world wrapper owns logical counter/seed state during movement and restores the outer
counter/RNG afterward. Its native clock reads are not globally replaced. Scheduling the
remaining weather blocks must therefore explicitly choose logical versus physical time,
RNG ownership and publication order. Pacing the fade alone leaves handling, target-gear
changes, effect generation and lifetime tied to different clocks. `+$4ce/$4d0` also gate
fast-planar fallback, so the native and fast render paths both need these checks.

### Available weather evidence and calibration entry point

The existing input-only `CUSTOM5=6` route selects track index 2 through native menu keys.
`coverage-weather-twin` already proves that this route reaches natural effects with timing
off on 060/50: 139 native effect draws/fallbacks and 5,129 staged renderer twins. Its
16,000-field capture starts at `$112f4`, after onset. It contains zero `$e1a2` warning
or `$e1f8` start events, so it cannot establish forecast delay, fade-in timing or their
A500 reference. At its initial snapshot the transition word is already zero, effects
are enabled, and the active deadline is 46,778 native clock units (233,890 ms) ahead.
At the final snapshot both deadlines/effect flags are inactive. This is reusable routing
and rendering evidence, not A500 timing calibration.

Start the new A500 baseline at `$e1a2`, not the first effect draw. Retain input route 6,
C3/C1/C4 off and the original game timing; capture the warning flag/deadline publication,
start, fade steps, active expiry, fade-out, steering/gear and effect mutations listed
above. Repeat on the full prototype with the same input route and explicitly record
whether histories and eligibility match before comparing durations.

The forecast RNG call at `$dd20` passes `d1=2` to `$53f6`. This argument is a right-shift
count, not a random range of two: the helper updates its 16-bit seed, then returns the
word shifted right by two. The zero test at `$dd28` succeeds only for updated seed values
0–3. Do not model this as a one-in-four trial or infer a waiting-time distribution without
analyzing the actual seed stream and other callers. A directed seed test could exercise
native transitions but would not replace the required natural A500 episode.

### Weather sampling schema

`tools/weather_state.py` defines 20 native clock/state fields plus D0/D1/D7/SP for
`PDWEATHER_EVENT`, including both deadlines, forecast/transition state, steering offsets,
effect generation/lifetime, current/target gear and RNG. Its probe builder contains only
read-only `printf` expressions. The 35 selected PCs cover native eligibility, deadline
arithmetic/commit boundaries, positive/negative fade updates, target-gear changes and
effect rendering. Their instruction boundaries have been checked against the native code.
Snapshot extraction also reproduces the existing weather capture's active initial and
inactive final state. Printf escaping matches the current capture-tool convention.

`swap_fields.py` now emits this schema for matching `COVERAGE_PROBES` offsets when
`TIMING_STATE=1`. A dry run against the frozen native weather capture generates all 35
read-only commands without needing installed timing hooks. A separate dry run against the
current timing fixture produces byte-identical debugger commands before and after this
integration for the existing eight-probe timing route. These checks verify command
construction only; paired runtime observations and original A500 cadence measurements
remain required before weather scheduling can be accepted.

The native A500 route uses input route 6, C1/C3/C4 disabled, 512 KiB chip plus
1,536 KiB slow memory and no fast RAM. It reuses the frozen native-weather coverage
slave, anchors at `$e1a2`, and requests 20,000 PAL fields (400 seconds). The first capture
`timing-weather-native-a500-1` reaches natural forecast entry on track 2, with both
deadlines inactive, forecast/transition/effect fields zero, gate `$104` zero and RNG seed
1. Its debugger rejects multiple breakpoints with a `Z0` insertion error, aborting at
field -1 before any measured fields complete. The log and initial snapshot are retained;
this is routing evidence only, not a weather-duration or mutation measurement. Generating
35 valid commands does not establish that the debugger supports all 35 concurrently.

The retry `timing-weather-native-a500-2` uses 14 weather probes: `$e1ca/$e1d4/$e1f8`,
`$e23c/$e242/$e246`, `$e278/$e294`, `$bd32/$bd36/$bd48/$bd4c` and `$112e6/$112f0`.
It targets forecast/deadline publication, start/expiry, both fade directions and renderer
lifetime decrement. Additional generation, palette and gear probes need a separate pass;
they are not implicitly covered by this reduced set. The reduced set is accepted by the
debugger and completes exactly 20,000 PAL fields (400 seconds), with 4,904 weather
observations. All observed mutation pairs pass.

The observed A500 onset has forecast clock 195,624 and deadline 200,624: exactly
5,000 native units / 25 seconds. Start occurs at clock 200,648, **120 ms after the deadline**,
at debugger field 1,254. Warning publication is at field -1, giving 25,100 ms in debugger
fields versus 25,120 ms in the game clock; these time sources differ by one PAL field.
The active-duration RNG changes **18,177 → 15,288** through the native recurrence.
Its base duration is 36,750 units and randomized result 53,894 units, producing deadline
254,542: **269,470 ms** after start. Both RNG arithmetic and deadline publication pass.
Expiry is observed at clock 254,616, **370 ms after the selected deadline**.
Physical start-to-expiry spans fields 1,254–14,747, or **269,860 ms**; the game-clock
difference is 269,840 ms. The native low-three-bit loop gate and polling delay remain
part of the original behavior to account for explicitly.

All 15 positive fade decrements are observed and verified, from loop counter 2,496 through
2,720 in increments of 16. First decrement is at field 1,302, last at 2,283. Start-to-first
is 960 ms; start-to-final is **20,580 ms** in physical fields (20,560 ms in the native
clock). Fourteen first-to-last intervals span 19,620 ms, averaging **1,401.4 ms**, with
individual intervals 1,180–1,900 ms. The negative transition is published at field 14,747. Its 15 increments occur at loop
counters 5,728–5,952, again every 16 loops, from fields 14,806–15,610. Start-to-first is
1,180 ms; start-to-final is **17,260 ms** (17,280 ms in the game clock). Fourteen
first-to-last intervals average **1,148.6 ms**, ranging from 1,040 to 1,400 ms. Thus simply
using the existing 90 ms control period times 16 for both fades would make the negative
fade's steady interval about 25% slower than this native reference. The different observed
rates follow the native frame-driven paths; this single episode does not establish an
intentional direction-dependent design. Corrected periods and initial-phase policy still
need to be selected explicitly against these measured bounds.

All 30 fade mutations, native RNG/deadline arithmetic, expiry resets and **90 effect-lifetime
decrements** pass. There are 4,746 effect-entry observations; the final unpaired entry has
zero lifetime, so no decrement is expected. The final snapshot has both deadlines inactive,
transition/effect/palette/delay fields zero, and target gear 3. Forecast flag remains 1 and
steering offsets remain nonzero, reflecting native retained state rather than an assumed
all-zero cleanup. Target gear at expiry is 1, establishing a gameplay-visible difference
across the transition, but helper-level ownership needs its separate probes.

The complementary `timing-weather-native-a500-effects1` pass completes the same 400-second
window with 17,613 observations. **All 4,836 shared effect-entry/decrement observations**
match the first capture exactly, including physical fields, clocks, state and captured
registers. All 20 initial and final weather fields match as well. This establishes the
same observed native episode across the two probe sets, rather than assuming it from
configuration alone.

The analyzer verifies **36 successful generation/lifetime assignments**, **36 random
delay selections and commits**, **90 lifetime decrements**, **90 palette activations**
and both track-specific target-gear helper commits. Generation executes on 2,992
consecutive eligible native loop values, 2,721–5,712, from fields 2,288–14,743. Its 2,991
first-to-last intervals average **83.283 ms**. There are 2,828 RNG-selection attempts and
200 delay decrements; 36 iterations do both when delay expires. This supplies the native
reference for generation scheduling, separately from the longer fade-step measurements.

Generation at `$bcea→$bd02` advances the native seed once, accepts the shifted result
only when it is at most six, then masks it with five for the lifetime. `$bd02→$bd16`
advances the seed a second time and selects delay `(seed >> 14) + 4`; `$bd1a` observes
the committed delay. Both RNG advances and stored values pass. Target-gear helpers
`$8a4c/$8a8e` load the track-indexed native tables at hunk `$2068/$204c`; their return
probes match the captured table words, not hardcoded gear expectations. Palette activation
is separately checked at `$112f4→$112fa`.

**Drawing itself also consumes simulation-visible randomness in the native game.**
The effect helper `$16de6` calls `$53f6` once, then its `$16e0a` helper three times; each
of the 90 observed draws advances the shared RNG exactly four times between `$112f0`
and `$112f4`. For example, seed 20,001 becomes 58,289. The analyzer now verifies these
four advances for every observed draw. Moving only lifetime decrement or generation
would therefore leave a rendering-dependent RNG path.

For the correction, account for those four visual RNG advances when a logical effect
update is due, and save the pre-draw seed/state for presentation. Repeated rendering of
that state must not consume additional simulation randomness. Keep palette activation
and cleanup associated with actual drawing separately: the native trace has palette
state set through `$11300` and cleared before the next outer generation observation.
Do not infer that the helper call itself immediately clears it. The effect presentation wrapper below now separates visual RNG ownership. Full mode/reset
handling remains open; these native measurements alone do not establish corrected weather timing.

`tools/report_weather.py CAPTURE` checks observed before/after arithmetic for forecast
and active deadlines (including native duration RNG arithmetic), fade increments/decrements
and their native 16-counter gate, effect
lifetime, palette activation, generation delay and expiry resets. It reports every probe
count, checked pair count, unpaired boundary and each fade step's physical field, clock
and loop counter. Missing event families are explicit and are not reported as passes;
the report is not a complete-episode or corrected-timing acceptance gate. Nine explicit
synthetic mutation examples pass and nine incorrect results are rejected. These synthetic
checks validate the analyzer only. A further explicit seed-1/base-1000 example verifies
seed 31,416 and duration 1,956; incorrect seed and duration are rejected. The observed
native onset now passes these checks, while unobserved event families remain open.
The duration helper `$8ae6` and forecast/steering helper `$53f6` both mutate state `$62`.
The world wrapper installs its logical seed at world entry and restores the outer seed
before rendering. Forecast/start/generation must therefore be moved into the same logical
ownership consistently; leaving any RNG caller at render cadence can change later weather
or handling even if the fade alone is paced.

Next implementation gates:

1. Capture an eligible natural weather episode on the original A500 and the full prototype.
   Probe `$dd14/$dd2c/$e1ca/$e200/$e242/$ddf8/$e278` and outer generation/fade boundaries;
   record both deadlines, all fields in the table, outer/logical counters and RNG. Verify
   the actual callers and eligibility before assigning a cadence.
2. Freeze A500 transition, active-duration and effect-lifetime bounds. Do not assume that
   a native low-bit gate maps directly to the current 90 ms control phase without measuring
   its caller frequency and counter behavior.
3. Extract forecast/start/expiry and generation mutations into logical updates. Preserve
   queued palette/sound/message presentation, target-gear effects and the selected RNG
   stream; replace the relevant clock reads locally rather than changing the global clock.
4. Move effect lifetime out of the renderer, then validate both buffers' draw/cleanup and
   native fallback. Preserve transient draw bookkeeping separately from persistent state.
5. Check matched logical state and physical duration across CPU/render configurations,
   catch-up, pause, pit, restart and the reused transition-word animation paths.

The 60-second matched-input captures have zero forecast/transition/effect fields at both
endpoints, inactive deadlines and no nonzero sampled transition phase. The completed
portion of the ten-minute route likewise has not established a weather episode. Those
runs must not be used to close this weather gate.

## Experimental logical weather-effect ownership

`TIMING_WEATHER_EFFECTS=1` now builds the first effect-ownership split in
`timing_weather_effects.s`. It requires `TIMING_PERIODIC=1` and WORLD20, remains disabled
by default, and installs its hooks only under `CUSTOM3`. This is not complete weather
timing: forecast and start/expiry still follow their existing paths. Fade/gear timing
has a separate disabled-by-default prototype described below.
No cache policy changes are made.

During supported human flight, the current `PDWEFX03` implementation uses separate
weather-loop and visual deadlines, serviced by 20-ms world updates:

1. At generation, apply native eligibility, decrement delay, and perform shift-7 lifetime
   and shift-14 delay selection through `$53f6` when due. Schedule the next generation
   80 ms later for a scene without an effect, or 140 ms later for a scene with one.
2. At generation +20 ms, publish the current lifetime and pre-draw seed, decrement
   lifetime once and advance logical RNG four times when an effect is present. A blank
   scene clears the previous visible publication at this same visual boundary.
3. On delay expiry, invoke the native sound helper immediately at the logical generation
   boundary, before selection RNG, when its sample resources exist. Retain cumulative
   deadlines; actual repeated draws do not consume logical RNG.

The earlier `PDWEFX01` prototype used a uniform 90-ms control cadence with visual work
before generation. It passed cross-CPU ownership checks but failed A500 active-effect
speed calibration: the native intervals are about 139 ms. The native ordering/cadence
measurements and the current candidate's bounded results appear below. General mode
transitions and natural weather acceptance remain open.

The renderer uses the latest published lifetime/seed. It temporarily installs the saved
visual seed around the native draw helper, then restores the outer seed. Repeated draws
therefore do not advance simulation RNG or decrement persistent lifetime. Palette state
and native presentation calls remain per actual draw. The outer loop skips its original
generation block while logical ownership is enabled; sound delivery is part of logical
generation and has no per-render queue. Outside the supported flight predicate, native effect behavior is retained;
those mode paths are not yet framerate-independent. Initialization/session cleanup clears
pending visual ownership. Pause, pit/recovery and full lifecycle contracts remain to be
validated with active effects.

The native call at game `$bce0` targets `$17836`, an audio-channel start routine.
It checks `state+$2f4`, stops the selected DMA channel, programs sample pointer/length/
volume/period, updates `$48c4/$48dc` bookkeeping and enables its interrupt and DMA.
Weather uses channel 3, volume 63, and the fifth 12-byte descriptor from `$5ae`.
The availability guard `$4f74` is set only after the larger 404,000-byte chip allocation
succeeds; it also controls allocation/loading of the extra sample table. Normal 512-KiB
guest captures use the smaller 266,400-byte allocation and lack this table. A verification
1-MiB guest configuration loads it naturally, without forced flags or sample pointers.

The legacy diagnostic names remain compatible: `cleanup_pending` was the deferred sound
flag in `PDWEFX01/02`, and stays zero in `PDWEFX03`; `cleanups` counts wrapper calls before
the native suppression check. Neither field proves audible playback. The renderer's
palette restoration at `$117c8–$117d4`, calling `$f914` under `state+$4d0`, is a separate
operation and still needs palette/buffer/scanout validation.

Audio validation uses these independent checks:

- `weather_audio_state.py CAPTURE...` reads allocation, optional samples, suppression and
  channel bookkeeping. `--require-available` rejects absent samples. Available resources
  must have the larger allocation, an in-bounds table and valid sample pointer/word length/
  period. The measured weather sample is 5,087 words with period 895.
- Read-only probes `$17836/$178e6` capture registers and return addresses. The reader follows
  the installed weather hooks, native-call branch and register restore to identify the
  actual weather caller, excluding other channel-3 sounds. Damaged hook/target/restore
  evidence is rejected.
- `check_weather_audio.py CAPTURE...` pairs native calls, checks arguments, distinguishes
  suppression from channel start, verifies preserved registers and reconciles delay-expiry
  requests with deliveries. With `PDWEFX03`, each call must occur at the current logical
  world/generation boundary and leave logical weather state unchanged. In-progress
  generation observations inside the audio helper are not mistaken for committed RNG state.
- `--require-mute` additionally requires native Tab handler probes `$c5fc/$c600`, both flag
  transitions, one suppressed weather request and two subsequent starts.
- `--require-unavailable` requires absent resources, an observed delay expiry, zero weather
  calls/queue counters and no entry into the owned native helper. It cannot pass an idle
  capture that never exercises the guard.

The deferred baseline `timing-weather-audio-test1` and native-mute `audio-keys1` pairs
validate resource loading and helper contracts, but their implementation fails the
closely spaced `audio-stall1` regression on both CPUs. The corrected `audio-stall2` pair
validates direct delivery of all four requests, including two 320 ms apart during a
500-ms stall. Native calls take 0–40 ms in PAL fields, which is a synchronization cost,
not a throughput measurement or proof of audible output. The detailed results and
remaining direct-delivery regressions are below. Wrong sample length, changed return
stack, missing pending evidence and both original coalescing captures are rejected.

Fast-planar eligibility additionally checks the published visual lifetime. This is
necessary on the last visible tick, when persistent lifetime is already zero: the scene
must still take the native effect path. The coverage fallback classification includes
that published state as well. Native hook bytes are checked before installation at
`$bc8a`, `$112e6` and `$112f4`. Diagnostics tagged `PDWEFX03` track publication/temporary
seed ownership, weather-loop generations, visual RNG events, generation attempts/selections,
actual draws and sound calls. `PDWECLK1` adds generation/visual deadlines and counts.
The installed draw JMP locates the live record; readers also accept the earlier
`PDWEFX01/02` capture formats.

Build and integration checks pass:

- All new hooks replace complete instructions; no decoded native direct branch enters
  their interiors. Both original-weather C3-off snapshots retain every declared native
  timing-hook byte.
- Explicit `TIMING_WEATHER_EFFECTS=0` reproduces the frozen full timing prototype byte
  for byte. The restored normal build reproduces its saved reference exactly.
- An invalid flag value and enabling effects without the periodic scheduler are rejected.
- `timing-weather-effects1-dry` passes 650-field A500/native and 030/fast runs. Against both
  unchanged `timing-contact13-1` references, 652 common world states and 144 common
  control/input/fuel updates match exactly. Diagnostics show 144/145 logical effect
  updates (030/A500), with zero effect events, attempts, selections, draws or cleanup
  and no pending visual state. The 030 adds 158 clean completed renderer twins with
  unchanged raster code; another draw is active at the endpoint and is not counted.

The frozen development artifact is `tmp/Powerdrome-timing-weather-effects1.slave`, built
with the same fixed-seed WORLD20/repair/pit-sync flags as the matched timing prototype plus
`TIMING_WEATHER_EFFECTS=1`. The dry-weather result validates integration only. Next observe
active lifetime/RNG publication and draw-seed restoration, verify cleanup and both render
paths, then move forecast/expiry and fade/gear progression to logical scheduling. Do not
report weather or the full F1–F8 feature complete from this bounded result.

### Active effect replay observations

`weather_effect_state.py` follows the installed `$112e6` JMP into the live slave and
locates its nearby `PDWEFX01` record, avoiding stale loader copies. `swap_fields.py`
now emits `PDWEFX_EVENT` for timing probes when that hook is installed, including private
publication/counter fields and native RNG, lifetime, delay, enable, transition and palette
state. Native builds without this hook acquire no extra effect-record samples.

`check_weather_effect_draw.py CAPTURE` checks owned draws at `$112f0/$112f4/$112fa`:
the published visual seed must be installed at entry, the native helper must advance it
four times without changing lifetime or publication, and the wrapper must restore the
saved outer seed and release ownership before native palette presentation. It counts
repeated draws of the same logical visual state, explicitly handles a first-draw anchor
snapshot and reports an observed partial final draw without counting it complete. Missing
boundaries and inconsistent state fail; the checker does not establish logical generation
arithmetic, pixels, cleanup or full weather timing. Explicit synthetic complete/anchor
cases pass; wrong installation, native advance, restoration and lifetime mutation are
rejected. Runtime evidence remains required.

The preliminary `timing-weather-effects1-active030` run on 030/25, route 6, was
intentionally stopped before reaching its first natural `$112f0` effect draw. Its log
is retained; it supplies no active-weather result. This was a deliberate switch to the
repeatable fixture below, not an inferred emulator failure or passing natural episode.
Natural integrated weather validation remains open after forecast/fade scheduling.
The normal build remains restored and unchanged.

### Repeatable effect-only fixture and first runtime result

`TIMING_WEATHER_EFFECT_TEST=1` requires VERIFY, COVERAGE_INPUT and
`TIMING_WEATHER_EFFECTS=1`. Once per process, on the first eligible logical control update
at or after 200 world steps, it enables effects with lifetime five and generation delay
four. It sets the forecast flag, clears transition and makes the two weather deadlines
inactive, isolating effect generation/drawing from forecast, fades and wind handling.
It does not rewrite simulation/input clocks or the random seed. `PDWEFT01` records the
activation count, world-step count and logical timestamp. This is directed branch coverage,
not a natural episode or A500 weather calibration.

The fixture builds; explicit zero reproduces the frozen effect prototype byte for byte,
a non-VERIFY request is rejected, and the restored normal slave still matches its saved
reference. `TIMING_EXTRA_PROBES` appends optional probes to the CPU matrix's mandatory
world/control probes, retaining all ordinary checks. No capture schema was changed while
a capture was running.

The 1,000-field (20-second) `timing-weather-effect-test1` A500/native and 030/fast pair
passes all existing per-run and cross-CPU checks. **1,004 common sampled player/engine/RNG
states and 223 control/input/fuel updates match exactly**. Both activate the fixture
exactly once at world-step count 204, logical timestamp 812 native units after the input
fixture epoch. Both execute 223 logical effect updates, including **five visual RNG events
and 176 unsuccessful generation attempts**. No new random effect is selected in this run.

The draw-ownership checker verifies **six complete owned draws on 030 and three on A500**.
The 030 repeats one logical visual state. Every observed draw installs its published seed,
performs the native four advances, preserves persistent lifetime/publication and restores
the outer seed. Thus the differing number of actual draws leaves matching sampled simulation
RNG/state and five logical visual events on both machines. Neither endpoint retains draw
ownership, pending cleanup, simulation debt or unfinished assigned work. The 030 adds
**256 clean completed renderer twins**, with unchanged raster code and no draw active at
the final snapshot. Effect draws themselves take the native fallback and are not those twins.

This first fixture has zero actual sound-trigger calls and zero successful new effect
selections, so it does not validate those branches. Its seed-preserving evidence is
separate from the explicitly seeded branch test below.

### Successful selection fixture

`TIMING_WEATHER_EFFECT_TEST=2` uses the same activation boundary and prerequisites as
mode 1, but sets lifetime and delay to zero and sets the logical RNG seed to 3705.
The native recurrence produces 640, selecting lifetime `(640 >> 7) & 5 = 5`, then
51585, selecting delay `(51585 >> 14) + 4 = 7`. This deliberate seed write belongs
only to the directed fixture. Clocks and input scheduling remain untouched. Mode 1
and the normal slave still rebuild byte-identically; invalid mode 3 is rejected.

`check_weather_effect_selection.py CAPTURE...` locates the live fixture record via the
installed effect hook. It requires the first selected publication at the recorded
activation clock, checks its seed/lifetime/delay and every subsequent logical publication
through delay expiry, then requires the next generation attempt. Cross-capture comparison
checks the relative publication clocks as well as lifetime/delay/visibility. Corrupted
seed, lifetime, missing-publication and delay-release evidence is rejected. This checks
the first selection lifecycle; it does not claim arithmetic coverage of every later
selection, native weather cadence or sound trigger.

The 1,000-field (20-second) `timing-weather-effect-test2` A500/native and 030/fast pair
passes. Both activate once at step 204 and show the exact first-selection sequence above.
Both finish with **five selections and 18 logical visual RNG events**, while actual draws
are **25 on 030 and 10 on A500**. All complete draws pass seed installation, four native
advances and restoration; seven 030 draws repeat a published logical visual state.
Neither endpoint retains effect draw ownership. **1,003 common player/engine/RNG states
and 222 common control/input/fuel updates match exactly**.

The 030 completes 1,003 movements and the A500 1,006. Their initial unsampled time is
80/140 ms and final unsampled time 20/20 ms, accounting for the three-step difference
without endpoint retained debt or assigned unfinished work. The 030 has **239 completed
renderer twins**, unchanged raster code and zero reported pixel/guard/register/scratch
failures; an additional scene is active at the endpoint and is not counted complete.
Effect draws use the native fallback, outside those twins.

Both runs still have zero actual sound-trigger calls. Cleanup, forecast/expiry,
fade/gear scheduling, natural integrated weather and mode/lifecycle validation remain
open. Neither directed fixture establishes the final weather cadence policy.


## Experimental logical weather fades

`TIMING_WEATHER_FADE=1` requires the experimental weather-effect owner and therefore
WORLD20. It remains disabled by default and uses the existing independent `CUSTOM3`
opt-in. The normal build and explicit fade-disabled effect fixture are byte-identical
to their saved references. A missing dependency is rejected. The new `$bd1a` hook covers
two complete instructions; no decoded native direct branch enters its interior. Both
snapshots of the native C3-off weather capture retain the declared native hook bytes.

`timing_weather_fade.s` moves transition mutations and native target-gear helper calls
into 20-ms world updates. It recognizes a changed weather transition, assigns a logical
deadline, and advances that deadline after each step. Every due simulation step runs
during catch-up. Only the latest absolute palette phase is published for presentation;
intermediate palette phases can be coalesced without coalescing transition/gear work.
The native palette helpers temporarily see their pre-mutation transition value, after
which the wrapper restores persistent state. Positive completion applies the native
weather palette; negative completion also draws the native zero-transition endpoint.
Native behavior is replayed outside supported human-flight weather ownership.

The candidate cadence is expressed in whole 20-ms simulation ticks:

| Direction | First step | Following steps | Fifteen-step logical duration | Measured native A500 episode |
| --- | ---: | ---: | ---: | ---: |
| Enter weather | 48 ticks / 960 ms | 70 ticks / 1,400 ms | 20,560 ms | 20,580 ms |
| Leave weather | 59 ticks / 1,180 ms | 58 ticks / 1,160 ms | 17,420 ms | 17,260 ms |

These are explicit calibration choices from one native track-2 episode, not proof of
an intended direction-dependent rule or a validated cadence across all tracks. The first
step delays deliberately reproduce that observed phase; the native global loop-counter
phase could differ in another episode. The steady periods approximate the measured
1,401.4/1,148.6-ms averages. This avoids silently applying the ordinary 90-ms control
period times sixteen, which would slow the measured exit fade by about 25%. Acceptance
still needs natural integrated weather and broader A500 reference coverage. Logical
deadlines do not guarantee that palette scanout occurs at exactly those physical times.

`PDWFAD01` records expected transition, deadline ownership, next deadline, pending palette
phase/kind, logical step/gear/presentation counts and transition start/latest-step clocks.
`weather_fade_state.py` locates that live record through the installed `$bd1a` jump.
Timing captures emit read-only `PDWFADE_EVENT` observations only when this hook exists.
The collector was updated before the capture and left unchanged during it.

`TIMING_WEATHER_FADE_TEST=1` requires VERIFY, COVERAGE_INPUT and the fade prototype, and
rejects simultaneous use of the effect fixture. At world step 200 it starts a positive
15-step transition with native forecasts/effect generation suppressed; one logical
second after completion it starts the negative transition. It changes no clocks, RNG
seed or input state. This is branch coverage on the regular track-0 input route, not a
natural weather episode or a track-2 reference replacement.

`check_weather_fade.py CAPTURE...` requires all 30 logical steps at their exact deadlines,
checks transition/deadline/gear state, and verifies each native gear-helper return against
the captured track table. Paired `$bd1a/$bd58` observations must preserve all logical fade
fields and native transition/target gear while consuming pending palette work exactly
once. Missing steps, changed deadlines, incorrect gear and presentation mutations are
rejected. Palette pixels and physical presentation latency are outside this checker.

The 46-second `timing-weather-fade-test1` A500/native and 030/fast pair passes all
30 steps and two native gear commits (targets 4 then 2 for track 0) at identical logical
deadlines. Both observe all 30 palette publications and finish without pending fade work.
**2,301 common player/engine/RNG states and 511 common control/input/fuel updates match
exactly.** The 030 adds **652 completed renderer twins**, unchanged raster code, zero
reported pixel/guard/register/scratch failures and no active endpoint draw. These scene
comparisons do not establish palette pixel equivalence.

The 030 completes 2,301 movements and A500 2,306. Initial/final unsampled time is
80/60 ms on 030 and 140/20 ms on A500, fully accounting for the five-step endpoint
difference. Neither retains simulation debt, unfinished assigned movement or a pending
control. Maximum sampled world-end delay is 240/780 ms; maximum allocations are 12/32
steps. Thus logical fade equality is established for this bounded route, while physical
palette latency, longer stalls and capacity limits remain separate measurements.

Forecast selection/start/expiry still use the original outer-loop paths and physical
clock. Moving these into the same logical RNG/time ownership is the next implementation
step. Actual effect sound trigger, natural onset/expiry integration, palette pixel
validation, pause/pit/restart and reused-transition lifecycle checks remain open. The
new weather flag predicate and reset hooks alone do not prove those lifecycle contracts.


## Experimental logical forecast/onset/expiry

`TIMING_WEATHER_CYCLE=1` requires the fade and effect prototypes, remains disabled by
default and uses CUSTOM3. During supported human flight it runs forecast trials and
onset checks on the logical 90-ms control schedule. Expiry retains an eight-control
phase gate (nominally 720 ms). Both consume the world owner's RNG/time, not render-loop
RNG or the physical clock. Those candidate polling cadences still need broader original
A500 calibration; this implementation does not establish final cadence acceptance.

The native `$e1a2` forecast and `$e1f8` onset routines are reused. Local hooks at `$e1c4`
and `$e23c` supply the logical clock only while the scheduler owns those calls; physical
clock reads remain intact for native callers. Forecast warning remains 5,000 native
units / 25 seconds. The onset retains the track table, native signed duration RNG math,
steering reset, transition and effect-enable selection. Expiry performs the native
persistent reset and queues its palette call. The human-flight predicate excludes the
positive-mode communications branch of `$e25e`.

The `$dd0e/$dde6` wrappers skip only the claimed forecast/deadline work, preserving the
surrounding HUD/status paths. Once claimed, the deadline domain remains protected from
physical outer-loop comparisons even when ordinary flight is temporarily suspended.
Session cleanup releases ownership. This prevents accidental physical reads of logical
deadlines; it does not yet establish correct progression through pit, rescue or restart.

The forecast's terminal message call is deferred through a hook on `$e1f0`'s ADDA/BSR,
leaving the shared `$e1f6` RTS available to the native early-return branch. Its queued
message pointer and logical message phase are delivered at world presentation; the
message-deadline helper uses that saved phase while delivering it. Message rendering
still applies the native visibility gates at delivery. Expiry's palette call is also
deferred to presentation. `PDWCYC01` records logical ownership, pending/delivered events,
trial/forecast/onset/expiry counts, clocks, selected duration and onset RNG inputs/results.

Initial ownership preserves negative sentinel deadlines and transfers the remaining
physical interval to the logical cursor. Due/overdue deadlines become due immediately;
the transfer clamps negative remaining time before adding the logical cursor. This fixes
a static edge case in the first candidate, where adding a negative clock offset could
turn a sufficiently overdue live deadline into an inactive sentinel. The completed
`timing-weather-cycle-test1` pair uses that first frozen candidate and enters ownership
with both deadlines inactive, so it cannot validate the corrected migration path. The
corrected source builds as `timing-weather-cycle-test2`; directed future/due/overdue and
clock-boundary runtime tests of actual mode ownership remain required, along with resume
rebasing and lifecycle handling. The private-cell helper test below now validates the
arithmetic itself on both emulated CPUs. The full weather-cycle observations from test1 apply to its inactive-deadline
entry path, not to all ownership transfers.

`TIMING_WEATHER_CYCLE_TEST=1` requires VERIFY, COVERAGE_INPUT and the cycle owner, and
rejects either other weather fixture. Once at a control update after world step 200 it
clears the seed so the native shift-2 trial returns zero (seed 0 becomes 1), with inactive
deadlines and no existing weather. It does not shorten warning or active duration or
rewrite a clock. The requested matched capture is 8,500 PAL fields / 170 seconds, enough
for this track's native maximum active duration and both fades.

`check_weather_cycle.py CAPTURE...` requires a single complete warning/onset/expiry,
checks the forecast deadline against the native D7 input, recomputes the unchanged
track-dependent native duration and RNG advance, checks onset/expiry polling bounds,
requires both deferred deliveries, and checks all 30 fade-step deadlines. It compares
logical histories across captures. Native cadence acceptance, actual message/palette
pixels, physical presentation latency and lifecycle transfers are outside its scope.
The first 170-second 030/fast run of `timing-weather-cycle-test1` passes: one warning,
onset and expiry, unchanged native RNG/duration arithmetic, all 30 fade steps and one
delivery each of the deferred warning message and expiry palette. Warning-to-onset is
25,020 ms, selected active duration 117,480 ms and expiry lateness 60 ms. Onset RNG is
47,712 → 64,161. No warning or active duration was shortened. The checker rejects wrong
warning time, onset RNG, active deadline, expiry reset and fade-step deadline evidence.

The run completes 8,502 movement steps and 1,889 control/resource updates, with no endpoint
retained debt, assigned unfinished movement or pending control. Initial/final unsampled
time 80/40 ms explains the two steps beyond the 170-second window. Maximum sampled
world-end delay is 260 ms. It adds 2,472 clean completed renderer twins with unchanged
raster code; a further scene is active at the endpoint and is excluded. Palette pixels
and actual weather-effect draw ownership are not checked by these scene twins. The effect
record shows 13 selections, 34 logical visual events and 52 actual draws, with zero actual
sound-trigger calls and no final effect ownership/pending cleanup.

The A500 counterpart also completes the entire 170-second cycle. Both have the exact
25,020-ms warning-to-onset interval, 117,480-ms selected duration, 60-ms expiry lateness,
onset RNG inputs/results, all 30 fade deadlines and one delivery of each deferred event.
**8,502 common player/engine/RNG states and 1,889 common control/input/fuel updates match
exactly.** Both effect records have 1,890 logical updates, 1,020 generation attempts,
13 selections and 34 logical visual events, while actual draws differ: 52 on 030 versus
25 on A500. Draw ownership and sound trigger are not directly observed by this probe
set, so their prior isolated tests and remaining gaps still apply.

A500 completes 8,504 movements, with 140/60-ms initial/final unsampled time explaining
its two-step endpoint difference from 030. Its maximum sampled world-end delay is 780 ms,
maximum retained debt 160 ms and maximum allocation 32 steps; all endpoint retained/assigned
work is drained. This is bounded full-cycle state equality, not final A500 cadence or
lifecycle acceptance. In particular, the effect-lifetime cadence gate below fails the
90-ms visual period despite this equality result.

Build checks pass: normal and explicit cycle-disabled fade-fixture bytes match their
saved references; a missing fade dependency is rejected. All new hook ranges contain
complete instructions, no decoded direct branches enter their interiors, and both C3-off
native-weather snapshots retain all declared native hook bytes. These checks do not
replace the running cycle captures or the outstanding migration/lifecycle work.


### Native effect-lifetime cadence gate

`report_weather_effect_cadence.py` reconstructs complete native effect episodes from
`$bd16` generation publication, `$112e6` positive-lifetime entry and `$112f0` final
lifetime decrement. It checks declining lifetimes and consecutive native loop counters,
rejects the experimental effect hook and requires the original 68000 capture. These are
mutation/draw-entry timings, not measured visible scanout durations.

`timing-weather-native-a500-effects1` contains 30 complete nonzero episodes, six zero-life
selections, 90 effect draws and no interrupted/pending episode. The **60 within-episode
intervals** average **139 ms in debugger PAL fields** (median 140, range 120–200 ms), or
140.667 ms in the game's sampled clock. The physical histogram is ten × 120, forty-five
× 140, four × 160 and one × 200 ms. An interval between separate adjacent episodes is
excluded; treating every adjacent draw as one episode would incorrectly count 61 gaps.

Generation-to-first-draw latency is 20–40 ms (mean 27.333, median 20 ms). Generation to
last lifetime decrement depends on the selected length:

| Native lifetime | Complete episodes | Mean | Range |
| --- | ---: | ---: | ---: |
| 1 | 12 | 26.667 ms | 20–40 ms |
| 4 | 12 | 443.333 ms | 420–460 ms |
| 5 | 6 | 586.667 ms | 520–680 ms |

The earlier 90-ms logical visual interval was about 35% shorter than the 139-ms native
interval. Its cross-CPU equality tests establish independence of render count, but **do
not pass the A500 speed gate**. The 83.283-ms generation-loop average includes the many
frames without an effect and must not be substituted for the active-effect cadence.

The `$bd1a` post-generation observations also resolve the generator ordering. Generation
precedes the upcoming draw with the same native loop counter; group the next generator
interval by that published lifetime, not the following interval's lifetime. There are
2,901 intervals without an upcoming effect, averaging **81.489 ms** (median 80, range
60–160), and 90 with an effect, averaging **141.111 ms** (median 140, range 120–200).
Together these give the earlier 83.283-ms aggregate. A five-life example selects at loop
3,633, decrements once in that loop's draw, then decrements generation delay before each
subsequent loop's draw. Its delay reaches zero at loop 3,637 before the final lifetime
decrement. No new selection interrupts a nonzero episode in this capture.

The current candidate implements a separate weather-loop schedule: **80 ms after an effect-free scene,
140 ms after an effect-bearing scene**, with visual publication **20 ms after generation**.
Generation eligibility/delay/trials come first; the next visual publication decrements
lifetime and accounts for four logical visual RNG advances. Preserve that order rather
than independently advancing delay at 90 ms. Repeated rendering still uses only the
published visual state. Clear the last visible publication on the following scene's
visual boundary. This gives generation-to-last-step values 20, 440 and 580 ms for
lifetimes 1, 4 and 5, respectively, close to this reference.

The seeded active-effect comparison now passes as described below. The full-cycle
comparison is running. RNG ownership, final-visible-state fallback and both buffers'
cleanup checks remain necessary; actual sound trigger is still unobserved. Calibration
across tracks and varied modes still needs evidence. This is an implemented candidate,
not final cadence acceptance for all gameplay.


### Direct deadline-transfer helper fixture

`TIMING_WEATHER_TRANSFER_TEST=1` requires VERIFY, COVERAGE_INPUT and the cycle prototype.
It invokes the actual assembled transfer helper on eleven private data cells once during
the first eligible logical control update. Cases cover two negative sentinels, future,
exactly due, recently and long-overdue deadlines, zero logical time, and values near the
native positive signed-clock boundary. It never changes native deadlines, clocks, RNG
or input data. `PDWTFR01` records the invocation/case/mismatch counts, inputs, results,
clock-register preservation and destination pointers.

`check_weather_transfer.py` follows the installed cycle hook to locate the live test
record in both snapshots. It requires every declared case, exact explicit expected
results, preserved physical/logical input registers and unchanged destination pointers.
This tests the transfer helper on emulated CPUs; it does not establish correct ownership
transfer through real pit/resume paths or beyond the native signed deadline domain.
The test-disabled build reproduces the corrected cycle candidate byte for byte, and the
normal build remains unchanged. The 650-field / 13-second
`timing-weather-transfer-test1` A500/native and 030/fast pair passes all eleven cases in
both initial and final snapshots, with one invocation and zero mismatches. It preserves
the input clock registers and destination pointers. Missing invocation, the old overdue
result, changed clock register, changed pointer and altered case-table evidence are all
rejected independently of the fixture's mismatch counter.

The surrounding timing run also passes: 653 common movement states and 145 common
control/input/fuel updates match exactly. Both end without retained/assigned simulation
work. This validates the corrected helper's arithmetic and its integration into the
inactive-deadline startup path; it still does not exercise actual pit/resume ownership
with live native deadlines.


### Calibrated effect schedule: first matched runtime result

`timing-weather-cadence-test1` uses the seeded mode-2 effect fixture and the new schedule
on A500/native and 030/fast for 1,000 PAL fields / 20 seconds. The fixture activates on a
weather-loop generation boundary at or after step 200, rather than an ordinary control
boundary. `PDWEFX02` keeps the earlier 48-byte record shape, but its tick count now means
generation boundaries and its clock means the latest visual publication. `PDWECLK1`
records both deadlines, both event clocks/counts, selected loop period and RNG results.
Capture readers identify the version through the installed hook; the old selection
checker explicitly rejects v2, while the draw-ownership checker supports both versions.

`check_weather_effect_schedule.py` pairs effect/clock observations with consecutive
20-ms world-step observations. It requires each mutation at its actual world deadline,
80/140-ms periods based on the upcoming scene, +20-ms publication, exact lifetime/delay
ownership and four logical RNG advances per positive visual publication. It also checks
that no logical weather field changes between scheduled boundaries. The seeded case
requires generation seed 51,585, lifetime five and delay seven, then verifies first
publication at 20 ms, last lifetime decrement at 580 ms, clearing at 720 ms and the next
generation trial at 860 ms. The last visible state must survive the intervening generation
boundary. Incorrect visual deadline, period, RNG, early clearing and world-clock evidence
are rejected. `--general` checks the same schedule invariants without substituting them
for the seeded first-episode checks.

Both CPUs pass. **485 common generation/visual states, 1,001 common movement states and
222 common control/input/fuel updates match exactly.** Both select three effects and
execute ten logical visual RNG events. Actual draws are **21 on 030 and nine on A500**;
all complete draws pass seed installation/four advances/restoration and persistent-state
checks. The 030 repeats eleven logical visual states. No draw owns the endpoint seed.

The 030 completes 1,001 movements versus A500's 1,006, fully accounted for by initial/final
unsampled time 80/60 ms and 140/20 ms. Both finish with no retained/assigned simulation
work. Maximum sampled world-end delay is 280/760 ms. The 030 adds **245 completed renderer
twins**, unchanged raster code and zero reported failures; another scene is active at the
endpoint and excluded. A500 has one scheduled visual publication at its next world cursor;
the checker verifies that it is not overdue and precedes the next generation. It is not
lost work or a completed publication.

Generation is now serviced before a simultaneous fade mutation, matching the native
outer-loop ordering. The frozen full candidate `Powerdrome-timing-weather-cycle-cadence1.slave`
includes this ordering and the corrected deadline-transfer helper. Its unshortened
8,500-field / 170-second full-cycle A500/030 pair is running. Until that completes, the
previous full-cycle results refer to the older 90-ms effect schedule.

The normal slave and effects-disabled full timing build remain byte-identical to saved
references. Hook boundaries and C3-off native snapshots pass; legacy effect draw/selection
captures still pass their version-specific readers. No cache policy changes were made.

## Palette data flow and remaining presentation proof

Native fade helpers `$8a1a/$8a60` pass source colour `state+$4b6`, the target colour
from table `$203e` (track index, or index zero for nonzero `state+$aa`), palette index 5,
and phase `15-transition` or `-transition` to `$17306`. The helper interpolates each
4-bit component using signed multiply/divide and arithmetic shifts. It writes entry 5
both through `state+$4b0` and through the colour-table pointer at `game+$4790` then `+4`.
Its final visibility gate controls whether `$16fe8` publishes the palette immediately.
Thus the fade is not just a diagnostic counter: it changes stored palette data.

Native restoration `$17062`, used by `$f914/$f948`, copies the other 15 palette entries
but deliberately skips entry 5. This preserves the current weather colour. `$f914`
selects its source table by track (special tables for tracks 1 and 3); `$f948` uses
`state+$4b0`. The renderer's `$117c8–$117d4` restoration and the fade's completion calls
must be checked separately from the weather audio helper.

The completed `timing-weather-cycle-cadence1` pair provides an endpoint check only:
initial and final snapshots have track 0, transition zero and view zero; entry 5 equals
its original source colour in both stored palettes, and all 16 entries of the saved
palette and colour table agree on each CPU. This does not validate intermediate phases,
all track/view choices or physical palette delivery.
`tools/weather_palette_state.py --require-restored CAPTURE...` reproduces this stored
endpoint check using live saved-palette and colour-map pointers in the captured chip or
expansion memory. It rejects out-of-range pointers/colour values, mismatched weather or
other palette entries and nonzero transition/effect state. The completed pair passes
all four snapshots; altered weather colour, another palette colour and transition state
are rejected. The module also expresses `$17306` signed integer interpolation. The completed directed
palette pair described below validates it against all 31 native calls on both CPUs.

`weather_palette_state.probe_command` now prepares read-only entry/return probes for
`$17306/$173a8` and `$17062/$1708c`. Each row includes all general registers, stack
return address, source weather colour, track/view/transition state, live palette pointers
and the saved/current/restoration-source arrays. Nested pointer bounds and alignment
checks guard each dereference against the captured chip/expansion regions; invalid
pointers emit `PDWPALETTE_INVALID` instead of stale or unbounded data. Only debugger
convenience variables are assigned. Command formatting/schema checks pass against the
completed pair's memory layout. Live GDB execution, caller classification and per-call verification pass in the completed
directed palette pair described below. Probes were integrated after the full-cycle run
finished, preserving its observation scheme.
The prepared schema also reads the guarded parent return address at stack `+4`.
`owned_fade_returns` follows the live `$bd1a` hook and identifies exactly the installed
positive, negative and negative-zero native helper calls. Initial/final snapshots on
both CPUs identify all three; altered installed hook, positive native target and
negative-zero restore evidence are rejected. This enables classification of interpolation
calls by both native and wrapper return addresses, instead of assuming every `$17306`
call belongs to logical weather. Live interpolation validation passes for the directed pair below.

`tools/check_weather_palette.py CAPTURE...` is prepared as a strict directed-fade
checker: pair complete entry/return records, classify the installed fade callers,
reproduce RGB4 component arithmetic, require exactly the 15 positive phases (0–14),
15 negative phases (15–1) and final zero phase, and compare both stored palette writes.
Restoration calls must copy entries 0–4 and 6–15 while preserving entry 5. Cross-CPU
histories are compared after pointer normalization through caller identity. Invalid
pointer markers, partial/missing calls, unexpected phase counts and changed palettes
fail. Endpoint-only cadence1 evidence is correctly rejected for lacking per-call probes.
Positive runtime validation passes for the directed pair below. This strict full-phase gate must not be
used to certify deliberately coalesced presentation; that needs separate due/published
phase accounting. Neither form proves physical scanout.

The next presentation checks should proceed in this order:

1. Observe `$17306/$173a8` around each owned fade call, recording source/target/phase/index,
   stored entry 5 and the active colour-table pointer. Independently reproduce the native
   signed integer arithmetic, and verify both writes without changing persistent timing.
2. Observe `$17062/$1708c` around restoration, checking entries 0–4 and 6–15 against the
   selected source while entry 5 stays unchanged. Classify caller return addresses so
   renderer restoration, positive completion and expiry are not conflated.
3. Check palette publication and scene-buffer identity together, then capture displayed
   frames at selected phases. Palette-memory agreement alone is insufficient scanout proof.
4. Repeat for both CPUs, active effects, both fade directions, relevant views/tracks,
   and a catch-up interval that skips intermediate presentations. Logical phase deadlines
   remain independently checked by the existing fade/cycle gates.

Do not add these probes to an already running capture. The direct-delivery full-cycle
regression intentionally retains its frozen observation scheme.

## Revised weather cadence: complete cycle regression

The frozen `timing-weather-cycle-cadence1` A500/030 pair completes 8,500 PAL fields per
CPU with `PDWEFX02` generation-before-fade ordering and the corrected deadline transfer.
Both pass `check_weather_cycle.py` and `check_weather_effect_schedule.py --general`:
4,217 common generation/visual states match on exact world deadlines. Warning-to-onset
is 25,020 ms, native selected duration is 117,480 ms, expiry is 60 ms late, and all 30
fade steps match. One deferred warning and expiry palette are delivered per CPU.
Both select 11 effects and execute 23 logical visual events, with 53 actual 030 draws
versus 23 A500 draws. These probes do not independently check every draw's seed restore.

The movement comparison matches 8,503 common states and 1,889 common control/input/fuel
updates. A500 executes 8,505 steps: initial/final unsampled time is 140/40 ms versus
80/20 ms on 030, accounting for the extra 40 ms. Maximum world-end delay is 780/260 ms
(A500/030), maximum allocation 32/12 steps, and maximum retained debt 160/0 ms.
Both finish with zero retained or assigned simulation work. A500's pending visual phase
is due exactly at its next world cursor; the 030 has no pending phase and its next
generation is 20 ms ahead. Thus neither endpoint contains overdue weather work.

The 030 completes 2,476 renderer twins with zero pixel/register/scratch/guard failures
and unchanged raster code. Its final additional active scene is unfinished and excluded.
This is a seeded full-cycle regression, not unseeded weather, audio playback, palette
pixel/scanout, general mode-transfer or whole-game framerate-independence acceptance.
Reports are saved as `cycle-check.txt` and `schedule-check.txt` within the capture pair.

## Weather sound suppression through native input

`timing-weather-audio-keys1` uses the same 1-MiB guest-memory seeded effect configuration
with `COVERAGE_AUDIO_KEYS=1`. The input tape publishes Tab at PAL fields 50 and 600.
Native `$c5fc` toggles `state+$2f4`; before/after probes at `$c5fc/$c600` check both
0→65535 and 65535→0 transitions and unchanged general registers. No fixture directly
writes the sound flag. The extra audio probes are read-only.

Both completed captures pass `check_weather_audio.py --require-mute`: the first
request at 4,860 ms is suppressed with all general registers preserved; requests at
15,740 and 18,840 ms complete native channel starts. All three generated requests are
accounted for, without coalescing. The pair matches 485 weather boundaries, 1,001 common
movement states and 222 control/input/fuel updates. Build guards reject missing VERIFY/COVERAGE and invalid values, while disabled
fixture and normal-build artifacts remain byte-identical. Deliberate stalls with closely
spaced requests and audible-output checks remain separate.

## Closely spaced weather sound stress fixture

`TIMING_WEATHER_EFFECT_TEST=3` is a VERIFY/COVERAGE-only fixture tagged `PDWEFT03`.
At the first weather generation with at least 200 world steps started, it sets delay 1,
zero lifetime and seed 557. Native generation decrements the delay to zero (request one),
then advances 557→44→6005, selecting lifetime zero and delay four. With four 80-ms
weather loops, the next delay expiry requests sound again 320 ms later. No clock, input,
resource-availability flag or native sample pointer is forced.

When combined with the existing `TIMING_STALL_TEST=500`, the stall starts after at least
190 steps rather than the usual 200, aiming to straddle those two requests. Actual stall
placement is measured from the live fixture. The completed 030 side of
`timing-weather-audio-stall1` confirms one 500-ms stall after 191 allocated ticks, with
world time held and then resumed without lost movement time. The sound-request checker
**fails**: the first pending request is still occupied when the second expires. The
single flag coalesces them. The weather schedule itself passes 487 observed boundaries;
maximum world-end delay is 560 ms and endpoint simulation debt is zero. The completed A500 side reproduces the same coalescing
failure. Both frozen failing captures are retained. The audio checker recognizes
the explicitly tagged first fixture request and still rejects an occupied queue when
another request arrives. Existing mode-2 and normal binaries remain byte-identical;
mode 4 is rejected. This fixture does not establish natural-weather cadence acceptance.

## Weather sound delivery at logical generation

`PDWEFX03` removes the lossy presentation flag. On an eligible delay expiry, the logical
weather routine calls `$17836` through a full-register-preserving wrapper before the
native selection RNG. It retains native resource availability and suppression checks.
The native helper may wait for audio DMA synchronization; that elapsed time enters the
existing time ledger. Catch-up can replay historical requests close together in physical
time; this does not reconstruct sound that would have played during an external stall.

The corrected `timing-weather-audio-stall2` 030 capture passes all four generated requests
at 4,000/4,320/8,460/11,740 ms relative to initial generation, including the previously
coalesced pair. Each native call lies at the current logical world/generation boundary,
with unchanged weather state across the helper. Sample/channel/register checks pass.
Calls take 0–40 ms in PAL fields; measured maximum world-end delay is 580 ms, maximum
allocation 30 steps, and endpoint retained/assigned debt is zero. The measured stall
is 500 ms, world hold/resume and all 485 common weather boundaries pass. The completed
A500 counterpart delivers the same four requests at identical logical times, also with
0–40-ms helper durations. Its maximum world-end delay is 1,240 ms and retained debt
peaks at 480 ms; both retained and assigned work are zero at the endpoint. The pair
matches 1,002 common movement states and 222 control/input/fuel updates. The 030
completes 241 renderer twins with unchanged raster code and zero failures.
The normal build is byte-identical. A full weather-disabled timing prototype also matches
the pre-fix source byte for byte. The current instruction-boundary/direct-branch audit
passes. Both old failing captures still fail request accounting.
Direct-delivery mute (`timing-weather-audio-keys2`), no-resource
(`timing-weather-audio-nosample1`) and full-cycle (`timing-weather-cycle-cadence2`)
regressions are queued in sequence, stopping on a failed gate. The corrected mute
pair passes on both CPUs: native flag transitions, one suppressed call and two resumed
starts at the original three request times. Earlier green captures
exercised the deferred implementation. Broader lifecycle acceptance remains required.
The audio checker's `--require-unavailable` mode requires absent optional samples, an
observed delay expiry, no weather helper call and zero queue/call counters across sampled
boundaries. Both no-resource CPUs pass that guard, a measured 500-ms stall, world hold/resume
and 485 common weather boundaries. They match 1,002 movement states and 222 control/
input/fuel updates. Maximum world-end delay is 560/1,200 ms (030/A500), with maximum
retained debt 0/480 ms; both endpoints have zero retained/assigned work. The corrected
full-cycle 030 side now passes warning/onset/expiry, native duration arithmetic, all
30 fade steps and 4,217 weather boundaries. Its normalized weather history also matches
the preceding deferred 030 capture. Stored palette endpoints are restored; maximum
world-end delay is 280 ms, with zero endpoint debt and 2,520 completed renderer twins.
A500 is running; full cross-CPU direct-delivery cycle acceptance is still pending.


The directed `timing-weather-palette-test1` 030 capture completes 46 seconds with all
31 native interpolation calls matching component arithmetic and both destination
palettes. One complete restoration preserves entry 5 while copying the other 15 colours.
`weather_palette_publication.check_publications` links calls in log order to pending
logical phases at `$bd1a`, checks consumption at `$bd58`, and verifies presentation does
not mutate persistent fade state. All 30 publications match, including the additional
negative-completion zero phase. Missing and duplicate calls are rejected. The completed A500
counterpart passes the same 31 calls, 30 logical publications and one restoration;
normalized phase/source/target/colour histories match across CPUs. The pair also matches
2,304 common movements and 512 controls, with zero endpoint simulation debt. This is
stored palette evidence, not scanout acceptance. Current-code effect coalescing and
restoration are being checked separately by `timing-weather-effect-publication1`.
