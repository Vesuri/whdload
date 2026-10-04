# Sub-unit rendering: work order

Instructions for an agent implementing smooth road motion in duel v1. Read `CLAUDE.md`,
`docs/open-work.md`, `docs/profiling.md` and `docs/optimisation-plan.md` first. All addresses
are duel hunk-0 offsets. `a4` variables are written `-N(a4)`. A data-hunk offset is
`$7FFE + (-N)`: that is where `-N(a4)` sits in a `state_fields.py` snapshot.

## Problem

From a standstill the picture moves in visible jumps. Physics is smooth: the player distance
`-17238(a4)` is 16.16 and grows by about 0.03 road units per step at first. The renderer uses
whole road units only:

- `06442` latches the full long into `render_distance` `-13394(a4)` once per frame.
- The road reads only its high word (`06c52`, `06d8c`). The fraction at `-13392(a4)` is never read.

One unit near the bottom of the screen is about 6 px. Nothing moves for the first 0.72–0.80 s,
then the frames step irregularly by 0 or 1 units. The original game behaves the same. The goal
is to draw at the exact position while matching the original at fraction 0.

## What is already established (re-check, don't trust blindly)

- **Road rows (`07370`).** `a3` walks 52-byte row records. Row k is at `-5702(a4) + 52k`. There
  are 44 main-view rows and 24 mirror rows (`-7600(a4)` = 44 / 24, set at `06c36` / `06d78`).
  - Main view (`06c0c`–`06c6c`): `d6 = 0`, walks forwards, starting segment `-13394.w + 1`.
  - Mirror (`06d82`–`06db0`): `d6 = 2`, walks backwards (`d4 = -1`), starting segment `-13394.w`.
  - Every scale field is read as `(N,a3,d6.w)`. The main view uses even field N and the mirror
    uses N+2, so the two views share rows but not fields.
- **Per-row constants.** Copied once at start-up by `06a90` (called only from `059ac`) out of
  the data hunk:

  | Field (main/mirror) | Source table (main 44 words / mirror 24 words) | Meaning |
  |---|---|---|
  | 18 / 20 | `-26780` / `-26968` | height scale. `muls` with the accumulated height at `07404` |
  | 22 / 24 | `-26870` / `-27018` | lateral scale. `muls` at `07432` |
  | 26 / 28 | `-26690` / `-26918` | road half-width in px. Main is exactly 1200/(k+4) |
  | 48 / 50 | same tables ×162 | `mulu` at `074f0` |
  | 34–44 | byte tables `-25984`… `<<2` | shape size (level-of-detail) index. **Leave alone** |
  | 46 | 43…0 | row number. **Leave alone** |

  The main tables fit C/(k+4): row k is drawn at depth k+4. Main field 18 is clamped to 32767
  at row 0.
- **Row geometry per frame (`073a0`–`0743e`).** Heading `-14936` and lateral position `-14930`
  are seeded from `-13388` / `-13382`, and height `-14928` is seeded with 83 by `06a3a`. Each
  row then adds its segment's curve and slope and projects:
  - y = row field 12
  - x = row field 10
  - edges = row fields 0/2/4/6/8
- **Scanline fill (`0766c`).** Interpolates linearly between consecutive rows' y and edges into
  the scanline table `-7574(a4)` (16 bytes per line, indexed by y). So rows at fractional depths
  draw correctly with no extra work, **provided no row's y lands below the bottom line**. A y
  below the bottom indexes past the table.
- **Objects (`079c6`).** The visible lists are built by `0e240`:
  - `-14710`, from scenery list `-14470`
  - `-14590`, from list `-13970`
  - Entries are 8 bytes: +0 segment, +2 type, +4 pointer to the source entry+6.

  For each row, an object whose segment equals the row's segment is drawn with x from row field
  10/4 (list 1, branch `07a1c`) or 10/2 (list 2, branch `07a5a`), y from row field 12, and size
  from the row through `0e32e`, which reads `(42,a3,d6)`. Objects therefore follow their row.
