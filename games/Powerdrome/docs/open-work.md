# Open work

## Current state

The original slave is reconstructed and rebuilds byte-identically. The WHDLoad 20 KickEmu
rebase has VERIFY input fixtures for the title demo (`CUSTOM5=1`) and Practice (`CUSTOM5=2`).
Practice uses Enter → native practice-button shortcut → Space, then captures at the first
pit departure animation iteration (`$14764`). A single 500-field A500 trace covers ten nominal
PAL seconds, including the ship leaving the pit, the cockpit transition and track gameplay.
See development for the command, internals for the route, and the
[practice profile](practice-profile.md) for measured phase costs and optimization priorities.
Track edge/span rasterization takes 54.27% of recorded cycles; background filling takes 8.45%.
The optional fast planar renderer is implemented behind `CUSTOM1=1`, off by default.
It stages the normal cockpit scene, copies the validated 21,600-byte extent back to chip
RAM, moves the rasterizer into fast RAM, and replaces hot branch
rewriting with static span loops. The original elapsed-time simulation and presentation
sequence remain intact. See [implementation and verification](performance-implementation.md).

A complete ten-second combined twin run passed 66 completed staged scenes with no pixel,
scratch, register, condition-code or guard failures. Copied code remained unchanged.
Independent 500-field 68020 measurements improved from 15.68 to 22.20 nominal PAL
presentations/s. Bitmap staging alone was approximately break-even; scratch relocation
added negligible benefit and remains a VERIFY experiment. A fresh final-build run reproduced
the full 500-field presentation sequence. The 68000
fast-RAM comparison slowed from 11.32 to 9.35 fps; the option remains off by default.
No-fast-RAM fallback preserved native hook bytes, imagery and frame cadence. These are
emulator results, not real-accelerator performance claims. The complete original Practice
baseline now has an identical 500-field fresh-boot repeat.

The title-demo baseline at revision `02dbc27` has two matching fresh-boot A500 traces and
independently verified frame counts on A500 and 68020 (9.7 and 13.2 demo fps). Those title-demo
figures are separate from the practice launch profile.

## Accelerator and cache validation

The uncached 68030/040/060 timing matrix and code-write audit are complete.
See [accelerator testing](accelerator-cache-testing.md). The driving measurements are
19.56 → 30.12 fps on the requested 030/25 configuration, 17.91 → 41.57 on 040/25,
and 17.91 → 42.99 on 060/50, including the selected raster refinement; these are emulator figures. Lower-frequency checks respond
to the requested clock. Physical-board validation is outside the selected scope.

Cache selection is left to the user's standard WHDLoad `CACHE` and `DCACHE` options.
There is no custom cache toggle or policy in either build. The native fallback still
rewrites two branch displacements; these results do not certify every user-selected
cache configuration. Shared KickEmu startup remains unmodified.

MMU testing also corrected the development loader's invalid DOS launch arguments and
exposed two register-comparison cases: an already-identical numeric value resembling a
bitmap pointer, and an empty-scanline colour-table pointer in `a4`. The verifier preserves
exact matches; return normalization now includes the relocated `a4` code pointer. The
first mismatch snapshots are retained for diagnosing future failures. Simulation timing
and renderer selection are unchanged. Final 68000/68020 twins, the no-fast-memory
fallback and normal-build launches also passed.

## Loader equivalence

The [loader comparison](loader-equivalence.md) resolves the legacy Copylock D2 question:
the game overwrites the value before use, and matched 68000/68020 captures converge.
Relocated game text, main state after explicit allocation/timing allowances, and name-entry
bitmaps match. Pit pixels differ only in elapsed-time digits. The loaders are not timing-
identical: the tested 68000 development run has a longer pit/departure sequence. Continue
performance A/B tests on the same development loader; this result does not certify all
long-gameplay routes.

## Raster refinement

The [numbered raster plan](raster-improvements.md) is complete (R1–R5). Direct plane-address
construction removes three instructions per nonempty row on 68020+, reducing matched-shape
fast-raster instruction costs by 1.01%. Independent 020/030/040/060 throughput gains are
0.20% / 0.33% / 0.98% / 0.70%, with exact final-build repeats. The 68000 trial failed the
throughput gate, so 68000/68010 retain their previous loops; the 68000 baseline sequence
repeats exactly. Endpoint masking and fixed-point edge changes were rejected.

