# Gunship 3D out-of-window view: static analysis of the +060A8 subtree

This is static analysis of the gamemule hunk 0 dump `tmp/prof/flight1-mem` together with the A500 profile
(`a500_*.txt`, 500 fields, 142101 cycles/field, about 10 fields per frame). All code locations are
hunk-0 offsets `+xxxxx`. `D+xxxxx` means gamemule data hunk 6. Some variables sit in other small gamemule
hunks; those are named by role:
- `PEN`: the byte that holds the current 5-bit colour, in the BSS hunk below hunk 0.
- `CLIP_XMAX/YMAX/XMIN, ORG_X/ORG_Y`: words 319/89/0/0/0, in the small hunk just before hunk 6.
- `SINTAB`: a word sine table in the small hunk after hunk 0.

The register block a5 points to globals in hunk 6. `6..12(a5)` hold the current segment `x1,y1,x2,y2`.
Anything marked **(guess)** is inference that the code does not prove.

Frame stats derived from calls/field × 10 (one frame ≈ 10 fields on the 68000):
- about 18 shapes drawn per frame,
- about 112 vertices projected,
- about 58 clipped lines,
- about 12 filled polygons,
- about 2 single-pixel objects,
- about 300 blits per frame. This matches the 30.4 BLIT interrupts/field in the profile.

## 1. Routine table

| offset | name (mine) | role | incl % | self % | calls/field | ≈cycles/call (incl) |
|---|---|---|---|---|---|---|
| +060A8 | `Draw3DWorld` | Walks the 3×3 terrain cells around the helicopter in two passes, plus one special object | 42.02 (+0.85 other root) | 0.39 | 0.1 | 600k per frame |
| +0625C | `DrawCellObjects` | Loops over a cell's object list: table transform of the position, frustum/depth cull, LOD pick, dispatch | 41.40 | 2.27 | 1.4 (loops internally per object) | – |
| +06372 | (inside +0625C) | Point-object path: projects one point and plots one pixel | – | – | – | – |
| +063DC | `DrawShape` | Per shape: transform+project vertices, backface test, edge clip cache, then executes the primitive list (lines / filled polys) | 39.13 | 5.21 | 1.8 | ~31k |
| +06642 | `XformVertex` | Vertex = palette vertex (+ optional 2nd palette vertex) + object translation, by table adds only. Falls into +066E8 | 7.47 | 2.28 | 11.2 | ~950 (incl. projection) |
| +066E8 | `Project` | Perspective divide (2× `divs`), roll shear (2× `muls`), aspect /2, screen centre, saturate | (in 06642) | 5.23 | – (fall-through + 2 callers) | ~660 |
| +06792 | `NearClipEdge` | Clips an edge against the near plane z=32 (`divu` + 2× `muls`), then reprojects via +066E8 | 0.19 | – | 0.2 | ~1.3k |
| +06818 | `BackfaceFlags` | Builds the eye vector in object space (`SINTAB`, 4 `muls`). Per face: 3 `muls` dot product compared with d → visible flag byte in +0778A[] | 0.38 | 0.39 | 1.8 | ~300 |
| +08208 | `SetPenFromTable` | `PEN = D+016DC[colour (+256 if D+03B9E)]`. Palette indirection, an alternate set (guess: night/IR) | 0.51 | 0.19+0.34 (+08214) | 7.2 | ~100 |
| +08228 / +0828A | `PlotPixel` | Adds the origin, then CPU `bset`/`bclr` on every plane (depth=5 from BitMap) in chip RAM | 0.81 (+0.30 cockpit) | 0.82 | 2.2 | ~530 |
| +082B6 | `PixelAddr` | `mulu BytesPerRow`, byte offset, bit number, plane loop count from the BitMap (D+047C4) | 0.24 | 0.34 | 2.2 | ~220 |
| +08538 | `DrawLineClipped` | `ClipLine` (+082EC), then `AddOrigin` (+08238), then falls into `BlitLine` | 11.77 | 0.20 | 5.8 | ~2.9k |
| +08548 | `BlitLine` | Blitter line mode, one blit per plane (4), set/clear minterm chosen per colour bit | (in 08538) | 11.75 | ~5.8 (+0.4 cockpit) | ~2.7k |
| +082EC | `ClipLine` | Cohen–Sutherland against 0..319 × 0..89, `muls`+`divs` per clipped end | 2.72 | 1.57 | 5.8 | ~670 |
| +08466 | `OutCode` | 4-bit outcode | 1.20+0.75 | 2.01 | 18.9 | ~150 |
| +08238 | `AddOrigin` | Adds ORG_X/ORG_Y (both 0 here) to both segment ends | 0.26 | 0.21 | 3.8 | ~100 |
| +08818 | `PolyBegin` | CPU-clears the 200-row span table (+08D88), then a blitter clear of the previous polygon's mask bbox (+08842) | 2.64 | 2.30 (+0.65 at +08842, another entry) | 1.2 | ~3.1k |
| +08698 | `PolyEdge` | Clips a polygon edge (same C–S code as +082EC). Off-screen left/right parts become vertical boundary spans (+08928). Tail-jumps to +089E4 | 4.81 | 1.17 | 3.6 | ~1.9k |
| +089E4 | `EdgeToSpans` | Bresenham walk storing min x / max x per scanline in +08D88[y] (4 bytes/row), updates the bbox | (in 08698) | 2.51 | – | – |
| +08928 / +089CA | `VertSpan` | Writes the boundary x into rows y0..y1 (4× unrolled) | 0.22 | 0.41 | 0.8 | – |
| +08B6C | `PolyFill` | CPU fills spans into a 1-plane **chip** mask, then 4 blits (mask → each plane, OR or AND-NOT), then waits for the last blit | 6.20 | 5.01 | 1.2 | ~7.3k |
| +077B8 | `DrawHorizon` (outside the subtree) | Sky band + ground band (+0921C), banked horizon wedge polygon, horizon line, plus cockpit-area rect fills (+090DA) | 8.49 | – | 0.1 | 120k per frame |
| +0921C | `BandFill` | Blitter D-only fill of full 320-px rows, all 5 planes, value $00/$FF per colour bit | 5.61 | 9.13* | 0.2 | ~40k |
| +090DA | `RectFill` | Blitter rectangle fill with first/last-word masks, 5 planes (degenerate case → `DrawLineClipped`) | 1.30 | 1.34 | 0.2 | ~9k |

