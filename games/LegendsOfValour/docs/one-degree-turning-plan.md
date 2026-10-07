# One-degree turning plan

Status: implemented and automated validation complete, 7 October 2026.
Normal interactive evaluation is the remaining acceptance step. This is separate from W7, which remains deferred.

## Intended result

Allow the player to face and render every whole-degree heading, with fine input
capable of a one-degree adjustment. Keep movement, walls and sprites aligned.
Preserve the user-approved walking-animation cadence and the 25 Hz simulation
setting. Precision and held-turn speed are separate controls: reducing the angle
unit must not accidentally make held turning five times slower.

Ship only an optional WHDLoad slave patch behind the user-approved CUSTOM2
boolean bit 7 (mask 128), labelled "1 degree turning". The option audit confirms
bits 0–5 belong to W1–W6 and bit 6 to timing; bit 7 is available. Read the toggle
at launch, not during gameplay. With the option off, leave the affected original bytes untouched
and retain the existing five-degree behavior. Do not enable the new option in
user preferences until validation and an interactive evaluation are complete.

## Evidence and feasibility boundary

The raw heading at h11:08c28 and the existing sine/cosine routines support
integer degrees. The displayed heading at h11:08c22 is rounded using the
five-degree unit at h11:06010 (h5:01e8e–01e96).

The wall renderer also depends on that unit. Setup at h12:0229e stores a row
stride of 4 × (view width + 8) at h12:0003a and the angle unit at h12:00038.
At h12:028d8–02904 it folds the heading into a half turn, divides by the angle
unit and selects a row from the table pointed to by h11:05faa. Rows contain
control markers and octant transitions as well as column parameters. Merely
changing the unit or interpolating arbitrary words is unsafe.

The three supported views currently load these tables:

| View | Resource | Current 36 rows | Proposed 180 rows |
|---|---|---:|---:|
| Large, 192 × 92 | mt0.dat | 28,800 bytes | 144,000 bytes |
| Medium, 112 × 64 | mt2.dat | 17,280 bytes | 86,400 bytes |
| Small, 80 × 48 | mt3.dat | 12,672 bytes | 63,360 bytes |

These are table payload sizes, not total additional memory. Original allocation
ownership and any retained original buffer must be included in the final budget.
One degree is a plausible localized extension, not yet a demonstrated minimum.
Sub-degree headings are outside this plan.

## 1. Recover and prove the table generator

- Decode all row fields, terminators, octant markers, signedness, fixed-point
  scales, rounding and singular-angle handling. Follow their renderer consumers,
  including h12:0290c onward, rather than inferring the format from file sizes.
- Reconstruct the mathematical generation algorithm. Prototype it with local
  reference data in tmp/ and compare every generated five-degree row against the
  original tables in all three supported views.
- Require byte-exact reproduction at the original headings as the first gate.
  Explain and resolve discrepancies before proceeding. If faithful generation
  requires a broader renderer rewrite, stop and report the revised scope.
- Generate all 180 one-degree rows and check bounds, marker structure, divisors
  and fixed-point ranges, especially at cardinal and octant boundaries.
- Keep game-derived tables, dumps and fixtures in tmp/. Commit only original
  generator/patch code and documentation; generate table contents at runtime.

## 2. Add owned table storage and view lifecycle

- Audit the original allocation at h1:02314, resource loading through h8:00774,
  view changes and shutdown. Identify every reader, writer and free of
  h11:05faa before redirecting it.
- Allocate slave-owned storage with MEMF_PUBLIC on every CPU. Let the allocator
  prefer fast RAM when available; do not require or explicitly request fast RAM.
  Prefer one reusable buffer sized for the largest supported table (144 KB).
- Generate the selected view outside the rendering loop. Publish its pointer,
  row stride and angle unit together only after successful construction. Avoid
  per-column interpolation or table generation in the hot path.
- Preserve a coherent original-table fallback. Allocation/generation failure
  must leave both rendering and input at five degrees, never mix a one-degree
  index with a five-degree table. Record the fallback in VERIFY diagnostics.
- Define ownership across view switches, load/restart and exit; free exactly
  once and never let the original game free slave-owned storage.
- Audit the hidden 160 × 92 and 64 × 40 setups and absent mt1/mt4 resources.
  If reachable, explicitly retain their original behavior until their tables
  are supported; do not index them using the new unit.

