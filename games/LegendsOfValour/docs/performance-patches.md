# Performance patches (W1–W6)

> Read before changing game code for speed. Measurement method: `docs/profiling.md` §8.
> Game timing (developer bit 6), mouse precision (bit 7) and click inputs (bit 8):
> `docs/simulation-timing.md`, `docs/one-degree-turning.md`, `docs/click-inputs.md`.
> Release builds enable all of them, and W1–W6, with one switch, Enhanced frame rate.

## Rules for every patch

- Ships as a WHDLoad slave patch, installed by `_patchgame` (`src/LegendsOfValourHD.s`)
  after the PowerPacker stub has loaded the 17 hunks. Hunk N is `_hunks[N]` (filled from the
  segment chain); patch with `_hunks[N] + offset`, checking the original bytes first and
  aborting with `TDREASON_FAILMSG` on mismatch. Flush caches after writing. Skip all patches in
  character-creation mode (CUSTOM1). Write every game offset as an `hN_OFFSET` symbol
  (`docs/versions.md`): `_lov_version` recognises the English, German or French AMIGA2,
  applies the fixup table for German and French, and clears CUSTOM2 for any other version,
  which runs as CFou!'s v1.0 instead of failing a check.
- Exception: `_blit_install` (`src/blitwait.s`) runs in every build and every CUSTOM2,
  skipping silently on any byte mismatch. The game's graphics.library glue (h15:
  SetRast `h15:00054`, Draw `h15:0008a`, RectFill `h15:000a8`) returns while the blit runs,
  and the game then draws text with the CPU (`h1:0117c` RectFill, then the print at
  `h1:02446`; `h1:014ec`). On a 68040 the blitter wiped planes of the first glyphs: red and
  green first words, with the cut row moving between runs. CFou!'s v1.0 shows it too. Each
  glue's `jsr` becomes a `jmp` to a copy that adds `WaitBlit`. Check: break at `h1:02462` on
  `SETUP=a1200-040` and look at "Legends of Valour!" (white, no red/green).
- Hooks replace **complete instructions** only. Before choosing a range, check that no
  relocation (`tools/xref.py`) or branch targets its interior.
- Each patch has a CUSTOM2 bit. Release builds map their single switch, Enhanced frame rate
  (any nonzero CUSTOM2), to all bits 0–8 and 0 to none; developer/VERIFY builds honour each bit. With a bit off, the original bytes stay untouched: declare each hook range with a
  `PERF_RANGE hN:OFFSET LEN bit=B` comment next to it, and `tools/check_disabled.py` verifies
  every declared range against `tmp/unpacked/AMIGA2` (with relocations applied).
- CPU choice comes from `WHDLTAG_ATTNFLAGS_GET` (read in `_bootdos`). Keep the original code on
  a CPU where the replacement measures no gain.
- Instruments (pixel twins, self-tests, forced failures) live in the VERIFY build only, selected
  by CUSTOM5 bits. Flag snapshots must use legal SR reads on the 68000 and CCR reads on 68010+.
- Both normal and VERIFY builds must assemble with vasm's 68000/PIC checks.
- No change to movement/AI timing, the 25 fps cap or the beam wait here (see game time below).

## The frame pipeline

1. The main loop (h5) calls `h12:027bc` to render into a **chunky buffer**: one byte per pixel,
   row stride always **192**, pointer at `h11:05fc2` (`-8254(a4)`, A4 = h11 + `$8000`),
   20 000 bytes allocated once at `h1:022c6`.
2. **Pixel format: the colour is the HIGH nibble.** The low nibble is not zero (wall texels are
   copied straight from textures; the sprite drawer masks with `$F0`). Converters must ignore it.
3. `h12:05ea6` shows the frame: `jsr h12:05e2a` (frame clock), then dispatch on `h11:0601e`:
   0 → per-frame C2P `h12:054ce`; 1..5 → one-shot paths (`05ca6`, `05fc4`, `05edc` =
   BltBitMap + WaitBlit from `h11:05f2c`, `05b82`, `05a92`) on view changes.
