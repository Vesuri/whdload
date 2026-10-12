# Open work

The step-by-step plan to finish and ship this work is in [the completion plan](completion-plan.md).

## Phase F in progress

The user has authorized F1–F4. The current candidate promotes `TIMING_FULL` into
normal builds and resolves C1/C3 as opt-outs at installation: 68000/68010 stay
native, 68020+ enables timing, and 68020+ with real fast RAM enables planar staging.
WHDLoad cache policy is unchanged. Normal, VERIFY and coverage candidates build;
the original reconstruction still matches the installed original slave.

F1 passes on normal builds: all declared rendering and timing hook ranges remain
native on M1 defaults and M7 with `CUSTOM1=1 CUSTOM3=1`. The declared wait hook
explicitly checks its complete six-byte TST/BEQ pair. F2 normal builds reach name
entry on M1/M3/M4/M7. Saved snapshots prove native M1, timing-only M3, both features
on M4/M7, and both disabled on opted-out M7. The matching VERIFY M7 Practice run
confirms initialized world scheduling and completed staged scenes, with no C1/C3
options: 490/499 fields = 49.098 fps with CACHE. This is the first release-matrix
measurement, not a claim for the remaining machines.

The first M1 capture used an unsupported one-field window; its two-field retry
passes. The first F1 checker rejected the display-wait hook under its old
single-instruction assumption; the explicit pair check passes on the saved capture.
Both invalid attempts are preserved under `tmp/phase-f/`, with `boot-defaults.json`
and the individual gate reports. No game-code fix was needed for either issue.

F1–F2 are complete. The remaining release matrix, final documentation consolidation
and F3–F4 commit are outstanding.

## Phase E complete with two deferred validations

D1–D5 are confirmed. Phases A–E are complete within the agreed scope. The user
has deferred steady A500 handling and natural-weather validation; neither gate is
counted as passed. All other required E2 gates passed. E3 optional title-demo pacing
was evaluated and not selected. No further Phase E work is scheduled.

E1 accepts the specified native brake/impulse/visibility histories and classifies
opponent `$54` as presentation-owned; that policy update changed no cadence,
tolerance or game code. Evidence is under `tmp/phase-e/`. `CUSTOM5=14` is the
initialized-lap pause fixture; natural finish uses the separate ten-lap route and
checker. Phase E deferrals remain in force during the separately authorized
Phase F integration above.

### Phase E gate ledger

| Gate | Current result |
| --- | --- |
| E1 policy | Complete; fixed 20/90 ms policy and original tolerances retained |
| Cross-CPU equivalence and accounting | Pass: six M4–M7 captures, 501 exact common world states and 111 control/input/fuel updates |
| Steady A500 handling | Deferred by the user; not passed: no native stop threshold; fuel inconclusive; acceleration to 130 passes; straight-line speed not evaluated |
| Lifecycle | Pass: pause, restart, initialized-lap pause, rescue and natural ten-lap finish |
| Stalls | Pass: 100/260/500 ms observed holds; exact recovered state and zero endpoint retained debt |
| Render cadence | Pass: ten requested-rate/unpaced captures, 651 exact common world states and 144 control/input/fuel updates |
| Endurance | Pass: corrected 600-second pair matches 30,001 common world/RNG states and 6,666 control/input/fuel updates; zero endpoint debt |
| Visible weather | Pass: directed fade/memory checks and three visible logical phases on the startup-only Practice retry |
| Natural weather race | Deferred by the user; not passed: the ten-minute retry has no natural weather episode, leaving expiry/restoration untested |
| E3 optional title demo | Evaluated, not selected: recorded camera remains frame-driven; no M7 duration pass claimed |

Equivalence evidence: `tmp/phase-e/equivalence/`, `equivalence-020-fast/` and
`equivalence-060-fast-retry/`. All six physical windows cover 500 PAL fields.
Retained allocator debt is zero throughout the sampled world ends. M4 finishes
inside an allocated batch with two unfinished steps, exactly accounted for;
the other five endpoints have no assigned unfinished steps. Peak sampled
world-end delay is 400 ms on M4 and 140–220 ms on M5–M7. These are instrumented
correctness captures, not throughput measurements. The fast-renderer runs pass
pixel, register/CCR, scratch, guard and unchanged-raster checks.

The first M7 fast capture was invalid: GDB returned `Invalid hex digit 79`
in the first field's weather-state read and the strict field counter rejected
0/100 fields. Its single fresh-boot retry passed, as did the subsequent
six-way comparisons. Preserve the invalid evidence; do not count it as a pass.

### Current lifecycle evidence