- **Cars sit at whole segments.** `0d47a` inserts an object at segment `d0`, lateral `d1` into
  list `-13970`. The source entries are 10 bytes: +0 segment (−1 ends the list), +4 type,
  +6 data. `-13466(a4)` is added at `0e2b6`. `0d4dc` advances an entry by one whole segment,
  and `0d456` wraps it by the road length `-13142`.
  - The opponent block is at `-13358(a4)`. Its 16.16 distance is probably at `-13356` (+2): the
    game swaps it with the player's at `05a88`. It is inserted at `0d772` with `d0 = 2(a5)`,
    `d1 = 6(a5)`.
  - `0d462` inserts something at the player's own segment.
  - Types 19/20 are the police (see `-14916`). Types 17 and 25 get special treatment in the
    draw branches.
- **Leave these reads alone.** The other whole-unit reads are the HUD (`08fbe` opponent-gap
  meter, `090b2` course-progress bar) and the ±60-unit cull (`0e262`, `0e2c4`).

## Design to implement

A new option, **CUSTOM2 bit 2**: "sub-unit road position (v1)". With the bit off, nothing is
patched.

Let f be the fraction, the unsigned word at `-13392(a4)`, already latched with the frame. Use
`f>>1` (15 bits) with `muls` and `asr`/`swap` so that `$8000` is never misread as negative.

### Step A: road rows

Hook main and mirror separately, so each view uses its own direction:

- `PL_PS $06c66,render_subunit_main`: re-execute `move.w #10,-7610(a4)` first.
- `PL_PS $06daa,render_subunit_mirror`: re-execute `move.w #20,-7610(a4)` first.

Each hook rewrites only that view's scale fields (18/22/26/48 or 20/24/28/50), interpolating
from the **original source tables**, never from the row fields it has already overwritten:

- **Main view**, rows k = 1…43, depth k+4−f: `v = t[k] + ((t[k−1] − t[k]) · f) >> 16`.
  - **Row 0 keeps its original values**, so the bottom band shrinks to zero height as f → 1.
  - Recompute field 48 as `width × 162` from the interpolated field 26, so that it matches the
    original exactly at f = 0.
- **Mirror**, depth k+4+f: `v = t[k] + ((t[k+1] − t[k]) · f) >> 16`, rows 0…22. Row 23 keeps
  its original value, or extrapolate. Verify the sign by watching the mirror: the road must
  recede while driving forwards. If the mirror's row 0 is also the bottom of its window, keep it
  fixed like the main view's row 0.
- **f = 0 must reproduce the original fields bit for bit.**
- **Cost:** about 240 `mul`s a frame, roughly 3 ms on the A500. Measure it, as described in
  `optimisation-plan.md`.

Prerequisite check before trusting the "row 0 fixed" argument: dump the row records and confirm
that main row 0's y (field 12) is the bottom line of the road window (117?) at f = 0 on level
road. Then confirm that no interpolated row ever has a y greater than row 0's. If one can, clamp
y in the hook path, or keep more rows fixed.

### Step B: cars (required, or Step A makes them worse)

With Step A alone, a car keeping pace with the player slides one unit towards the camera and
snaps back on every whole-unit tick.

1. Find where every drawn car keeps a 16.16 position: the opponent (`-13356`?), traffic in both
   directions, and police. Start from the list `-13970`:
   - writers of the +0 segment word: `0d4dc`, `0d456`, `0d47a`, and anything else that grep
     finds for `c96e`
   - the `+6` data each car type points to
   - the AI code that moves traffic (`traffic_forward` / `traffic_oncoming` in
     `tools/state_fields.py` name the state)

   If a car type has no fraction (it moves in whole segments), record that and use g = 0 for it.
