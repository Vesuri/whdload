# Phase 8: fixed-time simulation — complete

Accepted as PAL emulator beta 1.6b. Enable with WHDLoad `CUSTOM2=1`;
C2=0 preserves original gameplay apart from the overlay-cache fix. Normal builds
have no VERIFY controls. The player-facing label, icon and release package are documented in
phase 11. No rendering/FPS improvement is claimed. Real A1200/68040 results are
deferred, NTSC unvalidated. Preserve `tmp/dist/overlay-cache-ab/` unchanged.

## Implemented foundation

- `simulation.s` resolves each fresh h4 export after overlay load and patches it
  before the final cache flush. It selects five fields for 68000/010 and two for
  68020+. VERIFY instruments retain their separate option gates.
- Signed rational scaling splits the 32-bit magnitude before multiplication.
  Carries are signed and normalized on a change of sign. INT_MIN is supported.
  Speed has one carry shared by its continuous additive terms; RPM, distance,
  clock, speed integral and each traffic lane have separate carries.
- Clutch braking, neutral drag, normal braking, acceleration/drag, free RPM,
  RPM relaxation and tyre scrub have rate hooks. RPM loss at period 2
  is Q16 coefficient 827 = round(65536*(1-(31/32)^(2/5))). Period 5 retains
  the original shift/subtract truncation, rather than introducing a new carry.
- Displacement uses dt*(v+(1-dt)*A/2)/64, dt=p/5, post-step velocity v and
  unscaled continuous acceleration A. For p=2 this is
  2*(10*v+3*A)/3200. Five such constant-A steps cover two coarse steps:
  both sum to (2*v_initial+3*A)/64 before rounding. Collision impulses do not
  belong in A. Period 5 keeps the original v>>6 operation exactly.
- Count and integer-mph sum use 6*p/25 legacy units with separate carries.
  Original neutral-start latch, blocking event paths and +240 penalty remain.
  The shifter runs on a retained five-field phase and ignores renderer buffer
  acknowledgements. Police seen/clock/stop counters also use the retained five-field cadence.
  Manual/automatic/station gear decisions and the rev-limit counter now use
  the pre-step cadence. Shifter travel uses its own post-wait accumulator so
  a two-field step cannot prematurely consume a five-field lever update.
- Geometry work moves widths to a read-only road descriptor walk and computes
  traffic collision origins in the simulation. Descriptor nibbles select
  320+64*n; $FF inherits the nearest previous explicit width. Traffic slots
  0/2/3/4 use right-edge-minus-224, slot 1 uses centre-plus-224, police use the
  original clock-shaped lane offset, oncoming cars use centre-minus-224.
  Draw-side writes and lane advances are removed. Wall collision reads current
  x; renderer snapshots remain available for drawing. The accepted route, demo and slow-render fixtures cover these ownership changes.

- Traffic has independent displacement carries for six forward and five oncoming
  slots. Police acceleration/braking scale the stored original-unit velocity;
  following copies coarse player velocity, avoiding a second p/5 scaling.
  Traffic integrates before the speed update, so its Euler correction has the
  opposite sign from the player's: dt*(v-(1-dt)*A/2). Stopped motion is explicitly
  zero. Private police rate/force fractions clear while its slot is absent.
- Steering slew/return limits, road-edge response and automatic lane centring
  now have rate hooks. Grip comparison converts the fine-step steering displacement
  back to coarse-rate units before the original threshold/clamp routine. Unclamped
  motion passes through exactly; clamped motion scales back with a private carry.
  Banking uses coarse-rate heading delta because the original pose resets each step.
  The five-car matrix quantifies the period-2/5 handling differences.
- VERIFY C1 bit 2 forces period 5 for cross-CPU comparisons. For C3-scripted
  player fixtures, C5 bits 8..10 choose car 0..4 through the original demo-car
  call before the car loads. These controls do not exist in normal builds.

- Force lookup now samples max(0,v-3*A_previous/10) for p=2, matching the
  coarse-Euler reference. Period 5 uses the original velocity. Torque and drag
  use the same zero-remainder reference; the actual game RPM is not replaced.
- CUSTOM2 removes beam entropy in normal builds. Visual RNG advances at the
  simulation's five-field cadence, with four cached values and a fifth discarded
  draw. The odd stride avoids locking the effect-trigger sample to one parity.
  Background wind/heading phases, police lamp phase and windscreen spawning/
  aging also run on that cadence. Drawing does not mutate these phases.