\* The self figure for +0921C includes +09274/+09336, a 4-source cookie-cut blitter copy. The cockpit
(+0AB36, +0AC6A) reaches it with `jmp`, so the profiler charges it to the preceding call target. Its spin loops
+092F6/+092FC/+0933C/+09342 add up to 2.63% and belong to the cockpit, not the 3D view.

## 2. Pipeline in execution order

0. **Per frame, before the 3D view** (outside scope, needed for context):
   - +05D62 and +05EA4 (3.0%) rotate a global *vertex palette* (D+01994, count D+01992) into three
     camera-space tables: X `+06ACA`, Y `+06D3A`, Z `+06FAA`. Each holds 156 longs of 16.16 values, stride 624 bytes.
   - All world geometry shares one orientation. Objects only translate, so the rotation cost is per palette entry
     per frame, not per object vertex.
   - +077B8 then clears and paints the view background (§2.7).

1. **`Draw3DWorld` +060A8**:
   - Pass 1: 9 cells. The cell order comes from `+05BBC[octant*9 + 8..0]`, where `+05B22` = heading octant × 9.
     - Per cell: map tile byte → object-set id → count (`D+01D0C[id]`) and list offset (`D+01D0C+34+2*id`).
     - A per-tile alive bitmask byte (`D+045E2[tile]` → `+05B03`) selects which objects in the set are drawn.
     - This pass sets `+07797`=$FF, so `+0A450` registers each drawn object as a target candidate
       (up to 5 slots at `+0AA0A`; the candidate-list role is a guess).
   - Pass 2: object table `D+01CA6`, cell order `+05B74` (the reverse of the pass-1 order), mask = all objects.
   - Then, if the special object at `62(a5)` is within Manhattan distance 96, it draws object `+05ACC`.
     A second entry, +06224, draws `+05AD2` and is called separately from the frame function.
   - There is **no per-object depth sort**. Visibility order is painter's-by-cell, using fixed cell orderings for
     each of the 8 heading octants, plus the object order inside a cell.
   - **(Guess:)** One pass runs far→near and the other near→far. I could not tell statically which pass is
     which, or why.

