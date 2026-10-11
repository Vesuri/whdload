# Stellar 7: current work

## Performance plan (active)

Goal: play as smoothly as each machine allows, from an A500 up to an AGA
68040/68060 with fast RAM, capped at the display rate (50 fps PAL, 60 NTSC).
Game time is a fixed timestep, independent of drawing, and identical on every
machine. Follow the steps in order. Each step ends with its measurement in
`docs/internals.md`, its commands in `docs/development.md`, and one commit
(author, unsigned, no hooks, no trailers: see AGENTS.md).

### Diagnosis

The current SIM60 design runs the whole native update 60 times a second, as
12 substeps of each original 5 Hz update. Each substep costs about one
original update: 90004 cycles on the A500 in heavy combat (the
`scan-order-profile` default), against 97.4k main-context cycles available per
NTSC field. The other contexts take 18.3% (21.9k cycles/field). The sound
handler at $1126 alone takes 10.08% in combat and 4.49% in the native early
scene. One heavy render costs about 1.03M main-context cycles (13 fields).

| Machine, route | Updates/s | Presentations/s |
|---|---:|---:|
| Native A500, frame 90/120 (stationary SOL) | 5.0 (game pace varies) | 5.0 |
| Native A500, frame 180/240 | 3.3/4.0 | 3.3/4.0 |
| SIM60 A500, type-10 route 600–9212, per interval | 52.3–64.5 | 0.43–1.60 |
| SIM60 68020 + fast RAM, type-10 1800–2400 | 60.20 | 9.23 |
| Native 68020 + fast RAM, frame 90 | 11.4 (game runs 2.3× fast) | 11.4 |
| SIM60 68040/25 + fast RAM, type-10 1800–2400 | 59.90 | 29.05 |
| SIM60 68060/50 + fast RAM, type-10 1800–2400 | 59.90 | 29.35 |

The model `fps ≈ (60 × 97.4k − R × 90.0k) / 1.03M` for tick rate R reproduces
the measured A500 rate at R = 60 (0.43). It predicts 3.1 / 3.9 / 4.4 / 4.8 fps
at R = 30 / 20 / 15 / 10. At 60 Hz the A500 is now 5–10× slower to present than
the original game. Further micro-optimisation of the 60 Hz tick cannot fix
that: two dozen adopted changes took the tick from 137k to 90k cycles, and the
target for 3 fps at 60 Hz would be under 40k. The problems that remain are
structural:

1. The tick rate is too high for a 68000. Run fewer, equally exact ticks.
2. Pictures between ticks are identical. Interpolate the rendered poses.
3. The A500 renderer is the ceiling (about 5 fps even with zero simulation).
   Profile it once traces contain several renders.

Native A500 frame-90 profile (`tmp/prof/base`, inclusive shares of all
cycles): actor pass $12aa4 45.4%, of which model draw $13b96 37.0% and polygon
pipeline $14a9e 34.2%. Inside that pipeline, $17e88→$1d51c (blitter) takes
10.0%, $17d48 6.0%, the vertex cache $17c02 4.8%, $14df8 3.5% and the
perspective division $17cea 3.4%. The star/sprite path $18340→$1bc94 takes
11.5%, HUD $0bf8a 8.4%, a RectFill (graphics −306) background fill from $0c1ba
7.1% and WaitBlit (−228) from $1bc94 3.2%. Interrupt context is 21.4%,
including 1844 blitter-finished interrupts in 50 fields. The presentation
routine $1c84c waits for the next VBL when its argument is nonzero (flag
$f5de), so pictures are already capped at the field rate.

### Step 0: Baseline matrix (no game change)

1. Commit the `amiga/run.sh` window fix: debug and warp runs use the shared
   `fsuae_options`/`fsuae_env` window mode and open behind other windows.
2. Add `tools/rate_matrix.sh PREFIX` (single capture at a time, like LoV's
   `ab_window.sh`). It runs `fixed_window.py --state-only` with
   `--tick-checkpoints`, then `simulation_rate.py`, on these machines:
   A500 (68000, 512K chip + 1.5M slow); stock A1200 (68EC020, 2M chip, no fast);
   A1200 + 4M fast; 68030/50; 68040/25 and 68060/50 as `68040-NOMMU`/`68060-NOMMU`
   with the cycle-exact options from the shared playbook §8. All runs are NTSC
   with `uae_ntsc`, plus one PAL A500 and one PAL 68060.
   Routes: SOL ticks 600→1500; type-10 combat 1800→2400 and 4500→5400 (the
   `LEVEL_TEST=200 LEVEL_LAST=6 APPROACH_TYPE=10` fixture); the boss route at
   3500. Pass only `CUSTOM1=1 CUSTOM3=1`: the driver adds CUSTOM5 itself, and a
   duplicate stops the boot at an AmigaDOS argument error. The boot poll is 120
   dumps, which a cycle-exact 68040 can exceed; make it a deadline in seconds.
3. Measure native presentation fps for the same machines with `--swaps-only`
   at frames 90 and 240. Record the cache state (the slave calls SetCPU
   $393d/$7f3f).
4. Record the matrix in internals as the reference table. Every later step
   re-runs it, and reports must state updates/s, presentations/s, pending
   growth and the largest update-start gap (`simulation_latency.py`).

### Step 1: Make the substep count a build constant

`S60_RATE = 60` and `S60_LEGACY_DIV = 12` exist, but 12 is also written out
in many places. Introduce `S60_SUBSTEPS` (N ∈ {1, 2, 3, 4, 6, 12};
`S60_RATE = 5 × N`). Then rewrite every N-dependent constant as an expression
of it, at least:

- `s60_clock`: elapsed × 60 becomes elapsed × S60_RATE (keep the long
  arithmetic). Credit consumption per tick stays `field_hz`.
- `linear60.s`: `divs #12` and the remainder ranges ±11 / ±12.
- `boss60.s`: `moveq #12`, the 288 = 2N² divisor and the (2k − 13) term,
  which becomes (2k − N − 1).
- `events60.s`: jump 144 = N², 55 = g(N − 1)/2 and velocity × 12.
- `motion60.s`: the `S60_INPUT_SITE …,12` quanta and the 80/10/40 schedules
  (`floor((phase+1)·inc/N) − floor(phase·inc/N)`).
- `pickup60.s`: `muls #11` (N − 1).
- Every "twelve-tick" clock: powers, animation, contact, terrain, shake, HUD,
  knockback, cooldowns, AI decisions, spawning, frame counter.
- `hud60.s` `moveq #11`, and the input-quanta unroll tables.

Grep for 11, 12, 13, 24, 55, 144 and 288 in every `*60.s`, and in the `*_test.s`
fixtures and Python checkers that assume 12. Add N to the debugger ABI and
have `sim60_state.py` and every checker read it.

Gate: the N = 12 build is byte-identical to the current release and VERIFY
slaves. Build N = 1, 2, 3, 4 and 6 and run every native-reference fixture with
N taken from the ABI. Then compare across N at native boundaries: the state at
completed tick k·N should match the N = 12 state at tick 12k wherever an
integrator is exact at native boundaries. Report the first divergence per N
and classify it (sub-update collision timing, rounding, real bug). Do not
accept unexplained differences.

### Step 2: Choose one tick rate for every machine

Run the step-0 matrix for N = 2, 3, 4 and 6. Choose the largest N that meets
both conditions:

- A500 heavy combat 600→5400 sustains real time: bounded pending updates with
  no upward trend.
- A500 presentations/s is at least the native rate in the same scene.

The model predicts N = 4 (20 Hz) or N = 3 (15 Hz). Input sampling then takes
50–67 ms and interpolation adds one tick of display delay. That is still well
under the original 200 ms update. Set it as the SIM60 default, keeping
N = 12 buildable. Keep one rate for every machine. A per-CPU rate (60 Hz on a
68060) would change only collision sub-timing and input latency, at the cost
of a second validation matrix. Revisit it only after step 6, as a separate
measured option.

### Step 3: Interpolated presentation

The renderer re-projects every actor from its record each frame ($2bb4 →
$12aa4), so pose interpolation can be done in place:

1. Snapshot inventory. Trace render-time reads of actor and player pose
   fields: x/y/z, yaw +$18, pitch, bank, camera, damage-shake viewport
   offsets $7156/$7158 and star records. Use the existing
   `render_write_inventory.py` approach and list the readers.
2. At each completed tick, keep previous and current poses per active actor
   in a slave table keyed by actor address and tag-checked like
   RECORD_CACHE. Snap (prev = cur) on spawn, removal, recenter ($3ab8 shifts
   every coordinate: apply its delta to prev), level/session reset, death,
   modal return and when a pose jumps further than a bound.
3. In `s60_render`: poll the clock, set α = credit / field_hz (0…1). Save the
   current poses, write `prev + (cur − prev)·α` (shortest arc for angles,
   signed wrap for coordinates), render, then restore the saved poses
   byte-for-byte. RNG is already saved and restored here; extend that pattern.
   Do not interpolate discrete state: animation frames, explosions, HUD
   values, radar.
4. Pacing: present with the native VBL wait, so at most one picture per field
   (50 PAL, 60 NTSC). When α has not changed since the last picture (fast CPU,
   no new field), wait for the next field instead of drawing a duplicate.
5. Validation, all on A500 and 68060:
   - Matched-tick gameplay/HUD/fresh-projection with interpolation on and
     off, and with SLOW_DRAW, must be identical; render must not change
     state (restore check).
   - A VERIFY observer at render entry compares every written pose with the
     formula, using the saved prev/cur and α.
   - At α = 0, a lossless display-DMA comparison (`display_dma.py`) against
     the non-interpolated picture.
   - On the 68060, successive pictures within one tick must differ.
   - Snap cases (spawn, recenter, death/Continue, level exit) must not smear.

### Step 4: Input belonging to each tick

This is the existing correctness item (live input at $22750–$22756 and
$22730 is applied to overdue ticks). Sample joystick, mouse and key state in
the VBL into a ring buffer stamped with the field. Each tick consumes the
sample that belongs to its time, through the native input calls, preserving
modal ownership, key queues, mouse deltas, overflow and pause. Follow AmigaXDev
`fixed-time-simulation.md`. The test is a fixed elapsed-field input edge that
lands on the same tick with and without SLOW_DRAW.

### Step 5: Renderer cost (A500 and stock A1200)

After step 2 an A500 trace holds several complete renders. Profile 100-field
windows on SOL, combat and boss, using complete-call costs from
`routine_cost.py`. Candidates in order of measured share (re-measure first):

1. Polygon pipeline $14a9e: transforms $16c52, vertex cache $17c02,
   perspective DIVS $17cea, the blitter path $17e88/$1d51c, and per-blit
   interrupt overhead (37 blitter interrupts per field). Use 68000/68020
   variants, pixel twins (playbook §10) and the display-DMA check.
2. Star/sprite path $18340/$1bc94, including its WaitBlit.
3. Background RectFill from $0c1ba: direct blitter or CPU fill, and
   overlap with other work.
4. HUD $0bf8a: redraw only what changed, per buffer (two buffers).
5. Render-side projection when the simulation pass already projected the
   same poses (only at α = 0).
6. Sound handler $1126: model it and twin its Paula register writes.
   Optimise only if audio writes are identical.
7. MrgCop in shake/boss frames (the rejected cache's lesson: measure
   frequency first).

Apply the 3% full-frame rule. Keep the original code on any CPU where a
replacement is not faster.

### Step 6: Fast-CPU ceiling

The 68040/25 and 68060/50 both present about 29 pictures/s (above) with
pending updates 0→1. Doubling the CPU gains 0.3 fps, so each picture takes two
fields for a reason other than CPU speed. The suspects are a frame just over
one field (blitter or chip RAM), or the VBL wait at $1c84c plus the buffer
handshake costing an extra field. Profile one 68060 frame against the field
boundary first: this is the main obstacle to 50/60 fps. Also run the
68030/68040/68060 matrix, and find out whether chip RAM or the blitter limits it (playbook §11: a
faster CPU does not make chip RAM faster). Profile with `SWAP_ONLY`. Check
caches. Do not chase CPU savings that the bus erases.

### Step 7: Release

Run the full correctness suite at the chosen N: native twins, encounter
routes, death/Continue, level exits, ending, preferences, PAL. Then the
disabled-bytes check, `audit_hooks.py`, diagnostic exclusion and the
`play60.sh` smoke test. A user playtest on real controls confirms pace and
feel. Only then consider making SIM60 the default loader option. Update
README/docs to the current state and delete tools nothing uses.

### Rejected direction

Do not continue tuning the 60 Hz tick for the A500. The measured returns per
change are 0.3–3%, and the gap is a factor of five or more.

## Checkpoint before the performance plan

The 60 Hz conversion below is the base for the plan above.
This checkpoint contains the experimental implementation and
validation tools, not a completed release.
The current build includes input timing corrections, unrolled input constants
and X-distance rejection before collision candidate classification. It reaches
native death at tick 9212 in the extended combat route. Ticks 600–9212 average
59.67 updates/s on A500 with 131 presentations and pending updates 23→70;
delayed 68020 averages 60.00 with 274 presentations and pending updates 21→21.
Heavy A500 ticks 600–5400 average 59.11 updates/s with 77 presentations and debt
23→95; delayed 68020 averages 60.03 with 153 presentations and debt 21→19.
The preceding build averaged 58.70 in heavy A500 combat with 70 presentations
and debt growth of 106 ticks; the current growth is 72 ticks. This improves
throughput and presentation frequency, but does not establish sustained 60 Hz
in every heavy scene. The delayed 68020 heavy interval repays two pending ticks.
Gameplay/HUD/fresh projection and private timing state match across CPUs and
the preceding build at all eight checkpoints, allowing only deferred projection
scratch. Six level resets and 89 hooks pass, and the normal build is restored
(`tmp/scan-order-extended-validation.json`).
A saved 100-field current-build A500 profile shows one 13-field renderer span
and a 14-field complete update-entry gap (0.217–0.250 seconds). There is only
one presentation, so no complete presentation interval can be measured there.
Delayed 68020 renderer spans are five fields; its separately identified
20-field diagnostic waits explain the 25-field update-entry gaps. This checks
that intentional test delay is not attributed to the renderer; it does not
prove maximum input latency (`tmp/scan-order-latency-validation.json`).
Sustained A500 throughput, presentation/input delay, broader gameplay coverage
and release audits remain open. Faster later sections do not prove every heavy
scene meets its update budget.
Normal builds retain the opt-in legacy-loop prototype in `timing.s`; that
prototype does not achieve the 60 Hz goal. The replacement is selected with
`VERIFY_FLAGS=-DSIM60=1` and enabled with `CUSTOM1=1`.

Original 68000 NTSC measurements at native frames 90/120 both give 12 fields
per update (5.0 updates/s). Later stationary opening-level windows slow to
18–19 fields/update at frame 180 (3.30 updates/s across complete intervals)
and 14–17 at frame 240 (4.00). The current twelve substeps per native update
therefore preserve the early-scene reference pace and remove these observed
slowdowns; they do not reproduce native wall-clock pace in every scene.
`tmp/native-pace-expanded-validation.json` retains the four 100-field windows,
verified native loop instructions and restored normal build. These measurements
use the reconstructed loader and do not establish original-loader equivalence.
Confirmation of the intended nominal reference pace remains open.

Gameplay can be driven through the existing VERIFY input fixtures without
host UI access. They feed native input calls on simulation ticks, following the
shared playbook's Battlehawks/TD2 approach. The attempted host-app wrapper was
unnecessary for these checks and sent no input. Physical controls and audible
output remain unverified, but this does not block scripted gameplay validation.