Final ten-second twins validate 637 completed staged scenes across five CPU configurations
and the scratch-memory experiment, with zero reported mismatches and unchanged code. All
sixteen colour loops pass a structural audit. Option-off and no-fast-memory fallbacks retain
native hooks. Slave size grows by 100 bytes; renderer memory and simulation/cache policy are
unchanged. `CUSTOM1` remains off by default.

## Gameplay coverage and remaining scope

The [coverage campaign](gameplay-coverage.md) is complete (C1–C5): 30,623 staged scene twins
pass with zero mismatches, including longer races, moving opponents, views, collisions,
rescue/repairs, pit re-entry, restarts and natural weather routing. Exact repeats, title
inset, option-off and no-fast-memory checks pass. Normal and ordinary VERIFY builds remain
byte-identical; the input fixture is a separate development build.

No work remains in the completed renderer performance plan. Coverage is bounded to the
documented routes; guards and the off-by-default option remain unchanged. Widening supported paths
would require a separate validation effort. The selected implementation stages planar scenes
in fast RAM and copies them to the chip back buffer. Native elapsed-time simulation and
update order remain intact; a new scheduler or timestep policy was outside that completed scope.

## Simulation timing work in progress

The [framerate independence analysis and plan](framerate-independence.md) selects a smaller
A500-calibrated approach first: lower the PAL movement minimum to 20 ms and move per-frame
mutations to an elapsed-time cadence matching original A500 behavior. A logical base tick
is 20 ms; each operation runs every measured N ticks or equivalent rational period,
independently of drawing. This does not yet promise identical variable-step trajectories.

F1–F8 are `timing-map`, `timing-baseline`, `delta-20`, `periodic-split`, `a500-cadence`,
`timing-modes`, `timing-matrix` and `timing-release`. Implementation is now authorized.
F1/F2 are in progress; the isolated F3 correction is built and being validated. The cockpit
liftoff correction passes A500/030 checks at 100 ms per native step and is included in
experimental `CUSTOM3`; it preserves the nine-step geometry and final speed. A separate
F4/F5 control/orientation/resource prototype includes separately timed braking, with 15/15
input events preserved across A500/030. Timestamped button/modifier inputs now produce 19
identical early logical acceleration updates across A500, 030 and twin rendering. The
dedicated pause route preserves input debt and fractional time while excluding 49 paused
PAL fields. Those input and pause runs add 74 and 75 clean renderer twins. The input
prototype now separates external mouse deltas from logical axes and reuses the native
joystick response against historical samples. A500/030 mouse runs each pass 56 logical
state updates; the 030 run adds 77 clean renderer twins. A500/030 joystick runs likewise
pass the native response check. Timestamped braking now fixes the ordering difference:
all 55 complete common speed/input updates match across A500/030, including braking and
release, with 15 exact brake timestamps and 61 clean 030 twins. Resource mutation now
also runs after each logical control: 55 common fuel updates match exactly across A500/030,
with another 61 clean twins; the pause regression adds 75 clean twins. A native A500
comparison passes the 10% fuel gate for the measured 4.4-second interval. High-speed
joystick braking still differs substantially (native settled speed 108, periodic 53),
so response calibration is not complete. The explicit engine prototype now schedules native cooling/failure decisions after logical
controls and defers failure presentation until drawing. Sustained-boost A500/030 runs each
pass 178 logical updates, both thermal failures and all six ordered presentation events;
the 030 adds 211 clean renderer comparisons. Engine calibration, random-stream ownership,
repairs and other mode transitions remain open. Boost heating now has a private native RNG
stream and an explicit fixed-seed test mode. Its A500/030 arithmetic checks pass, but the
full matched-seed heat route fails equivalence after the first engine failure: an A500
incident resets speed 407→0 and directly invokes controls outside the logical scheduler.
Movement probes additionally show nested presentation overwriting the movement delta:
a 220-ms gap used only 20 ms on the 030. An explicit `TIMING_MOVE_CLOCK=1` experiment now
owns a separate unpaused movement timestamp and exposes upper-clamp losses. Its first
030 run verifies 52 intervals but still discards 490 ms above the cap. The corrected
wrapper also passes a 49-field pause exclusion with 76 movement intervals and 75 clean
renderer twins. The next priority remains historical speed integration, incident/control
chronology, collision subdivision and blocking presentation effects; do not treat passing
arithmetic checks as full engine-history or movement equivalence.