2. **`DrawCellObjects` +0625C**, per object (6-byte record: `posVtx, sizeClass, shapeNear.w, shapeFar.w`):
   - Translation = palette vertex `posVtx` + cell-origin palette vertex `(cell+17)`. This is 3 table adds per axis,
     with **no multiplies**. The results go to `68/72/76(a5)` (X/Y/Z, 16.16).
   - Culls:
     - Z against `[+05B0E[size], 19968)`.
     - Frustum test `|X| < (Z+r)/2` with r = `+05B04[size]`.
     - Combined `(|X|+|Y|)/4 + |Z|` distance < 19968.
   - LOD: if the distance ≥ `+05B18[size]`, the far shape word is used.
   - Shape −1 means a single dot (path +06372: `Project`, `OutCode`, `PlotPixel` with colour 38 or 1).
   - Shape −2 means the special shape `+05A24`. Anything else means shape base `94(a5)` + offset, drawn by `DrawShape`.

3. **`DrawShape` +063DC**. Shape format:
   `nVtx-1, vtx bytes…, nFace-1, face planes (4 words, word-aligned)…, colour, nEdge-1, edge recs…, prim list…, 0`.
   - a) **Vertices**: a `dbf` loop over `XformVertex` +06642.
     - A vertex byte $FF means the sum of two palette vertices (lets shapes extend the palette).
     - Camera coordinates go to `+075E6/+0763A/+0768E`, stride 84 = at most 21 vertices.
     - If Z ≥ 32.0 (`cmpi.l #$200000`), the vertex is projected (+066E8). The output is sx/sy before roll
       (`+07736/+07760`) and final screen x/y (`+076E2/+0770C`).
   - b) **`BackfaceFlags` +06818** → per-face byte flags at `+0778A`. Sets `D+03958` if all faces are hidden.
   - c) **Edge pass**: each edge record is `faceA, faceB, v1, v2`.
     - The edge is skipped unless one of its adjacent faces is visible.
     - A v1 with bit 7 set means a point primitive (z test, OutCode, plot pixel).
     - Otherwise both ends are tested against the near plane (z−32 sign). Edges fully behind are skipped.
       Edges with one end behind are clipped by `NearClipEdge` +06792.
     - The 2D endpoints are cached in `+06984/+069C0/+069FC/+06A38`, with a flag in `+06A74`
       (−1 invalid, 0 ok, 1 near-clipped). At most 30 edges.
     - Nothing is drawn in this pass.
   - d) **Primitive list** at +06504. Each byte:
     - `0` = end.
     - `0..63` = edge index, followed by a colour byte → `SetPenFromTable`, then `DrawLineClipped`.
     - bit 7 set = polygon: count is the next byte if bit 6 is set, otherwise 3; the low 6 bits are the face index
       (63 = always draw).
       - If the face is visible: `PolyBegin`, then `PolyEdge` for each cached edge. Near-clipped edges
         are collected in `+06AB2`.
       - A closing edge is added along the near plane between the first two clipped endpoints.
       - Then the colour byte → `SetPenFromTable`, then `PolyFill`.

4. **Lines**: `ClipLine` → `AddOrigin` → `BlitLine` (§3.1).
   A zero-length line goes to `PlotPixel`.