The current conversion is playable with `amiga/play60.sh`, which builds a
separate SIM60 slave and enables CUSTOM1 with normal controls and sound.
`make -C whdload sim60` builds that artifact without launching. The original
loader path and original-timing development build remain available.

## Replacement implemented

- Separate update/draw paths and a 60 Hz clock accumulator. Elapsed display
  fields are converted using Exec's observed 50/60 Hz rate. Each catch-up batch
  snapshots owed updates before rendering; time accrued during that work is
  retained by the next poll. This prevents indefinite presentation starvation.
- Integer remainder integration for translation, rotation, acceleration and stars.
  Collision checks and native input sampling run every simulation tick. The
  repeated player-separation loop retains native correction strides; ordinary
  collision rollback reverses the exact fractional displacement.
- Continuous jump integration through the reference trajectory's 5 Hz samples.
- Flying-enemy height and banking integrate every tick, with native decisions
  once per twelve active callback ticks.
- Boss banking, level-2 climb/descent, level-4 sideways motion and type-7 exit
  pitch integrate every tick, with native decisions once per twelve active callbacks.
  Type-7 entry/exit speed changes also integrate each tick, with a movement
  correction for the native move-before-AI order. Altitude clamps, temporary
  collision queries and spawn positions remain native.
- Type-13 climb/fall and type-47/48 descent/extra charge movement now integrate
  every tick. Their native decisions advance once per twelve active ticks.
- Per-impact knockback phases hold the native speed override for twelve ticks,
  preventing per-tick acceleration from weakening it between decay steps.
- Type-4 contact, shield ramming and type-43 actor-contact effects use independent
  per-actor twelve-tick clocks; the separate boss collision callback has its own
  clock, and shield impact audio uses the shield-damage schedule.
  One-shot projectile and self-destruct impacts remain immediate.
- Level-5 type-46 terrain contact uses an independent player clock: immediate
  first damage, subsequent effects at least twelve ticks apart, no rendering
  advancement, and reset on new gameplay sessions. Direct native energy-word
  subtraction and inactive behavior are preserved.
- Pickup rise and yaw integrate every tick. Healing/countdown events occur at
  each twelve-tick boundary, with the native removal branch on the thirtieth.
- Per-projectile lifetime phases and per-player weapon cooldowns, measured from
  activation instead of the global legacy phase.
- Mesh animation, explosion and frame-oscillator updates have independent per-actor twelve-tick
  clocks, reset at their native initializer sites. First callbacks are immediate;
  duplicate update calls and rendering do not advance their counters.
- Death detection and pending Quit to DOS requests run every tick. Periodic
  spawning, warning sounds and the native frame counter retain their original
  twelve-tick cadence. Native level-exit paths already clear the active-game flag
  during collision handling. A requested native level-0 to level-1 transition
  passes reset and cross-render checks. A native first-boss kill/exit and a
  controlled-health final-boss ending also pass; later-level exit coverage remains.
- Damage shake has a per-impact twelve-tick clock, including same-value refresh
  and immediate native menu/reset clearing. Its separate byte RNG and offsets
  are included in mapped-state comparisons.
- Simulation-owned animation callbacks and gameplay RNG restoration after drawing.
  Removed actors discard their fractional records.
- Actual modal dialog/preferences wrappers exclude only the modal interval and
  retain existing simulation debt. Nested wrappers defer to the outer modal. Ordinary
  Forbid/Permit calls do not discard elapsed simulation time.
- Shorter signed-distance arithmetic preserves native wrapped results and both
  returned registers, validated with native twins and boundary cases.
- Cached depth-sort distances with pointer traversal and original strict-comparison/zero-distance order.
  A VERIFY twin compares each call with the native routine.
- Inline collision-list scanning preserves native ordering, overlap arithmetic and
  every hit-link write. It is enabled by default within SIM60 after native-twin
  validation and measured routine savings on both CPUs. SCAN_FAST=0 is the baseline.
- Zero-pitch native movement uses the existing flat calculation even when bank
  is nonzero, with guarded trigonometric prerequisites and native-reference checks.
- Stationary stars skip arithmetic only with zero effective velocities and zero
  stored remainders; native bounds checks, respawns and RNG remain active.
- Zero-numerator divisions in motion and star integration bypass DIVS with the
  same result/flags; nonzero numerators retain native division.
- Scalar radius projection omits the unused zero component while retaining native
  signed multiplication/division. Native twins and replacement-only state checks
  pass on both CPUs; the measured optimization defaults on within SIM60.
- Power-up timers have individual activation phases and preserve native expiry
  callbacks. AI decisions and remaining native counters retain 5 Hz units.

Residual HUD work remains in updates. Generic AI intentionally retains the shared
five-Hz decision phase; continuous movement is integrated every tick. Terrain damage now has an independent player contact clock. Boss acceleration needs broader trajectory
validation. This is cooperative
scheduling: a long render delays input handling and updates catch up afterward.
It does not run physics in an interrupt or interpolate rendered positions.

## Verified evidence

- The current shared-geometry build also passes a real PAL/50 Hz display run
  of the type-10 combat route. Exec reports 50 Hz; gameplay/HUD/fresh projection
  matches NTSC at ticks 1800/2400, allowing only deferred projection scratch.
  All six level resets and 88 hooks pass. Scheduler credit conserves
  `60 × elapsed fields = 50 × completed ticks + credit change` between polls.
  The 600-tick interval uses 470 PAL fields (9.4 seconds), six presentations
  and debt 95→59; it repays backlog and is not sustained-throughput evidence.
  `tmp/geometry-pal-validation.json` retains the checks and confirms normal
  build restoration. The underlying game remains NTSC; this verifies the
  replacement's field-to-timestep conversion, not PAL audiovisual equivalence.

- B767 adds eight coupled type-7 curved-exit checks to the existing 52 boss
  cases. Both CPUs pass 384 ticks checking speed/pitch, exact XYZ rollback,
  retention of completed rotation and full actor/record replay after restoring
  the replay angular inputs. Four starting speeds cross the positive signed-word
  boundary. The deliberate X rollback error fails all eight new cases; earlier
  cases remain passing. Gameplay/HUD/fresh projection matches the preceding build
  and across CPUs at tick 150, with only deferred projection scratch differing.
  All 87 installed hooks pass; normal builds are byte-identical. Results are in
  `tmp/boss-exit-spatial-validation.json`. This proves rollback/replay consistency
  during curved movement. Optional BP60 now independently checks the specified
  continuous trajectory: all 1152 XYZ coordinates per CPU stay within one unit
  of a rational velocity integral using native projection tables. Maximum error
  is 287/288. Omitting acceleration fails 890 coordinates; a two-unit X corruption
  fails exactly one point. Gameplay/HUD/fresh projection and all 87 hooks pass.
  See `tmp/boss-path-validation.json`. Coarse native curved-position equality
  and full encounter behavior are not claimed by this interpolation check.

- Boss eligibility is now simulation-owned. Native radar drawing previously
  produced data $1efc, which the boss-spawn check consumes. SIM60 suppresses
  those writes and computes the identical active-list predicate before the
  native periodic spawning block. Both CPUs pass 262 native-reference cases;
  the deliberately wrong classification fails five cases. Gameplay/HUD/fresh
  projection and the newly mapped eligibility/spawn-progress fields match
  through tick 1500. A read-only before/after capture of one A500 render at tick 229 retains all
  561 changed data bytes; mapped gameplay stays unchanged, with only deferred
  shared projection scratch differing. A guarded inventory identifies all 561
  changed bytes by storage family, without adding any comparison exclusions.
  Code/gameplay corruption controls fail, and added unknown bytes remain
  visible (`tmp/render-write-inventory.json`, `tmp/render-inventory-controls.json`).
  Model-sort classification covers only the observed first nine slots.
  Separate lifetime checks pass thirteen complete model draws across current
  heavy A500, boss A500 and delayed 68020: all 520 key and 129 pointer reads
  follow initialization in the same pass; omitted initialization is rejected
  (`tmp/model-sort-lifetime-validation.json`). This does not prove total array
  capacity, unseen consumers or all rendering paths. Broader consumer-lifetime
  classification and full boss encounters remain open. The vertex-cache
  audit now covers 3614 coordinate reads/2294 writes in 27 reset epochs across
  early A500, late A500, delayed 68020 and boss A500 traces. All 2554 transformed
  and 1060 projected reads follow initialization within their epoch; no prefix
  accesses are excluded. The full-width transform producer is also guarded.
  A trace missing projected writes is rejected
  (`tmp/vertex-projection-lifetime-validation.json`). Unexecuted clipping sites,
  other scratch consumers and unseen paths remain outside that check.

- HUD_CLOCK now defaults on within experimental SIM60. The cockpit indicator
  executes native arithmetic on an independent twelve-tick clock, preserving
  visibility, bounds and signed steps; rendering no longer advances it.
  Both CPUs pass 64 native-reference cases/2304 substeps, repeated-render and
  inactive/reactivation checks. A broken render gate yields 6174 expected
  fixture errors. Gameplay, indicator phase and clock match across CPUs and
  a fixture-free run. Matched-tick images on both CPUs now agree throughout the observed game
  rectangle; remaining differences lie at capture-buffer edges. Lossless display-DMA checks now also match all 16000 fetched words and
  effective display state across all held fields on both CPUs. They detect
  the old HUD defect and reject altered pixel/palette data and unsupported
  modes. Host capture-buffer bounds remain unproven, but guarded guest-display
  equality no longer depends on cropping those images. The HUD-enabled level-5
  comparison now matches gameplay, indicator timing and fresh actor projection
  at ticks 600/1500/3600 on normal A500 and delayed 68020, with five resets
  passing. A500 mean update cost falls 9.04% (77214.92→70237.30 cycles), and
  presentations increase 84→119 over 3000 ticks. This still leaves substantial
  input/presentation delays. PROJECT_BATCH now defaults on within experimental
  SIM60 after the native fixtures, held display and cross-render checks.

- PROJECT_BATCH defaults on within experimental SIM60. The initial heavy-combat A500
  capture matches mapped gameplay and fresh actor projection at 1800/2400,
  with all six resets passing; only intentionally deferred shared geometry
  scratch differs. Complete update means fall 117479.52→108110.68 cycles
  (7.98%). All 92 observed passes accept and preserve animation callback order.
  The delayed 68020 also matches at both ticks, with 96 accepted passes and
  correct callback order; mean update cost falls 7.57%. Both CPUs match each
  other for gameplay and fresh actor projection. Separate full-pass native
  twins now pass 64 cases on each CPU, including unknown scratch consumers,
  visibility, hooks, view exclusions and duplicate lists. Removing the
  visibility guard produces eight actor/scratch/path failures as expected.
  The A500 hundred-field combat window still contains no presentation. The
  HUD-fixed held combat frame now passes lossless display comparison; broader
  encounters and acceptable latency remain outstanding for the full goal.


- The heavier type-10 A500 window at tick 1800 completes 83 updates in 100
  fields with no rendering: complete updates average 119867 cycles. This
  confirms simulation cost itself needs reduction in that encounter.
  RECORD_CACHE_SLOTS now defaults to 32 after matching gameplay/projection and
  all six reset records on both CPUs. Mean update cost falls 1.99% on A500 and
  2.09% on 68020, with 64 additional bytes and no added lookup instructions.
  The measured candidates match default-on builds; 16 retains the baseline.
  This small change does not close the performance gap.


- MOVE_IDLE now defaults on within experimental SIM60. The fully stationary
  shortcut passes 64 full actor/record/CCR comparisons, 480 native movement,
  52 boss and four collision cases on both CPUs, plus native death/retry.
  A broken-flag negative control fails as expected. Gameplay/projection
  matches across CPUs/render costs through tick 3600 and all five level
  resets pass. Matched update means fall 4.20% on A500 and 3.06% on 68020.
  Render pauses remain; these savings do not finish the full performance goal.

- A current level-5 A500 trace measures a complete 15-field render phase and
  a 15-field gap between update starts (233–267 ms), without artificial delay.
  Complete updates average 80302.90 cycles, but catch-up and one presentation
  in 100 fields demonstrate that near-sixty average simulation throughput does
  not establish responsiveness. Movement and collision scanning remain major
  targets. The new simulation_latency report distinguishes complete gaps from
  truncated boundary intervals; full results are in internals.

- The native inactive-game branch now also bypasses simulation projection,
  stars and shake. A failing old-path control executes all three after exit;
  corrected A500 and delayed 68020 traces omit them and retain exactly one
  cooldown, clone timer, power timer, post-update and recenter call. Both pass
  native level reset checks and match gameplay/projection at tick 190 and
  resumed ticks 600/1500. The exit is injected at the native check; natural
  boss/collision triggers remain to be validated. The ordinary five-level route
  still matches the preceding build at ticks 600/1500/3600, with all resets
  passing; the normal slave rebuild passes.

- Five consecutive requested native transitions through level index 5 pass all
  clock/private-state reset checks on normal A500, delayed A500 and delayed
  68020. Level-5 gameplay/projection matches at ticks 600/1500/3600, including
  natural damage. Across 3000 ticks the three runs present 72/18/103 times;
  A500 backlog falls 117→27 and 184→95, while 68020 changes 21→27. Type-9
  decisions pass twelve-tick cadence checks in the 68020 trace. Natural exit
  triggers, unforced terrain spawning and type-9 firing remain outside that route.

- MOVE_ZERO defaults on within SIM60. Zero-forward-speed movement retains
  rotation and linear velocity terms while omitting zero products. Both CPUs
  pass 480 native actor comparisons (80 shortcut cases), 52 boss cases, four
  collision cases, native retry and matching gameplay/projection through 3600.
  Matched level-1 measurements reduce update cost 4.57%/3.54% to
  92420.93/41183.80 cycles on A500/68020, with matching state and enemy firing.
  A500 presentations rise 13→15 over ticks 1500–3600; the short 68020 interval
  has no throughput gain. Sustained performance remains unfinished.

- Level-1 traces now exercise type-8 decisions and one real enemy shot on both
  CPUs. Ordered calls follow twelve-tick boundaries; projectile owner/return
  checks pass, and gameplay/projection match before and after firing at
  ticks 3700/4200. The earlier tick-1500 A500 profile averages 96849.75 cycles
  per complete update and has no presentations during its sixty-field catch-up
  window. Full-scene throughput and broader enemy behavior remain unfinished.

- A requested native level-0 to level-1 transition passes on normal A500, delayed
  A500 and delayed 68020: session advances, all private simulation state resets, and loading
  time is excluded from the new gameplay clock. Mapped gameplay/projection
  match at resumed ticks 600/1500/3600. Delayed A500 averages 58.96 updates/s
  over ticks 600–3600 and adds 53 pending ticks; sustained throughput in this
  scene remains unproven. This does not validate a natural boss
  kill, mid-update exit, later transitions or the ending.

- Three-minute runs reach tick 10800 on normal A500, A500 with twenty added
  fields per render, and equivalently delayed 68020. All mapped gameplay and
  projection state matches at 3600/5400/7200/9000/10800, including natural
  damage (energy 680/480/264/264/144). Across ticks 3600–10800, rates are
  60.10/59.93/59.99 updates/s with debt 67→55, 159→167 and 20→21.
  Presentation counts are 90/40/219. This establishes longer render-independence
  coverage on the level-0, nine-object route; it does not bound unsampled debt
  or presentation/input latency, or establish heavier-scene performance.