A separate `TIMING_WORLD=1` extraction pilot now couples each 90-ms control epoch with
movement, track transitions, collisions and opponents before drawing, and isolates the
world RNG from ordinary drawing. Recovery animation no longer advances opponents per
frame. The corrected A500/030 boost route matches all 55 common world/engine states and
96 timed boost draws through the incident and both thermal failures, with 52 clean 030
renderer comparisons. The common-exit cleanup build also passes 56 world updates through
a 50-field pause, all 15 brake events and 77 clean twins. This is an extraction milestone,
not the final physics rate.
`coupled-20` now has a development-only 20-ms world cursor with rational 90-ms controls,
resources/engine and opponents. Scalar/vector division remainders preserve fractional
movement. The matched A500/030 throttle/brake route passes all 253 common sampled world
states, 56 fuel updates and 15 brake events, with no outstanding movement debt; the 030
adds 74 clean renderer comparisons. Independent guest arithmetic probes verify both
fractional carries. The pause route excludes 48 paused fields, preserves the time ledger
and fractions, and adds 75 clean renderer comparisons. Falling and impulses now integrate
20-ms displacement with signed remainders and exact local 90-ms age/decay boundaries.
The ten-second A500/030 failure route matches 501 common sampled world states; independent
arithmetic checks pass 181/178 falling steps, and the 030 adds 98 clean renderer comparisons.
The centering route passes 490/495 impulse steps and 109/110 native resets, with another
143 clean twins. The subsequent mixed command route below covers nonzero impulses on
all axes and full expiry; fall limit/reset and opponent-contact generation remain untested.
Timestamped C/X/Z publication and historical movement modifiers now fix the centering
route's earlier CPU divergence. The final C-key A500/030 pair matches all 501 common
centering/modifier histories and sampled world states, with nine exact command timestamps
and another 144 clean renderer comparisons. The final pause regression verifies 253
movement-modifier states, excludes 50 paused fields, retains all 56 fuel/15 brake updates
and adds 76 clean twins. The A500 centering capture ends with two assigned
unfinished steps (one control started); strict endpoint accounting distinguishes these
from completed work. The mixed C/X/Z route now matches 754 common sampled world and
command/modifier states across A500/030, verifies 13 command timestamps, and adds 244
clean twins. It covers nonzero impulse components on all axes and three complete
900-ms logical impulse lifetimes. Native A500 comparison measures boundary durations
of 800/900/1,120 ms versus 880 logical ms: the third exceeds the frozen duration tolerance,
so impulse calibration remains open. Physical observation latency also varies despite
matching logical states and zero final debt. The C-key upper cap, hardware publication,
queue wrapping and keys across mode changes remain untested. Those and the remaining
force coverage precede logical mode clocks, mode/debt lifecycles and the full
calibration/capacity matrix.
The expanded input queue also passes the 030 pause regression with 78 clean twins.
Response/resource calibration, collision/input mode lifecycles, other frame-counted behavior
and the remaining F6–F8 checks are still open. See [timing implementation](timing-implementation.md) for current evidence.

The shared-clock audit now accounts for all 85 relocated absolute references (79 reads,
four stores, two read/modify/writes). Besides pause and reset, the native game restores
saved clock values and adds a gameplay time adjustment. Opponent repair/lap timestamps,
rescue deadlines and contact timing need paired logical-clock conversion. Blocking waits,
including a 200-ms sound shutdown outside the gameplay address range, must retain advancing
physical time. The next F6 implementation step is the paired opponent repair clock after
its callers and state lifecycle are audited; a global frozen-clock substitution is unsafe.

The WORLD prototype now closes timing at `$c2aa`, after native ending animation and
before menus. Early `$bf32` is not a reliable close point because it can resume gameplay.
The input-only Practice restart route passes two closures and two new gameplay entries
on both 030 (1,800 fields) and A500 (3,600 fields), with 228 clean 030 renderer twins.
Menu/pit-setup time is excluded from new-session movement; queue ownership and deadlines
start fresh. These runs have zero pending work at closure, so nonzero discard, interrupted
steps, same-session pit return and rescue remain unverified. Native Shift-Q publication
is still frame/mode dependent; this is lifecycle coverage, not matched full trajectories.