4. `h12:054ce` reads `h11:05fc2`, plane pointers `h12:00042..00051` (already offset to the view
   origin; reread every call), width `h12:0002e`, height `h12:00030`. Screen 320 × 200, 4
   separate planes 8 000 bytes apart, 40-byte rows. It saves d0–a6 itself and ends in `rts`.

| View | Width × height | Origin x,y | Plane offset |
|---|---|---|---|
| Large | 192 × 92 | 64,16 | `$288` |
| Medium | 112 × 64 | 104,30 | `$4bd` |
| Small | 80 × 48 | 120,38 | `$5ff` |

**Game time.** `h12:05e2a` runs before every displayed frame: elapsed = field counter
(`h11:0602e`, low word of `h11:0602c`) − last (`h12:05e28`); it **busy-waits while elapsed < 2
(25 fps cap)**; at exactly 2 it also waits for beam line `$98` (`h12:063ce`). `elapsed − 2`,
capped at 10, indexes `h12:05e7a`: word 1 → per-frame movement step `h12:0cdd6` (10 … 48),
word 2 → frames per animation phase `h11:00df6` (read by `h5:0193c`). Movement is compensated
only down to 12 fields/frame (4.2 fps), and AI advances per rendered frame, so in the original
a faster renderer changes game speed below 4.2 fps. Bit 6 replaces this with fixed ticks. The
beam wait exists because the C2P writes straight into the displayed planes: **do not remove it**
without checking a fast CPU for tearing.

## CUSTOM2 bits

| Bit | Patch | CPUs | Source |
|---|---|---|---|
| 0 | W1 Kalms chunky-to-planar | all (routine chosen by CPU) | `c2p.s`, `kalms/` |
| 1 | W2 chunky buffer in MEMF_PUBLIC | all | `chunky.s` |
| 2 | W3 unrolled wall columns | 68000/10 | `walls.s` |
| 3 | W4 counted sprite rows | 68000/10 | `sprites.s` |
| 4 | W5 exact reciprocal cache | 68000/10 | `rays.s` |
| 5 | W6 MOVEM chunky clear | all | `clear.s` |
| 6 | frame-independent game timing (opt-in) | all | `simulation*.s` |
| 7 | one-degree mouse precision (automatic in release) | all | `turning*.s` |

VERIFY twins (`*_verify.s`, CUSTOM5 bits 1 and 4–7) may force W3–W5 bodies on either CPU.

## W1 — Kalms chunky-to-planar (bit 0)

Replaces the first ten bytes of `h12:054ce` (whole `movem` + `movea`) with a jump and two NOPs;
the adapter preserves d0–a6 and returns to the caller. Mikael Kalms' public-domain routines are
vendored in `src/kalms/` (commit `d8ecf79`; the README lists every local change):
`c2p1x1_4_c5_bm_word.s` (word writes) on 68000/10, `c2p1x1_4_c5_bm.s` (longword writes) on
68020+. Local changes: read the high nibble, source stride 192, finish each row's pipeline before
skipping to the next row.

Kalms needs widths that are multiples of 32. Large reads the game buffer directly. Medium and
small convert an **enclosing window** (x 96 width 128, x 112 width 96; plane offsets `$4bc`,
`$5fe`): the adapter copies the active pixels into a private staging buffer with eight black
pixels each side, and **saves/restores the extra destination bytes** around the conversion,
because after a view switch they still hold large-view pixels. Never read before chunky column 0.