- SHOT_FAST=1 defaults on within experimental SIM60. The first projectile scan
  preserves ordering, owner exclusion, self behavior and signed overlap math.
  Both CPUs pass 64 all-register native comparisons, native retry and matching
  gameplay/projection at 1500/2400/3600 across options and CPUs. Complete scan
  costs fall 54.53%/53.68%; update costs fall 5.08%/5.27% to
  94297.69/43275.95 cycles. A500 intervals are 59.60/61.86 updates/s with
  six/thirteen renders and debt 97/103/67. The delayed 68020 measures
  60.81/59.60 updates/s with debt 24/12/20. Longer/heavier validation remains.

- HEADING_FAST=1 defaults on within experimental SIM60. The guarded lookup-table
  replacement passes 4217 all-register native comparisons on both CPUs, native
  retry, and matching gameplay/projection at ticks 1500/2400/3600 across options
  and CPUs. Heading means fall 42.15%/50.08%; complete updates average
  99343.20/45723.64 cycles (3.97%/4.76% lower). A500 intervals are
  57.75/64.17 updates/s, six/eleven renders and debt 106/141/63. The delayed
  68020 measures 60.27/59.75 updates/s with debt 26/22/27. Sustained throughput
  remains unproven. Default binaries reproduce the explicitly enabled builds.

- Boss callback checks now include four positive speed-word overflow cases,
  bringing B766 to 52 cases. All pass on the 68000 and delayed-render 68020,
  including native death/retry. Mapped gameplay/projection state matches at
  ticks 1500/3600 across CPUs and the preceding baseline. These additions test
  callback speed publication/endpoints; coupled overflow trajectories remain open.

- Terrain damage now uses an independent player clock instead of the shared
  phase. Both CPUs pass 96 native-instruction cases and 3456 substeps, covering
  initial phases, energy-word/tick wrapping, rendering, duplicate contacts and
  alternating terrain objects, plus intermittent/inactive/reset checks. Native
  death/Continue/retry clears a deliberately populated clock on both CPUs.
  Mapped gameplay/projection state matches through 1500/3600 across CPUs and
  differing render costs. Controlled native level-5 contact now also passes as
  described under remaining gameplay coverage; unforced spawning remains open.

- RECORD_CACHE=1 defaults on within experimental SIM60. Every cached record
  pointer validates its actor tag; misses preserve original search/allocation.
  Forced one-slot collisions on the 68000 and normal caching on the delayed
  68020 pass boss, collision, animation, special, flying, contact and pickup
  fixtures plus native retry. Five fixtures now run once per boot, fixing
  duplicate counts after Continue. Replacement-only state/projection matches
  at 1500/2400/3600. Lookup averages fall 56.82%/58.79%, with update averages
  103447.79/47993.64 cycles on the 68000/68020. The 68000 intervals are
  56.02/64.46 updates/s, six/nine renders and debt 101/165/82. The first interval
  includes an additional render; this does not establish sustained performance.

- MOVE_WORD_MUL=1 defaults on within experimental SIM60. Five movement products
  use signed word multiplication; two wider intermediate products remain native.
  Both CPUs pass 480 whole-actor comparisons, 48 boss and four collision cases,
  plus native retry. Replacement-only gameplay/projection state matches at
  1500/2400/3600 across CPUs and against the baseline. Movement averages fall
  7.10%/8.75%, with total update averages 105148.64/49035.07 cycles on the
  68000/68020. The 68000 intervals are 56.66/64.11 updates/s with five/nine
  renders and debt 108/161/84. The delayed 68020's second interval is exactly
  60 updates/s with debt held at 21; this is still limited scene coverage.

- SCAN_HOIST=1 defaults on within experimental SIM60 after 15047 native scan
  comparisons, including 68 boundary cases, pass on each CPU. Query geometry
  loads and type-7 query exclusion move outside the candidate loop. Scan costs
  fall 8.51%/6.38% on the 68000/68020; update averages are 106816.21/49971.02
  cycles. Replacement-only gameplay/projection state matches at 1500/2400/3600,
  with native retry passing. The 68000 intervals are 55.67/64.11 updates/s,
  five/eight presentations and pending ticks 109/179/102. Presentation remains
  far too slow; this is a local improvement, not completion of the timing goal.

- SORT_ORDERED=1 defaults on within experimental SIM60. Positive nonincreasing
  key lists skip redundant selection scans; other lists retain the full path.
  Both CPUs pass 3910 native-order comparisons including 64 boundary cases.
  Replacement-only gameplay and projection state match the baseline and each
  other at 1500/2400/3600, including native retry. Measured sort costs fall
  27.97%/30.91% on the 68000/68020; update averages fall to 107615.07/50253.44
  cycles. The 68000 intervals are 55.21/64.81 updates/s with five/seven renders
  and pending ticks 120/198/109. This remains insufficient presentation speed.

- PROJECT_SKIP=1 now defaults on within experimental SIM60.
  State plus simulation-written projection fields matches at 1500/2400/3600
  across modes and CPUs. It reduces measured later-scene 68000 update cost from
  130769.57 to 110082.22 cycles, with intervals 54.22/64.86 updates/s (the latter
  pays backlog) and five/six presentations. The delayed 68020 also has lower
  update costs. The final J762 native-reference fixture passes all 240 cases
  on both CPUs, including unknown scratch consumers, visibility paths, final
  view objects, inactive/rendering guards and counts 0/1/2/3/256 with duplicates.
  All fake actor bytes and final scratch match; temporary code/state is restored.
  Fresh default builds reproduce the 68000 costs/intervals and match state at
  all three checkpoints across CPUs. The delayed 68020 measures 51551.85 cycles
  per update and intervals of 60.47/59.60 updates/s, with pending ticks 25/18/26.

- The default scalar shortcut (RADIUS_SMALL=1) passes
  384 boundary cases and over 30000 native comparisons per CPU through tick
  3600. It requires scale 128 and radius 0..65535; wider inputs preserve a
  native multiplication quirk. Mapped state and native retry match on both
  CPUs. Replacement-only state also matches at 1500/2400/3600. Scalar-call cost
  falls 45.66% on the 68000 and 46.44% on the 68020. Later 68000 update averages
  fall to 130769.57 cycles, but still exceed the field budget. Its longer intervals
  improve to 48.43/58.58 Hz, with debt 167 to 382 to 411 and three presentations
  each. The delayed 68020 stays near sixty while paying down earlier debt.

- Longer pre-RADIUS_SMALL captures match mapped state at ticks 1500/2400/3600
  across the 68000 and a 68020 with twenty added fields per render. The 68000
  averages 46.47 then 55.94 updates/s, with only three presentations per interval;
  debt grows 194 to 456 to 543 ticks. The delayed 68020 averages 61.02 (catch-up)
  then 59.85 updates/s, with debt 36 to 21 to 24. These remain SOL checks,
  not full level-transition or encounter coverage. Complete later-scene 68000
  updates average 137057 cycles, above the 119665-cycle field budget even before
  rendering/interrupts; simulation projection accounts for 40690 cycles.

- Signed-distance twins pass 471605 comparisons and 512 boundary cases on each
  CPU, alongside 1778 sort comparisons and 32 configurations. Replacement-only
  state matches at ticks 600/1206/1300/1500 across modes and CPUs after retry.
  Distance-call cost falls 401.49 to 334.77 cycles on the 68000 and 190.84 to
  157.81 on the 68020. The 68000 completes 900 updates in 965 fields (55.96 Hz),
  with six presentations, but debt still grows 129 to 194 ticks. The delayed
  68020 has an extra presentation and averages 58.32 versus 59.87 Hz; no overall
  speedup is claimed there. DISTANCE_FAST defaults on within experimental SIM60.

Exact-tick snapshots use `tools/fixed_window.py --tick`; multiple boundaries use
`--tick-checkpoints`. The comparator covers mapped objects, fractional motion,
star remainders, jump integration, weapon cooldowns, RNG, inventory and counters.
It deliberately excludes raw pointers and projected coordinates; it is not a
complete machine-state proof.

- Zero-pitch movement passes 384 original-versus-optimized full-actor cases on
  both CPUs, including signed extremes, cardinal headings, angle/position wrap
  and nonzero-pitch controls. All 48 boss and four collision cases pass after retry;
  their diagnostic counters now have once-per-boot guards. Replacement-only
  states match at 600/1206/1300/1500 and death/retry passes. Movement-call cost
  falls 9.11% / 10.22% on the 68000/68020. The 68000 reaches 55.33 Hz over 900
  updates with six presentations, but debt grows 134 to 210 ticks. FLAT_PITCH
  defaults on; zero restores native path selection.
- Stationary-star integration matches at 600/1206/1300/1500 across both CPUs,
  covering idle, moving and turning inputs, with unchanged remainders and RNG.
  Death/retry passes. In the idle capture, complete star updates average 2037.64
  versus 4534.91 cycles on the 68000 and 864.12 versus 1834.62 on the 68020.
  The 68000 reaches 54.44 Hz across 900 updates with six presentations; debt
  grows 143 to 235 ticks. The delayed 68020 has no measured overall interval
  gain. STAR_IDLE defaults on, with zero retaining the previous implementation.
- Pointer-walk sorting passes 1778 native-order comparisons on each CPU, including
  32 synthetic configurations covering ties, zero/negative keys, level overrides
  and full duplicate-pointer lists. Replacement-only states match at 600/1500
  across CPUs, with death/retry passing. Sort costs fall 17.12% on the 68000 and
  17.67% on the 68020 versus the indexed cached sorter. The 68000 reaches 54 Hz
  over 900 updates with six presentations; debt still grows 138 to 238 ticks.
  SORT_WALK defaults on within SIM60; zero selects the indexed baseline.
- Zero-division shortcuts preserve mapped gameplay and motion/star remainders at
  ticks 600/1500 across both CPUs, and real death/retry still passes. Complete
  movement calls average 4417.59 versus 5160.35 cycles on the 68000, and 2040.54
  versus 2187.88 on the 68020. The 68000 reaches 52.99 Hz in this route, with six
  presentations versus five over the same 900 updates. Debt still grows 145 to
  264 ticks. DIV_ZERO=0 reproduces the preceding binaries exactly.
- Scalar projection matches 14008 native calls on the 68000 and 14482 on the
  delayed-rendering 68020, including 128 signed/extreme synthetic cases each.
  Replacement-only states match across implementations and CPUs at ticks 600/1500,
  with real death/retry passing. Complete-call cost drops 49.26% / 47.43%.
  The 68000 now completes 900 updates in 1025 fields: 52.68 Hz versus 50.05 Hz,
  with five presentations versus three. Pending debt still grows 163 to 288;
  sustained 60 Hz remains unmet. RADIUS_FAST=0 provides the native baseline.
- Collision scanning passes 6647 native-twin calls per CPU, including 68 synthetic
  cases, with zero result/link mismatches. Fast-only captures match mapped state
  at restarted ticks 600/1500 across implementations and CPUs. Complete-call cost
  falls 48.43% on the 68000 and 55.44% on the 68020. On the 68000, 900 resumed
  updates take 1079 fields versus 1146: 50.05 versus 47.12 Hz, with three renders
  in each interval. Pending debt still grows from 214 to 393 ticks, so sustained
  60 Hz remains a demonstrated failure. The delayed 68020 interval is near 60 Hz
  but does not show an overall throughput gain; see the measured table in internals.
- Moving/firing at tick 1500 matches between normal rendering and an added
  20-field draw delay (150 versus 37 renders in the retained PAL captures).
  The genuinely NTSC capture matches that PAL state after 146 renders.
- A jump activated after completed tick 1205 matches with normal and delayed
  rendering at ticks 1217, 1229, 1475 and 1745. Heights are 220, 430, 2531 and 0.
  The comparison includes fractional jump and individual weapon/projectile timing.
- A real native P dialog held for at least 60 fields resumes without catch-up
  for the paused interval. Between checkpoints 1307 and 1308, 66 fields pass
  and only the in-progress simulation tick completes. States at 1475 and 1745
  match the uninterrupted jump run. Preferences/death/transitions remain untested.
- A native-callback oracle checks twelve type-13/47/48 motion cases on the
  68000: four native calls versus 48 physics ticks per case. XYZ matches the
  expected fractional path on every tick; complete actor and RNG state matches
  at every twelve-tick boundary. This includes descent across zero, clamping,
  charge expiry, steering, transformation and player contact. The normal SOL
  route still matches its previous mapped state at ticks 201 and 1500. The
  slower-rendering 68020 run passes the same oracle. On each CPU that is
  576 checked substeps and 48 complete actor/RNG comparisons. Mapped gameplay
  matches across CPUs/render costs at ticks 201, 600 and 1500 (11 versus 43
  renders at the final boundary). Sustained rate remains unproven.
- Flying-AI height/bank integration passes twelve native-callback cases on both
  the 68000 and a 68020 with twenty extra render fields. Each run checks 576
  intermediate XYZ/bank samples and 48 complete actor/RNG boundaries. Native
  descent, climb/clamp, signed banking and decision timers are retained at those
  boundaries. Mapped gameplay matches at ticks 201, 600 and 1500, with 14 versus
  43 renders at the final boundary. The expanded 72-byte record also passes the
  special-enemy and collision oracles on the 68020. Clock debt remains, so this
  is state/cadence evidence rather than proof of sustained 68000 performance.
- Boss motion passes thirty native-callback cases plus eighteen coupled braking
  cases on the 68000 and delayed-rendering 68020. Callback cases check 1440
  XYZ/bank/pitch substeps and 120 complete actor/RNG boundaries per CPU; entry/exit
  speed is also checked each tick. Braking adds 864 speed checks and 72 complete
  native actor/position boundaries, covering fixed straight, diagonal and pitched
  directions, stops, zero crossing, reverse motion and signed braking-speed wrap.
  The scalar-speed correction failed two diagonal cases; integrating native axis
  displacement vectors fixes both and retains native boundary positions in all
  eighteen cases. Rollback/replay restores the extra vector remainder.
  Callback cases span all seven level handlers, altitude crossings/clamps, sideways
  trig rounding, contact reversal, bank thresholds and pitch wraparound. Animation,
  random heading and aim-target state match at native boundaries. Allocation is
  stubbed; these are isolated cases, not full encounter/creation tests. Curved exit
  movement and positive-acceleration overflow need further pace validation.
  Mapped gameplay matches at ticks 201, 600 and 1500 (6 versus 41 renders), and
  matches the preceding build with the new vector fields verified zero on this
  ordinary route. The 128-byte records pass collision, special, flying, contact
  and pickup oracles on the 68020. Native allocation, speed-update and immediate-
  impact entries are intact afterward; BOSS_TEST has no effect without VERIFY.
  Clock debt remains, so sustained performance is not established.
- Mesh/explosion/oscillator clocks pass eight native-reference cases on both CPUs,
  with 384 full actor/animation-array substep comparisons per CPU. Real type-11
  and two-part type-41 animations, explosion progression/expiry, oscillator normal
  and endpoint cycles, signed-byte extremes, duplicate calls, extra rendering,
  same-actor refresh, staggered actors and tick wraparound pass. Oscillator restart
  preserves the separate mesh clock; the null-actor path is exercised too.
  Guarded initializer hooks and temporary-return restoration pass byte checks.
  Real unlinking and visible sprite output remain outside this isolated fixture.
  Mapped gameplay matches at ticks 201, 600 and 1500 (13 versus 41 renders).
  The 144-byte records pass all 48 boss cases plus collision, special, flying,
  contact and pickup oracles in the delayed-rendering run. ANIMATION_TEST is
  byte-excluded without VERIFY, and the normal build is restored. Clock debt
  remains; these correctness results do not establish sustained performance.