`tmp/phase-e/pause-030/` excludes 48 paused fields, consumes all five input events,
and preserves the logical remainder without resumed throttle leakage. It passes
75 completed renderer twins. `restart-030/` observes two explicit closures and two
fresh gameplay entries, with six inactive menu/pit probes and exact discard accounting.
`lap-pause-030/` excludes 49 fields and checks 72 exact logical HUD outputs, including
28 after resume, with unchanged private/native lap starts and no reset fallback.
`rescue-030/` covers one 77,040 ms pit visit: four interrupted assigned steps are
explicitly discarded, 3,444 inactive pit observations preserve player ownership,
and reentry assigns one 20 ms step with no retained debt (120 ms outside-pit allowance).
All 281 completed renderer twins pass.
`natural-finish-030/` reaches a natural opponent-3 victory on lap 10. Reported
and stable logical winning duration both equal 225,620 ms, with preserved native
pilot sorting, registers/stack/flags and cleared result-clock ownership. Its
result-only 200-field window adds no staged scenes; the pre-result counter records
2,489 completed clean twins from the same boot.

### Stall evidence

`unpaced-030/` and `stall-100-030/`, `stall-250-030/`, `stall-500-030/` under
`tmp/phase-e/` cover 650 fields each. The requested 250 ms hold rounds to 260 ms
on PAL; the others measure exactly 100/500 ms. All world clocks hold and resume
at the same logical cursor, with every elapsed step serviced afterward. The four
captures match 653 common player/engine/RNG states and 145 control/input/fuel
updates. Peak sampled world-end delay is 180/320/560 ms for the three stalls;
retained debt is zero throughout these sampled ends and at every endpoint.
All renderer checks pass. These measurements include verifier overhead.

### Render-cadence evidence

The four requested rates plus unpaced run on both M5 and M7, all with renderer
twins and 650 PAL fields. `tmp/phase-e/rate-*-030/`, `rate-*-060/` and
`unpaced-030/`, `unpaced-060/` match 651 common player/engine/RNG states and
144 control/input/fuel updates. All per-run rational pacing, elapsed accounting,
input, integrator and renderer checks pass.

| Requested Hz | M5 measured presentation markers/s | M7 measured presentation markers/s |
| --- | ---: | ---: |
| 10 | 9.753 | 9.888 |
| 15 | 12.472 | 13.205 |
| 25 | 12.472 | 13.708 |
| 50 | 12.472 | 13.708 |

These are instrumented correctness rates with late-deadline accounting, not
release throughput or evidence of achieved 25/50 Hz scanout. The 25/50 Hz cases
have no pacing wait. Retained allocator debt is zero at all endpoints; unfinished
steps and presentation waits are explicitly accounted for by the existing checkers.

### Endurance accounting and equivalence finding

`tmp/phase-e/endurance-native-030/` completes 30,000 physical PAL fields
(600,000 nominal ms). All per-run checks pass: 30,002 consecutive 20 ms steps,
6,667 rational 90 ms controls and fuel updates, and 25,167 opponent reads.
Retained debt is zero at every sampled world end and both endpoints; the final
snapshot has no assigned unfinished steps or pending controls. Peak sampled
world-end delay is 240 ms. The extra two completed steps are exactly explained
by initial/final unsampled elapsed time of 60/20 ms.

`endurance-twins-030/` also completes 30,002 steps and passes every individual
checker, with zero retained debt throughout and at both endpoints. Its peak sampled
delay is 180 ms; initial/final unsampled time is 80/40 ms. It adds 7,077 clean completed
renderer twins. The two runs match all 6,667 control/input and fuel updates.