5. **Polygons**:
   - Rasterisation: `PolyEdge`/`EdgeToSpans` fill a per-scanline `[xmin,xmax]` table at +08D88.
     The table sits in hunk 0, so in fast RAM in this setup. Only convex polygons work (one span per row).
     The bbox is kept in `+090A8..+090AE`.
   - Filling, by `PolyFill`:
     1. Waits for the blitter.
     2. CPU writes each row's span into the mask plane `D+0482C` (chip RAM, 40 bytes/row): masked first word,
        `move.w #-1` run through a computed `jmp` into a 20-way unrolled store, masked last word.
     3. Records the bbox in `+08526..+0852C` so the *next* `PolyBegin` can blitter-clear exactly that area.
     4. Issues 4 blits (planes 3..0): A = mask, C = D = plane, `BLTCON0=$0B0A|$F0`
        (`$0BFA` = A|C when the colour bit is set, `$0B0A` = ¬A·C otherwise).
     5. Spins until the last blit finishes.
   - A degenerate bbox is drawn as a line.

6. **Colour**: every primitive writes all 4 planes (3D view) or 5 planes (bands/rects). A 0 bit is drawn
   with a clear minterm, so every primitive costs one blit per plane whatever its colour.

7. **Background, +077B8** (runs before +060A8):
   - Computes the horizon endpoints from the roll factor `86(a5)` and the pitch term `88(a5)`.
   - `BandFill` paints the sky rows (colour 16) and the ground rows (colour 17) across the whole 320×90 view in
     5 planes. **This is the frame clear.**
   - The banked wedge between the two horizon ends is filled with `PolyBegin`/`PolyEdge`×3/`PolyFill`.
     The horizon line (colour 18) is drawn with `DrawLineClipped`.
   - Two `RectFill` calls and a second polygon (colour 5, using `EdgeToSpans` directly) paint cockpit-area shapes at
     rows 111..196. These are unclipped (guess: instrument backgrounds).

8. **Swap** (+04496 → +00B7C): the frame is double-buffered.
   - `D+04BB0` toggles between two BitMap structs (40 bytes each, array in the BSS hunk). +084E2 selects the back one
     into `D+047C4` at frame start.
   - +00B7C spin-waits until Intuition's front screen is ours, copies the BitMap into Screen+184, then calls
     `MakeScreen` + `RethinkDisplay`. `RethinkDisplay` → `MrgCop`/`MakeVPort`/`WaitTOF`.
   - The swap costs 4.5% per frame.

**Blitter ownership**:
- The game calls `OwnBlitter`+`WaitBlit` (+0867C) and `DisownBlitter` (+0868C) only at mode changes:
  +04992..+04A32, +05622, +0A826/+0A8DC. During flight it holds the blitter and writes the custom registers
  directly (`lea $DFF000,a0`).
- No QBlit, no graphics.library drawing calls, and no semaphores appear in this subtree.

## 3. Hot loops (evidence)

### 3.1 `BlitLine` +08548: 7.4% spinning, 11.75% self in total
```
0860c  move.w d7,d0 ; add d0,d0 ; add d0,d0
08612  movea.l (8,a2,d0.w),a4      ; BitMap->Planes[d7]
08616  adda.w a3,a4                ; + y*40 + (x>>3)&~1  (mulu #40 done once at +085e4)
08618  btst d7,d1 ; beq ; ori #$f0,d2 / andi #$ff0f,d2   ; minterm $FA (set) or $0A (clear)
08626  btst #6,2(a0)               ; DMACONR BBUSY      <- 4.94% of ALL cycles
0862c  bne.s 08626                 ;                    <- 2.49%
0862e  move.l a1,80(a0)            ; BLTAPT = 4dy-2dx (error term)
08632  move.l a4,72(a0) / 84(a0)   ; BLTCPT/BLTDPT
0863a  move.w d2,64(a0) ; d6,66(a0); BLTCON0/1 (octant table +08530, LINE=1, SIGN bit 6)
08642  #$8000->BLTADAT, #$FFFF->BLTBDAT, d5->BLTAMOD, d4->BLTBMOD, 40->BLTCMOD/BLTDMOD, -1->AFWM/ALWM
0866e  move.w d3,88(a0)            ; BLTSIZE=(len+1)<<6|2
08672  dbf d7,0860c                ; 4 planes (+08524 = 3)
```
- About 4 plane blits per line. The CPU writes 15 registers per blit.
- The wait sits *before* each blit, so a line's first plane overlaps the preceding geometry/clip work.
  Planes 2–4 wait for the full length of the previous plane's blit.
