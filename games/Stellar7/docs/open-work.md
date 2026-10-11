# Stellar 7: current work

## Performance plan (active)

Goal: play as smoothly as each machine allows, from an A500 up to an AGA
68040/68060 with fast RAM, capped at the display rate (50 fps PAL, 60 NTSC).
Game time is a fixed timestep, independent of drawing, and identical on every
machine. Follow the steps in order. Each step ends with its measurement in
`docs/internals.md`, its commands in `docs/development.md`, and one commit
(author, unsigned, no hooks, no trailers: see AGENTS.md).

### Diagnosis

The N=12 reference SIM60 design runs the whole native update 60 times a second, as
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
at R = 30 / 20 / 15 / 10. At 60 Hz the measured A500 is 5–10× slower to present than
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

Status: complete. The serial driver, seconds-based boot deadline, chip-only
A1200 memory capture and field-based update-start observations are implemented.
All 48 initial cells under `tmp/rate-baseline` and all 24 native combat cells
under `tmp/rate-native-combat` pass the strict report checker. All 56 sampled
cross-CPU/PAL gameplay comparisons match, apart from deferred projection scratch.
The baseline tooling tests pass. N=12 is the reference; step 2 selects N=1.
See internals for both complete tables and development
for the capture and verification commands.

Native frame-90/240 cells are SOL references. The native combat routes provide
scene-specific presentation spot references for step 2: A500 NTSC early
and late type-10 are 4.444 and 4.110 presentations/s; boss is 1.818.

The VERIFY-only `NATIVE_SCENE` fixture has passed runtime validation on every requested
machine for type-10 and boss scenes. It requests native exits into level six for
type-10, or reuses the controlled boss setup while CUSTOM1 stays disabled.
Setup hooks restore native instructions before measurement. The checker
verifies 151969 original code bytes, all relocated longs, removed setup hooks,
zero SIM60 ticks and the intended level/actor state. Omitting the diagnostic
leaves the ordinary VERIFY slave byte-identical. The matrix driver now includes
native type-10 frames 150/375 and boss frame 292, selected explicitly with
`--routes native-type10-early native-type10-late native-boss`. All captures
share the exclusive matrix lock and run one at a time.

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
   duplicate stops the boot at an AmigaDOS argument error. The boot poll uses
   a seconds-based deadline (1800 seconds by default).
3. Measure native presentation fps for the same machines with `--swaps-only`
   at frames 90 and 240. Record the cache state (the slave calls SetCPU
   $393d/$7f3f).
4. Record the matrix in internals as the reference table. Every later step
   re-runs it, and reports must state updates/s, presentations/s, pending
   growth and the largest update-start gap (`simulation_latency.py`).

### Step 1: Make the substep count a build constant

Status: complete. Parameterized sources and ABI-aware readers are in place.
All six rates compile; N=12 release and VERIFY are byte-identical to
the baseline. Thirteen private fixture groups (78 builds) compile, with every
N=12 fixture build identical to its unmodified baseline build. All 78 private
fixture combinations pass on A500. Six full-duration power runs and six jump
runs pass.
The 285 cross-N comparisons and startup replays classify the observed
differences as substep timing, native branch consequences and rounding;
fixed-direction actor-relative native endpoints remain exact. See internals
for the measured examples and limits.
Step 2 selects the lower default. Retained parameterization evidence is under
`tmp/substeps-prototype`.

`S60_SUBSTEPS` is the build constant (N ∈ {1, 2, 3, 4, 6, 12});
`S60_RATE = 5 × N` and `S60_LEGACY_DIV = N`. The parameterization and
acceptance audit cover every N-dependent constant, including:

- `s60_clock`: elapsed × 60 becomes elapsed × S60_RATE (keep the long
  arithmetic). Credit consumption per tick stays `field_hz`.
- `linear60.s`: `divs #12` and the remainder ranges ±11 / ±12.
- `boss60.s`: the 288 = 2N² divisor and the (2k − 13) term,
  which becomes (2k − N − 1).
- `events60.s`: jump 144 = N², 55 = g(N − 1)/2 and velocity × 12.
- `motion60.s`: the `S60_INPUT_SITE …,12` quanta and the 80/10/40 schedules
  (`floor((phase+1)·inc/N) − floor(phase·inc/N)`).