- The renderer's verge helper at h4:$1E20 formerly reduced speed and updated
  RPM after a CLI-set draw latch. That remaining dependency is disabled under
  C2. Simulation applies the original 23-mph threshold and edge inequalities,
  then scales the -12288 rate. This is an intentional geometry-ownership change.

## Accepted evidence

Paths below are relative to `tmp/phase8/`. The functional build is pinned in
`grip-snapshot/manifest.json`; `version-equivalence.json` proves final 1.6b differs
from it only at the three version-string bytes in each slave. Accepted source,
builds, tools and reports are pinned by `acceptance.json` and
`acceptance-manifest.json`. Historical pilots and interrupted attempts are not
acceptance evidence.

| Requirement | Evidence and result |
|---|---|
| Signed arithmetic, rounding, carries and limits | 668 native assertions; `math-vectors.json`, source vectors and each VERIFY capture's `units.json`. Integer model includes INT_MIN, sign changes, near zero, constant-rate composition, Euler distance, relaxation, cadence, widths, traffic and grip normalization. |
| CPU budget | `grip-budget-a500/budget.json` and `grip-budget-a1200/budget.json`: 10/25 completed moving iterations; maximum 10.636%/8.907% of the period, including interruptions, excluding the explicit frame wait. Not a universal worst-case bound. |
| Original period-5 rate/travel | `grip-native-p5-equivalence.json`: 170 completed native calls with nonzero inputs; scaling/reference/coarse rate/traffic reproduce identity, player distance reproduces v>>6, D1–A6 preserved. Intentional clock, clutch, RNG and geometry changes are excluded. |
| Five-car handling and PAL time | `grip-matrix-matrix.json`: all 20 combinations of five cars, periods 2/5, straight/steering tapes pass 1,300 consecutive fields, clock/speed-integral checks, 668 assertions, selected-car and installed-byte checks. No event/chance loss. |
| Same-period cross-CPU route | `grip-crosscpu-route-comparison.json`: A500/A1200 period 5, all selected core states and background/lamp phases match over 1,300 fields; 107/212 presentations. |
| Slow drawing | `grip-slow-route-comparison.json`: A1200 period 2, C4 off/on, same core states over 1,300 fields with 206/79 presentations. Renderer saved-x is separately reported and may differ. |
| Nonempty RNG/effects comparison | `grip-final-demo-comparison.json`: A500/A1200 period 5, 1,600 fields, all selected states, five ordered gameplay draws and one windscreen slot match; 129/258 presentations. |
| Neutral-start exclusion | `grip-manual-a1200/neutral/result.json`: actual player, 200 fields in neutral, count 1 and sum 0. |
| Actual grip clamps | `grip-real-clamp-a1200/result.json` and `grip-real-negative-clamp-a1200-centred/result.json`: signed coarse limit +/-4,521,984 becomes +/-1,808,793; each tyre scrub subtracts 6,553 speed units. |
| Original natural crash | `grip-natural-crash-a1200-centred/result.json`: one +240 penalty, 31 animation fields, frozen count/sum through manual acknowledgement wait, recovery and exactly one lost chance. Original animation/blocking time remains CPU-dependent. |
| Automatic event fixture | `grip-final-events-a1200`, `final-capture-checks.json`: 2,100 fields, one crash/penalty/recovery, police counter 1..30 then release, original blocking path. |
| Natural police stop | `grip-natural-police-a1200/police-check.json`: 490-field stop, alternating 4/6-field script increments, zero vehicle speed, 117 counted time units, no crash penalty. |
| Actual results and next stage | `grip-stage-results-a1200/result.json`: native Ferrari stage, count 2,180, sum 149,267; real call arguments and rendered text show 3:01, 68 mph, 2,702 points. `stage-reset.json`: next stage, count 1, sum 0, all private carries zero, score retained. |
| Overlay lifetime | `grip-live-reload-a1200`: export observed as unloaded BSR, then genuine h4 race re-entry with all 62 selected/nonoverlapping patch declarations checked. |
| C2 off | `grip-normal-disabled-a1200` and `grip-verify-allzero-a1200`: all 66 declarations retain original bytes (62 physical ranges plus four mutually exclusive aliases). |
| Normal final build | `final-normal-enabled-a1200`: final 1.6b, C2=1, 400-field driving demo, installed bytes pass; cockpit, road and mirror screenshot inspected. |
| Quit | `grip-manual-a1200/normal-quit.png`: native keypad-* returns to AmigaDOS; own emulator/server then shut down cleanly. |
| Static checks | `final-audit.json`, `final-inventory.json`: signatures, complete instruction boundaries, overlaps and direct incoming candidates pass. Indirect targets are not statically proven. |