- Post-update event splitting passes 48 signed-energy death cases, 24 pending-quit
  cases and 768 periodic substeps on each CPU. Native masks 15/63, frame-counter
  wrap and first-update request suppression retain their behavior. Mapped state,
  including the active-game flag, matches at ticks 201/600/1500 (12/41 renders),
  and the 68000 matches the preceding build at all three boundaries. Shake,
  contact, animation and 48 boss cases pass in the delayed run. Temporary entries
  are restored and POST_TEST is byte-excluded without VERIFY. The normal build
  is restored; real quit dialogs and level transitions remain unverified. Native
  death/retry and a known sustained-rate failure are described below.
- Finite catch-up batches restore rendering after native retry: the 68000 shows
  the SOL cockpit and scene and renders eight times by tick 1500. Mapped state
  still matches the continuously extended catch-up loop. The pause test exposed
  a pre-existing bug that cleared owed ticks; modal entry now accounts active
  elapsed time and return preserves that debt. Corrected runs on both CPUs
  exclude exactly 60 paused fields, including a 391-tick backlog on the 68000.
  Mapped states match at resumed ticks 600/1307/1308/1500. The 68000 still has
  484 pending ticks at 1500, so the target rate and responsiveness are not met.
- The complete native death/Continue/retry path passes on both CPUs after a
  one-time lethal energy injection at tick 200. Death is detected at tick 201;
  Continue is held for 60 fields. Native cleanup/reload enters session 2 with
  all private motion/timer state cleared, energy 680, level 0 and fresh clock
  credit. Mapped state matches at dying tick 201 and resumed ticks 600/1500.
  However, the 68000 averages only 50.47 updates/second between the latter two
  checkpoints, accumulates 170 additional ticks of debt and never renders in
  the restarted window. The delayed 68020 delivers matching state with 39 total
  renders. This is a known throughput failure, not merely missing evidence.
  The fixture does not cover lethal collision geometry or visual death output.
- Damage shake passes four native-reference cases on both CPUs: 384 substep
  comparisons per CPU cover counter, separate RNG, offsets and unchanged main RNG.
  Both real impact setters pass same-value refresh, and the native menu fragment
  clears pending shake immediately. Duplicate calls, rendering and tick wrap pass.
  Mapped gameplay matches at ticks 201/600/1500 (13 versus 41 renders). The delayed
  run also passes contact, animation and all 48 boss cases. Temporary returns are
  restored, SHAKE_TEST is byte-excluded without VERIFY, and the normal build is
  restored. Visible shake and full menu transitions remain untested.
- Per-impact knockback passes eight native speed/impulse cases on both CPUs,
  including signed extremes, input in both directions, return to input, and a
  same-value hit restarting its interval. The collision oracle still passes.
  An injected -160 impulse during the real input route matches mapped gameplay
  across CPUs/render costs at all seven boundaries from tick 1206 through 1500.
  Speed stays -160 through 1217, -80 through 1229, then decays to allow input
  again at 1302. Final render counts are 13 versus 43. This route bypasses impact
  geometry; the native separation fixture tests that geometry separately.
- Contact effects pass all five native-call-site cases on the 68000 and delayed
  68020: 240 substep effect checks per CPU, independent path/actor clocks,
  shield-bypassing negative damage, tick wraparound and shield-audio scheduling.
  The added boss-contact case preserves its combined native level-zero health
  and energy effects independently of AI. Boss projectile paths retain original
  bytes, including the call at $32a2 and helper entry $111ac.
  Mapped gameplay matches at ticks 201, 600 and 1500 (15 versus 43 renders).
  The 92-byte records also pass the collision, special-enemy and flying oracles
  on the 68020. All six audited immediate-impact sites retain original bytes.
  The effect fixture suppresses sound/animation bodies and uses nonlethal actor
  damage; lethal outcomes and full contact encounters still need coverage.
- Pickup integration passes 504 substeps and 42 complete native actor/global
  boundaries on both CPUs, including all 360 ticks of the normal sequence,
  signed/extreme increments and final-interval removal timing. Mapped gameplay
  matches at ticks 201, 600 and 1500 with 14 versus 43 renders. The ordinary route
  also matches the pre-pickup build, with the new integrator verified inactive.
  The oracle stubs fake-actor removal, inventory presentation and audio helpers;
  actual unlinking, inventory/UI effects and selection changes remain untested.
- The native player-separation loop was reproduced with isolated actors at
  speeds 0, 1, -1 and 12. The old fractional undo made no progress for the first
  three and required the fixture watchdog; the fourth ended at the wrong place.
  The corrected 68000 run matches native position, bounce speed and iteration
  count in all four cases, and preserves ordinary fractional rollback/remainders.
  The fixture leaves mapped gameplay state unchanged at tick 201; the later
  tick-600 state matches the pre-fix route. The same four cases pass on a
  68020 with 20 extra fields per render. Both runs match mapped gameplay state
  at ticks 201, 600 and 1500 (12 versus 43 renders by tick 1500). Outstanding
  clock debt remains; this proves these state comparisons, not sustained rate.
- Five shortened power timers activated after tick 1205 remain at two through
  tick 1216, decrement at 1217 and expire at 1229. Normal and 20-field-delayed
  rendering match at all seven captured boundaries through tick 1300, including
  power phases, inventory and clone state. This diagnostic bypasses acquisition
  and shortens durations. A separate
  68000 test keeps native durations and refreshes speed power at tick 1210
  while its word is still 200: its first decrement moves from 1217 to 1222,
  proving same-value refresh resets its phase.
- Full-duration powers expire at ticks 3605, 7205 and 12005 after activation
  at 1205 (40, 100 and 180 seconds). All seven captured boundaries match
  between normal and 20-field-delayed rendering on the 68020, including clone
  activation, expiry and timer phases. Across the 10799-tick window, the native
  VBL counter advances 10801 versus 10798 fields: 59.989 versus 60.006 completed
  ticks/second, with conserved scheduler credit. This diagnostic suppresses
  damage and bypasses acquisition; it does not validate death or normal difficulty.
  These retained captures precede the flying-AI decision correction below.
- Flying-AI state 3 read an uninitialized stack byte at $f29e. An isolated native
  test produces states 5 and 3 from identical actors with different stack residue.
  The corrected fallback consumes one simulation RNG draw and retains the native
  threshold. Both possible decisions pass paired stack-residue tests, with exact
  RNG consumption, on the 68000 and delayed-rendering 68020. Mapped gameplay
  matches between these runs at ticks 201 and 1500. The correction intentionally
  changes the later RNG sequence and some enemy behavior relative to the undefined
  native branch; it is not bit-identical historical gameplay.
- The cached-sort twin completes through tick 1745 on the fast 68020, checking
  the native and replacement list after every call. Mapped jump-route state
  matches the pre-cache build at 1217 and 1745. The 68000 twin also completes
  through tick 1222 with movement, firing and power activation/refresh. More
  edge/level coverage is needed.
- Before caching, an A500-equivalent 10-field update-only profile spends 14.0%
  of total recorded CPU cycles in depth sorting including its distance calls;
  projection accounts for 23.4%. These shares justify investigating those costs.
- The final cached-sort/power build matches the pre-cache common mapped state
  at ticks 300 and 600; its newly added power phases are all zero in this route.
  It has six renders by tick 600 versus four before caching. The 300-to-600
  interval spans 305 fields versus 306 before caching, with outstanding debt.
  A matched tick-300 ten-field profile measures about 6127 cycles per completed
  cached sort versus 13992 for the native sort (56% less in this early scene).
  This update-only capture completes 13 ticks and presents nothing; it is a
  catch-up window, not proof of sustained 60 Hz or a presentation FPS claim.
  The gameplay image was inspected. Longer/heavier scene measurements remain.


The ineffective frontend option `ntsc_mode=1` left the emulator in PAL. The
launcher uses `uae_ntsc=true`; captures reject a mismatch with Exec's observed
clock. Genuine NTSC traces contain approximately 119665 CPU cycles per field,
versus 142102 for PAL. Earlier nominal NTSC reports based on PAL are invalid.

## Current HUD-enabled combat budget

With PROJECT_BATCH now enabled, `sim60-hud-combat-batch-a500` matches the
explicit-off baseline for gameplay, HUD timing and fresh actor projection at
1800/2400, with six reset checks passing. Mean update cost is 108427.04 cycles
versus 117800.88 (7.96% lower). The candidate's hundred-field trace includes one
presentation; across 600 ticks it takes 602 fields, presents four times, and
increases pending updates 154→156. The baseline takes 621 fields, presents
twice, and increases debt 218→239. The candidate is closer to real time but
still has about 2.6 seconds of accumulated debt and poor presentation speed.
The next performance work should target collision scanning: complete world and
projectile scans average 2057/2104 cycles each in this trace. A constant-heading
movement-vector cache passed 4703 native actor comparisons but saved only
2.88% of update cost; it was removed because it did not establish the required
full-frame gain. The current default combat binary remains unchanged. The
projection optimization alone does not achieve the full goal. A subsequent
exact-output AI geometry cache passes native-output checks but saves only
0.84% of update cost and is also removed. Its standalone run exposed a
comparison issue: actor byte 1 is the radar flag backup. Guarded trace audits
now verify its save/restore lifetime on both CPUs, and the mapper separates it
from live byte-0 flags. `--render-scratch` retains the two observed differences;
negative controls still detect live-flag changes and missing restores. This
improves comparison scope without changing the game binary.

## Movement save-set reduction

A current-build bound rejects further lazy register saving as a worthwhile
standalone optimization. The collision-order A500 profile enters movement
1056 times. Even removing D3/D4/A2 from every save and restore, with no added
branches or replacement preservation, saves at most 50688 cycles: 0.42% of
recorded cycles and an intentionally generous 0.59% of complete-update cost.
Boss movement still needs these registers, so real savings would be lower.
No candidate was added (`tmp/movement-save-budget.json`).

The current short-branch A500 trace averages 98933.35 cycles per complete
update. Movement averages 1897.34 cycles per call; world/projectile scans
1929.05/1982.32; sorting 6352.47; star updates 4562.86. These inclusive means
must not be summed as disjoint costs (`tmp/short-branch-current-budget.json`).
The native AI geometry setup accounts for 2.32% of recorded cycles before
replacement work; no new geometry cache or inlined block is adopted from that
bound (`sim60-short-branch-late-a500/geometry-span-cost.json`).

`MOVE_TRIM_SAVE=1` now defaults on within SIM60, reducing the movement stack save
from 60 to 44 bytes. D5–D7/A4 are not modified by the adapter; native movement
preserves D7, its trig helpers do not change these registers, and the multiply
helper saves D2/D3. The candidate changes only three MOVEM masks and two stack
displacements: eight differing bytes, with no added instructions or storage.
Explicit-off is byte-identical to the current release, and diagnostic flags
remain byte-excluded without VERIFY (`tmp/move-trim-build-validation.json`).

Both CPUs pass 6144 actor/record/CCR movement comparisons, 64 idle cases and
52 boss cases. L861 additionally checks D5–D7/A4 around all 9216 movement
invocations. A deliberate D5 corruption produces 9216 register errors while
actor/record/CCR checks stay clean; the checker rejects it. The combined
fixtures exposed a name collision between the boss test helper and the live
boss gate; only the test helper was renamed. Mapped gameplay/HUD/fresh actor
projection matches the preceding captures at tick 150, with deferred scratch
separate; all 87 hook checks pass (`tmp/move-trim-twin-validation.json`).
The A500 capture matches gameplay/HUD/fresh projection at 4500/5400 and passes
six resets and all 87 hooks. Mean update cost falls 0.53%, 98933.35→98406.08
cycles; movement mean falls 1897.34→1838.53. Over 900 ticks, fields fall
897→891 with four presentations in each, and pending growth improves −3→−9.
These are short-window measurements, not a new sustained-throughput result
(`tmp/move-trim-profile-a500-validation.json`). Delayed-68020 update mean falls
0.95%, 52009.23→51516.95 cycles, and movement mean 997.39→949.25. Its interval
takes 882 versus 911 fields with 27 versus 28 deliberately delayed presentations;
pending growth changes +11→−18. Gameplay/HUD/fresh projection matches within
both pairs and across CPUs at 4500/5400, with six resets and 87 hooks passing
(`tmp/move-trim-profile-020-validation.json`).
The small saving is retained under the playbook's free-change exception: it
removes redundant transfers with unchanged code size and no new state or
instructions. Default production and diagnostic builds match the measured
candidate byte-for-byte; `MOVE_TRIM_SAVE=0` restores the preceding build and
normal legacy builds remain unchanged (`tmp/move-trim-default-validation.json`).
Current-build disabled-code checks pass on both CPUs: 151969 original hunk
bytes, including all 87 simulation patch ranges, have zero unexpected changes.
The six native mutable data objects remain separately guarded; all 4833 code
relocations and the three exact menu-fixture jumps are accounted for. Default
VERIFY bytes match both captured builds; the normal build is restored
(`tmp/disabled-branch-trim-validation.json`). No new long-run throughput claim
follows from the short performance captures.

## Straight-motion integration

MOVE_LINEAR now defaults on within experimental SIM60. It combines the repeated
native vector and fractional integration work for straight, flat motion, retaining
full rollback backups and native fallback. Host arithmetic checks pass 1,507,351
combinations. Both CPUs pass 6144 full actor/record/CCR comparisons and match
fixture-free tick-150 gameplay/HUD. A broken-carry control yields 602 actor/record
mismatches. The full-width remainder guard includes high-word pitch fractions.

A500 baseline/candidate and delayed 68020 gameplay/HUD/fresh projection match
at 1800/2400/3600/5400/7200/9000, with all six resets passing; only deferred
shared projection scratch differs. Complete heavy-window update cost falls
4.49% on A500 (108427.04→103557.23 cycles) and 3.60% on 68020
(57474.49→55403.43). Across 7200 ticks the A500 candidate takes 7208 fields,
presents 39 times and changes debt 142→150, versus 7288 fields/32
presentations/debt 154→242. The delayed 68020 takes 7190 fields, presents
219 times and changes debt 24→14.

The A500 still falls to 54.63 Hz during ticks 3600–5400 and builds 271 pending
updates. The tick-1800 trace retains a fourteen-field update-start gap. Profile
the later slowdown next; near-sixty aggregate throughput is insufficient proof
of responsiveness. The long 68020 route naturally ends at tick 9212 (energy
-80, native death flag 1, active/running clear). Its interrupted end-state is
retained separately; tick 10800 is unreachable. The natural death-entry trace now passes on both CPUs: negative-energy
branch, active clear, death flag, completed tick, loop exit, input restoration
and native cleanup occur in order, with no subsequent simulation updates in
the observed window. Pre-death tick-9190 gameplay/HUD/fresh projection matches.
Declining Continue and starting a new session after this encounter passes on
both CPUs; broader later-death coverage remains. Diagnostic flags are byte-excluded from non-VERIFY builds;
explicit-off and legacy binaries remain unchanged.

## Later combat bottleneck

The tick-4500 A500 trace completes 92 updates in 100 fields without rendering;
complete updates average 107589.65 cycles. Other execution contexts consume
about 16.4% of recorded field cycles, leaving insufficient update/render headroom.
Its tick-5400 state exactly matches the retained long run. Motion-record lookup
averages 248.38 cycles and shows address collisions: eleven observed actor
addresses produce 377 modeled cold-cache misses at shift 5, including with
larger capacities. Using shift 4 produces eleven modeled misses and needs no
extra instructions or memory. `RECORD_CACHE_SHIFT=4` now defaults on after
matched A500/68020 captures pass gameplay/HUD/fresh projection and all six
resets at 4500/5400. Complete update means fall 2.38%/2.20%; record lookup
means fall 248.38→116.97 and 129.38→62.54 cycles. Only two rotate opcodes
change, with no additional allocation or lookup instructions. A500 still adds
21 pending updates over 900 ticks (versus 29), with three presentations each.
The 68020 takes 897 fields and presents 27 times with either index.