- `pickup60.s`: `muls #11` (N − 1).
- Every "twelve-tick" clock: powers, animation, contact, terrain, shake, HUD,
  knockback, cooldowns, AI decisions, spawning, frame counter.
- HUD cadence and input-quanta unroll tables. The HUD installation loop
  copies exactly 48 native instruction bytes (12 longwords); that copy count
  is independent of N and must remain fixed. The boss pitch/acceleration
  bit mask `(1<<2)|(1<<3)` is also independent of N.

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

Status: complete, including selected-default regression checks. All 128 requested N=2,3,4,6 cells and 224 cross-CPU/PAL comparisons
pass their measurement/state checks, but none passes both A500 presentation
gates. The additional supported N=1 fallback passes all 32 cells and 56
cross-CPU/PAL comparisons and is now the **5 Hz default on every machine**.
Explicit N=12 release and VERIFY remain byte-identical to the baseline.

Native A500 frames 150–200 and 375–450 measure 4.411765 and 4.083485
presentations/s. N=1 delivers 4.723618 and 4.385382 respectively. Its nominal
600→5400 heavy window completes 400 ticks in 80.183333 seconds, with pending
samples of 0–1 and no accumulating backlog. The same pass/fail decision holds
against the original native 100-field spot references. Full tables, pending
samples and cross-N limits are in internals; captures are under `tmp/rate-nN`,
`tmp/rate-nN-heavy` and `tmp/rate-native-exact`.

Choose the largest supported N meeting both measured conditions: sustained
A500 heavy-combat game time and at least native presentations/s in both
matched type-10 windows. N=1 is the only supported value that passes both.
The simple cost model's N=3/N=4 prediction is not borne out by the scene
measurements. No per-CPU rate is introduced.

Selected-default SLOW_DRAW, death/Continue and No/restart, normal/early exits,
disabled-code preservation, hook audits and the actual play60 launcher smoke
all pass. All 16 matched-tick endpoint comparisons agree except for deferred
projection scratch. The normal and playable builds are restored.

The selected timestep is 200 ms. Fast machines currently repeat poses between
ticks; interpolation is deferred. One-tick interpolation would add 200 ms of
display delay with that design. Steps 0–2 stop here; wait for the user's pace playtest before step 3.

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

The N=12 reference 68040/25 and 68060/50 both present about 29 pictures/s with
pending updates 0→1. Doubling the CPU gains 0.3 fps, so each picture takes two
fields for a reason other than CPU speed. The suspects are a frame just over
one field (blitter or chip RAM), or the VBL wait at $1c84c plus the buffer
handshake costing an extra field. Profile one 68060 frame against the field
boundary first: re-measure this at the selected N before attributing its ceiling. Also run the
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

## Remaining release validation

The performance plan above controls the work order. Steps 0–2 do not make the
conversion a finished release, and step 3 waits for the user's pace playtest.
Current implementation details and retained N=12 measurements belong in
`docs/internals.md`; build and fixture commands belong in `docs/development.md`.

- Preserve input belonging to each overdue tick (step 4). The playable build
  still reads live joystick hardware at $22750–$22756 and current key state
  through $22730 during catch-up. Tick-indexed VERIFY fixtures do not establish
  equivalence for elapsed-field input edges. Cover keyboard queues, mouse
  deltas, mode switches, overflow, modal ownership, reset and PAL timing.
  Scripted reproduction does not require physical host UI access.
- Broaden full-encounter coverage at the selected rate: boss kills and ending,
  later natural deaths, level and UI transitions, lethal shield/type-43 hits,
  boss helpers and mine detonation. Controlled placement, native twins and
  sampled mapped-state comparisons do not cover every encounter branch.
- Extend power checks to active-power cycling and combat effects, and jump
  checks to arbitrary terrain and midair impacts. Check combined preference
  changes, re-enabling settings and additional native dialog paths.
- Confirm original-reference gameplay pace and the reconstructed loader's
  behavior through playtesting. The modern KickEmu loader is not a byte-identical
  rebuild of the supplied 2008 slave.
- Finish replacement-semantic and indirect-entry coverage before enabling
  SIM60 in the normal loader. Static patch-boundary checks and observed
  calls/returns leave exceptions, external-source returns and unseen paths
  outside coverage. Keep disabled-code preservation and diagnostic exclusion
  in the final release checks.

Do not resume per-tick 60 Hz micro-optimisation or start interpolation as part
of the current steps 0–2 request.
