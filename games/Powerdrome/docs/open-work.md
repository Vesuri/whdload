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
The modal opponent prototype now schedules 90-ms updates with private RNG/counter
ownership and logical repair/lap clock views, then drains the departure tail at return.
The current 030 rescue capture verifies 737 updates over 66.36 seconds with 30 ms retained,
2,948 fixed-delta movement samples, 682 outer-state restores and ten logical lap-gate
clock results. Player reentry still has zero pit debt; 409 renderer comparisons pass.
The verifier rejects an earlier implementation that omitted 19 departure-tail updates.
The same artifact passes A500: 1,148 updates over 103.40 seconds, 80 ms residual,
4,592 movement samples and 15 logical lap-gate clock results. The restart regression
adds 232 clean twins (641 current-build twins total). The next handoff correction must
carry the modal residual, elapsed flush/return time and opponent phase into an independent
ordinary-flight deadline; the current flight path still shares player control cadence.
Full opponent arrays, repair-clock cases, nonlocal exits, other pit paths and native
calibration remain F6 work. Native repair/setup/
presentation timing still makes whole pit visits CPU-dependent.
Nonlocal pit exits and other pit-entry paths remain unverified. The final-build ordinary restart regression also passes two closures/reentries and
232 renderer twins (654 final-build twins including rescue). The normal build is unchanged.