`LINEAR_ACTOR_HASH=1` now selects the straight-motion cache slot by default
from the actor address while retaining the full yaw/speed validity key. The
retained tick-4500 baseline contains five distinct eligible vectors, but the
old yaw index repeatedly collides: 285 hits and 189 misses. Complete wrapper means
are 1754.78 cycles on hits versus 3613.71 on misses. A cold-cache trace model
predicts 469 hits and five misses with the actor index, versus 282/192 with
the yaw index; this is an opportunity estimate, not a measured speedup.
Both CPUs pass 6144 full actor/record/CCR native-reference comparisons with
the candidate. Gameplay/HUD/fresh projection matches the baseline and across
CPUs at 4500/5400; all six reset records and 87 installed hooks pass. A500
complete update means fall 3.08% (105029.13→101789.13 cycles); delayed 68020
means fall 2.47% (55980.75→54599.13). The A500 interval uses 906 rather than
921 fields for 900 ticks, with three presentations in each and pending growth
6 rather than 21. Its trace has 489 eligible cache hits and no misses. The
candidate release changes only two instructions, with unchanged binary size.
The default build is byte-identical to that measured candidate; explicit-off
reproduces the previous SIM60 release, and the normal build is unchanged.
Over ticks 600–5400, A500 gameplay/HUD/fresh projection matches at all five
checkpoints and all six reset records pass. Throughput improves only 0.34%,
57.1882→57.3819 Hz, with 45 presentations each and pending growth 236→219.
The change is retained because it adds no instructions, storage or allocation,
while reducing measured update cost on both CPUs. It does not close the A500
performance gap. `LINEAR_ACTOR_HASH=0` restores the yaw index. Evidence is
retained in `tmp/motion-path-profile.json`, `tmp/linear-actor-validation.json`,
`tmp/linear-actor-a500-validation.json`, `tmp/linear-actor-hook-validation.json`
and `tmp/linear-actor-long-validation.json`.

The retained heavy-combat trace contains 136 executed conditional word branches
in the slave whose current displacement fits a short branch. Counting actual
fall-through destinations across interruptions gives an estimated 254120-cycle
saving at four cycles per untaken short branch: 2.12% of recorded cycles.
This is an instruction-cost estimate, not a paired emulator result, and does
not include changed code layout. Details are retained in
`tmp/short-branch-cost.json`.

`SHORT_BRANCHES=1` now defaults on within SIM60: vasm branch optimization
is scoped to the SIM60 sources, preserving explicit `.w` sizes (including the
capture ABI entry). The non-VERIFY build shortens 320 branches and removes one
jump to the following instruction, reducing code by 644 bytes. Both CPUs pass
6144 movement actor/record/CCR twins, 507 world-scan comparisons (68 synthetic
cases), 64 projectile cases and 4217 heading cases. The latter three fixtures
do not establish full CCR equivalence. At tick 150, gameplay/HUD/fresh actor
projection matches the preceding build; deferred scratch is separate. All
87 installed hooks and direct-entry checks pass. Diagnostics remain byte-excluded
without VERIFY. Results are in `tmp/short-branch-twin-validation.json`.
The paired A500 heavy-combat captures match gameplay/HUD/fresh projection at
4500/5400 and pass all six resets and 87 installed hooks. Complete update mean
falls 2.88%, 101871.09→98933.35 cycles. Over 900 ticks, fields fall 906→897,
presentations rise 3→4, and pending growth changes +6→−3 (59.60→60.20 Hz).
The candidate still ends 198 ticks behind; this short recovery interval does
not prove sustained 60 Hz. Results are in
`tmp/short-branch-profile-a500-validation.json`. Delayed-68020 update mean
falls 4.80%, 54630.09→52009.23 cycles. Its interval takes 911 versus 896 fields
while presenting 28 versus 27 times, with pending growth +11 versus −4; the
extra deliberately delayed presentation prevents treating elapsed time alone
as an update-cost comparison. Gameplay/HUD/fresh projection and six resets
match within that pair and across CPUs at both checkpoints; only deferred
scratch differs (`tmp/short-branch-profile-020-validation.json`).

Over ticks 600–5400, the paired A500 run improves 57.4506→57.8894 Hz (0.76%),
with fields 5013→4975, presentations 45→51, and pending growth 213→175.
All five gameplay/HUD/fresh-projection checkpoints match, all six resets pass,
and all 87 installed hooks pass. The candidate ends 198 ticks behind; sustained
60 Hz remains unachieved (`tmp/short-branch-long-validation.json`).
The optimization is retained under the playbook's exception for free changes:
it removes instruction bytes and adds no runtime state or instructions.
The default release and diagnostic build are byte-identical to the measured
candidate, `SHORT_BRANCHES=0` reproduces the preceding release, and normal
legacy builds are unchanged (`tmp/short-branch-default-validation.json`).

## Rejected world collision cache

The tick-4500 A500 trace rejects 4016/4201 world-scan geometry candidates on X
and the remaining 185 on Z. Projectile scans reject 2635/2737 on X and 102 on Z.
Repeated category/type checks plus excluded category-$fd loops account for
907280 cycles across both scans, a 7.58% gross upper bound before caching costs
(`tmp/collision-filter-budget.json`). This was not an achievable speedup estimate.

The world-only ordered eligibility cache retained raw slot ordering, read
geometry fresh and invalidated on update boundaries, AI dispatch, sorting,
removal and nine native category stores. Four A500/68020 cache-off/on runs each
pass 507 native comparisons, including all 68 synthetic cases. Each enabled
run records 199 builds and 289 hits. At tick 150, mapped gameplay, HUD timing
and fresh actor projection match; only deferred projection scratch differs.
All 87 default or 96 experimental hooks pass exact installation checks and
native direct-entry checks (`tmp/scan-slot-validation.json`). This does not
prove all mutation/invalidation paths or full-register/CCR equivalence.

The paired A500 heavy-combat captures match gameplay/HUD/fresh projection at
4500 and 5400 and pass all six reset records. Complete update means improve
only 0.67%, 101871.09→101187.18 cycles; world-scan means improve
2061.38→1873.18 cycles. Over 900 ticks, elapsed fields increase 906→918,
presentations increase 3→4, and pending growth increases 6→18. These differing
presentation counts preclude attributing the whole interval to update cost;
the result does not establish improved sustained throughput. Results are in
`tmp/filter-world-profile-validation.json`. The experiment is rejected under
the playbook's minimum-gain rule; projectile caching was not implemented.
The full prototype is archived in `tmp/collision-filter-prototype/`, and its
flags, hooks, storage and source are removed from active builds.

One correctness fix is retained. Native `$3a74..$3a7c` leaves the final raw
active-list slot in A0; native overlap `$85f6` does not change it. The optimized
scan formerly returned the actor pointer, exposed by 504 mismatches in the
first 507-call comparison. It now returns the slot, and every SCAN_TWIN checks
A0 in addition to D0 and all owner-link writes. Post-removal diagnostic and
combat builds are byte-identical to the validated cache-off captures. The
normal build remains byte-identical to its retained baseline.

## Boss rendering bottleneck

The exact `sim60-boss-profile-a500` trace starts at tick 3500 with gameplay,
HUD and fresh projection identical to the untraced boss-exit run before its
jump activates. The 100-field window completes 113 simulation updates and
one presentation. Complete update calls average 67524.07 cycles (112 complete
calls); the complete render costs 2334618 cycles. The render spans 26 fields,
and update-start gaps reach 26 fields (endpoint bounds 0.417–0.450 seconds).
Other task/interrupt contexts consume about 16.1% of recorded field cycles.
This scene can catch up between pictures; the earlier 56.87 Hz interval alone
must not be interpreted as proof that its physics cost exceeds the field budget.
The heavier ordinary-combat update bottleneck remains separate.

The trace advances past the optional tick-3600 checkpoint. Its retained
`after-trace` snapshot is explicitly tick 3614, not 3600. Over 3500→3614,
114 updates take 101 fields (67.72 Hz), repaying thirteen pending updates
(139→126), with one presentation. The original checkpoint assertion failed;
the complete trace and correctly labeled post-trace boundary remain usable.
Reports are `latency-costs.json`, `latency.json`, `profile-details.json`,
`report.txt` and `frames.txt` in that capture. The normal build is restored.

One complete model draw at $13b96 costs 1168202 cycles, about 50.0% of the
measured render. The presentation routine at $1c84c costs 650192 cycles;
its graphics.library MrgCop wrapper at $250cc accounts for 538058 cycles,
about 23.0% of the render. These are substantial portions of this particular
render; the longer-run cache result below limits their overall benefit. The native display-list rebuild is gated by
data $2ee6; the setter at $1c9be marks both buffers dirty, including when
shake updates viewport offsets at $40d4/$40ec. Any caching or direct copper
update must preserve those changes, both buffer lists, palette/user-copper
content and native menu/transition behavior. No such optimization is enabled.

### Rejected copper merge cache

Content-checked MrgCop caching is not retained in active sources. Its complete
assembly source tree and counter reader are archived in ignored
`tmp/copper-cache-prototype/`. Normal builds never enabled it, and both normal
and non-VERIFY SIM60 binaries remain identical after removing its hooks.

The prototype compared full guarded inputs, reconstructed output in fresh
native-type allocations and relocated output pointers. Native replay twins
passed on both CPUs, both allocation-failure fallbacks preserved gameplay,
and corrupted output was rejected. Wide copying/comparison passed 496
length/alignment cases and 1440 unequal-buffer checks per CPU; the dropped-tail
control produced 80 errors. At tick 3848, the byte-cache live display matched
native output in all 16000 fetched bitplane words and effective palette/control
state, with stable output across 51/74 settled fields. Wide-helper replay twins
also matched native output; live display coverage applies to the byte-cache
version.

Wide operations reduced a measured hit from 272600 to 96430 cycles and miss
overhead from 267794 to 121576. These isolated savings did not translate into a
useful sustained improvement. In the paired A500 level-6 combat run from ticks
600–5400, native rendering takes 5036 fields and the cache 5030, with 45
presentations in both. Rates are 57.1882 versus 57.2565 updates/s: only 0.12%
improvement. Pending updates grow 24→260 versus 25→255. The cache handles only
eleven merge requests in that interval, of which five hit. The heavy
4500–5400 interval improves 57.63→58.89 updates/s but presents four versus
three times and still adds debt; this does not establish a sustained 60 Hz fix.

The delayed-68020 cache run averages 59.73 updates/s over 600–5400 and 60.27
in the heavy interval, with two hits among twenty merge requests. There is no
paired native 68020 run for a speed claim. All three configurations match
mapped gameplay/HUD/fresh projection at 600/1500/3000/4500/5400; deferred
scratch is reported separately. All six level-reset records and every installed
hook pass. Exact results are in `tmp/copper-long-validation.json`, with scoped
microbenchmarks in `tmp/copper-wide-profile-summary.json`, display evidence in
`tmp/copper-frame-validation.json`, and edge checks in
`tmp/copper-fast-validation.json` and `tmp/copper-wide-twin-validation.json`.
The remaining throughput work returns to the heavy simulation-update budget.

## Stationary star experiment

The content-checked stationary-star cache is not retained. It passes 240
ordinary-path star/fraction/RNG comparisons with 39 cache hits on both CPUs;
the broken fraction-key control produces eighteen star and eighteen fraction
errors. Paired and cross-CPU gameplay/HUD/fresh projection match at 4500/5400,
with six requested resets passing. Nevertheless, average update cost falls
only 3.40% on A500 and 2.43% on 68020, without establishing the playbook's
three-percent full-frame saving. The cache adds 652 bytes including its state.
The A500 900-tick interval improves 58.63→59.80 Hz but still adds three pending
updates. The delayed 68020 presents 27 times in either build. Retained source,
fixtures and checker are in ignored `tmp/stable-stars-prototype/`; exact-build
results remain in `tmp/stable-stars-validation.json`. Active sources retain
the preceding star update without this extra cache or its diagnostic hooks.

## Recenter loop

RECENTER_FAST now defaults on within SIM60. The pointer-walking equivalent of
the native recenter loop passes 128 native-reference cases on both CPUs;
deliberate actor corruption fails every case. It retains the native
secondary/reset tail and adds no persistent state or game patch site.
Gameplay/HUD/fresh projection matches at tick 150 and through heavy-combat
4500/5400 across CPUs and against the preceding build, with six resets and
all 87 installed hooks passing. Explicit-off SIM60 reproduces the preceding
release, and normal legacy builds remain unchanged.

Complete update cost improves 1.83% on A500 and 1.63% on delayed 68020. The
longer A500 comparison matches all five checkpoints at 600/1500/3000/4500/5400:
4800 updates take 4969→4944 fields (57.96→58.25 Hz), presentations rise 52→56,
and pending growth falls 169→144. Mean fields per presentation improves 7.61%
over this matched route, supporting retention of this simple loop despite the
modest update saving. It adds 156 allocated code bytes and 16 temporary stack
bytes. The gain does not establish sustained 60 Hz or acceptable maximum
presentation/input delay. Results: `tmp/recenter-{twin,long,build}-validation.json`
and `tmp/recenter-profile-{a500,020}-validation.json`.

A trace-based collision-order estimate finds no clear margin for testing X
before eligibility: the work added for currently excluded actors can offset
most of the removed checks. No such reorder is implemented; see
`tmp/collision-order-budget.json` for the planning estimate and its limits.

## Inline sort distances

SORT_INLINE_DISTANCE defaults on within SIM60's pointer-walk sorter. It uses
identical wrapped distance arithmetic directly in the already-saved sort
context, removing per-actor argument/call/register-save overhead. It adds 20
code bytes, no persistent state and no new game hook. Both CPUs pass all 64
native-order cases and 214 comparisons through tick 150; the corrupted-key
control reaches the mismatch handler in the first 16-actor fixture case.
Gameplay/HUD/fresh projection matches the preceding build and across CPUs at
150/4500/5400, with only deferred projection scratch differing. All six resets
and 87 installed hooks pass.

Complete update means fall 96608.98→94246.69 cycles on A500 (2.45%) and
50676.35→49310.33 on delayed 68020 (2.70%). The long A500 route matches all five
checkpoints: 4800 updates take 4944→4933 fields (58.25→58.38 Hz), presentations
rise 56→62, and pending growth falls 144→133. This is retained as removal of
call overhead with no extra runtime guard/cache; it does not claim a three-percent
full-frame saving or solve the sustained-rate/presentation-delay problem.
Results: `tmp/sort-inline-{twin,long,negative,cross}-validation.json` and
`tmp/sort-inline-profile-{a500,020}-validation.json`. Explicit-off reproduces
the preceding release; the diagnostic corruption is absent without VERIFY.
The default release equals the tested candidate, and normal legacy builds are
byte-identical and restored. Disabled-mode original-code preservation checks
pass on both CPUs (151969 bytes, zero unexpected changes); see
`tmp/sort-inline-build-validation.json` and
`tmp/disabled-sort-inline-validation.json`.

## Extended heavy-combat route