The native-rescue regression first exposed 65.64 seconds of pit time becoming player
movement debt. The corrected WORLD20 boundary now suspends flight input, records four
discarded assigned updates, retires the interrupted tail and initializes fresh player
deadlines on return. Both 030 and A500 resume with one 20-ms step and zero debt and preserve random
streams and logical cooling phase; the 030 passes 422 renderer twins. A500 explicitly
discards seven assigned updates after a 100.58-second pit interval. All 1,052 sampled
pre-pit world states match the failing reference. Native repair/audio time keeps advancing.
The opponent prototype now carries an independent 90-ms deadline, phase and remainder
from timed flight into rescue pits and back. Flight uses logical world time, pits use
unpaused physical time, and native clock views follow the scheduled opponent deadline.
The current 030 capture verifies the handoff: 100 ms after the pit cutoff becomes one
90-ms update plus 10 ms residual, while the player resumes with no pit debt. It checks
4,444 movement samples, 682 pit ownership restores, 659 resumed world counter restores
and 32 logical lap-clock results. All 1,049 common pre-pit sampled player/engine/RNG states
match the prior scheduler, and 416 renderer comparisons pass. The same artifact passes A500: 50 ms residual plus 200 ms after cutoff becomes two 90-ms
updates plus 70 ms residual. Its checker validates 7,112 movement samples and 52 logical
lap-clock results. Actual opponent multiplication operands already differ at the first
common sampled update, so matching initial opponent state remains necessary for trajectory
comparisons. The current restart regression passes two closures/reentries and 228 renderer twins.
The pause regression excludes 48 fields, verifies 255 world steps and 224 opponent
movement samples with zero outstanding debt, and adds 75 twins (719 current-build twins
total). Full opponent arrays, repair-clock cases, initial setup,
nonlocal exits, pause/epoch changes and native calibration remain F6 work. Native repair/
setup/presentation timing still makes whole pit visits CPU-dependent.
Nonlocal pit exits and other pit-entry paths remain unverified. The normal build is unchanged.
Controlled native initialization is now available through the explicit VERIFY-only
`TIMING_SETUP_SEED` flag, with read-only capture of all four 190-byte opponent records.
It establishes matching complete records immediately after initialization on A500/030,
but they already differ before timed flight: initialization-to-flight takes 7.14 seconds
on 030 versus 16.90 on A500, with matching speeds but different track positions. This
localizes the next work to the initial setup/pit interval; unequal-time snapshots alone
are not proof of unequal movement rates. The initial-pit prototype now starts the opponent
timeline before flight and preserves it across the handoff. All 62 common complete
four-opponent records and random states match during the active pit at equal elapsed
deadlines (90–5,580 ms). The 030 adds 192 clean renderer comparisons. Player work remains
inactive before flight. A500 retains a 6,560-ms departure tail and serves it over three
capped allocations without losing time; the 030 tail is 1,720 ms.