The extra paired world-state comparison fails first at index 14,351, logical time
287,040 ms: player/engine fields still agree, but RNG is 59,896 versus 51,905. At
opponent update 3,456, the fourth opponent reaches movement in the native-renderer
run and skips it in the twin run. Read-only boundary snapshots in `endurance-{native,twins}-boundary/` confirm the
cause: repair elapsed time is 4,202 versus 4,194 native units (21,010/20,970 ms).
Integer division by 200 yields 21 versus 20, so only the former clears the repair.
The stored repair starts are 59,014/59,002 and sampled clocks 63,216/63,196.
These are clock values, not memory addresses. Preserve both captures;
no comparison field is masked and no tolerance is changed. This is the first failed
comparison attempt. The candidate fix makes the existing `$d4b6/$d4fe` wrappers
read the continuous opponent deadline for both repair start and expiry. Native
fallback, register/flag behavior and race/lap clocks remain unchanged. The frozen
`sync-repair.slave` passes focused before/after boundary comparison: all four
opponent records match byte-for-byte and both RNG values end at 51,905. The
native-renderer retry in `endurance-native-030-retry/` passes all individual checks:
30,001 movement steps, 6,666 control/fuel updates, 25,166 opponent reads, zero retained
debt throughout, and zero assigned unfinished steps or pending controls at the end.
Peak sampled delay is 240 ms. Initial/final unsampled time of 60/40 ms accounts
exactly for the one extra completed step. The corrected twin run in `endurance-twins-030-retry/` passes 30,002 movement
steps, 6,667 controls/fuel updates and 7,077 completed renderer twins. Its maximum
sampled delay is 180 ms, retained debt stays zero, and there are no assigned unfinished
steps or pending controls at the endpoint. Its 80/40 ms initial/final unsampled time
accounts for two extra completed steps. The pair matches all 30,001 common
player/engine/RNG states and 6,666 complete common control/input/fuel updates exactly.
Normal build bytes remain unchanged. The existing continuity checker identifies the live wrapper's
clock domain so old captures remain readable without weakening the new assertion. The corrected pair passes the finite endurance gate and its exact logical-state
comparison; the initial failed pair is retained as regression evidence.

This mostly stationary input tape is an accounting endurance test, not sustained
race/weather coverage; the separate unseeded race gate remains required.

### Visible-weather evidence

`fade-030/` passes all 30 fade steps, two native gear commits, 31 owned palette
interpolations, restoration and both prepared Copper lists. Enter/leave durations
are 20,560/17,420 ms. `weather-screens-retry/` passes the separate visible gate:
phases 3/8/13 from one directed fade show RGB4 colours `$46c/$247/$112`.
The checker finds 8/8/11 complete 16×16 JPEG blocks within the unchanged
5/5/5 RGB-channel bound, with flat palette-index-5 regions in both source bitmaps.
The palettes and logical phases remain unchanged during each two-field capture.
All three images were also visually inspected.

The first `weather-screens/` route drives into a wall, leaving too little flat sky
for a defensible colour measurement; its dominant non-black colour was the grey wall.
The single retry uses existing `CUSTOM5=2` startup-only Practice. The corrected
checker identifies the unique weather palette colour and requires whole flat image
blocks rather than the largest colour in the scene. Neither palette arithmetic nor
colour tolerance changed. Wrong-phase images and removed bitmap weather regions
are rejected (`weather-screen-negative/`). Preserve both attempts.

Barto stores JPEG images, even where older capture filenames end in `.png`.
`check_weather_screen.py` derives a flat-colour DC quantization bound from the JPEG
tables; it does not claim exact whole-image RGB equality. All 4,096 RGB4 flat colours
passed the independent encoder/decoder check at the observed quality: maximum R/G/B
errors 3/3/4 levels, within the derived 5/5/5 bound
(`weather-jpeg-bound-check.json`). All paths above are under `tmp/phase-e/`.

Reproduce from a completed directed-fade calibration with its frozen slave:

```sh
source amiga/env.sh
python3 tools/capture_weather_screens.py tmp/phase-e/fade-030 tmp/phase-e/weather-screens-new
python3 tools/check_weather_screen.py tmp/phase-e/weather-screens-new
```

The capture driver validates the slave, emulator and Kickstart hashes, waits for both
alternating display buffers to receive each phase, and writes no game state at its
checkpoints. These narrow tools are needed because the existing palette/Copper
checkers inspect stored memory only. Screenshots use the pre-repair-fix frozen fade
slave; the two-byte opponent repair-clock change is outside this Practice route.

### Deferred natural-weather validation

`tmp/phase-e/natural-weather-030/` aborts before its first measured field: 33
requested observation/field breakpoints exceed the emulator's 20-breakpoint limit,
producing conflicting Z0 insertion responses and `PDWINDOW -1`. This is an invalid
capture, not gameplay evidence. Preserve it as the first attempt.

The single retry retains 18 observation sites plus the VBL and presentation markers:
world entry/movement/end and allocator entry; session/pit transitions; palette
presentation and interpolation/restoration entry/returns; and weather effect drawing.
Those observations cover every natural-race requirement. Dedicated brake, resource,
opponent-movement, gear and native forecast-arithmetic probes are omitted here;
their separate gates have already run. No required natural-race observation or
acceptance tolerance is removed. The unseeded fixed slave is unchanged.

The retry `natural-weather-030-retry/` completes all 30,000 PAL fields (600,000 ms).
Its 6,574 additional forecast trials produce no forecast, onset or expiry. Effect
selections, visual events and both fade-direction counters remain zero. Consequently,
an inactive final palette is not evidence of restoration after weather; the required
natural episode is missing. This is insufficient coverage, not proof of a weather-code
failure. The runner's “supplied checks passed” only reports capture/renderer checks;
it does not certify this gate.