## 3. Integrate heading and input precision

- Audit every heading writer and consumer: relative mouse input, turn buttons,
  scripted/cardinal turns, movement vectors, sprite orientation/projection,
  collision and save/load. Reuse the existing whole-degree trig functions.
- Set the active supported view's quantization and renderer divisor to one only
  after its new table is ready. Reapply this consistently after view changes.
- Check heading wrap in both directions. The existing positive wrap subtracts
  359 while negative wrap adds 360; establish canonical 0–359 normalization
  for the new mode and cover large deltas as well as one-degree crossings.
- Provide one-degree discrete adjustments. Preserve the accepted sustained
  turn rate separately with an input accumulator/repeat policy; document the
  chosen tap, hold and mouse mapping before the play-test. A short tap must
  actually show a one-degree change, not immediately jump by five degrees.
- Audit interaction with the timing patch's existing five-degree feel hooks.
  Support both option combinations if practical; otherwise explicitly report
  a dependency before implementation rather than silently requiring bit 6.
- Use guarded signatures and preserve registers/condition codes at every hook.
  Add the new disabled-option sites to the existing untouched-bytes checker.

## 4. Verify geometry, behavior and cost

- VERIFY compares generated legacy-angle rows to the original tables and aborts
  on the first mismatch with view, heading and row/column diagnostics.
- At identical world state and headings divisible by five, compare rendered
  pixels with the original path in all three views. Isolate animation/random
  state so scene differences cannot masquerade as geometry differences.
- Exercise every heading 0–359 in both directions, including 359/0 wrap and
  cardinal/octant boundaries. Check intermediate rays against the recovered
  mathematical model, plus wall/sprite alignment and movement/collision in
  representative scenes. Distinct table rows alone do not prove finer output.
- Test tap, hold, mouse reversal and release; view switches, save/load/restart;
  repeated allocation lifecycle and forced allocation failure. Verify that
  the existing animation regression still passes.
- Run on the A500-equivalent and 68020, including no-fast-RAM fallback behavior.
  Keep captures serial, JOY0=none, in amiga/.cap; leave the user's session alone.
- Run fixed-window A/B using profiling §7 and record results in §8. Compare
  matched headings/world state and cycles per call as well as FPS, since finer
  input can otherwise change the scene. Record table construction time and
  actual memory overhead separately. Make no speed claim before both-CPU A/B.

## 5. Deliver and evaluate

Keep this work isolated from unfinished keyboard and cosmetic-random prototypes.
Build from an explicitly identified animation-approved baseline, with unrelated
changes excluded. Use coherent source-only commits under the repository's author,
unsigned and no-hooks rules; never stage play-test directories or generated data.

After the gates above pass, launch a normal-slave trial on the previously accepted
realistic 68020 setup with normal blitter timing. Let the user assess one-degree
taps, sustained turning and wall/sprite stability before changing their defaults.
Record the tested build, enabled options, remaining limitations and easy-to-adjust
input-rate constants. W7 and sub-degree rendering remain deferred.

## Implementation and verification evidence

The plan/toggle decision was committed as `09dc53b`. The following are automated validation results. Interactive acceptance remains
with the user; the A/B limitations are recorded in profiling §8.

- `python3 tools/turning_tables.py` reconstructs all 13,824 consumed columns of
  all 108 original rows exactly. The empirical floating-point model uses the
  double immediately above pi; this reproduces the original asymmetric 90°
  truncation. It does not establish how the original offline tool was written.
- Each ray is the rotated vector `(focal, (width-1)/2-column)`. Store
  `floor(65536*minor/major)` and `round(65536/major)` with its octant. A zero word
  advances to the preceding octant. Unconsumed row padding in smaller original
  files contains unrelated trailing values; it is not ray geometry.
- The shipping candidate copies the 36 existing rows at runtime, including their
  padding, and constructs the other 144 with original Q22 sine constants and
  68000 integer arithmetic. This preserves legacy rounding exactly without an
  FPU or copying game tables into source. Across all 55,296 intermediate columns,
  projection words match the floating model and slope error is at most 1/65536.
- Near-axis rays need a minimum slope of two: zero is a control marker and one
  overflows the original `65536 / slope` DIVU. The same explicit bound is applied
  to the independent mathematical reference; it is below 0.002° angular error.