The current default now matches across A500 and delayed 68020 at
600/1500/3000/4500/5400/7200/9000 and the native death at 9212. Energy is 320
at 5400, 80 at 7200, zero while still active at 9000, then −80 with active
cleared and death set at 9212. The requested tick 10800 is not reached; its
capture directory retains an explicit early-stop record and actual tick 9212.
All six requested level transitions and 87 installed hooks pass. The repeated
A500 snapshots and clock state through 5400 are identical to the shorter run.
Level selection is the existing six-transition fixture; subsequent approach
uses only input, without injected damage, health or death.

Over 8612 updates, A500 takes 8671 fields (59.5917 Hz), presents 98 times and
grows pending updates 23→82. Delayed 68020 takes 8597 fields (60.1047 Hz),
presents 270 times and reduces pending updates 25→10. The extension after
5400 recovers 74 A500 ticks and ten 68020 ticks. These averages do not establish
maximum presentation/input latency or remove the earlier heavy-scene deficit.
Results: `tmp/sort-inline-extended-validation.json`; exact builds and captures
are `sort-inline-extended-{a500,slow-020}`. Separate hundred-field traces at
anchor 9200 now verify the native death path on both CPUs: negative energy,
active clear, death flag, completed tick 9212, simulation exit, input restore,
native cleanup and native death entry, with no subsequent simulation update
or render in the observed trace. Gameplay/HUD/fresh projection also matches at
9200; six resets and 87 hooks pass. Tick 9212 is established from guarded
recorded tick loads, not by adding trace entry counts to the earlier snapshot:
field recording can omit the start of the first update. Results are in
`tmp/sort-inline-death-validation.json`; the normal build is restored byte for
byte. Continue answers/retry on this level-6 route remain outside this check.

## Early-combat profile before shared AI setup

The preceding default at tick 1800 completes 91 updates and one presentation in
100 NTSC fields (54.60 updates/s over that short window). Ninety complete update
calls average 95212.49 cycles. Across completed ticks 1800–2400, it executes
600 updates in 570 fields (63.16 updates/s), presents five times and reduces
pending updates 102→72. The short window includes a long presentation; the
longer window pays down existing debt. Neither establishes sustained 60 Hz or
acceptable maximum input latency. Gameplay/HUD/fresh projection matches the
retained straight-motion build at both endpoints, allowing only projection
scratch; all six transitions and 87 installed hooks pass. The normal build is
restored. Exact evidence: `sim60-current-heavy-a500` and
`tmp/current-heavy-validation.json`.

The one fully observed render costs 1033644 main-context cycles and spans
13 fields. The largest complete update-start gap is 14 fields, giving endpoint
bounds 0.217–0.250 seconds. Three complete native model draws total 482136
cycles (46.6% of render cost); the presentation helper costs 1692 cycles and
no copper merge occurs. Copper caching cannot help this observed frame.
`tmp/current-render-cost.json` retains exact-build latency and complete-call
measurements. One presentation cannot establish a complete presentation
interval, a game-wide maximum delay or an achievable rendering speedup.

Complete-call means are 1937.14 cycles for movement, 1934.72 for world scans,
1997.96 for projectile scans, 520.46 for heading, 3932.88 for sorting and
4484.44 for stars. These inclusive costs overlap and cannot be summed.
Straight-motion cache capacity is not the bottleneck in either current trace:
all 364 eligible early-combat calls and all 528 later-combat calls hit.
Cold-cache models with 16/32/64/128 slots have identical miss counts (four
early, five later); increasing capacity is not justified here. Guarded audits
are `tmp/current-heavy-a500-linear-cache-audit.json` and
`tmp/sort-inline-late-a500-linear-cache-audit.json`. Other scenes may differ.

## Completion review

The requested conversion has three distinct requirements. The release is
playable through `amiga/play60.sh`, but the overall goal remains open.

| Requirement | Current evidence | Remaining uncertainty |
|---|---|---|
| Gameplay advances in 1/60-second steps | `s60_clock` accumulates elapsed fields ×60 and the loop consumes the observed 50/60 field rate per update. Motion retains signed integer remainders; clocks for contact, animation, weapons and powers have separate phases. | Full encounter behavior on remaining boss/contact/power paths. |
| Drawing frequency does not determine gameplay progression | Separate update/draw routines; draw restores gameplay RNG, clock debt survives rendering, and matched-tick gameplay/HUD/fresh projection agrees through encounters, deaths and retries across differing CPUs and draw delays. The current extended encounter has eight matching checkpoints through tick 9212. | Remaining scratch consumers and unexecuted rendering paths; release gameplay with real controls has not yet been observed. |
| Reference gameplay pace is preserved | Twelve substeps reproduce the early measured native cadence of five updates/second; timed powers, cooldowns and continuous trajectories have dedicated checks. | Original native cadence also drops to 3.3–4 updates/second under heavier rendering. The current conversion intentionally removes those slowdowns; intended nominal pace still needs confirmation/playtesting. |

The non-fixture release reaches its native menu with normal input ports enabled.
Interactive control verification is still open: the available UI automation did
not expose the emulator window, and the read-only macOS window probe did not
return. That probe and this project's emulator were stopped. This is a test
access limitation, not evidence of a game failure.

Stock-A500 sustained realtime throughput is a separate unresolved hardware
acceptance question. Current heavy-combat throughput is 59.11 updates/s with
backlog growth; this is not evidence that the fixed-step conversion is missing,
but it prevents a claim that all heavy scenes sustain realtime. Keep the
measured limit visible rather than equating a 60 Hz timestep with guaranteed
60 updates per wall-clock second on overloaded hardware.

The geometry-era sort audit finds 258 of 271 sampled eleven-actor lists already
positive/nonincreasing and handled by the existing fast path. No sampled list
has an ordered positive prefix followed by a nonpositive suffix. An additional
shortcut for that suffix would not help these windows. Exact key lists and
installed-build checks: `tmp/geometry-sort-opportunities.json`. Remaining native
movement inputs are also unique in all three windows (93/87/91 complete calls),
so another last-input movement cache has no observed hits
(`tmp/geometry-motion-inputs.log`). These are opportunity audits, not speedups.

`INPUT_QUANTA_UNROLL=1` now defaults on within SIM60 and replaces the per-tick
sixteen-entry input-constant table walk with direct stores generated from the
same list as guard and restore code. It retains cache flushing and adds no
native hooks. With `SCAN_GEOMETRY_FIRST=0`, setting it to zero reproduces
the input-fixed release used for its paired measurements.

Both CPUs pass QI60's twelve full 558-byte input-region comparisons against the
preceding updater and all 180 native neutral-braking cases. Restoring native
constants before candidate calls catches missing stores. The deliberately
corrupted immediate fails all twelve phases at the expected byte offset.
Gameplay/HUD/fresh projection and private clocks match baseline/candidate and
across CPUs at ticks 1800/2400, allowing only deferred projection scratch.
All six level resets and 89 installed hooks pass.

Complete-call cost drops 2394.60→1162.06 cycles on A500 (51.47%) and
1253.59→571.21 on delayed 68020 (54.43%). Whole-update means drop
93682.68→92452.15 and 49419.21→48768.58 cycles, both about 1.3%.
The A500 600-tick interval has six presentations instead of five and lower
pending counts, but both intervals repay backlog; they are not sustained-rate
measurements. The delayed-68020 interval has nineteen presentations in both.
Reports: `tmp/quanta-fixture-validation.json`, `tmp/quanta-perf-validation.json`,
`tmp/quanta-unroll-store-audit.json`. Candidate traces audit 6305 executed
indirect calls/jumps without a patch-interior target; baseline traces add 5996.
The current playable release includes the subsequent collision-order change.
It passes static release checks, diagnostic exclusion, disabled-mode checks
with zero unexpected native-code changes, and native-menu startup with all 89
hooks and no menu fixtures. The menu was visually inspected; real controls and
audio remain unverified. `SCAN_GEOMETRY_FIRST=0` reproduces the preceding
unrolled-input release byte for byte (`tmp/scan-order-default-validation.json`,
`tmp/disabled-scan-order-validation.json`,
`tmp/prof/play60-scan-order-smoke/validation.json`).

## Active input timing correction

The neutral directional-input path (native joystick fallback disabled, no
direction held) contains a second
80-unit turn-braking branch. Its MOVEQ constants at $1004e/$1006a/$10072 were
missing from `s60_input_sites`; they therefore ran at full native magnitude on
every 60 Hz tick. The table now includes all three with the existing 80/12
phase schedule. Native-fragment checks pass 180 cases on A500 and 68020 (fifteen
signed velocities × twelve starting phases). The old-code negative control
fails 60 cases as expected, including 81→0 instead of native 81→1 over twelve
substeps. Gameplay/HUD/fresh projection matches between the two good captures,
allowing only projection scratch; all 88 hooks pass and the normal build is
restored (`tmp/input-neutral-validation.json`). The native Preferences and
direction-release encounter now also passes A500 and delayed 68020. Joystick
(preference 2) is disabled through the native menu; data $293e remains zero at
all eight checkpoints. Turn speed falls 512→506→472→466→432→6→0→0 at completed
ticks 420/421/426/427/432/496/497/498. Mapped gameplay/HUD/fresh projection
matches across CPUs, allowing only projection scratch. The old-code control
matches before release and brakes to zero at tick 427 instead of 497, so it is
rejected. All 88 installed hooks pass and the normal build is restored
(`tmp/input-neutral-release-validation.json`).

The initial route toggled Mouse (preference 1), leaving the native joystick
fallback enabled; its immediate zero velocity did not exercise neutral braking.
Those captures remain under `sim60-input-neutral-play-*`. The first corrected
68020 startup was manually interrupted during slow memory detection; no game
failure was established. The fresh retry completes successfully. Static input
hooks remain a deferred optimization, separate from this correctness fix.

A second input dependency is confirmed in retained contact snapshots: type-46
contact sets data $46d8 at $36e6; native input $100a8–$100d2 quarters turn/forward
velocities while that flag is set. Forward speed falls 24→6→1→0 at consecutive
contact ticks 3604–3607. Current terrain timing gates the level-5 energy decrement
at $36f8, not this separate damping path. The retained evidence is in
`tmp/terrain-friction-pre-fix-evidence.json`. Direct input-entry/return observation
is prepared to distinguish damping from other changes during each update.

Terrain damping now has its own immediate-first, twelve-tick clock, independent
of level-five damage. Both CPUs pass all 2592 native-fragment observations;
the old-timing control fails 2064. Full ABI-29 timing state, gameplay/HUD/fresh
projection matches across CPUs after the fixture, and all 89 hooks pass
(`tmp/terrain-friction-validation.json`).

A real type-46 contact encounter now confirms damping at input ticks
3605/3617/3629 on A500 and delayed 68020. Twenty-four intervening contact calls
leave nontrivial velocities unchanged. Complete player bytes match the expected
native arithmetic at every input entry/return; gameplay/HUD/fresh projection and
all private clocks match at all 59 cross-CPU observations, allowing only deferred
projection scratch. Five level resets and 89 hooks pass. This uses the explicit
boss-state setup, not an unforced boss decision. Reports:
`tmp/terrain-friction-contact-validation.json` and
`tmp/terrain-friction-negative-validation.json`. Omitted damping, a lost clock
and an unknown state ABI are rejected. The state reader now rejects unsupported
SIM60 ABI versions instead of silently omitting timing state.

The release passes static hook checks and is byte-identical with diagnostic
flags supplied without VERIFY. The separate playable SIM60 artifact is rebuilt
with both input fixes and matches that release; the normal build is unchanged
(`tmp/scan-order-default-validation.json`). Current-build throughput is measured by the extended run summarized above.
The current SIM60 build with CUSTOM1 off also passes original-code preservation
on A500 and 68020: 151969 bytes, 4833 relocated longs and all 89 compiled patch
ranges checked, with zero unexpected changes. Native mutable code-data objects
and exact menu-fixture patches are reported separately; the normal build is
restored (`tmp/disabled-scan-order-validation.json`).
The actual playable launcher also boots the exact current release to its native
menu, with all 89 hooks installed and all three menu-fixture locations unchanged.
The captured menu was visually checked. This silent, disconnected-input smoke
test verifies release startup, not interactive controls or audio
(`tmp/prof/play60-scan-order-smoke/validation.json`).
Interactive controls, broader encounters and the remaining release audits are
still open.

## Checkpoint verification

All 15 Python unit tests pass, all Python tools parse, shell syntax and
`git diff --check` pass. The normal and SIM60 builds match their validated
reference bytes after the diagnostic runs. The SIM60 SHA-256 is
`c2a1d0ad93a0f3255155a14950fb2b74a7cced43a52fb8cefca94dbf54a82628`.
The in-flight emulator measurements completed and the harness exited.
No new implementation work should run until the user resumes it.

## Remaining work

The star-coordinate bounds candidate was not adopted. Exhaustive checks cover
all 65536 word values on each axis, but the retained A500 profile improves
mean update instruction cost only 90004.42→89719.25 cycles (0.32%); delayed
68020 improves 0.014%. Both completed-tick state comparisons and all 89
installed hooks pass (`tmp/star-bounds-profile-validation.json`).
Candidate sources, captures and reports remain in ignored `tmp/star-bounds*`;
active source and the playable default retain the preceding bounds checks.

Priority correctness gap: preserve the input belonging to each overdue tick.
The exact playable release still calls native input from every catch-up update;
the joystick path reads live hardware at code $22750–$22756 and current key
state through $22730. Tick-indexed VERIFY fixtures hide this timing difference.
The loaded-code/source audit is `tmp/live-input-timing-audit.json`; it is not
yet a field-driven runtime reproduction. First reproduce a fixed elapsed-field
input edge with differing draw costs, then add clock-indexed input capture and
consumption. Preserve native modal ownership, key queues, mouse deltas and
mode switches; define/test overflow, pause/reset and PAL-to-60-Hz mapping.
This follows AmigaXDev `docs/playbooks/fixed-time-simulation.md`. Physical
host UI access is not needed for the scripted reproduction.