The read-only observations retain one session ledger and 30,007 consecutive world-end
samples, including samples before field zero. Every sampled delay is exactly explained
by unsampled time, retained debt and assigned later steps. Peak retained debt is 60 ms,
peak world-end delay is 680 ms, and endpoint retained debt is zero. These are
instrumented accounting observations, not release frame-time measurements. All 5,940
completed renderer twins have zero pixel/register/CCR/scratch/guard failures, and the
copied raster code is unchanged. One additional draw is active at the endpoint.
`natural-gate-result.json` records the evidence beside the capture.

The initial setup failure and unsuccessful retry exhaust this gate's two attempts.
No third run, seed injection, longer substitute window or relaxed acceptance is made.
The user has deferred this validation. Natural effect expiry and palette restoration
remain unverified by this unseeded route, without blocking completion of the agreed
Phase E scope. No additional capture is scheduled. Handling also remains deferred,
optional title-demo pacing remains unselected, and Phase F is untouched.

### Deferred handling findings

The first handling attempt, `tmp/phase-e/steady-a500/`, aborted before measurement:
the scratch helper incorrectly requested `TIMING_EARLY=1` with C3 disabled.
The diagnostic correctly rejected the missing scheduler hooks. The helper now
uses `TIMING_EARLY=0` for native timing; no tracked tool or game code changed.

The allowed retry and its M5 pair completed all 300 fields:
`tmp/phase-e/steady-a500-retry/` and `steady-030-twins/`. Both use C5=7,
NoCache and the same frozen full coverage slave, with C3 off on M1 and on on M5.
The existing response and fuel reports are `steady-response.json` and
`steady-fuel.json`. Their JSON statuses matter; successful script exit is not
acceptance of an inconclusive result.

| Required measurement | Result |
| --- | --- |
| Acceleration to 130 | Pass: native 1,400–1,420 ms, M5 1,360–1,380 ms; conservative error 20–60 ms against 141 ms allowed |
| Stop | No reference threshold: native speed remains 7 after brake release, through the capture endpoint. M5 applies all 15 owed events and reaches zero, first presentation at fixture field 155, beyond the checker's field-150 window. Both report missing stop thresholds. |
| Fuel, fixture fields 20–240 | Native 72–74 units, M5 63–65; bounded difference 7–11 against 7.3 allowed. Existing checker reports `needs finer sampling`; not a pass. |
| Straight-line speed | Not evaluated before the stop rule applied |
| M5 renderer correctness | 89 completed staged scenes inside the capture; zero pixel/register/CCR/scratch/guard failures, unchanged raster code |

The setup rejection and unsuccessful retry exhaust this gate's two attempts.
No third capture, weakened tolerance, changed brake hold or silently substituted
native reference was used. This identifies insufficient acceptance evidence, not
a proven scheduler defect: the native route does not stop, while the candidate
does. The user has now deferred this gate and authorized the other Phase E work.
When handling is resumed, resolve the reference/measurement contract for stop and
fuel before rerunning it; preserve the fixed numerical bounds. The existing frozen native reference and the fresh reference have different
stop outcomes; establish which route/build assumptions explain that difference.

The unseeded weather race is deferred by the user. No required Phase E runtime
gates remain in the agreed scope. Corrected endurance and visible fade phases
have passed. Lifecycle,
stalls and requested render rates have passed as recorded above. Weather handling
bounds are included in the user-deferred handling row. The optional E3 title patch
is not selected: it is a separate recorded-camera animation, not an E2 gameplay gate.
Its current per-frame index advance remains documented in internals; no M7 duration
comparison or correction is claimed. Phase F is untouched.
Handling validation changed no game code, cache policy, runtime defaults or existing
checker. The new visible-weather checker is separate. The normal
build remains byte-identical to the Phase D control (SHA-256
`ca8639921c1d8c2781578a62a42003a6ba888990a4a22b8d4f82cc829be061f3`).