- `turn-table-oracle-a1200` and `turn-table-oracle-a500` both reach the spin anchor
  with the full large-view table active. All 180 guest rows match the host model
  byte for byte, both angle units are one, and two table generations completed.
  VERIFY checks all copied rows and an independent mathematical checksum of new
  rows before publication. These runs use CUSTOM2=191 (timing disabled).
- `turn-table-a1200` establishes a real allocation-failure fallback: both angle
  units remain five and the active table is null. The original KickEmu 512 KB
  expansion pool cannot accommodate the full new table. The candidate raises
  FASTMEMSIZE by 144 KiB (to 656 KiB); this increases the slave's reservation even
  when the option is off. PUBLIC allocation in the successful runs selected chip
  RAM. Physical host fast RAM alone does not expand KickEmu's fixed pool.
- The original table pointer remains owned by the game. Only the renderer's row
  selector uses the new allocation; original loading/freeing paths never see it.
  One owned buffer is reused on view changes and released on game cleanup.
- Candidate button policy: first press one degree; suppress repeats for eight
  PAL fields (160 ms), then retain the view's existing held increment. Use consumed
  simulation fields when timing is enabled. Mouse headings normalize to 0–359.
  The 020 `turn-tap-a1200` completed-tick capture records exactly one change,
  heading 156→157, from the four-field test press; the following 35 ticks hold
  at 157. Its shared-animation regression passes 40 ticks/five phase advances.
  The later input cases are recorded below. The unverified cosmetic-random hook is
  now opt-in at build time so timing-enabled turning tests retain the approved
  shared-animation correction without introducing that experiment.

Remaining acceptance work: normal interactive evaluation. Automated table, input, full-angle ray, wall-twin,
allocation/fallback and both-CPU fixed-window checks are complete as detailed
below and in profiling §8. No local performance preference has been changed.

The all-view captures `turn-views-a500` and `turn-views-a1200` pass every table
oracle and 231/1,161 original-versus-Kalms conversion twins respectively. Their
small/medium/large table-generation counts are 1/2/2 and 2/2/3. These conversion
twins validate conversion integration, not wall geometry by themselves.

A separate VERIFY bit-19 wall twin runs h12:02808 twice at headings divisible by
five: once with the new table/divisor and once with the original table/divisor.
Actor/world updates preceding that pass run only once. It compares all 20,000
chunky bytes and aborts on a mismatch, restores the new table state and output
registers, and publishes the normal ray-output cursor. Its shared staging buffer
requires W6's nested twin (CUSTOM5 bit 7) to be off. `turn-wall-twins-a1200` passes
357/250/312 small/medium/large wall twins, plus 958 conversion twins. This covers
the legacy headings encountered by the route, not every possible heading.

The tap drawing-delay pairs `turn-tap[-delayed]-a500` and
`turn-tap[-delayed]-a1200` each compare 41 consecutive completed ticks. All
decoded world categories match except the independent live game clock; player,
all 56 actors, RNG and animation match. Each short press adds one degree after
queued pre-anchor input is consumed. No frame-rate inference is made from these
observations.

`turn-wall-twins-a500` adds 60/40/40 small/medium/large full-wall comparisons,
plus 179 conversion twins. No wall-pixel differences occurred in either CPU run.

`turn-mouse-sweep-{a500,a1200}` and `turn-mouse-reverse-{a500,a1200}` each retain
401 consecutive completed-tick samples. `tools/turning_input_check.py --sweep
forward|reverse` verifies exactly 360 unit steps, every heading 0–359, one wrap,
and exact agreement with the historical mouse-counter deltas. The displayed
heading equals the raw heading throughout. These are input/state tests; they
do not assert that the slower A500 displayed every simulation tick. The 020
forward run also passes 400 ticks/50 shared-animation phase advances.

The VERIFY bit-21 native ray-walker sweep has now passed all 360 headings in
all three views on both CPUs (`turn-ray-sweep-a500`, `turn-ray-sweep-a1200`).
It holds the world position fixed, checks the words immediately outside the
chunky allocation, and restores the real heading before the ordinary drawing
pass. Actors are not advanced by this fixture. The captures also pass all-view
legacy wall twins (A500 8/18/9; 020 298/251/229) and conversion twins.