1. Continue reducing simulation and presentation cost. The validated collision
   ordering now defaults on within SIM60.
   `SCAN_GEOMETRY_FIRST=1` moves the signed X-distance rejection before actor
   flag/type classification in both actor and projectile scans. It preserves
   query-type rejection, list order, wrapped arithmetic, link writes and first/
   last-hit behavior. Setting it to zero reproduces the preceding release
   bytes exactly.
   Both CPUs pass 23591 live native scan comparisons through tick 2400,
   plus 68 synthetic scan cases and 64 projectile cases. Gameplay/HUD/fresh
   projection and private timing state match the preceding build and across
   CPUs at 1800/2400, allowing only deferred projection scratch. All 89 hooks
   pass. Reports: `tmp/scan-order-twin-validation.json` and
   `tmp/scan-order-boundary-validation.json`.
   Separate paired profiles without twin overhead reduce complete-call mean
   update cost 92303.10→90004.42 cycles on A500 (2.49%) and
   48635.96→47507.87 on delayed 68020 (2.32%). Actor scan means improve
   9.16%/8.14%, projectile scan means 12.77%/12.75%. All four benchmark
   captures match gameplay at both checkpoints and pass installed-hook checks;
   the normal build is restored (`tmp/scan-order-profile-validation.json`).
   The extended route passes through tick 9212 on both CPUs, with the current
   rates summarized above (`tmp/scan-order-extended-validation.json`). These
   results still leave heavy A500 backlog growth. Static release checks cover
   89 hooks/69 merged ranges with no direct interior entry; 6236 observed
   indirect calls/jumps also avoid patch interiors
   (`tmp/scan-order-release-hook-audit.json`,
   `tmp/scan-order-indirect-validation.json`).
   Default adoption also passes disabled-mode preservation on both CPUs
   (151969 native bytes, 4833 relocated longs, all 89 patch ranges, zero
   unexpected changes), diagnostic exclusion, opt-out release identity and
   actual native-menu launcher checks. See `tmp/scan-order-default-validation.json`,
   `tmp/disabled-scan-order-validation.json` and
   `tmp/prof/play60-scan-order-smoke/validation.json`.

   Combining the adjacent excluded-state comparisons into a byte-range test
   is not adopted: measured complete-update instruction savings are only
   0.129% on A500 and 0.065% on delayed 68020. Both native byte-domain suites
   and tick-1800/2400 mapped-state comparisons pass, but the change is too small
   to address backlog. Retained reports: `tmp/scan-range-boundary-validation.json`
   and `tmp/scan-range-profile-validation.json`. The optional 256-value fixture
   extensions remain available; active gameplay code and release bytes are unchanged.

   Fix sustained 68000 throughput and presentation speed with the current
   default PROJECT_SKIP, SORT_ORDERED, SCAN_HOIST, MOVE_WORD_MUL, RECORD_CACHE and
   HEADING_FAST and SHOT_FAST paths. Native-reference validation is complete for these guarded
   optimizations and replacement-only state matches the preceding route.
   Before MOVE_ZERO, the level-0 build averages 94297.69 cycles per later-scene update,
   below the raw 119665-cycle field budget but leaving too little time for
   interrupts and rendering. Tick intervals 1500–2400/2400–3600 average
   59.60/61.86 updates/s, with the latter paying backlog; pending ticks are
   97/103/67. Six/thirteen presentations occur (about 0.40/0.67 per second).
   The level-1 MOVE_ZERO measurement now averages 92420.93 cycles per A500
   update (4.57% lower), with 15 versus 13 presentations over 2100 ticks.
   Movement remains a major target after the zero-speed and word-product improvements;
   the record cache, heading and projectile-scan replacements reduce repeated
   arithmetic, but
   remaining wrapper work and other simulation costs need further reduction.
   A fresh consumer audit makes per-actor heading eligibility a candidate for
   further investigation, not an approved optimization. Of 1064/1100 geometry
   calls in A500/delayed-68020 combat traces, 968/1001 occur between global AI
   decision ticks. Native heading consumers $f582 and $f26c still execute on
   those ticks (eight reads each per CPU), and distance consumer $f5cc also
   executes eight times. Independent callback phases must therefore be respected;
   simply gating geometry on s60_logic would use stale inputs. Direct candidate
   sites and observed counts are retained in `tmp/heading-consumer-audit.json`.
   This does not cover indirect/aliased reads, unseen paths or full field lifetimes.
   The expanded explicit-operand lifetime audit finds 1030/1065 unread values
   among 1053/1089 complete heading lifetimes on A500/delayed 68020. It also
   covers indirect/indexed aliases and block spans; no unsupported explicit
   native/slave operand occurs in these windows. Synthetic indirect reads make
   every completed lifetime read, and missing producers expose uncovered reads
   (`tmp/heading-lifetime-validation.json`). Eleven lifetimes per CPU are partial.
   The external-code extension decodes 70194/174166 further instructions in
   the current A500/68020 windows without finding another heading reader.
   Earlier late-combat and boss traces add 946/770 complete lifetimes, with
   930/653 unread. The boss trace crosses three unlink events and two later
   geometry reuses; its VERIFY pilot reads prior headings 113 times, and native
   consumers $10c00/$114a0 also execute. The pilot is diagnostic behavior but
   illustrates why recomputing from newer coordinates is not equivalent to
   retaining the value from the earlier geometry epoch. Full allocation/reuse,
   implicit stack accesses and unseen paths remain unproven. Results:
   `tmp/heading-lifetime-expanded-validation.json`. Audit those obligations
   before attempting per-actor lazy computation; current gameplay fields
   continue updating every tick. Fractional-division shortcuts
   remain smaller candidates: even eliminating all divisions with magnitude
   below 24 has a 1.891% A500 recorded-cycle upper bound before overhead
   (`tmp/current-arithmetic-budget.json`).

   The enemy geometry block ($ee44–$ee8c) now shares distance/heading setup
   without caching or changing decisions. Its baseline measurements follow.
   Across 1008 early-heavy and 1155 late A500 blocks, inclusive means are
   1111.88/1113.59 cycles. Instructions in the native setup block itself use
   282100/324098 cycles (2.36%/2.71% of all recorded cycles); this includes
   necessary work and is not an achievable saving estimate. The delayed 68020
   mean is 514.75 cycles over 1001 blocks, with setup using 0.58% of recorded
   cycles. Calls interrupted at the trace end are excluded. Guarded report:
   `tmp/ai-geometry-setup-cost.json`. AI_GEOMETRY_FUSED now defaults on within
   experimental SIM60 after native-reference and encounter checks. It shares current coordinate deltas,
   retains the existing heading routine and resumes at the native callback
   logic. GEOMETRY_TWIN compares fifteen registers, CCR and the two actor
   outputs against the original setup sequence on each observed call.
   Normal-68020 combat passes 29016 comparisons through tick 2400, with
   gameplay/HUD/fresh projection matching the baseline at 1800/2400, allowing
   only projection scratch. Six resets and 88 installed hooks pass
   (`tmp/geometry-twin-020-validation.json`). Default release bytes are unchanged.
   Both A500 and 68020 pass all 128 synthetic coordinate cases plus live
   calls (842 comparisons each); the deliberate corruption produces 842/842
   mismatches. Boundary-run gameplay/HUD/fresh projection also matches across
   CPUs, allowing only projection scratch, with 88 installed hooks verified.
   The release audit passes 88 patches/68 merged ranges with no conservative
   direct interior entry. Diagnostic flags are byte-excluded without VERIFY.
   Reports: `tmp/geometry-boundary-validation.json`,
   `tmp/geometry-build-validation.json`, `tmp/geometry-release-hook-audit.json`.
   The replacement-only early A500 window matches gameplay/HUD/fresh projection
   at 1800/2400 and reduces sampled mean update cost 95212.49→93032.24 cycles
   (2.29%). Over those 600 ticks, fields change 570→573, presentations 5→6,
   and pending debt 102→72 versus 97→70. Both windows repay debt; this is not
   sustained-60-Hz evidence. The geometry helper averages 871.25 cycles before
   its hook/continuation overhead. Report: `tmp/geometry-early-a500-validation.json`.
   Late A500 sampled update means fall 94246.69→92036.74 cycles (2.34%);
   delayed 68020 falls 49310.33→48634.60 (1.37%). Both match gameplay/HUD/fresh
   projection at 4500/5400, allowing only deferred projection scratch, with
   six resets and 88 hooks verified. A500 takes 855 versus 876 fields for
   900 ticks, with five presentations each and pending debt 163→118 versus
   180→156. Delayed 68020 takes 901 versus 899 fields, with 28 presentations
   each. Reports: `tmp/geometry-late-a500-validation.json` and
   `tmp/geometry-late-020-validation.json`. The longer encounter now matches
   across both configurations and against the preceding build at all eight
   checkpoints through native death at 9212, with six resets and 88 hooks
   passing. A500 heavy 600–5400 improves 58.38→58.87 updates/s and 62→66
   presentations; full 600–9212 improves 59.59→59.65 and 98→109 presentations.
   Delayed 68020 averages 60.07 with 271 presentations and debt 25→15.
   See `tmp/geometry-extended-validation.json`. The optimization defaults on
   within SIM60, with default release bytes matching the audited explicit
   candidate. With CUSTOM1 off, both CPUs preserve 151969 checked original-code
   bytes, including all 88 compiled simulation patch ranges; zero unexpected
   changes occur. The normal build is restored byte for byte. See
   `tmp/disabled-geometry-validation.json`. The whole conversion remains
   experimental and heavy A500 backlog remains.
   A retained-trace audit rules out a small-numerator DIVS shortcut (under 0.4%
   even before guard overhead). Reprofile the current default before selecting
   further changes; preserve all fractional state and caller-visible results.
   The current SORT_INLINE_DISTANCE tick-4500 traces rule out expanding heading
   fallback coverage as a useful target for this window: all 1155 A500 and
   1001 delayed-68020 calls take the existing fast path. Its DIVU instructions
   account for 1.25% and 0.15% of total recorded cycles respectively, even
   before any replacement overhead. Exact input repetition occurs in 520/1155
   and 450/1001 calls across the entire window, but this is not a cache-hit or
   achievable-speedup measurement. No new heading cache is justified by those
   counts. The guarded audit is `tmp/current-heading-audit.json`; prioritize
   collision/movement costs over additional heading fallback machinery.
   A guarded rotation-loop audit also rejects an additional all-zero shortcut
   for this window. Only 105/317 A500 and 92/276 delayed-68020 complete
   rotation groups have zero velocities and zero remainders. Their entire
   loop costs total 27812/14955 cycles, only 0.23%/0.06% of recorded cycles
   before any new guard or branch overhead (`tmp/rotation-budget.json`).
   Existing idle and straight-motion paths already bypass much of this work;
   do not add another zero-rotation guard based on this sample.
   The route now matches through tick 10800, averaging near sixty over its
   last 7200 ticks even with delayed rendering on the same A500. Extend coverage
   into heavier encounters and other levels; checkpoint debt is not a bound
   on maximum presentation/input delay.
   Recentering $3ab8 changes world coordinates and must remain per-tick physics.
   Collision-list scanning is reduced with SCAN_HOIST. The profiler fixes
   native-continuation attribution and calls lost at interrupted entries; use
   complete-call costs rather than approximate self ranges for decisions.
   Preserve exact accumulated time/state,
   and repeat longer/heavier routes on both CPUs and differing render costs.
   Projection now averages 12879 cycles per update. The native-reference tests
   cover its omission guards, but full gameplay encounters remain necessary.
   A movement-input audit rules out a general displacement cache in the earlier
   route: only cheap stationary inputs repeat. Verify acceptable presentation
   intervals as well as sustained simulation rate; do not discard simulation debt.