- Measured: about 455 cycles of spin per plane-blit (about 64 µs).
- Hot because blitter line mode is slow per pixel, and each line is drawn 4 times (once per plane, including the
  planes where the colour bit is 0).

### 3.2 `BandFill` +0921C: 5.5% spinning
```
09240  moveq #4,d2
09242  btst #6,2(a0)       ; 3.75%
09248  bne.s 09242         ; 1.75%
0924a  move.l (a1),d0 ; add.l d1,d0 ; move.l d0,84(a0)   ; BLTDPT = Planes[d2]+y*40
09252  btst d2,d3 ; sne d0 ; ori.w #$0100,d0 ; move.w d0,64(a0) ; BLTCON0 $0100|$00/$FF (D only)
09264  clr BLTCON1, BLTDMOD ; move.w d4,88(a0)              ; BLTSIZE = rows<<6|20
0926e  dbf d2,09242
```
- A pure screen clear by blitter: 2 bands × 5 planes × up to 90 rows × 20 words per frame.
- The CPU has nothing to do meanwhile, so the whole clear time shows up as spin.
- With 5 lores bitplanes fetching, the blitter gets fewer chip-bus slots during the visible lines.

### 3.3 `PolyFill` +08B6C: 2.1% spinning, plus the CPU mask write
- `+08BD6` waits before the CPU writes into the mask plane, because the previous blit (the mask clear from
  `PolyBegin`) must finish first. This wait is not in the hot list.
- The span store runs through the computed jump at +08C46 into an unrolled run of `move.w d2,(a2)+` (+08C4A..+08C70).
  These are CPU writes to **chip RAM**.
- 4 mask→plane blits, each preceded by `+08D3E/+08D44 btst/bne` (1.59%).
- After the loop it waits again for the last blit (`+08D7A/+08D80`, 0.54%). This wait is redundant: every
  blitter user here waits before starting its own blit.

### 3.4 Projection divides in `Project` +066E8: about 2.3%
```
06704  move.l d4,d0 ; asr.l #8,d0
06708  divs.w d2,d0        ; X/Z   0.95%   (d2 = Z integer part; Z>=32 guaranteed)
0670a  bvc ; overflow -> saturate +-32277 ($7E15)
06720  move.l d3,d0 ; asr.l #8,d0
06724  divs.w d2,d0        ; Y/Z   1.00%
06742  muls.w d1,d0        ; sy*roll        (d1 = 86(a5))
06764  muls.w d1,d2        ; sx*roll
```
- Focal length is about 256 px (horizontal FOV about 64°).
- Bank is applied as a 2D shear (`x' = x + y·r`, `y' = (x·r − y)/2 + cy`), not a true rotation. The /2 is the
  aspect correction for the 90-line view.
- Screen centre is `+05AF6/+05AF8` = 160/45.
- `divs` costs about 140–158 cycles on the 68000, so 2 per vertex × 112 vertices is roughly 33k cycles per frame.

### 3.5 Span-table clear in `PolyBegin` +08818: about 2.2%
```
08826  move.l #$FFFF0000,d0      ; xmin=$FFFF, xmax=0
0882c  move.l d0,(a0)+  x8       ; each 0.21–0.25%
0883c  dbf d2,0882c              ; d2=24 -> 200 rows
```
- Every polygon clears all 200 rows, but the 3D view only uses rows 0..89 and the polygon's bbox is usually much
  smaller.
- The +08842 part then waits (`+088D8`) and starts a D-only blitter clear (`BLTCON0=$0100`) of the previous mask bbox.

### 3.6 Other measurable loops
- `OutCode` +08466: about 1.3% spread over +08468..+08496. It is a run of compares against absolute-addressed
  clip globals, called 18.9 times per field.
