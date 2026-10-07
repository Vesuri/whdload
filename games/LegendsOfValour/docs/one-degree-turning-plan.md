# One-degree turning plan

Status: approved for implementation, 7 October 2026. No one-degree patch has
been implemented or validated. This is separate from W7, which remains deferred.

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