2. The shortened-wave boss fixture now reaches native carrier/boss creation
   and lethal combat. A500 and delayed 68020 mapped gameplay, HUD and fresh
   projection match at ticks 60/600/1800/3600 and native death at 4474. Both
   have energy -48 at death; only deferred shared projection scratch differs.
   All 87 installed simulation patches pass exact-build checks. Captures are
   `sim60-boss-cross-{a500,slow-020}`; the requested checkpoint-7200 folders
   explicitly retain the early death at tick 4474, not a reached tick 7200.
   Over 1800–3600, A500 averages 56.87 updates/s with 30 presentations and
   debt 33→132; delayed 68020 averages 59.80 with 48 presentations and debt
   22→28. This route establishes consistent boss contact/death behavior,
   not a boss kill or level exit. Results: `tmp/boss-cross-validation.json`.
   With the existing native jump activation diagnostic at tick 3500, the
   shortened-wave route kills the boss, scores 1000 and exits level 0 at tick
   4264. A500 and delayed 68020 gameplay/HUD/fresh projection match at
   3500/3600/3800/4100/4264 and session-2 ticks 600/1500. The passive transition
   observer reports one ordinary level increment, zero errors, zeroed private
   simulation state and initial credit 60 on both CPUs. All 87 installed
   patches pass. Captures `sim60-boss-exit-{a500,slow-020}` and
   `tmp/boss-exit-cross-validation.json` establish this first boss/exit route;
   jump acquisition/selection is bypassed and the opening wave is shortened.
   Read-only native breakpoints additionally confirm a player-owned elevated
   shot at tick 3831 (boss health 9→0, score 0→1000) and type-25 collision at
   tick 4263 clearing active without death; see `sim60-boss-native-hit`.
   The selected-level BE62 fixture now reaches level 6 after six separately
   checked injected exits, which stop before that encounter. It clears six
   initial enemies (native wave progress 6→25) through native damage and then
   leaves boss creation/combat native. The stationary firing route dies at
   tick 3274 (`sim60-ending-encounter-pilot`). An input-only
   APPROACH_STANDOFF=12000 route backs away from the carrier and maintains
   range while firing; it survives through 7200 with energy 472 and boss
   health 38. No health or damage override is used in that route.
   Normal 68020, A500 and delayed 68020 gameplay/HUD/fresh projection match at
   600/1800/3600/6000/7200. All six resets and 87 installed patches pass on the
   paired captures `sim60-ending-boss-cross-{a500,slow-020}`. Over 600–7200,
   A500 averages 59.79 Hz with 149 presentations and debt 13→36 (peaking at
   235 at tick 3600); delayed 68020 averages 59.92 Hz with 207 presentations
   and debt 7→16. This validates a sustained final-boss fight, not its death
   or the ending. Results: `tmp/ending-boss-cross-validation.json`.
   The unchanged normal-68020 route extends to tick 10800 (energy 264,
   boss health 33) and dies at 12838 with boss health 32; no ending is reached.
   `sim60-ending-standoff-long/validation.json` retains that result and an
   exact tick-7200 match to the earlier pilot. The checkpoint-14400 directory
   is explicitly an early death at 12838. A separate BOSS_FINISH_TEST=7200
   diagnostic sets a surviving final boss to one health, leaving projectile
   damage and ending triggers native. Its BE63 record makes that setup explicit;
   this focused ending check passes as described below and does not replace
   full-strength encounter evidence. The initial observer waited at ordinary-enemy damage
   $32ba, which class-5 bosses bypass through $41ba. It was interrupted and
   retained without claiming an ending result. The corrected observer uses
   the native final-boss damage call at $11202, with A3 as the boss and A2
   as the projectile. Its pre-setup tick-7200 gameplay/HUD/fresh projection
   matches the full-strength pilot; only deferred projection scratch differs.
   The corrected normal-68020 capture now passes the focused ending check.
   BE63 records boss health 38→1 at tick 7200; a native player-owned type-23
   projectile deals one damage at tick 8009. Native boss death clears active
   without death, update 8010 completes, and native ending sequence 6 enters
   at level 7 with victory set. Simulation running is zero and update/render
   counts stay frozen through sequence return. Native world reset reasserts
   the scene-active byte before the ending; that byte alone cannot indicate
   a running simulation. `sim60-ending-finish-corrected/validation.json`
   is checked directly from snapshots by `tools/ending_state.py`. The VERIFY
   input fixture may skip sequence visuals; this proves lifecycle entry/return,
   not all ending frames. A500 and delayed-68020 repetitions also pass at
   hit tick 8009 and completed tick 8010. Gameplay/HUD/fresh projection matches
   at 7200, before the hit, before active clear and the completed exit; only
   deferred projection scratch differs. All six reset records and all 87
   installed patches pass. Presentation counts at ending entry are 1129/220/256
   for normal 68020/A500/delayed 68020, while each retains frozen counters
   through return. Results: `tmp/ending-finish-cross-validation.json`.
   Extend natural boss/collision exit validation to later levels.
   Requested transitions through level index 6 also pass all six reset checks
   across three configurations, with matching gameplay and projection at ticks
   600/1500/3600; those injected exits do not prove later natural triggers.
   Validate visible damage shake. The level-5 terrain path now passes a controlled
   encounter on A500, normal 68020 and delayed 68020. BE64 explicitly selects
   the existing boss's state 0→1 at tick 3600; native allocation creates type 46
   at 3603. Twenty-five consecutive native contacts at 3604–3628 deal exactly
   one damage at 3604/3616/3628, preserving immediate first contact and the
   independent twelve-tick clock. Gameplay/HUD/fresh projection matches at all
   53 before/after checkpoints; only deferred projection scratch differs.
   Five reset records and all installed hooks pass. The raw-snapshot checker
   rejects omitted damage and a no-contact encounter. Results are retained in
   `tmp/terrain-contact-cross-validation.json` and
   `tmp/terrain-contact-negative-validation.json`.
   This validates allocation/contact after an explicit state selection, not the
   boss's random decision to enter that state. Unforced routes die at 9161
   (stationary wait) and 8433 (moving wait). Read-only breakpoints confirm no
   terrain-allocation call or terrain contact before the moving route's death;
   its state matches the observer-free run exactly. Broader unforced boss
   behavior remains outside this check.
   Generic AI dispatch now passes ordered twelve-tick gate checks in retained
   normal/delayed-render captures for $eec4, level-1 type-8 $f136 calls
   and level-5 type-9 decisions.
   One real type-8 projectile creation passes native owner/return checks on
   both CPUs with matching gameplay through tick 4200. Keep the shared decision
   phase; type-10 state-0 decisions now pass on both CPUs in the standard route.
   An input-only approach reaches state 3 and three owned projectiles with
   matching gameplay/projection across normal A500, normal 68020 and delayed
   68020 at 1200/1800/2400. Both traced runs verify one successful type-10
   spawn via $f86e. Read-only native-return observers now cover ten successful
   type-10 shots through all three sites ($f86e/$f8e4/$f912, counts 5/3/2)
   through tick 5400 on all three configurations. All 22 gameplay/HUD/fresh
   projection snapshots match, with only deferred projection scratch differing;
   six resets and 87 hooks pass. Observer-free A500 endpoints also match.
   The checker verifies ownership, full actor/projectile consequences and the
   decision gate, and rejects corrupted owner, yaw, counter, gate and missing
   branch coverage. See `tmp/type10-native-cross-validation.json` and
   `tmp/type10-native-negative-validation.json`. Level selection uses six
   requested transitions; subsequent firing uses only the input fixture.
   Extend coverage to failed allocations and the nonpositive-yaw
   alternative at $f912. This does not establish full native-trajectory equivalence.
   The type-9 input-only approach route passes normal 68020, A500 and
   delayed 68020: native successful shots at ticks 2052/3396 exercise channels
   1/0. Type-22 projectile ownership, horizontal position/yaw, native +225
   launch height, lifetime 500, cooldown 28 and channel lifetime 84 pass,
   including remaining-channel decrements. All six gameplay/HUD/fresh-projection
   checkpoints match through tick 3600, allowing only deferred projection
   scratch. All five level-reset records and 87 installed hooks pass on each
   configuration; the normal build is restored. Four corrupt-copy controls
   reject owner, lifetime, channel-loop and decision-cadence errors. Reports:
   `tmp/type9-native-cross-validation.json` and
   `tmp/type9-native-negative-validation.json`. Failed allocation and firing
   variant 5 remain outside this encounter. The observer-free normal-68020
   initial snapshot at tick 1800 also matches.
   Type-7 coupled curved exits and positive speed-word overflow now pass the
   independent BP60 rational trajectory model at every tick on all three axes,
   as well as callback and rollback/replay checks. These eight fixed-state
   sequences validate the specified interpolation, not equality to coarse
   native curved positions or full encounter state transitions. Broaden the
   original-reference pace comparison and extend encounter coverage below.
   Validate full boss encounters, creation/removal and temporary collision-query
   paths alongside the integrated banking/height/sideways/pitch motion;
   extend pickup coverage to natural spawning and further power selections. A PE61
   controlled scene now passes real type-31 contact acquisition at tick 837,
   thirty native events at twelve-tick intervals, healing, inventory 1→3,
   actor unlinking and fractional-state cleanup on normal 68020, A500 and
   delayed 68020. All 65 gameplay/HUD/fresh-projection checkpoints match,
   allowing only deferred projection scratch, and all 87 hooks pass.
   Eight corrupted captures are rejected. Results:
   `tmp/pickup-encounter-cross-validation.json` and
   `tmp/pickup-encounter-negative-validation.json`. Allocation, placement,
   initial energy and inventory are explicitly controlled; selection remains
   unchanged. A500 and normal 68020 repetitions without native-event
   breakpoints match all mapped state exactly at completed ticks
   200/201/1198/1318, including projection scratch, with all 87 hooks passing
   (`tmp/pickup-plain-validation.json`). This establishes endpoint equivalence
   without the event observer; audible output remains unverified.
   An input-only PICKUP_USE sequence now selects index zero through native
   second-button release and activates it with both buttons. Three charges
   become native byte -2 (two left, active), and the 900-unit timer decrements
   every twelve ticks. All ten completed checkpoints through 1500 match across
   normal 68020, A500 and delayed 68020, allowing only projection scratch;
   all 87 hooks pass, four corrupt-copy controls fail as expected, and release
   bytes exclude the diagnostic. Results: `tmp/pickup-use-cross-validation.json`
   and `tmp/pickup-use-negative-validation.json`. The extension through tick
   2000 now verifies delayed native clone activation at completed tick 1882
   (480 ticks after use): timer 860, active word 1 and mesh pointer switch
   $4498→$4598. All fourteen checkpoints match across all three configurations,
   allowing only deferred projection scratch; all 87 hooks pass and four
   corrupt-copy controls fail as expected. See
   `tmp/pickup-clone-cross-validation.json` and
   `tmp/pickup-clone-negative-validation.json`. Other selections, cycling
   while active, depletion and visible animation remain outside
   this encounter check.
   The expiry extension passes normal 68020, A500 and delayed 68020 at all
   seven completed checkpoints 2000/3000/6000/9000/12201/12202/12203, allowing
   only deferred projection scratch. Native expiry occurs at tick 12202,
   10800 ticks after activation: timer 1→0, clone flag 1→0, mesh $4598→$4498
   and inventory -2→2; selection remains zero. All 87 installed hooks pass
   on each configuration, five corrupt-copy controls are rejected and the
   normal build is restored. See `tmp/pickup-expiry-cross-validation.json`
   and `tmp/pickup-expiry-negative-validation.json`. This does not verify
   depletion, other powers or visible/audio output.
   Speed-power selection and depletion now have separate input-only coverage.
   `PICKUP_USE_SELECTS=7` cycles through all seven available slots, consumes
   the existing last speed charge at tick 1414, and lets the native 200-unit
   timer expire at tick 3814: 2400 simulation ticks, or 40 seconds. Native
   expiry automatically selects slot zero after exhausting slot six. All
   fifteen checkpoints match A500 and delayed 68020, including private clocks,
   with only deferred projection scratch allowed; all 89 hooks pass. The
   diagnostic is excluded byte-for-byte from the playable release and the
   normal build is restored (`tmp/pickup-speed-cross-validation.json`).
   Reanalysis of those exact retained captures also checks native boost
   acceleration: 0 at tick 1414, 3 at 1415, 37 at 1425, 40 at 1426 and
   287 at 1500, then the native cap of 400 at sampled pre-expiry points.
   Neutral mouse input returns speed to zero at 3815. Both CPUs match the
   integrated 40-units-per-twelve-ticks expectation; a one-unit corrupted
   speed fails the checker (`tmp/pickup-speed-movement-validation.json`).
   These captures precede the collision-order release. This does not
   independently establish displacement, active-power cycling, other power
   effects or audible output.
   The other three timed powers (inventory slots 1, 4 and 5) also pass native
   input activation, last-charge consumption and full 6000-tick/100-second
   expiry on A500 and delayed 68020. Their activation/expiry ticks are
   1404/7404, 1410/7410 and 1412/7412; exhausted slots select 2, 5 and 6.
   All 40 paired checkpoints match gameplay/HUD/fresh projection and private
   clocks, allowing only deferred projection scratch. Presentation counts
   differ in each pair, and all 89 installed hooks pass on all six runs.
   The release is unchanged and the normal build restored; see
   `tmp/pickup-timed-cross-validation.json`. This closes input-driven timer
   lifetime and depletion coverage for the five phased powers. Effect-specific
   combat, cycling while a power is active and audible output remain open.
   Jump now also passes input-driven selection and last-charge consumption
   on A500 and delayed 68020. Activation at tick 1406 lands at tick 1946
   (540 ticks, nine simulation seconds), clears all jump integrator state and
   selects slot three. All 45 native 5 Hz height boundaries match the native
   220-launch/10-decrement trajectory exactly; additional apex and landing
   samples satisfy the rational curve with less than one unit of position
   rounding. All 55 mapped gameplay/HUD/fresh-projection/private-state
   checkpoints match across CPUs, allowing only deferred projection scratch,
   with different presentation counts and all 89 hooks passing. Release bytes
   remain unchanged and the normal build is restored
   (`tmp/pickup-jump-cross-validation.json`). Arbitrary terrain and midair
   impacts are outside this controlled encounter.
   Native slot-three activation now also passes on A500 and delayed 68020.
   Selection at tick 1408 consumes the last charge, allocates a type-43 mine,
   places it using the native full -1000-speed movement call, and selects slot
   four by completed tick 1409. Guarded native trig tables independently give
   the observed position (-305, 952, 0); it remains stationary through 2400.
   This specifically checks that one-shot placement is not divided by twelve.
   All eleven mapped gameplay/HUD/fresh-projection/private-state checkpoints
   match, allowing only deferred projection scratch; all 89 hooks pass, the
   normal build is restored and release bytes are unchanged
   (`tmp/pickup-mine-cross-validation.json`). Mine impact/detonation and
   other contact outcomes remain outside this placement check.
   Extend contact coverage to full encounters, lethal
   shield/type-43 hits and boss helpers, preserving immediate projectile and
   self-destructing actor impacts; see the call-site table in internals.
3. Validate preference changes, later deaths and remaining UI/level transitions.
   A DEATH_NATURAL extension now arms the death observer without changing
   energy and checks Continue at the same level in the next session. It is
   excluded from release builds and leaves the preceding type-9 encounter
   binary unchanged; three invalid combinations are rejected and prior
   injected-death/menu snapshots still pass (`tmp/natural-retry-build-validation.json`).
   Normal 68020, A500 and delayed 68020 all observe natural death at tick
   9212 with energy -80, after arming at 9000. Continue resumes level 6/session
   8 with energy 680, fresh credit 60, zero tick/render/phase counters and
   cleared timing regions. Post-retry gameplay/HUD/fresh projection matches at
   600/1500, allowing only deferred projection scratch. Six prior level resets
   and 88 installed patches pass on each configuration; nine corrupt-record
   controls are rejected and the normal build is restored. Reports:
   `tmp/natural-retry-cross-validation.json`,
   `tmp/natural-retry-020-validation.json`.
   The input-only combat pilot survives through tick 21600 but has not reached
   an exit. Read-only breakpoints confirm a native player projectile hit at
   tick 5711: type-3 health goes 1→0, damage returns 1 and score rises 30→60.
   Normal A500 and delayed 68020 now match gameplay/HUD/fresh projection before
   and after that kill at ticks 5711/5712 and through 7200. Over 600–7200 they
   average 59.71/60.00 updates/s, with 281/231 presentations and pending updates
   19→51/7→7. This validates ordinary projectile removal/scoring across render
   costs, not sustained heavy-scene performance or a boss kill.
   APPROACH_TYPE=0 with APPROACH_FIRE selects grounded enemies and prioritizes
   a type-25 exit. LEVEL_OBSERVE records native exits without requesting them;
   its pre-transition tick-600 gameplay/HUD/fresh projection matches the
   observer-free pilot, and the checker rejects the incomplete transition.
   These diagnostics are byte-excluded from release builds.
   Declining Continue, returning through the native menu and starting a new game
   now pass on both CPUs. Tick/phase/private state clears at session 2, with
   exactly one initial tick of credit; resumed gameplay/HUD/fresh projection
   matches at 600/1500. Choosing Yes instead is rejected by the decline test.
   Real preferences plus a nested native pause dialog now pass
   on both CPUs, preserving 32/30 owed updates and matching fixture-free
   gameplay/HUD/fresh projection through tick 1500. The lost-credit negative
   control is rejected. The input-only Mouse preference toggle now also passes
   on A500 and delayed 68020: native value 1→0 persists at 201/600/1500,
   all four preference words and gameplay/HUD/fresh projection match, and
   modal entry/return ticks remain 200 with 32/30 owed updates retained.
   `tmp/preferences-choice-validation.json` records the Mouse PF61 checks.
   Joystick, Music and Sounds now each pass native 1→0 changes on both CPUs;
   settings/gameplay/HUD/fresh projection match at 201/600/1500, and modal
   entry/return remains at tick 200 with 32/30 owed updates retained.
   `tmp/preferences-remaining-validation.json` records all six captures and
   eighteen checkpoints. These checks exercise each setting independently;
   combined changes, re-enabling and further UI paths remain outside coverage.
   Extend mapped-state coverage as new dependencies are found.
4. Broaden original-reference pace evidence and original/reconstructed-loader
   behavioral equivalence. The modern loader is not a byte-identical rebuild of
   the 2008 slave. Confirm the intended gameplay cadence through playtesting.
5. Finish remaining replacement-semantic and indirect-entry coverage before
   making SIM60 the normal default. The current release passes whole-instruction
   boundaries for all 69 merged ranges, conservative direct-entry checks and
   663 relocated code-pointer checks (`tmp/scan-order-release-hook-audit.json`).
   All 89 installed hooks pass on both CPUs in the current combat and terrain
   encounters. With CUSTOM1 off, 151969 original code bytes and 4833 relocated
   longs pass, including all 89 compiled patch ranges, with zero unexpected
   changes (`tmp/disabled-scan-order-validation.json`). Six native mutable
   code-data objects and exact menu-fixture jumps remain separately checked.
   Diagnostic flags without VERIFY produce the same release bytes, and the
   normal build is restored after captures.

   Current table-loop and unrolled-input profiles also pass trace-register
   indirect-entry audits: 5996 executed calls/jumps in the baseline and 6305 in
   the adopted candidate, with all 89 installed hooks checked in each capture
   (`tmp/quanta-perf-validation.json`). No observed target enters a patch
   interior. Earlier sort/geometry audits retain additional encounter coverage.
   These checks cover address-register and brief-indexed calls/jumps; returns,
   exceptions, unseen paths and full replacement semantics remain outside them.

   A separate current collision-order return audit verifies 23484 A500 and
   28843 delayed-68020 RTS/RTR/RTD transitions from game/slave code. Of these,
   10961 cross profiler gaps with matching gap/next-instruction snapshots,
   preserved D0–D7/A0–A6 and the expected stack adjustment. The marker denotes
   between-instruction cycles, not necessarily an interrupt. Every verified
   target avoids patch operands; declared installed NOP padding is allowed at
   native $2c9c, $3238 and $2bdc. The remaining 15/65 discontinuous boundaries
   are unverified; exceptions, external-source returns and unseen paths remain
   open. Deliberate operand/odd-padding destinations and mismatched snapshots
   are rejected; changed registers/stacks and missing PCs remain excluded.
   See `tmp/scan-order-return-gap-validation.json` and `tools/return_entry_trace.py`.
   Routine-cost reports count instruction records only, excluding all gap costs
   and other stack contexts; historical means have the same scope. Field/tick
   throughput measurements above are unaffected by this accounting distinction.
   Separate attribution of paired same-context gaps preserves the measured
   collision-order benefit: update means including these gaps improve
   92303.10→90004.42 cycles on A500 (2.49%) and 53499.50→52422.49 on delayed
   68020 (2.01%). All prior instruction means and completed counts reproduce.
   Entry/return/context-switch gaps remain excluded; this is not elapsed time.
   No gaps were attributed to these A500 calls, so it does not explain their
   remaining backlog (`tmp/scan-order-gap-costs.json`).
