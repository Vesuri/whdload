# Performance plan — Legends of Valour

> Handoff for the agent that implements the improvements. Written 2026-10-05 from the fixed
> window and baselines in `docs/profiling.md` §6–§7. **Read `CLAUDE.md`, then `docs/profiling.md`
> (all of it), then this file.** Every number here is from that window unless marked
> *estimate*; estimates must be replaced by measurements before anything is claimed.

**Status 2026-10-05:** W0 and W1 implemented and measured; evidence and exact commands in
`docs/profiling.md` §8. W1 is enabled in ignored local preferences. W2 is next; W7 is deferred.
The remaining items below are the work plan, not implemented features.

## 0. Ground rules (from CLAUDE.md and the playbook, restated because they bite)

- Every change ships as a **WHDLoad slave patch** in `whdload/LegendsOfValourHD.s`, applied in
  `_patchgame` after the PowerPacker stub has loaded the 17 hunks. No game bytes in git.
- Every change is **gated by a CUSTOM bit** declared in `slv_config`. With the bit off, the
  original bytes must be untouched (write a checker, as Test Drive II's `check_disabled.py`).
  CUSTOM1 is taken (character creation), CUSTOM5 is the VERIFY input tape. Proposal:
  **CUSTOM2 = performance patches, one bit per item** (`C2:X:faster chunky-to-planar:0;`,
  `C2:X:...:1;` …), so each item can be A/B'd alone and the user can turn them off.
- Instruments (self-tests, pixel twins, slow-drawing delays) live in the **VERIFY build only**.
- Docs use `hN:OFFSET` / `slave+OFFSET` / `kick:` addresses, never absolute ones.
- Captures: one at a time, `JOY0=none`, in `amiga/.cap`; never touch an emulator in
  `amiga/.run` (the user's). Never `pkill fs-uae`/`gdb`.
- **No performance claim without a fixed-window measurement** (§3 below).
- Commits: author Vesa Halttunen <vesuri@jormas.com>, unsigned, `core.hooksPath=/dev/null`, **no
  Co-Authored-By lines**, one commit per coherent feature.

## 1. Where the time goes (baseline)

Fixed window: spin route (`tools/tapes/spin.txt`), large view (192 × 92 chunky pixels), turning
right, 100 fields from the tape anchor. `tools/fixed_window.sh`; reproducible (two boots
identical in every instruction, DMA slot and screenshot).

| Machine | fps | fields/frame |
|---|---|---|
| A500-eq. (68000 7 MHz, 512K chip + 1.5M slow, `tmp/prof/a500`) | 2.5 | 19.75 |
| A1200 (68EC020 14 MHz, 2M chip + 4M fast, `tmp/prof/a1200`) | 12.5 | 4.0 |

CPU busy 100% on both (no STOP). Hot code by 64-byte PC block (share of all CPU cycles; this
is more trustworthy than `lov_report.py`'s self-time names, because hunk 12 is hand-written
asm without prologues and the report files whole loops under the previous call target — e.g.
the chunky-to-planar loop appears as "h12:05288"):

| Code | What | A500-eq. | 68020 |
|---|---|---|---|
| `h12:04c00`–`04cc0` | wall column inner loops (`04c1a` and twins) | **~27%** | **~32%** |
| `h12:05500`–`05600` | chunky-to-planar (C2P) `h12:054ce`–`055e6` | **~26%** | **~30.6%** |
| `h12:05140`–`051c0` | sprite column loop `h12:05114` | ~12.6% | ~4.9% (fewer sprites in that scene) |
| `h12:03ec0`–`04680` | per-column ray setup / wall selection | ~7–8% | ~2% |
| `h12:05200`–`05240` | chunky buffer clear (`h12:051ee`) | ~2.4% | ~3.2% |
| h5 (C) | game logic, objects | ~3% self (16% incl. sprites) | ~1% self |
| VBL server + module player (`h12:06404`, chip `$020124`) + Kickstart | interrupts/OS | ~9% | ~3% |

Reproduce the histogram with the snippet in §3.3.

## 2. Facts the implementer needs

### 2.1 The frame pipeline

1. Main loop (h5) → `h12:027bc` renders the view into a **chunky buffer** (1 byte per pixel,
   row stride always **192 bytes**). Pointer at `h11:05fc2` (`-8254(a4)`), allocated once by
   `h1:022c6` (20 000 bytes via the Lattice pool allocator `h1:020d4` → `h0:00cd4` →
   `h0:00dd4`). **It is in chip RAM on both machines** (`$498B4`), even with 4 MB fast RAM.
2. `h12:05ea6` shows the frame:
   - `jsr h12:05e2a` — the **frame clock** (§2.3);
   - dispatch on the command word `h11:0601e`: 0 → `h12:054ce` (the per-frame C2P);
     1..5 → one-shot paths (`05ca6`, `05fc4`, `05edc` = BltBitMap + WaitBlit from the bitmap at
     `h11:05f2c`, `05b82`, `05a92`) used on view changes/redraws. Leave those alone at first.
3. `h12:054ce` C2P: reads `h11:05fc2` (chunky), `h12:00042..00051` (4 plane pointers, already
   offset to the view's top-left), `h12:0002e` (width in pixels), `h12:00030` (height). Source
   row step `192 - width`, destination row step `40 - width/8` (screen is 320 × 200, **4
   separate planes, 8 000 bytes apart**, not interleaved). Saves/restores d0–a6 itself; ends in
   `rts`. Large view: width 192, height 92, planes at their current bitmap bases + `$288`
   (= x 64, y 16: byte-, word- and longword-aligned, x multiple of 32).
4. **Pixel format: the colour is the HIGH nibble** (bits 7..4) of each chunky byte. The
   original takes bit 7 → plane 3 (`a4`), bit 6 → plane 2, bit 5 → plane 1, bit 4 → plane 0
   (`a1`). The low nibble is **not guaranteed zero**: wall texels are copied straight from the
   textures (`h12:04c3a`), and the sprite drawer masks with `$F0` (`h12:05184`), so the low
   nibble carries other data. A C2P must ignore it.
5. The original C2P has a shortcut: 8 equal pixels in a row (sky, floor) skip the bit
   shuffle. Its cost therefore depends on the scene; measure on the fixed window, not on paper.
   Measured: ~738 000 cycles per frame on the A500-eq. for 17 664 pixels ≈ **42 cycles/pixel**.

### 2.2 Other hot loops (disassemble with `tools/disd.py` / objdump on `tmp/unpacked/h12.bin`)

- **Wall columns** `h12:04c1a` (also `04cbe`, `04d42`: same loop, different tails). Draws a
  texture column outward from the middle: `a1` goes up, `a2` down, `a6` = texture middle,
  `d4.d6` 16.16 texture position, `d7` step, `d3` = 32 (half texture), `d2` = rows left on
  screen. Inner loop per **2 pixels** (`04c38`–`04c52`):
  `not.w d4; move.b (0,a6,d4.w),(a1); not.w d4; move.b (0,a6,d4.w),(a2); lea -192(a1),a1;
  lea 192(a2),a2; add.w d7,d6; addx.w d5,d4; cmp.w d3,d4; dbge d2` ≈ 82 cycles on a 68000
  (~41/pixel). Tails `04c96`/`04d2a` handle one-sided continuation (other texture for
  `170(a0)&3` / `>>2&$3c`).
- **Sprite columns** `h12:05114` (and a palette-remapping twin at `h12:093f0`..`09474`). Per
  column: z-test `cmp.l (a6)+,d4` against a per-column depth table (`a6` = `$252`-based); per
  pixel (`0517e`–`0518e`): `move.w (a5)+,d0` (row→texel offset table), `move.b (0,a3,d0.w),d0`,
  `and.b d6,d0` (`d6 = $F0`), `beq` (transparent), `move.b d0,(a0)`, `lea 192(a0),a0`, `dbf` ≈
  60 cycles/pixel.
- **Chunky clear** `h12:051ee`: `move.l d0,(a1)+` ×4 per `dbf`.
- **Ray setup**: hot blocks `h12:03ec0`–`04680` (called via `h12:02808`, which also has a
  `divu.w`/`mulu.w` pair at `028f8`). Not analysed yet.

### 2.3 Game time — read before changing the frame rate

`h12:05e2a` runs before every displayed frame:
- `elapsed = field counter (h11:0602e, low word of h11:0602c, incremented by the VBL server)
  − last (h12:05e28)`; **busy-waits while elapsed < 2** → frame rate capped at **25 fps**;
- if elapsed == 2 exactly, it also **waits for beam line $98** (`h12:063ce`, d0 = $9800);
- `elapsed − 2`, **capped at 10**, indexes a table at `h12:05e7a`: word 1 → `h12:0cdd6`
  (10, 12, 16, 20 … 48: a per-frame step, grows with frame time), word 2 → `h11:00df6`
  (4, 4, 3, 3, 2, 2, 1…: frames per animation phase, read by `h5:0193c`).

Consequences:
- Movement is frame-time compensated **only down to 12 fields/frame (4.2 fps)**. The A500-eq.
  runs at ~20 fields/frame, so today **the game runs slower than real time on an A500**. Making it
  faster up to 12 fields/frame changes the perceived game speed (towards the intended speed).
  Above that, the world speed should stay constant.
- Not everything is compensated: the townsman reached the player far sooner on the 68020
  (see profiling.md §6), so some AI advances per frame. W1 maps the heading to `h11:08c28`
  and finds a movement-step reader at `h12:14b78`. The townsman's world position and deeper
  AI timing remain open; the user accepted existing timing behaviour. Faster frames change
  the scene at the fixed-window anchor, which matters for §3. Evidence is in profiling §8.
- The beam wait exists because the C2P writes **straight into the displayed bitplanes**
  (single buffer). Starting at line $98 keeps the conversion out of the beam's way in the
  view area (rows 16..108 of the screen). **A faster C2P reduces tearing; do not remove the
  wait** without checking a fast CPU for tearing (Test Drive II's lesson).

### 2.3.1 Required follow-up: frame-rate-independent simulation timing

The user's acceptance of existing timing applies to W1 compatibility; it does not close
this investigation. Investigate a simulation time step independent of rendered frames,
covering movement, turning, animation, and AI. Keep the 25 fps rendering cap and beam wait
as separate constraints while investigating.

1. Complete the state map: identify the townsman's world position and AI state, every
   movement-step reader, turn increments, animation counters, and per-frame AI updates.
2. Establish intended rates from the compensated range (12 fields/frame or faster), then
   compare equal elapsed PAL-field intervals with the same field-timed input at different
   rendering rates. Compare world state, not screenshots or frame counts alone. Include
   the A500's uncompensated range and W1 off/on on both CPUs.
3. Evaluate elapsed-field scaling versus fixed simulation ticks with an accumulator.
   Preserve fractional motion, handle collisions and input consistently, and measure the
   CPU cost of catch-up ticks on the A500. Define how pauses, dialogs, loading, and long
   stalls affect elapsed time; avoid silently accumulating a backlog during a pause.
4. Document a proposed reference rate and any gameplay changes before implementing a
   separate optional slave patch. Do not repurpose the W1–W6 CUSTOM2 bits; choose its option
   when the design is concrete. Validate equal-time player/AI progression across rendering
   rates as well as performance, including the existing cap and display synchronization.

W1 keeps its existing timing behaviour. This follow-up remains required alongside the
remaining performance work; W7's layout deferral does not defer the timing investigation.

### 2.4 Slave infrastructure that exists

- `_patchgame` (`whdload/LegendsOfValourHD.s`) gets hunk 0's address; hunk N is found by
  walking the BPTR chain (W0 now fills the shared `_hunks[17]` table).
- The chain is a real AmigaDOS segment list, so `resload_PatchSeg` (`seglist = (hunk0-4)>>2`)
  can apply `PL_*` lists — check in the WHDLoad autodoc how it numbers offsets across hunks
  before relying on it; otherwise patch with `_hunks[12] + offset` by hand like `tape.s` does,
  verifying the original bytes first and aborting with `TDREASON_FAILMSG` on mismatch.
- CPU detection: W0 reads `WHDLTAG_ATTNFLAGS_GET` via `resload_Control` in `_bootdos`,
  test `AFF_68020`.
- Build: `make -C whdload` / `make -C whdload verify` (listing `tmp/build/LegendsOfValour.lst`
  gives slave symbol offsets; `fixed_window.sh` reads `_tape_anchor` from it).
- **Prerequisite (playbook §10), completed W0**: profiling §8 records the first-button-poll
  original/rebuilt comparison and its startup timing/pointer limitations. Repeat with
  `tools/behaviour_check.py OUT` (original), or add `--slave tmp/build/LegendsOfValour.Slave`
  after a normal build. Both explicitly disable performance patches and supply no tape.

## 3. Measurement protocol (every item)

1. Build both variants from the same source; the only difference is the CUSTOM2 bit
   (`WHD_ARGS=CUSTOM2=…` is passed through `fixed_window.sh` → `run.sh`).
2. `tools/fixed_window.sh tmp/prof/<item>-off` and `…-on` with `WHD_ARGS="CUSTOM2=<bits>"`, on
   the A500-eq. **and** the A1200 configuration (commands in profiling.md §7). One at a time.
3. Per window: `frames.py` (fps), `lov_report.py` (inclusive per call: compare **cycles per
   call** of the changed routine, which is robust to scene changes), and the block histogram:

   ```sh
   SLAVE=tmp/prof/X/slave.slave python3 - <<'EOF'
   import sys, collections; sys.path.insert(0,'tools'); import barto
   from lov_report import regions
   code=open('tmp/prof/X/code.bin','rb').read(); base=0xc00000   # 0x200000 with fast RAM
   R=[(lo,hi,n) for lo,hi,n,o in regions(code,base)]
   t=barto.load('tmp/prof/X/trace.bin'); c=collections.Counter(); tot=0
   for f in t.fields:
       for pc,cost,r in t.instructions(f):
           tot+=cost
           for lo,hi,n in R:
               if pc is not None and lo<=pc<hi: c[(n,(pc-lo)&~0x3f)]+=cost; break
   for (n,o),v in c.most_common(30): print(f'{100*v/tot:5.2f}  {n}:{o:05x}')
   EOF
   ```
4. **Scene caveat.** Because game time depends on frame time (§2.3), a faster build reaches
   the anchor in a different state and renders a different scene. fps over the window is
   still the headline number, but always show `first.png`/`last.png` of both windows, and use
   cycles-per-call (C2P: per frame; walls: per column) for the routine itself. If scenes differ
   too much, add a second route that is scene-stable (e.g. stand still facing a wall).
5. **Correctness.** Pixel-exact for C2P (§4 W1 test); for drawing changes, a VERIFY "pixel
   twin": run original and new routine on copies of the same input and compare (Test Drive II
   did this), abort with `TDREASON_FAILMSG` on the first difference.
6. Record results (date, commands, fps off/on, cycles/call) in `docs/profiling.md` §8 (new).

## 4. Work items, in order

### W0. Groundwork (completed)

- Hunk table in the slave (`_hunks`), shared by `tape.s` and the patches.
- `WHDLTAG_ATTNFLAGS_GET` read in `_bootdos`.
- CUSTOM2 in `slv_config`; `check_disabled.py` that verifies, from `tmp/unpacked/AMIGA2` and a
  memory dump, that every patched range is original with CUSTOM2=0.
- §10 behaviour check of the rebuilt slave against the original (above).
- Adapt `swap_fields.py` to count `h12:05ea6` entries with read-only breakpoints (needed for
  CPUs without an instruction trace, e.g. a 68030 at 25/50 MHz; template in Test Drive II).

### W1. Replace the C2P with Kalms' (completed)

**Source.** Mikael Kalms' public-domain collection, shared checkout
`~/.local/share/amiga/kalms-c2p` (upstream https://github.com/Kalmalyzer/kalms-c2p, commit
`d8ecf79a3325615305dd800ae7704b518e0d9dda`, same as Alone in the Dark's). **Vendor** the files
you use into `whdload/kalms/` with a README naming the commit, the file, and every local change
(as Alone in the Dark's `src/platform/amiga/kalms/README.md` does); the build must not
depend on the shared checkout. Everything outside `others/` is public domain.

**Which routines** (4 bitplanes = 16 colours, 1×1):
- **68000/68010: `bitmap/c2p1x1_4_c5_bm_word.s`** (2022, "word writes to chipmem, good for
  OCS/ECS"): only 68000 instructions, 100% PC-relative, handles a destination modulo via a
  `BitMap` (`bm_BytesPerRow`, `bm_Planes`, `bm_Depth`) plus x/y offset. Restrictions: chunky
  width a multiple of 32, x offset a multiple of 8, and word-aligned source/destination.
- **68020+: `bitmap/c2p1x1_4_c5_bm.s`** (2016): same interface, longword writes (32-bit chip
  bus on AGA). Same restrictions, longword alignment preferred (the large view's plane
  pointers are longword aligned).
- Not suitable: `normal/c2p1x1_4_c5_gen.s` (no destination modulo — would need one call per
  row — and absolute variables, not PC-relative), `special/c2p1x1_4_c5_word.s` (uses 68020
  scaled indexing despite being "word").

**Interface glue** (a slave routine that replaces `h12:054ce` with `PL_P`-style `jmp`; it must
save/restore d0–a6 like the original and `rts`):
- Build a `BitMap` in slave memory: `bm_BytesPerRow` = 40, `bm_Rows` = 200, `bm_Depth` = 4,
  `bm_Planes[0..3]` = `h12:00042..00051` (already at the view origin), offsx = offsy = 0;
  `d0` = width (`h12:0002e`), `d1` = height (`h12:00030`), `a0` = `h11:05fc2`. Re-read the
  pointers every frame (they change with the view size and on screen rebuilds).
- **Source stride.** Kalms assumes chunky rows of exactly `chunkyx` bytes. The game's stride
  is always 192. Large view: width 192 = stride → direct. Smaller views: add a **source
  modulo** to Kalms' modulo path (one `add` to `a0` per row in the outer loop; document it in
  the vendored README), or call once per row (chunkyy = 1, advance a0 by 192 and the plane
  pointers by 40; ~92 calls of overhead per frame).
- **High nibble.** Kalms reads the colour from the low nibble: the first merge is
  `and.l #$0f0f0f0f` on four longwords, then `lsl.l #4` on two and `or`. For this game change
  it to `and.l #$f0f0f0f0` on all four and `lsr.l #4` on the **other** two (the ones Kalms
  does not shift), then `or` into the unshifted ones, so the intermediate layout (first pixel
  of each pair in the high nibble) is unchanged — same cycle count in the word routine.
  The longword routine actually lacks upstream masks, so explicit masks add instructions (see the vendor README). Do this in both the
  prologue copy and the loop copy of the merge, in both routines, and document it in the
  vendored README. Verify bit/plane order with the pixel test, not by reasoning.
- **Sizes: convert a little extra rather than exactly** (user decision, 2026-10-05). The
  large view is 192 wide (= 6 × 32) at x 64 and meets every restriction as is. The medium and
  small views are narrower and not multiples of 32 (verified: medium 112 × 64 at
  104,30; small 80 × 48 at 120,38). For those, convert an **enclosing window**:
  width rounded up to the next
  multiple of 32 (80 → 96, 112 → 128), left edge at a multiple of 16 (word writes on the
  68000; a multiple of 32 is better for the 020's longword writes), containing the view.
  - **W1 correction:** the first medium conversion retains previous large-view pixels
    in the extra columns. Source padding alone failed the pixel twin. Save/restore all
    extra destination bytes, while zeroing staged source padding each frame. Geometry
    and normalized plane offsets are recorded in profiling §8. In settled views,
    the screen around the smaller views is **solid colour 0** (black) for tens of pixels on
    each side inside the frame (checked on `tmp/explore/viewcycle` screenshots: the frame's
    dither starts far outside the view). So the extra pixels are invisible **provided they
    convert to colour 0**. Confirm on the real geometry that the enclosing window stays inside
    the black area for every size.
  - The renderer does not necessarily write (or clear) chunky columns outside the view, and
    after a switch from the large view those columns hold stale pixels. So each frame,
    before converting, **zero the chunky bytes of the enclosing window that lie outside the
    view** (high nibble 0 is enough; ~16 bytes × rows, a few thousand cycles), or prove the
    game's clear `h12:051ee` already zeroes them (it may fill sky/floor colours instead).
  - Prefer extending to the **right**. If the view's left edge is not aligned and the window
    must extend left, check where the view sits in the 192-byte chunky row first (read the
    row origin the renderer uses, e.g. `a5` at `h12:04c1a` and `h12:05114`'s `4(a1)`/`6(a1)`
    arithmetic): bytes left of chunky column 0 belong to the previous row, and for row 0 they
    lie before the buffer — do not write there.
  - Read the actual width, height and plane pointers for each size from memory
    (`tools/tapes/viewcycle.txt` visits small → large → medium; dump `h12:0002e/00030/00042`
    with `lov.py gdb` at each step) and record them in `docs/profiling.md`.
- CPU choice at `_patchgame` time from the attention flags: 68020+ → `bm`, else `bm_word`.
- Kalms' init routines may compute and store values (check each file for variables written at
  run time; the slave's code hunk is writable, so PC-relative storage is fine).

**Tests.** (There is no host-side 68k test harness here; test inside the emulator.)
1. VERIFY self-test (`CUSTOM2` bit + VERIFY build): each frame, run the **original** C2P into
   a scratch 4-plane buffer (same geometry) and the new one into the screen, compare the view
   area byte for byte, `resload_Abort` with a message naming the first differing byte on any
   mismatch. Run the spin route on both CPUs for a few hundred frames, plus the viewcycle route
   (all three sizes) and a route with sprites (the townsman, the street) to exercise the
   high/low nibble.
2. A/B on the fixed window (§3), completed. Measured main-task costs are about 28.4
   cycles/pixel on 68000 and 9.6 on 020; spin fps 2.5 → 3.0 / 12.4 → 14.8, with a
   scene-stable wall A/B as well (profiling §8). The initial 15–20 cycles/pixel estimate
   for 68000 was optimistic; use the measurements, including adapter costs.

### W2. Chunky buffer in fast RAM (68020+ with fast memory)

The renderer's writes (walls, sprites, clear: ~40% of the 68020 frame) and the C2P's reads go
to **chip RAM** today. Allocating the 20 000-byte chunky buffer in fast RAM should help every
020+ machine with fast RAM.
- Find where the Lattice pool gets its memory (`h0:00dd4` takes from the free list
  `-8912(a4)`; follow the refill path to the `AllocMem` and its flags — Lattice's `_MemType`
  or a literal `MEMF_CHIP`). Option A: patch the single allocation at `h1:022c6` to call
  `AllocMem(20000, MEMF_ANY)` (prefer fast) and leave the pool alone. Option B: if the pool is
  chip only because of a global flag, do **not** change the flag (other pool users need chip:
  bitmaps, audio).
- Check every user of `h11:05fc2` (`h12:02816`, `051a8`, `054d4`, `05606`, `05704`, `05a98`,
  `05b88`, `05cac`, `09404`, `0948c`; `h1:02760` frees it; `h2:026c6`, `h5:0026a`,
  `h5:00412`, `h9:00024`) for blitter or DMA use (any `BltBitMap`/`BltClear`/custom-register
  access on it would break with fast memory). Freed with the matching size at exit
  (`h1:02760`): the replacement must free with `FreeMem` too.
- A500-eq.: no fast RAM (the 1.5 MB slow RAM is chip-bus memory) → no change; keep it gated.

### W3. Wall column loop (`h12:04c1a` family)

~27–32% of the frame. Ideas, cheapest first (measure each):
1. **Drop the two `not.w d4`** per step: keep a second texture pointer to a mirrored copy, or
   index the upper half with the negated position maintained by its own `sub`/`subx` (costs
   the same as the `not`s) — better: store each texture's upper half reversed once at load
   time so both halves use `(a6,d4.w)` and `(a3,d4.w)`.
2. **Precompute the iteration count** (rows until the texture edge `d4 ≥ 32`, min rows left on
   screen `d2`) once per column (one `divu` or a table on scale), then use a plain `dbf` and
   remove `cmp.w d3,d4`/`dbge`.
3. **Unroll with fixed displacements** and jump into the unrolled block (Duff): writes become
   `move.b (a6,d4.w),k*-192(a1)` / `k*192(a1)`, removing both `lea`s per step. Max half height
   is ~46 rows (92/2), so one 46-step block per tail.
   Together (1–3) roughly halve the loop (*estimate*: ~82 → ~44 cycles per 2 pixels on a 68000).
4. 68020+: the same, plus `move.b (a6,d4.w*1)` addressing gives nothing new; but it can keep
   fixed-point in one 32-bit register (`add.l d7,d6; swap` style tricks) to drop `addx`.
5. The tails `04c96` / `04d2a` (one-sided, other texture) get the same treatment.
Correctness: pixel twin against the original loop on the same column inputs (VERIFY).

### W4. Sprite columns (`h12:05114`, twin `h12:093f0`)

Up to ~13% on the A500 when people/pillars are in view (scene dependent: make a route that
looks at the townsman or a street with pillars, `tools/tapes/street.txt` as a start).
1. Same unroll/count tricks as W3 (the `lea 192(a0),a0` + `dbf` per pixel).
2. The `move.w (a5)+,d0` row→texel table read per pixel can become a 16.16 step like the walls
   (if the table is linear — check how it is built) or stay but unrolled.
3. Transparent runs: precompute per sprite column the first/last opaque texel and clip the
   loop to it (cheap, big win for narrow figures), or RLE the columns at load time.

### W5. Ray setup (`h12:03ec0`–`04680`, `h12:02808`)

~7–8% A500. Analyse first: find the per-column `divu`/`mulu` (one at `h12:028f8`) and other
per-column divides; replace by reciprocal tables or incremental stepping. Lower priority.

### W6. Chunky clear (`h12:051ee`)

~2.4–3.2%. Replace `move.l d0,(a1)+` ×4 with `movem.l d0-d7/a2-a6,-(a1)` blocks (~2× faster on
68000; check what colours are written — sky gradient rows vs floor) or skip rows fully covered
by walls. Small but easy; good warm-up for the patch framework.

### W7. Later / only with measurements

- Chunky-buffer layout tricks (e.g. column-major chunky so wall/sprite columns write
  sequential bytes) would speed W3/W4 a lot but require a matching C2P (Kalms can't be used
  as-is). Only if W1–W4 leave the renderer dominant.
- Interrupt side: the module player in chip RAM (`$020124`, ~2–3% A500) — leave.
- 25 fps cap and the beam wait in `h12:05e2a`: game design; only revisit with the user.
- 68030/040/060: run `SWAP_ONLY` windows after W0 adapts `swap_fields.py`; Kalms' bm routine
  is fine there too.

## 5. Expected outcome (W1 measured; remaining items are estimates)

W1 measured: C2P cycles/call −33% / −52% (68000 / 020), spin fps 2.5 → 3.0 /
12.4 → 14.8. Fixed-wall results confirm the savings at a matching scene.

Remaining estimates: walls −~12% of the original A500 frame (W3), sprites −~5% (W4).
Re-measure their share after each change, because scene and frame timing affect it.
On the 68020, W2 should move further towards the 2-field / 25 fps cap; quantify it with
the same paired measurement protocol.

## 6. Decisions for the user (ask, don't assume)

1. Decided: CUSTOM2 bits 0–5 map to W1–W6. Enable each completed, verified patch in local prefs.
2. Decided: accept existing game-time behaviour for W1, including changes below 4.2 fps.
   Investigate frame-rate-independent simulation timing as required follow-up (§2.3.1).
   W1 keeps movement/AI timing, the 25 fps cap, and beam wait intact.
3. ~~Medium/small views~~: decided — convert an enclosing 32-pixel-multiple window (W1).
4. Decided: defer W7 beyond W0/W1.