The native Ferrari stage was driven with debugger keyboard events and read-only
telemetry, through ordinary traffic, both bend signs, a natural police stop and
road widths 448 -> 896 -> 448. No host accessibility or debugger memory writes
were used to drive or manufacture the results.

## Retained pre-correction handling measurements

Current curvature rounding is corrected as documented in `handling-collision.md`.
The following matrix predates that fix and is not current bend-response acceptance.
`grip-handling-comparison.json` compares matched elapsed-field samples. Period 2
is finer integration, not a claim of exact period-5 state identity. Decision/sample
boundaries contribute to transient differences. These are measurements, not an
arbitrary tolerance-based fidelity verdict.

| Car | Peak mph, p2 / p5 | Travel difference | Maximum route lateral difference |
|---|---:|---:|---:|
| Porsche | 35.478 / 35.493 | -0.045% | 4.558 |
| Ferrari | 79.046 / 79.236 | -0.337% | 11.592 |
| Lotus | 80.261 / 80.705 | -1.013% | 11.124 |
| Countach | 41.661 / 42.137 | -1.338% | 4.580 |
| Corvette | 81.031 / 81.146 | -0.277% | 12.297 |

Maximum peak-speed difference is 0.477 mph; maximum transient speed difference
is 3.795 mph. The short matrix does not reach tyre slip; both actual signed grip
clamps are covered separately. Native period-5 arithmetic and the original event
paths are checked separately from intentional ownership/clock changes.

## Reproduction

From the game directory, source `tools/env.sh` and use its Python. Build with
`tools/build.sh` and `VERIFY=1 tools/build.sh`. Inputs/compiler/SDK are pinned;
builds write only to `tmp/build/`. Captures require a fresh output name and refuse
an already-active worktree server. Never restart a running capture because one
observation timed out. The final captures preserve their exact slave/listing and
machine/options. Normal and VERIFY outputs are separate.

- `tools/audit_simulation.py`, `tools/identify_game.py`: static checks.
- `tools/simulation_car_matrix.py PREFIX`: all 20 car/period/tape arms.
- `tools/simulation_capture.py NAME --preset a500 --c1 4 --c5 0 --fields 1600`
  and the same on a1200: demo cross-CPU pair. `compare_simulation_demo.py A B`
  requires nonempty gameplay RNG; `verify_state.py A B --expect-equal` permits
  empty logs for short route comparisons.
- Route comparisons use C5=1, C1=4 for cross-CPU period 5; slow drawing uses
  a1200 C1=2 C5=1 with C4=0/1. Both use 1,300 fields.
- Automatic event fixture: `simulation_capture.py NAME --preset a1200 --c1 2
  --c5 23 --fields 2100`; run `check_police.py CAPTURE`.
- `simulation_normal_capture.py NAME --preset a1200 --c2 1 --fields 400`:
  normal build smoke; C1/C3/C4/C5 must be zero.
- `check_disabled.py CAPTURE` checks original or enabled bytes/helper targets.
  `check_timing.py CAPTURE` proves per-step nonblocking clock/speed integration;
  separate events/results checks cover blocking intervals and actual display.
- `check_p5_trace.py CAPTURE...` checks recorded native calls; moving traffic
  is needed for nonzero traffic evidence. `check_simulation_budget.py CAPTURE...`
  checks completed-loop work against each CPU's own measured field cycles.
- `test_p5_trace.py`, `test_simulation_budget.py`, `check_simulation_comparator.py`
  reject corrupted returns/registers, over-budget/accounting errors, divergent
  states, reordered RNG and changed windscreen positions. Saved-x-only changes
  are deliberately allowed and reported as drawing snapshots.

`simulation_interactive.py`, `simulation_drive.py`, `simulation_grip_probe.py`,
`simulation_crash.py`, `simulation_results.py` and `simulation_reload_live.py`
provide the native-input/read-only probes for the manual evidence. Crash probing
requires a stopped, centred player state; it has a fallback acknowledgement
breakpoint. Results probing requires the actual near-station route. A breakpoint
wait alone is never evidence that the desired event occurred.

The remaining project work is in `open-work.md`: phase 12, deferred hardware/publication
follow-up and unvalidated NTSC. No phase-8 acceptance item remains open.