The final ordinary retune boundary passes the A500/030 pair: six old-speed updates (540 ms)
on 030 and 57 (5,130 ms) on A500 complete before native speed changes. All 68 common complete
opponent snapshots and random states through 6.12 seconds match, with guest-observed flags,
caller registers and stack depth preserved. The later first-winner revision stops the
interrupted opponent body and explicitly retires unfinished time. A VERIFY-injected initial
result passes correct native stack delivery, six retired assigned updates plus 60 ms debt,
no subsequent opponent movement, and native cleanup followed by fresh player/opponent clocks with zero inherited debt;
52 renderer comparisons pass. Mode snapshots confirm this is a qualifying-to-race transition,
so natural race-finish ranking and duration remain separate requirements. The rescue-result fixture also passes: six retired updates plus 80 ms residual, correct
additional stack unwinding, fresh race clocks without debt, and 437 clean renderer
comparisons. The final ordinary 030 regression adds 192 clean renderer comparisons (681 across the
ordinary and two result fixtures), and its A500 counterpart passes timing/ownership checks.
Ordinary 030 rescue and pause now pass: rescue carries 50 ms residual into an
80-ms return interval and serves 90 ms, retaining 40 ms; pause excludes 50 PAL fields
with no queued input leakage or time debt. They add 414 and 76 clean renderer comparisons.
Session restart also passes two native closures and two fresh entries, adding 232 clean
renderer comparisons. Wider A500 lifecycle checks remain. Unforced ten-lap finishes now validate the five-pilot list and native ordering. Result
duration is 20 ms late on 030 and 40 ms late on A500 relative to each logical winning
instant; different winners mean these runs are not trajectory-equivalence evidence.
The opponent result-clock latch passes the corrected 030 natural finish: reported and
logical duration both 215,020 ms, removing a 60-ms physical-read delay in that run.
Corrected A500 reported/logical duration both equal 227,920 ms, removing a 40-ms delay.
Caller registers, flags, five-pilot ordering and cleanup pass on both CPUs. Player finishes, other
result modes and deferred-pit duration remain open. The forced-outcome test does not establish those requirements.
The native A500 external-animation calibration now passes all 17 table steps and stack
checks: nine 80-ms intervals, five 60-ms intervals and three 40-ms intervals, totaling
1,140 ms through return. Unpaced 030 takes 820 ms. The WORLD20 prototype now paces
this sequence using cumulative elapsed deadlines: 030 measures 1,120 ms and A500
1,160 ms in PAL fields, both within one field of the native target at every boundary.
The 030 guest-clock schedule matches exactly; A500 has at most 20 ms lateness. All
17 positions and stack checks pass. Full pit-to-track checks now pass on both CPUs,
including retune register/flag/RNG preservation and exact time accounting; 188 completed
030 renderer comparisons report no failures. All 72 common opponent snapshots through
6,480 ms match. The extended through-departure gate remains **failing**: 194 of 266
snapshots differ, first at 6,570 ms after the 030 retunes earlier than A500. Their event
histories are unequal, so whole-trajectory equivalence is not established. A VERIFY-only
synchronization experiment holds retune/return to 18/24 seconds without rewriting state.
Both CPUs reach those times exactly and pass time accounting; the 030 adds 64 completed
renderer comparisons. The synchronized comparison still fails: 82 of 336 snapshots
differ, first in lap timers at 22,950 ms (2,580-ms discrepancy); RNG agrees throughout.
From 25,650 ms, persistent opponent animation fields also differ. Native `$11228` calls
`$9950` while drawing and advances these fields per render. The stable lap-clock
prototype passes initial-lap checks on both CPUs. Lap timing and RNG now match across
all 336 common snapshots. The WORLD20 opponent preparation split now advances native
animation/contact/effect preparation every six 20-ms world ticks while projection remains
per render. Its paired run has 335 common snapshots: nine differ solely in projection word
`$54`; all other words and RNG agree. Forty animation transitions pass on each CPU, and
64 completed 030 renderer twins are clean. Native A500 calibration remains failing for
pilot 1 (2,040 ms versus 920 ms for the visible nine-update prefix); both CPUs reproduce
the same visibility gap. Pilots 2–4 take 960 ms and pass both calibration limits. The full
record gate remains failing. A 50-field effective-address audit finds 55 projection-word
accesses only at the known drawing sites; all 17 reads follow a fresh per-view producer
across all four pilots. Unexecuted paths and accesses outside the game hunk remain unaudited,
so no comparison field has been masked.
The native mode-7 countdown reset now rebases the stable lap epoch at `$dbd8`, while
preserving the native five-pilot and race-start reset. A 2,000-field 030 capture verifies
one rebase, all five loop visits, four unchanged opponent reset stamps and eight subsequent
lap-clock reads; it removes a measured 70-ms clock-domain mismatch. The matching
2,000-field A500 run passes the same reset/read checks and removes a 410-ms mismatch.
Alternate reset entry and guest flags/registers remain to verify. Pause/rescue/clock adjustments and total
result clocks still need coverage. The result latch now uses each opponent step's stable
lap-domain instant. The corrected 030 natural finish reports exactly 215,060 ms and passes
ranking, caller registers/flags and cleanup; the sampled mapping would be 60 ms later.
The A500 stable-domain finish also passes at exactly 226,290 ms; its sampled mapping is
120 ms behind. Winners differ, so these are timing-accounting checks, not trajectory
equivalence. Player/deferred/mode-specific results remain to validate. The player path
must keep lap storage (`$10bf0`), displayed elapsed time (`$f108`) and result entry
(`$f9f0`) in one clock domain; Practice needs an origin independent of opponents.
A 300-field 030 baseline confirms the first natural player crossing is inside a logical
world step and starts lap zero without charging a lap duration. Its 118 cockpit clock
reads differ from retained-world elapsed time by -20 to +680 ms, ending at zero. This
is baseline evidence, not completed-lap validation. The WORLD20 prototype now keeps a
private logical lap start while retaining native `$206`. Corrected 300-field first-crossing
captures verify 118 exact logical HUD outputs on 030 and 37 on A500, with preserved native
starts and no reset fallback. The A500 physical/simulation-progress gap reaches 1,580 ms;
the timer correction does not prove real-time throughput. Practice now passes 182 logical
HUD outputs with no initialized opponent timeline. A guarded player-finish latch captures
the actual player world step as source 3. The explicit forced boundary/checkpoint/finish
fixture verifies a 500-ms synthetic lap, accumulated total and result duration, native
sentinel/registers/stack, duration flags, sorting and cleanup on 030. The fixture is off
by default and does not prove natural laps or victory. The A500 directed counterpart
passes the same 500-ms accounting and contract checks. A new input-only `CUSTOM5=14`
Practice route schedules pause after the natural first lap start. On 030, it excludes
49 PAL fields while preserving private/native starts and logical clocks; 70 logical HUD
outputs (26 resumed) pass, with no reset fallback and 61 clean renderer comparisons.
The A500 counterpart also passes: 47 excluded fields, 53 exact logical HUD outputs
(16 resumed), unchanged timestamps and no fallback. The latest 030 rescue regression
preserves initialized lap starts across 67,520 ms in the pit, passes 437 logical HUD outputs
(179 resumed) and 32 stable-domain opponent lap reads, and adds 394 clean renderer twins.
It also verifies one **natural completed player lap of 92,220 ms**, including native total,
best time and lap index, with all three synthetic finish predicates disabled. The A500
counterpart passes a 103,540-ms pit interval, 556 HUD readings (404 resumed), 52 stable
opponent lap reads and one natural 128,300-ms lap with matching records. Its full opponent
continuity check passes 7,116 movement samples and 2,819 world restores. The different
CPU histories are not trajectory equivalence or throughput evidence. Additional natural
laps/modes, natural player victory and external-reset fallback remain to verify.
Guest flag/register/stack checks now pass the initial lap boundary plus 75 HUD hooks
on 030 and 37 on A500. A separate natural completed-lap window passes the 030 logical
92,220-ms duration, native records and 82 HUD contracts, adding 73 clean renderer twins.
The A500 completed-lap contract also passes: 128,380 ms, matching native records and
55 HUD hooks. Broader mode/arithmetic cases remain open. The next concrete timing
correction is the repair-animation pilot. Both variants/directions now have complete
native A500 baselines. `TIMING_REPAIR=1` (default off, requires WORLD20 and CUSTOM3)
paces both 33-step stages with cumulative deadlines and measured minimum sound/display
pauses. The 030 run passes all 264 word-geometry/deadline samples and exactly matches
native invocation times of 8,260 / 8,840 / 7,900 / 7,960 ms. The A500 counterpart fails
by 120–860 ms. With repair pacing disabled, the same full timing prototype is already
100–820 ms slower than native, so adding waits cannot close that gap. Paired 50-field
instruction traces now isolate eight complete first-stage steps: their WORLD20 total is
13.277 ms longer, with 10.121 ms added in opponent service. Body composition and copying
remain large existing costs; display waits vary with refresh phase. Extend the complete-step
attribution across the stage and reduce or separate work without dropping simulation time.
The matched longer traces now cover 32 complete steps: WORLD20 executes 42 opponent
updates versus native's 32 and takes 113.172 ms longer. A message-lifetime mismatch
also keeps costly text drawing active: native has 27 counter increments remaining at
repair entry, WORLD20 254; native expires the message for the final five steps while
WORLD20 does not. A read-only setter/consumer trace confirms that an opponent phase
escapes into the outer pit's message deadline. The new WORLD20 helper uses the saved
outer counter for that pit publication; three A500 register/SP/deadline contracts pass,
and native message expiry now occurs. The complete unpaced A500 repair regression
preserves all 264 geometry states and shortens the four invocations by 400–960 ms,
but durations still fail calibration. Uniform pacing on the corrected baseline passes
one full case, with the other invocations 120–520 ms long. The next candidate preserves
all 264 measured native per-step deadlines instead of uniformly dividing stage totals;
all geometry/deadline checks pass, but A500 timing still fails in three cases (160–520 ms
long). The next step is reducing or separating repair drawing while retaining logical
updates, input/opponent service and nonlocal stack behavior; changing the deadline
schedule alone did not remove the throughput constraint. A disabled-by-default
TIMING_REPAIR_DROP prototype now separates late presentation from native service:
234 rendered plus 30 dropped pictures preserve all 264 geometry/deadline observations,
with suppression cleared at every step. Three A500 invocation gates pass; the fourth
is 60 ms long and still fails the conservative gate. Carrying lateness across stage
transitions resolves that measured failure: repairdrop3 passes all four A500 invocation
and eight stage gates, all 264 geometry/deadline observations and exact stage-epoch
transfers. Whole durations are within 0–40 ms of native, including the unchanged
conservative uncertainty gate. It draws 234 presentations and drops 30. The 030 counterpart
passes all geometry, deadline, stage-transfer and timing checks, matching all four native
invocation durations exactly and drawing all 264 presentations. This pit window adds no
3D renderer comparisons. The complete A500 buffer capture now verifies all 264 step pairs:
all 30 dropped steps preserve both screen buffers and the pit background byte-for-byte,
and all 180 part-bank selections survive. All 234 drawn steps exchange buffers normally;
the native outer service counter advances exactly once in every step. The same capture
passes all geometry and timing gates, with no incomplete or busy-entry exclusions.
The dedicated service capture also passes: all 264 steps call opponent service and poll
keyboard availability once, including all 30 dropped pictures. The ledger verifies 1,772
movement samples, 298 restored pit calls and twelve stable-domain lap-clock reads, with
exact bounded service and retained debt. Those keyboard polls are empty. A separate
input-only fixture now verifies one `x` published on a dropped step: native availability,
exactly-once consumption, writer/reader indices, command handoff and key-reader/repair
stack restoration pass. Its complete route has 236 drawn / 28 dropped steps and 263 empty /
one nonempty poll; it is input evidence, not a new timing claim. Special commands,
queue wrap/capacity, concurrent producers and exits remain to test. Independent native pixel equivalence,
skipped drawing-register/HUD scratch state, full opponent-record equivalence, native exits
and broader modes still remain open; both
experimental repair switches stay disabled by default. Ordinary flight-message publication
and expiry now share the logical control phase in WORLD20: A500/030 each pass thirteen
publications and two clears at 45 phases (4,050 ms), with 204/241 expiry branch/register
checks and 294 clean completed 030 renderer comparisons. The three pit publication
contracts still pass. The WORLD20 lap hook now preserves the logical message deadline
while retaining native D1/register/stack results; a paired 030 natural-lap check observes
the old 1,045 → 693 subtraction and the corrected 1,044 → 1,044 preservation at phase 352.
A500 also passes one inactive deadline at 849 → 849. The ordinary 030 flight regression
passes thirteen publications, two 45-phase clears, 240 expiry checks and 293 clean twins.
The differing arrival values and unobserved pre-window publisher do not establish
trajectory equivalence or rescue-message lifetime. Rescue reinitialization now translates
remaining message counts into the resumed flight clock: 030 preserves 26 remaining counts
and clears exactly 26 phases later (32 expiry checks, 117 clean twins); A500 preserves an
already expired -55-count deadline without reviving it. These different histories do not
calibrate native pit durations. A private 32-bit message clock now extends the unchanged
native 16-bit control phase. Directed A500/030 rollover fixtures each pass thirteen
publications and two exact 45-phase clears, including 65,523 → 65,568 across rollover;
203/241 expiry checks pass, with 294 clean 030 twins. The fixture-free rescue regression
retains its 26-count lifetime and adds 117 clean twins. Normal-build bytes remain unchanged.
Direct/less common publishers, broader lap contexts, wrap combined with mode changes,
mode handoffs and A500 message-duration calibration remain open; pit expiry still uses
the outer pit counter. Do not treat this bounded correction as complete message timing. Register/stack and nonlocal
result contracts, opponent continuity and the other repair branches remain open. The
pilot stays disabled by default; the normal build is unchanged. Next audit the projection flag and matched native animation visibility,
then collision/effect feedback and lifecycle regressions, race reinitialization and repair
pacing. See the numbered F6 steps and measurements in timing-implementation. Normal-build bytes remain unchanged; broader timing
is still an experimental build, not a completed framerate-independence feature.