- `EdgeToSpans` x-major loop +08A3A..+08A5C (+08A42/+08A46/+08A4A, 0.21% each): one iteration per x pixel, not per
  scanline.
- `DrawShape`/`DrawCellObjects` bookkeeping (+063E2, +0641C, +06454, +0649E, +06362 and others, 0.12–0.16% each):
  byte-stream decoding, indexed tables, `a5` globals.
- `RectFill` spin +09198/+0919E: 1.07%.

### 3.7 Where the 42% goes (68000, approximate grouping of self cycles)

| bucket | % of all cycles | routines |
|---|---|---|
| Geometry (transform, project, cull, clip) | ≈19 | +0625C, +063DC, +06642, +066E8, +06818, +06792, +082EC, +08466 |
| CPU rasterisation (span table, mask spans, clears, pixels) | ≈9 | +08698, +089E4, +08928, +08818, +08B6C, +0828A |
| Blitter register setup | ≈5 | – |
| Blitter busy-wait inside the subtree | ≈10 | +08626, +08D3E, +08D7A, +088D8 |

Spin loops elsewhere:
- +077B8 (horizon) adds about 6.6% (+09242, +09198).
- The cockpit adds about 4.7% (+092F6 and others, +02D84).

### 3.8 Hidden cost: BLIT interrupts (supervisor)
- Graphics keeps INTENA.BLIT enabled, so **each game blit raises a level-3 interrupt** (30.4 per field):
  - The exec dispatcher at `$FC0D14` routes it to the graphics blitter handler (`$FC6DFA`, exec IntVects[6]).
  - That handler acknowledges INTREQ, finds no QBlit queue, and leaves through ExitIntr. KickEmu code near the
    WHDLoad area also runs on this exit path.
- The L3 handler's inclusive time is 19.7% of all cycles. Minus about 4.6% STOP idle, that leaves roughly
  **10–15% of all cycles**, about 500–700 cycles per blit (estimate).
- The interrupt arrives exactly when the blit ends, while the CPU sits in a BBUSY loop waiting to start the next
  blit. So the handler time adds straight to the critical path and keeps the blitter idle between blits.

## 4. Memory touched

| data | location | access |
|---|---|---|
| Vertex/translation/screen tables (+06ACA.., +075E6.., +076E2.., +06984 edge cache, +0778A face flags, +08D88 span table, bboxes) | hunk 0 (fast RAM in this setup) | CPU only |
| Shapes, object sets, map, colour table D+016DC | hunk 6 (fast) | CPU only |
| Bitplanes: 2 BitMaps, 40 B/row × 200 rows, 5 planes non-interleaved; the 3D view uses rows 0..89 of planes 0..3 | chip RAM | CPU writes only in `PlotPixel`. Otherwise blitter |
| Mask plane D+0482C (40 × 200) | chip RAM | CPU span writes + blitter clear/source |

## 5. Blocking and timing assumptions

- **BBUSY polling** with `btst #6,2(aN)` (byte read of DMACONR high byte = bit 14), before every blit:
  +08626, +088D8, +08BD6, +08D3E, +09198, +09242. There is also one after-blit wait at +08D7A.
  - No `WaitBlit`, no OwnBlitter per frame, no semaphores, and no QBlit in the render path.
  - The only other blocking points are the swap's front-screen spin (+00B86) and `WaitTOF` inside `RethinkDisplay`.