**A500 unchanged at 11.404 fps**, reproducing 104 intervals in 456 fields in the
prescribed 500-field Practice window. D1's four pipelined blitter clears regress
to 104/494 = 10.526 fps (7.69% lower); the candidate is removed. It has no accepted
twin result. D2's largest individual graphics call is BltBitMap at 2.580%; LoadView
is 0.186%, and no traced VBL callback reaches 3%. D3's entire mutable dispatch setup
is only 0.181% of track time, below the prerequisite even if removed for free.
No A500 code change is retained. Measurements and reproduction details are in
[Phase D](internals.md#phase-d-a500-measurements-and-decisions), with evidence under
`tmp/phase-d/`. The normal build is restored byte-identically to the Phase D control.

### Retained Phase C work

C1 is complete and retained. Its normal/weather write audits have no unhandled
operations. Staged drawing now defers the handshake until immediately before copy;
native fallbacks and VERIFY twin reference drawing keep the original early wait.
NoCache Practice gains versus Phase B are 9.87% / 21.31% / 5.73% / 4.67% on M4–M7.
CACHE improves on M5 and retains 49.098 fps on M6/M7. All 308 checked copies follow
the required VBL; the M4/M5/M7 twins complete 16/26/29 staged scenes with zero
pixel, register/CCR, scratch or guard failures and unchanged raster code.
Evidence is under `tmp/phase-c/`; the full table and gate counts are in internals.

C3 is complete with no code change: copy already uses aligned ten-register MOVEM
blocks; HUD writes rows 156–199 outside the copied rows 19–153 and uses blits;
presentation including LoadView is below the 3% threshold.
C2 is complete and retained. Every polygon uses installed static code on 68020+,
including native bitmap fallbacks. The 200-field departure/track audit reports
zero game-code writes and explicit pit/render/driving coverage. Pit/title images
are pixel-identical; M4/M5/M7 twins pass with nonzero staged-scene coverage. All
NoCache throughput comparisons improve; cached M6/M7 remain at 49.098 fps.
C2 is retained for its specific no-SMC correctness gate, with modest performance
gains reported rather than claiming the general 3% optimization threshold.
Evidence is under `tmp/phase-c/c2/`.

C4 is complete and rejected: M3/CACHE with code-only chip placement slows from
144/494 = 14.575 fps to 139/495 = 14.040 fps (3.67% slower), failing the required
3% gain. The snapshot proves code in chip RAM and no bitmap staging. The experiment
and its assembly flag are removed; no twin acceptance is claimed for the rejected
candidate. Evidence is under `tmp/phase-c/c4/`, including `decision.json`.

The chip-only capture correction is retained: the slave snapshot comes from chip
RAM, and missing/short dumps fail instead of reusing scratch files. Older M3
auxiliary dumps are not used as diagnostic evidence. All retained C1/C2 gates pass;
C4's single performance failure is resolved by dropping it as the plan directs.
The normal build is restored. Cache policy and option defaults remain unchanged.

### Completed baseline gates

- **B1 passes.** `VERIFY_PHASE=1` adds a 16,384-record beam-clock ring in an
  additional 256 KiB of requested expansion. It records actual renderer returns,
  preserves staged-render eligibility and accounts for incident/aborted world steps.
  The M4 trace compares 46 common complete present intervals. Eleven initial
  snapshot records precede the trace and are excluded from both sides; none are
  missing inside it. Maximum phase-sum disagreement is 0.00571%, against the 2%
  gate. Evidence: `tmp/phase-b/b1-m4-final-trace/` and `b1-final-comparison.json`.
- **B2 passes.** All 77 captures are complete: 60 baseline, 14 separate full-timing
  phase captures, and three 8 MHz checks. All six published native Practice
  references reproduce exactly. M3 has no prior reference and supplies a new
  baseline. All frequency checks are slower. The complete table, including cache
  settings, intervals/fields, histograms and phase mean/p95, is in internals.
  Evidence: `tmp/phase-b/b2-gates.json` and each capture's `baseline.json`.
- **B3 complete; D2 retained.** The uninstrumented M1 trace measures 100 complete
  world bodies: 10,357.86 mean and 18,778 p95 cycles, including interrupts but
  excluding frame allocation, rendering/HUD-owned work and post-commit tails.
  M1 full timing loses 8.23% fps in Practice (99/473 versus 104/456) and 6.64% in
  race (104/485 versus 113/492). Keep native timing on 68000/68010. Evidence:
  `tmp/phase-b/b3-m1-world-trace/` and `b3-world-cost.json`.
- At the completion of Phase B, normal and uninstrumented full coverage builds
  were byte-identical to Phase A (baseline hashes below). Phase C changes the
  optional renderer; the ordinary normal build is restored after candidate builds.
- No unresolved failed gate remains. The M4 phase-boundary correction passed
  its single 500-field retry; the B3 listing reader accepts VASM's Latin-1 text
  and successfully reports the original capture. No tolerance was widened.

Full timing with WHDLoad CACHE reaches 49.098 fps in Practice on M6/M7 and
49.900/50.000 fps in race. Rendering remains the largest active cost. Copy and
HUD clear Phase C's candidate threshold; presentation including LoadView is below
1%. These emulator measurements do not change the user's WHDLoad cache policy.

Phase A/B baseline byte evidence (SHA-256; ignored output in `tmp/phase-a/`):

| Build | Before, umbrella and after-pruning result |
| --- | --- |
| Fixture-free full coverage | `167a586ba1dbfcfdf0097de0a1a87e077d3601701ebb10386a3c6cbed0246aae` |
| Normal | `4eeb5d12994ca6582fbc37488cf1cabdd7443de87b66e4a5e64c84826a972b0f` |

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
There is no custom cache toggle or policy in either build. Native routing still
rewrites two branch displacements when static code is disabled; C2 removes those
writes from 68020+ fallbacks with installed static code. These results do not
certify every user-selected cache configuration. Shared KickEmu startup remains unmodified.

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
Movement time is owned by the 20-ms world scheduler with retained debt. The independent
frame-delta and 90-ms-only world experiments are no longer compiled. The retained
configuration combines 20-ms movement with 90-ms control/resource/engine/opponent epochs.
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


Current bounded F7 coverage uses the full experimental timing prototype with fixed seeds
and the VERIFY-only 18/24-second initial-pit synchronization fixture. The unsynchronized
batch still fails RNG equality because different initial-pit durations produce different
opponent histories; no compared fields are excluded to conceal that difference.

| Completed check | Exact common sampled world states | Exact control/input/fuel updates | Clean renderer twins |
| --- | ---: | ---: | ---: |
| Ten CPU/renderer configurations, 10 seconds | 502 | 111 | 454 |
| A500/native and 030/fast, 60 seconds | 3,004 | 667 | 851 |
| A500/native and 030/fast, 600 seconds | 30,000 | 6,666 | 7,069 |
| 100 ms stall pair plus unstalled references | 652 | 144 | 155 new |
| 250 ms request (260 ms PAL hold), plus references | 652 | 144 | 153 new |
| 500 ms stall pair plus unstalled references | 652 | 144 | 151 new |
| Four requested-rate pairs plus unpaced references | 652 | 144 | 600 new |

The ten configurations include A500 without fast RAM, 68000 with fast RAM and native/fast
rendering, 020 native/fast, 030/25 fast, 040/25 native/fast and 060/50 native/fast. All
completed windows have zero endpoint retained/assigned debt, but sampled delay is material:
A500 reaches 780 ms and 68000 fast rendering with twins reaches 1,120 ms. These are
instrumented observations, not release performance. The 60-second pair accounts explicitly
for 80 ms carried into the window, producing four extra completed world steps.

The joystick oracle verifies native contact steering damping by 230/256, including saved
axis continuity and final state. Endpoint control/fuel counts are derived from physical,
world and control clocks, with complete boundary controls and unchanged session ledgers;
common values must match exactly. This replaces a guessed one-update endpoint limit in
the matrix, without changing game behavior or gameplay tolerances.

All three single-stall pairs verify exact holds, resume cursors, input ownership and
elapsed-work recovery. Peak sampled delay is 260/780 ms, 320/780 ms and 560/760 ms
(030/A500 for 100/250/500 ms requests). The 250 ms A500 case retains up to 160 ms debt
at a sampled world end, then clears it. The fixture is verification-only; disabled
prototype and normal-build bytes remain unchanged.

The 30,000-field `timing-endurance600-1` pair passes all per-run and cross-CPU gates:
30,000 common world states and 6,666 common control/input/fuel updates match exactly,
with 7,069 clean 030 renderer twins. The physical windows are each 600 seconds. A500's
30,003 steps versus 030's 30,000 are accounted for by initial/final unsampled time
(140→80 ms versus 80→80 ms). Both finish with zero retained/assigned debt or pending
controls. Peak sampled delay is 780/260 ms and retained debt 160/0 ms (A500/030).
This tape brings the ship to rest after its initial maneuver, so the extended window tests
mostly stationary accounting and cannot establish sustained-driving capacity or active
weather. Restart, controlled rendering rates, repeated stalls, full opponent/effect state,
further CPU configurations, calibration, lifecycle and release gates remain open. See the current
measurement tables and checker contracts in timing-implementation. Bounded passes do
not establish whole-game framerate independence.


A controlled render-rate fixture is prepared for requested 10/15/25/50 Hz, with rational
PAL pacing, explicit late-deadline accounting and no changes to simulation clocks/debt.
The build guards, direct record decoding and disabled/normal byte comparisons pass.
The checker now derives presentation intervals from guest-clock-aligned markers and
reproduces the existing unpaced frame reports. All four requested-rate pairs pass;
652 common world states and 144 control/input/fuel updates match across the eight runs
and two unpaced references. They add 600 completed renderer twins; each 030 endpoint
has another draw active. The 10 Hz request measures 9.572/s on 030 and 8.200/s on A500.
Requests of 15/25/50 Hz all measure 12.275/s and 9.039/s; 25/50 add no pacing wait and
therefore supply no achieved high-rate coverage. Every run accounts for elapsed work
with no endpoint retained/assigned simulation debt. `CASE_SET=rate-native` now selects
030/25 and 060/50 native rendering. That extension passes at measured marker rates
18.568/s and 16.629/s, respectively; all twelve captures share 652 exact common world
states and 144 exact control/input/fuel updates. The 060 endpoint contains a completed
control inside one unfinished movement. The comparison checker now requires explicit
clock/counter/ownership and post-control probe evidence for that case; seven contradictory
or missing-evidence cases are rejected, with earlier long/stall checks still passing.
The original failing runner log is retained. No gameplay code or tolerances changed.
The matched native-renderer 10 Hz pair also passes: both CPUs measure 9.707 markers/s,
versus 18.568/16.629 in the higher-rate runs. Across those four captures, 649 common world
states and 144 controls/input/fuel updates match. Both lower-rate endpoints have no
assigned/retained simulation debt; the 060 is inside a presentation wait with 80 ms still
unsampled and fully accounted for. Higher achieved rates, variable intervals and other
effect routes remain open; this bounded result does not close the rate gate.


## Weather timing: current prototype and remaining gates

Weather timing remains compile-only behind `TIMING_WEATHER_EFFECTS`,
`TIMING_WEATHER_FADE`, `TIMING_WEATHER_CYCLE` and CUSTOM3; all three are off by default.
The normal CUSTOM3 build still contains only the minimum movement delta and cockpit
liftoff correction. Weather does not close F1–F8.

The current `PDWEFX03` effect scheduler uses 80 ms weather-loop periods without an
upcoming effect, 140 ms with one, and visual publication 20 ms after generation.
Generation precedes drawing and fade updates. Logical simulation owns lifetime and
RNG advances; actual rendering replays the saved visual seed and restores outer state.
Sound calls execute at logical delay expiry, before selection RNG, with native resource
availability and mute checks. The obsolete pending flag stays zero. Helper `$17836`
is audio-channel start, not bitmap cleanup; per-draw palette restoration is separate.

These periods come from two matching 400-second native A500 track-2 captures:
`timing-weather-native-a500-2` and `timing-weather-native-a500-effects1`. They match
4,836 shared observations, with 36 generation/delay updates, 30 fade steps and 90 effect
draws. Eligible loops average 81.489 ms without an upcoming effect and 141.111 ms with
one. Within-effect intervals average 139 ms (median 140); first draw follows generation
by 20–40 ms. The former uniform 90 ms candidate shortened effects by about 35% despite
cross-CPU equality, so it is not the accepted cadence. Broader native calibration remains
open; these numbers describe one measured route/configuration.

The fade scheduler retains native gear commits and uses first-step delays of 960/1,180 ms,
then 1,400/1,160 ms per entering/leaving step. Complete transitions take 20,560/17,420 ms,
against measured native 20,580/17,260 ms. Palette helpers publish the latest logical phase
in presentation. The directed 46-second `timing-weather-fade-test1` pair checks 30 logical
steps and publications, 2,301 common movements, 511 controls and 652 renderer twins.
It does not prove intermediate palette arithmetic or displayed colours.

The cycle scheduler reuses native forecast/duration arithmetic with local clock hooks,
90 ms control checks and the eight-control expiry gate. It defers messages and expiry
palette work. Native deadline migration preserves inactive sentinels and maps due/overdue
values to the current logical cursor. Its assembled helper passes eleven future, due,
overdue, sentinel and boundary cases on A500/030, with preserved registers/pointers;
five damaged cases are rejected. This is arithmetic evidence, not mode-transfer coverage.

### Completed bounded runtime evidence

All capture names below are under ignored `tmp/prof/`. “Pair” means A500/native rendering
and 030/fast rendering. Earlier frozen captures must not be treated as current-code tests.

| Capture | Result and scope |
| --- | --- |
| `timing-weather-cycle-cadence1` | Deferred-sound version: full 170-second pair, 4,217 common weather boundaries, 8,503 common movements and 1,889 controls. Warning-to-onset 25,020 ms, selected duration 117,480 ms, expiry 60 ms late; all 30 fades match. Eleven selections and 23 logical visual events versus 53/23 actual draws. 2,476 completed renderer twins. A500 retained debt peaks at 160 ms and clears. |
| `timing-weather-audio-stall1` | Preserved failing regression: deferred sound coalesces two requests 320 ms apart during a 500 ms stall on both CPUs. Current readers reject this superseded sound format. |
| `timing-weather-audio-stall2` | Current direct sound: all four requests at 4,000/4,320/8,460/11,740 ms delivered on both CPUs. Helper duration 0–40 ms; no queue loss. 485 common weather boundaries, 1,002 movements, 222 controls and 241 renderer twins pass. Maximum world-end delay 580/1,240 ms; A500 retained debt peaks at 480 ms, endpoint debt zero. |
| `timing-weather-audio-keys2` | Current direct sound: native Tab mute/unmute gives one suppressed request and two starts on both CPUs at matching 4,860/15,740/18,840 ms logical times. Native arguments and suppressed-call register preservation pass. |
| `timing-weather-audio-nosample1` | Current direct sound: both CPUs exercise delay expiry and a 500 ms stall with optional resources absent. No owned audio call or queued request. 485 common weather boundaries, 1,002 movements and 222 controls pass. Maximum delay 560/1,200 ms, endpoint debt zero. |

Normal build bytes are unchanged. The current full weather-disabled prototype is
byte-identical to the pre-sound-fix build; native hook boundaries/direct branches pass.
Audio fixtures with 1 MiB guest chip memory exercise actual optional sample allocation;
normal 512 KiB fixtures exercise the native missing-resource guard. Native helper checks
do not prove audible output or recover sound time lost during an external stall.

### Completed validation and next steps

The current direct-sound `timing-weather-cycle-cadence2` 170-second pair passes the
complete cycle, all 30 fades and 4,217 common weather boundaries, with 8,503 common
movement states and 1,889 control/input/fuel updates. Warning delay, duration and expiry
lateness remain 25,020/117,480/60 ms. Actual draws are 54/23 on 030/A500. Maximum
world-end delay is 280/780 ms; A500 retained debt peaks at 160 ms and both endpoints
have zero assigned/retained debt. Both stored palettes restore at both endpoints.
The 030 passes 2,520 completed renderer twins. Its 8,503 steps versus A500's 8,505 are
accounted for by initial/final unsampled time of 80/20 versus 140/40 ms.

The completed `timing-weather-palette-test1` 46-second pair passes all 31 owned
interpolations and one restoration on each CPU, with identical phase/source/target/colour
histories. All 30 pending logical publications are consumed exactly. The pair matches
2,304 common movement states and 512 control/input/fuel updates. Maximum world-end delay
is 280/780 ms on 030/A500; endpoint debt is zero. Stored palette calls are verified;
physical palette/buffer pairing and scanout remain open.

The completed current-code `timing-weather-effect-publication1` pair matches 1,003
common movement states and 222 controls. Of ten visible logical states, A500 draws nine
and omits one; 030 draws 21 times, including eleven repeats. Every observed draw uses the
latest completed publication and preserves RNG ownership. All 42/18 observed native
palette restorations on 030/A500 preserve entry 5 and copy the other entries. Maximum
world-end delay is 260/760 ms; both endpoints have zero debt. Corrupted weather colour,
copied colour, saved palette and source-pointer evidence are rejected.

Next work when resumed:

1. Check active display selection and captured pixels through weather transitions.
   Prepared scene Copper lists pass initial/final palette and bitmap pairing checks on
   both CPUs in the directed fade pair. This does not prove intermediate publication or
   scanout. `check_weather_copper.py` deliberately rejects unsupported interlaced/chained
   lists and repeated colour/plane writes.
2. Extend skipped/repeated effect coverage to stalls and mode transitions. Ordinary flight
   allocates at most 32 movement steps (640 ms) before rendering, shorter than the 1,160 ms
   minimum regular fade interval; a longer physical stall alone does not force multiple
   fade steps into one ordinary batch. Shorter effects already exercise omitted/repeated
   presentations in the completed current-code pair.
3. Validate natural unseeded weather and pause, pit, rescue, restart and shared-transition
   lifecycle handling, including clock/domain handoff and message/palette publication.
   Extend A500 calibration beyond this native episode and validate the 90/720 ms cycle
   check policy. Complete off-mode, memory/configuration and sustained-driving coverage
   before promoting the broader timing prototype into the normal CUSTOM3 feature.

Other unresolved F1–F8 gates above remain open, including braking/impulse calibration,
opponent projection/animation ownership, finish/restart paths and presentation-rate
coverage. Passing this weather subset cannot establish full framerate independence.