Verify: VERIFY `CUSTOM5` bit 1 runs the relocated original into scratch planes seeded from the
screen and the replacement into the screen, compares all 40 bytes of every row in all four
planes, and aborts at the first difference; it XORs every low nibble with `$0f` first so
duplicated nibbles cannot hide a wrong merge. `SELFTEST_FRAMES=300 TAPE_OPTIONS=3` on
`c2p-views.txt`, then `c2p_check.py --require-all-views`. Measured: C2P main-task cycles per
large frame 748 288 → 502 191 (−33%, ~28 cycles/pixel) on the A500-equivalent, 356 316 →
169 955 (−52%, ~9.6 cycles/pixel) on the 68020.

## W2 — chunky buffer in PUBLIC memory (bit 1)

The original suballocates the buffer from the Lattice pool (`h1:020d4` → `h0:00cd4`/`00dd4`,
private size header; refill `h0:00d68` calls AllocMem with flags 0), which lands it in chip RAM.
W2 hooks two complete eight-byte ranges:
- `h1:022c6` (PEA/BSR → JMP/NOP): `AllocMem(20000, MEMF_PUBLIC)`, keeping the original argument
  slot and returning to `h1:022ce`; on failure, fall back to the original pool allocator and its
  error handling. The pointer is recorded as slave-owned.
- `h1:02760`: slave-owned pointers are freed with `FreeMem(pointer, 20000)`; pooled pointers take
  the original `h1:02a4a` → `h0:00f04` path. Never pass a pooled pointer to FreeMem.

Every user of `h11:05fc2` is CPU work (no DMA or blitter reads the chunky buffer):

| Site | Use |
|---|---|
| `h1:022ce`, `h1:02760` | store result / free |
| `h12:02814` | wall renderer base |
| `h12:051a6` | sky/floor clear |
| `h12:054d2`, `05604`, `05702` | C2P into screen / planar bitmap / `h11:05fae` staging |
| `h12:05a96`, `05b86`, `05caa` | one-shot column conversions (with planar blits) |
| `h12:09402`, `0948a` | palette-remapped sprites |
| `h2:026c6` | map drawing |
| `h5:0026a`, `00412` | pointer passed to the sprite drawer `h12:05114` |
| `h9:00024` | masked byte copies, stride 192 |

On the A500-equivalent Exec reports expansion slow RAM as FAST and the buffer lands there; tell
attributes from physical placement with `chunky_check.py` (ownership, TypeOfMem, region). VERIFY
`CUSTOM5` bit 2 forces the AllocMem failure path; bit 3 runs allocate/free/reallocate through
the game's dispatchers. Measured: 68020 C2P −15% cycles/call (169 973 → 144 062), sky/floor clear
−48%; no fps change on a stock 7 MHz 68000 (slow or physical fast RAM).

## W3 — wall columns (bit 2, 68000/10)

The original inner loop (`04c38`–`04c52`) draws a texture column outward from the middle, two
pixels per step: `not.w d4; move.b (0,a6,d4.w),(a1); not.w d4; move.b (0,a6,d4.w),(a2);
lea -192(a1),a1; lea 192(a2),a2; add.w d7,d6; addx.w d5,d4; cmp.w d3,d4; dbge d2`. W3 hooks the
six-byte CMP/DBGE at `h12:04c50`, `04cf4`, `04d78` (bodies `04c38`, `04cdc`, `04d60` are
identical) with sixteen pairs at fixed destination displacements. Texture indexing, NOT,
ADD/ADDX, clipping and the material tails are unchanged; every exit advances both pointers by
exactly the number of pixels drawn.

VERIFY `CUSTOM5` bit 4 copies the original body at runtime and compares the whole column, all
15 registers and X/N/Z/V/C, rotating through all three blocks. Measured on the A500 wall route:
4 275 → 3 993 cycles per column (−6.6%), renderer −4.6%. The 68020 candidate regressed (2 276 →
3 009 cycles per column), so 020+ keep the original loop.

## W4 — sprite columns (bit 3, 68000/10)