- **Agnus BBUSY quirk**: the code never does a dummy DMACONR read before polling.
  - The ROM's own blitter handler does a double `btst #6,$DFF002` for exactly this reason.
  - On a 68000 the poll comes several instructions after `BLTSIZE`.
  - On 020–060 the first `btst` after a `BLTSIZE` write can see BBUSY still clear:
    - +08D7A follows the last `BLTSIZE` of `PolyFill` almost immediately.
    - The plane loops write `BLTSIZE`, run `dbf`, then poll within a few instructions.
  - If that happens, register writes for the next blit (or `PolyFill`'s CPU mask writes after +08BD6) can hit a
    running blit, giving corrupted lines or polygons.
  - **This is a real fast-CPU hazard** (inferred from code; not observed).
- `PlotPixel` does read-modify-write on chip planes **without waiting for the blitter**. It can race a running line
  blit on the same plane and lose a pixel. This is benign but exists on every CPU.
- No CPU-speed delay loops or VBL-counted timing were found in this subtree. The renderer is purely
  work-then-swap; the frame rate follows rendering time. This analysis did not check whether game physics scales
  with frame time.

## 6. Observations for 68020–68060 + fast RAM

1. **The geometry stage (≈19%) scales well.**
   - Tables and code are already in fast RAM.
   - The vertex transform is table adds (the rotation happens once per frame in +05EA4).
   - `divs`/`muls` drop from about 150/70 cycles to tens on 020/030 and a few on 060.
   - On an 030/50 or better this stage nearly disappears.
2. **What remains is blitter- and chip-bus-bound.**
   - About 300 blits per frame are fixed work: 4 per line, 5 per polygon (including the mask clear), and
     10 for the band clears.
   - Rough estimate from the measured spin, **(guess)** of total blitter busy time per frame:
     - lines ≈ 20 ms,
     - band clears ≈ 10 ms,
     - polygons ≈ 4–5 ms,
     - cockpit blits ≈ 5–9 ms.
   - That totals roughly 35–45 ms, so even with an infinitely fast CPU the frame rate tops out around 20–25 fps.
   - Add the BLIT-interrupt latency per blit. On fast CPUs the handler runs from ROM: slow unless shadowed, and the
     exception path through KickEmu also costs.
3. **Cheap wins that keep the blitter design.**
   - Mask off INTENA.BLIT while the game owns the blitter. This removes about 10–15% on the 68000 and the per-blit
     latency everywhere. Verify that nothing else (console.device, Intuition) needs QBlit during flight.
   - Remove the redundant final wait at +08D7A.
   - Clear only the previous bbox rows of +08D88 instead of all 200.
   - Add a dummy DMACONR read before each poll, to fix the quirk in §5.
   - Skip the clear blit for planes whose colour bit is 0 *and* that are already 0 under the sky/ground. This is
     not generally valid, because primitives overlap. **(Guess.)**
4. **Bigger win on 020+: move rasterisation to the CPU and fast RAM.**
   - The 3D view is 320×90×4 planes = 14.4 KB.
   - Draw lines and spans with the CPU into a fast-RAM planar (or chunky + c2p) buffer:
     - The sky/ground clear becomes `movem`/`move16`.
     - The mask-plane trick becomes direct span fills.
     - No per-plane repetition of each line.
   - Then copy the 14.4 KB (plus plane 4 if needed) to the chip back buffer once per frame. That is about 2–4 ms
     of chip writes on an A1200/A4000.
   - This turns roughly 35–45 ms of serialized blitter time into a few ms of chip-bus time and frees the blitter
     for the cockpit.
   - Alternative: keep the blitter, but queue blits (the BLIT interrupt already exists) so the CPU never spins.
     This overlaps geometry with blitting, but the blitter time stays the floor.
5. **Double buffering exists, but the swap is heavyweight.**
   - `MakeScreen`+`RethinkDisplay` rebuild the copper lists each frame: 4.5% of all cycles on the 68000, mostly ROM.
   - `RethinkDisplay` waits for top of frame, so frames are quantised to whole fields.
   - Poking the bitplane pointers of the existing copper list (or using `ScrollVPort`/`LoadView` with
     pre-built views) would make the swap almost free.
   - Triple buffering would only help once the blitter work is asynchronous.
6. **Chip-bus contention.**
   - Five lores planes plus copper and sprites leave the blitter fewer slots during the 3D view's visible rows.
   - Fast-RAM code and data already keep the CPU off the chip bus except for `PlotPixel`, the mask spans and the
     DMACONR polls. Each poll is a chip-bus access that also steals cycles from the blitter, mildly.
   - On a fast CPU the BBUSY spin loops become tight chip-register read loops. A short delay or an
     interrupt-driven queue avoids hammering the bus.