2. For each car, compute g = car_frac − camera_frac. If g < 0, add 1 and use the nearer row.
   In the two draw branches (`07a1c` for list 1 and `07a5a` for list 2), interpolate x and y
   between the matched row and its neighbour by g:
   - the farther row (`a3+52`) in the main view
   - the nearer row in the mirror, so mind the sign

   Keep the segment match and the row order, so the painter's order does not change. Keep the
   size index from the matched row.
3. Scenery has no fraction and needs no change: it rides its row.

### Step C: curves and hills (measure first)

Row geometry is accumulated from the segment boundary, not from the camera's position inside the
segment. On a curve or hill, check whether row x/y jumps when the high word ticks over. Compare
the row records just before and just after a tick on the demo's curves.

If the jump is more than about 1 px, scale the first row's heading/curve and slope increments by
(1−f):
- around `073e2`–`073f2` (slope)
- around `07412`–`07424` (curve)

## Verification (all required before committing)

Build both slaves: `make -C whdload`, `make -C whdload verify`.

1. **Simulation untouched.** The renderer must not feed the simulation. Run the straight tape and
   the demo with `CUSTOM2=1` against `CUSTOM2=5`, with `CUSTOM3=1`, using `STATE_FIELDS`
   captures as in `profiling.md` §"state". `compare_state.py --assert-core` must report 0
   mismatches. Do this on the A500 and the A1200; the setups are in `profiling.md` and
   `amiga/run-a1200.sh`.
2. **Identity at f = 0.** Add a VERIFY-only `CUSTOM5` bit 3 (now free): "sub-unit with f forced
   to 0". Capture state with `CUSTOM2=1` and with `CUSTOM2=5 CUSTOM5=8`. Every row record
   (`-5702(a4)`, 44×52 bytes, data-hunk offset `$7FFE-5702`) and the scanline table `-7574(a4)`
   must match byte for byte at every sample. Identical rows and scanlines mean identical pixels.
3. **Smoothness.** For each drawn frame of a straight-tape capture with `CUSTOM2=5`, from field
   STATE_FIELDS, report:
   - main row 1's y (field 12) and the y of the first colour-band boundary
   - the share of frames with any road motion once the car moves

   Compare with `CUSTOM2=1`. Expected: motion on every frame where distance changed, and a
   largest per-frame jump of row 1 well under the old ~6 px.
4. **Cars.** On the demo with `CUSTOM2=5`, track the opponent's and the nearest traffic car's
   screen y per frame while the distance gap is nearly constant. There must be no 1-unit
   sawtooth. Compare with `CUSTOM2=1`.
5. **Look at it.** Run `WHD_ARGS=CUSTOM2=7 amiga/run-a1200.sh` and the A500 equivalent:
   - no flicker or garbage at the bottom of the road or the mirror
   - mirror direction correct
   - roadside objects and cars stay attached to the road
6. **Regression suite.** Run with bit 2 on and off and confirm the results are unchanged:
   `check_units.py`, `check_disabled.py` (add the new patch ranges to its list),
   `audit_simulation.py`, and the fps measurements from `optimisation-plan.md` on the A500 and
   the A1200.

## Delivering

- **Slave code:** in `whdload/render.s`, gated by `render_options` bit 2, and listed in
  `slv_config` (`TestDrive2HD.s:89`). Patch lines go in `pl_main_v1` under `PL_IFC2X 2`.
  Comments should be as concise as the surrounding code.
- **Docs:** update `docs/open-work.md` (status and results table), `profiling.md` (CUSTOM5
  bit 3) and `optimisation-plan.md` (cost). Delete this file once the work is done, or turn it
  into a short design note.
- **Commits:** one per coherent step (A+B together if B is needed to avoid a regression; C
  separately). Follow the rules in `CLAUDE.md`: author `Vesa Halttunen <vesuri@jormas.com>`,
  `git -c core.hooksPath=/dev/null -c commit.gpgsign=false commit --author=...`, no
  Co-Authored-By.
- **If something blocks a clean patch, stop and report** rather than widen the change. Examples:
  a car type with no recoverable fraction, a row y overrunning the table, or a cost above 3% of
  an A500 frame.