The original per pixel: `move.w (a5)+,d0` (row→texel table), `move.b (0,a3,d0.w),d0`,
`and.b d6,d0` (`$F0`), `beq` (transparent), `move.b d0,(a0)`, `lea 192(a0),a0`, `dbf`. W4 hooks
the six-byte row-table/texel loads at `h12:0517e` and the palette-remapped twins `09452`, `094e2`
with eight rows per block at fixed displacements (A0 advances 1 536 per block), one counter
update per block, and the original one-row loop as the tail. A1 is saved and restored for counter
arithmetic that preserves X; TST restores the final pixel's NZVC. Lookup, transparency, palette
mapping, clipping and z-test are unchanged.

VERIFY `CUSTOM5` bit 5 compares each body against a runtime copy (registers, flags, the whole
destination column). Measured: A500 sprite-row cost −9.0% (spin) / −7.5% (wall). The 68020
candidate changed row cost by under 1%, so 020+ keep the original.

## W5 — exact reciprocal cache (bit 4, 68000/10)

Eight ray-setup sites build a quotient with two DIVUs. W5 replaces the initial six-byte immediate
MOVE at `h12:02998`, `02de4`, `03236`, `03676`, `03ab4`, `03f0c`, `0435e`, `0479c` and resumes
eighteen bytes later. A 1 024-slot direct-mapped table of eight-byte records holds the exact Q32
quotient and the full 16-bit divisor tag (zero tag = empty); a miss runs the original arithmetic
and stores the result, divisor zero takes the original divide exception. D2 holds the quotient,
D3 the divisor; four callers swap D2/D3 around the helper. D7 and CCR differ at the hook return,
which is safe only because every continuation overwrites D7 and defines all flags with ADD before
reading them: the installer checks the skipped arithmetic and each continuation through that ADD
before writing any hook, and `tools/ray_liveness.py` checks the same against the unpacked game.
The once-per-view divide at `h12:028f8` stays original.

VERIFY `CUSTOM5` bit 6 tests all 262 140 cases (every nonzero divisor, both register orders, X
clear/set) before rendering, then compares all registers and flags after the canonical
continuation in live frames. Measured on the A500: quotient cost −1.7% (spin, 71% hits) /
−21.3% (wall, 90% hits). The 68020 candidate regressed (87 → 134 cycles per quotient), so 020+
keep the divides.

## W6 — MOVEM chunky clear (bit 5)

Replaces the six-byte half-height load at `h12:051ee` (`move.l d0,(a1)+` ×4 per `dbf` in the
original). Eleven repeated-colour registers (D2–D7/A2–A6) write 44-byte predecrement MOVEM
blocks, with exact paths for widths 192, 112 and 80 and the general sixteen-byte path for any
other width; rows still advance 192 bytes. Colours, row count, unused columns, the original
A0/A1/D1/D2/D3 and X/N/Z/V/C are preserved; the MOVEM mask excludes its own address register.

VERIFY `CUSTOM5` bit 7 runs a runtime copy of the original and compares the whole 20 000-byte
buffer, registers and flags (VERIFY alone enlarges the C2P staging buffer to 20 000 bytes for
this). Measured: clear cost −38% / −39% (A500 spin/wall), −18% / −19% (68020).

## Validation of a change

- `tools/render_validate.sh PREFIX [BITS]` — all twins on both CPUs over all three views, with a
  calibration boot and a startup breakpoint so aborts are caught (VERIFY_WAIT_RESCUE pulses EXIT
  if a W wait is stuck behind another panel). Last full run: on both CPUs every wall/sprite block,
  every clear width, 262 140 reciprocal cases and 300 large-view conversions after the anchor.
- `tools/ab_window.sh PREFIX OFF ON` + `tools/ab_summary.py PREFIX` — fps and cycles per call on
  `spin` and `wall`, both CPUs (`docs/profiling.md` §8). Results so far: `docs/profiling.md` §9.
- `tools/behaviour_check.py` — rebuilt versus original slave at the first start-screen poll.