The current high-speed brake audit confirms a remaining calibration mismatch rather
than a duplicate-decrement bug. Native A500 executes eight decrements and finishes at
speed 108; both current WORLD20 A500/030 builds execute all fifteen owed brake events and
finish at 53. All eleven held-command logical control states match across CPUs, native
clamp/damping arithmetic passes, and input/brake queues retain no debt or overflow. The
030 adds 72 clean completed renderer comparisons. The original slowdown depends on scene
render time; the representative-handling versus scene-dependent reference policy remains
unresolved, and the native response gate remains failing. Cadences and tolerances are
unchanged. See the current brake arithmetic audit in timing-implementation.

The extended opponent projection audit now covers six A500 seconds and all nine
mismatching raw-record timestamps. All 382 accesses to opponent word `$54` are confined
to the known drawing sites; 117 reads follow fresh projection writes across all four
pilots. The attempted 030 instruction capture contains no PCs and is rejected, so
accelerated effective-address evidence remains missing. Strict comparison still reports
nine `$54` differences, with all other compared words and RNG equal; no field is masked.
Pilot 1's animation timing agrees between corrected CPUs but differs from the native
reference's visibility history. The track-range endpoint is updated by movement, so
there is no established stale-render visibility bug to fix. Matched native event histories
and accelerated field-ownership evidence remain required.