`turn-lifecycle-{a500,a1200}` run the standalone feature without the timing
prototype. VERIFY bit 22 allocates, releases through the actual shutdown helper,
checks both ownership pointers cleared, reallocates, and reaches gameplay with
an exact generated table. `turn-fallback-{a500,a1200}` force the PUBLIC attempt
to fail (bit 18); both angle units remain five and the active table stays null.

`turn-hold-{a500,a1200}` each cover 51 consecutive completed ticks. The 40-field
press produces steps `[1,0,0,0]` followed by sixteen five-degree steps, then no
turn after release. Animation regressions pass on both CPUs. This explicitly
checks that finer taps do not reduce sustained turning to one fifth speed.

The source-isolated normal build excludes the unfinished simulation work. Its
SHA256 remains `e38c94ff27c6349036e82bca6d1168f5f449dbe227603e5173acfdfc7caf3118`
after adding the exhaustive VERIFY ray sweep; those instruments do not enter
the normal slave. Timing integration is covered separately by the captures above.


Save/load format audit: h2:04cce serializes fourteen bytes from h11:08c1c
through h11:08c29, including displayed heading at 08c22 and raw heading at
08c28. h2:04bde restores the same bytes. Their copy helpers h2:04a5e/04a8a
perform byte copies, without angle quantization. The optional patch does not
change the save format. Native UI round trips pass on both CPUs as recorded below.

The final standalone A/B is recorded in profiling §8. It shows matched camera
poses but different actor state, so no speedup is claimed. Large-view table
construction takes 542/87 PAL fields on the A500/14 MHz 020; this is a setup
cost. The tap delay can be adjusted with `TURN_REPEAT_FIELDS` in turning_input.s;
held increments retain the game's current view/timing setting.


### Reproducing the geometry checks

`python3 tools/turning_tables.py` checks the mathematical reconstruction against
locally supplied game files. For guest verification, build with
`make -C whdload verify VASMFLAGS=-DVERIFY_WAIT_RESCUE=1`. Retain that slave and
listing in the capture folder, then use the §7 machine settings with
`KEEP_SLAVE=1 WHD_ARGS=CUSTOM2=191 TAPE_OPTIONS=2621443 SELFTEST_FRAMES=40
TURNING_CHECK=1 TURNING_CHECK_ARGS="--require-all-views --require-wall-twins
--require-ray-sweeps" tools/fixed_window.sh OUT tools/tapes/c2p-views.txt`.
This enables the conversion twin, wall twin and complete ray sweep together;
W6's separate scratch-sharing twin must remain off.

For the allocation/free/reallocation fixture use `STATE_ONLY=1`,
`TAPE_OPTIONS=4194305`, and `TURNING_CHECK_ARGS=--require-lifecycle` on the spin
route. Forced allocation failure uses `TAPE_OPTIONS=262145` and
`TURNING_CHECK_ARGS=--fallback`. The tick-input checker consumes retained
`ticks` observations from the separate, still-uncommitted timing harness; it
is not a dependency of the standalone turning patch or geometry checks.


### Save/load and normal trial

`turn-save-load-a1200` records stable raw/displayed headings 166° before saving,
32° after turning away, then exactly 166° after loading. The A500 counterpart
records 316° → 347° → 316°. Both return to large-view gameplay with the exact
180-row table active and both divisors equal to one. The tape takes three
anchors (before save, before load, after load); checkpoint dumps and route are
retained with the captures. A500 menu clicks need forty fields: the initial
short-click route stalled before entering the save panel and was rejected.
The successful A500 build includes the existing VERIFY-only wait rescue.
No save format or user save files were changed.

Normal standalone SHA256:
`e38c94ff27c6349036e82bca6d1168f5f449dbe227603e5173acfdfc7caf3118`.
The separate normal interactive candidate adds the current animation-approved
25 Hz simulation prototype; SHA256:
`8ea3d1773ca76844c98a39b19ec4384f86fdefd712b927df2487f67e4cf9cd54`.
`SIM_FIRE_EXPERIMENT` and `SIM_KEYBOARD_EXPERIMENT` are absent. The normal build
contains no tape or verification fixtures. Trial settings are CUSTOM2=255,
68020 at 28,375,160 Hz, 2 MB chip/8 MB fast, PAL, normal blitter timing and no
warp. It uses `tmp/playtest-turning`, leaving amiga/.run and preferences alone.
The broader simulation goal is still unfinished; this trial evaluates angular
precision while retaining the accepted animation correction.