The bounded F7 accelerator matrix now compares the current full timing prototype on
030/25 fast rendering, 040/25 native/fast and 060/50 native/fast. With the existing
VERIFY-only 18/24-second initial-pit synchronization fixture, all five configurations
match 502 common sampled player/engine/RNG states, 111 control/input updates and 111
fuel updates. Arithmetic/input/debt checks pass, with 358 clean renderer twins. Each
capture spans exactly 500 physical PAL fields; 502–504 completed world steps account
for the measured initial/final unsampled elapsed time, with zero endpoint retained debt.
The corresponding unsynchronized batch matches control/fuel samples but fails RNG
comparison from the first step: different initial-pit durations produced different
opponent/RNG histories. No fields are excluded to obtain a pass. This does not finish
F7 or certify full opponent/effect equivalence, longer windows, stalls, capacity or
remaining CPU configurations. See the bounded accelerator matrix in timing-implementation.

The synchronized matrix now also covers A500 without fast RAM, 68000 with 4 MB fast
RAM and both renderer paths, and A1200/68EC020 native/fast. All ten configurations
match 502 common sampled player/engine/RNG states and 111 control/input/fuel updates.
The five new cases add 96 clean twins (454 across both synchronized batches). New
per-step delay accounting exposes responsiveness limits hidden by zero endpoint debt:
A500 reaches 780 ms observed delay and 160 ms retained debt; 68000 fast rendering with
twins reaches 1,120 ms and 380 ms. Both retain the elapsed work and return to zero
retained debt, although unsampled elapsed time can remain at the endpoint. The 020
native/fast-twin maxima are 400/580 ms. These instrumented maxima are not release
performance figures or proof of long-run capacity. Controlled stalls, 60/600-second
routes, further configurations and the remaining calibration/lifecycle work stay open.


A first 60-second 030 capture completes 3,004 world steps, 667 control/fuel updates and
851 clean renderer twins, but stops the batch at a joystick oracle gap after 10.94 seconds.
Native contact response damps saved steering axes by 230/256; the old oracle omitted it.
New read-only contact observations and independent arithmetic/continuity checks pass a
13-second A500/030 pair with three damping updates each, 652 identical sampled world
states and 144 identical control/input/fuel updates. No production code or acceptance
tolerance changed. Repeat the full 60-second pair with these observations before claiming
endurance coverage; 600-second and controlled rate/stall tests remain open.
