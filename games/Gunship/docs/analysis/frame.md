# Gunship frame anatomy (everything except the 3D view subtree +060A8)

Static analysis of `gamemule` from the flight1 dump. All code addresses are hunk-0 offsets `+xxxxx`.
Other hunks are named by number. The dump puts them at: h1 (BSS, $12C) $97FE10, h2 (data, $30) $97EE00,
h4 (data, $444) $994DA8, h5 (BSS, $A8) $97FF48 and h6 (data, $50D0) $9951F8. Hunk-6 offsets are
written `Dxxxx`, and others `hN:xxxx`. The bases come from matching the relocation tables in the
file against the dump. The C parts of the program use `a4` = hunk-6 base (small data), so for
example `5448(a4)` = `D1548`. The hand-written asm uses absolute addresses, mostly with `a5` = `D38F6`.

Cost figures come from the A500 profile (500 fields, 142101 cycles/field). RethinkDisplay runs
0.11 times per field, which gives about 55 rendered frames in the window: **about 5.5 fps, or about
1.29 M cycles (9.1 fields, about 182 ms) per frame.** 1% of all cycles is therefore about 12.9 k
cycles, or about 1.8 ms, per frame. "Calls/frame" below is calls/field × 9.1.

## 1. Big picture

```
+0563A  game tick loop (sim)            <- runs ~2.75 times/s on the A500
  ... controls -> engine/instrument targets D157D..D158C, camera target h4:0000..000B
  jsr +04288  TickRender: N rendered frames per tick, camera/instruments interpolated
  ... +07D92/+0A150/+07CB2 (conditional), +04E3C (keyboard commands; <0 = leave),
      +0937C, +0979C, +09C5C, +09F74, every 16th tick +07F80 ...   (all together < ~1%)
  bra +0563A
```

* **The renderer is almost all of the cost.** +04288 is 69.97% inclusive and +05C04 is 69.62%.
  The other gamemule task code (the sim tick) adds up to about 1–2% (the roots +09C5C 0.62% plus
  others below the 0.15% threshold). The rest is supervisor time: 26.4%, of which 4.6% is idle.
* **There is a fixed-step sim with interpolated rendering** (+04288, details in §3). With the
  shipped constants `D1548`=6 (period) and `D154A`=3 (step), **each sim tick renders 2 frames**:
  one at half-way, interpolated, and one at the new state. The interpolation covers the camera
  (x, y, alt, heading, pitch, roll), the 6 "effect" objects in table +0C6A0 and the cockpit
  instrument values D1584..D158C → h4:0036..h4:003E.
* **There is no wall-clock compensation.** The step is constant. The elapsed-VBL measurement at
  the end of +04288 (+02276) computes an average fps (×10, guess) into `d6` and then throws it
  away (dead debug code). **So game speed is tied to frame rate.**

## 2. Routine table

Incl/self = % of all cycles. Self comes from `a500_self.txt` when the routine has an entry there.
"–" = below the profile threshold (0.15% incl / 0.11% self).

| offset | name (mine) | role | incl % | self % | calls/frame |
|---|---|---|---|---|---|
| +0563A | GameTickLoop | sim tick: timers, controls → targets, call +04288, AI/weapons/commands | (window started inside it) | – | – |
| +04288 | TickRender | interpolates camera/objects/instruments, calls +05C04 1–2× per tick, fps meter | 69.97 | 0.29 | 0.5 (1/tick) |
| +04250 | TickRenderInit | acc=0, prev=target, VBL stamp (mission start) | – | – | 0 |
| +02276 | FpsMeter | elapsed-VBL → fps×10 average, result discarded | – | – | 0.5 |
| +05C04 | RenderFrame | the frame: §4 | 69.62 | <0.11 | 1 |
| +084E2 | SetDrawBitmap | RastPort D47C0.rp_BitMap = h1:0064 + 40·D4BB0 (back buffer) | – | – | 1 |
| +07A1C | Sin | 256-entry sine table h4:01C8 + linear interp, angle word → s.15 | – | – | 2 here (+ many) |
| +05F8E | SelectTerrainCells | picks 3×3 map cells (D15DC) for the view octant (heading 20(a5)), re-bases position | 0.15 | 0.15 | 1 |
| +05CBE / +05D62 | BuildAxisTables | per-axis premultiplied coordinate×rotation tables (+0721A..+07592, in code hunk) | 1.22 | 1.17 | 1 / 1–2 |
| +05EA4 | TransformGrid | 111 grid vertices (+35 derived) → view space using table sums, out to +06ACA/+06D3A/+06FAA | 3.04 | 3.04 | 1 |
| +077B8 | SkyGroundADI | 3D-view sky/ground fill + horizon line + attitude-indicator ball | 8.49 | small | 1 |
| +0921C | BlitFillRows | full-width 320-px row fill, 5 planes, D-only blit, waits between planes | 5.61 | 9.13* | 2 |
| +090DA | BlitRectFill | masked rectangle fill (BLTCON0 $03CA), 5 planes | 1.30 | 1.34 | 2 (+ADI) |
| +08538 / +08548 | Line / BlitLine | clipped line (+082EC clip), blitter line mode, one blit per plane | 1.47 under +077B8 | 11.75 (mostly 3D) | ~53 total |
| +08208 | SetPen | h5:009C = pen map D16DC[pen (+256 in alternate palette mode D3B9E)] | – | 0.19 | many |
| +060A8 | 3D view | **other agent** (lines in 4 planes, `+08524`=3) | 42.02 | | 1 |
| +0468C / +0489A | MapMFD | moving map in centre MFD: every 8 frames recompute scroll; blit when changed | 1.36 / 1.34 | – | 1 |
| +044DC / +04546 | MapMarker | player marker = hardware sprite (SimpleSprite data D4D34) | – | – | 1 |
| +06224 | RenderEffects | renders effect objects (explosions/flak, list +05AD2, mask +0BA08) via +0625C, 5 planes (guess) | <0.15 | – | 1 |
| +0AA4C | Cockpit | instrument updates (subtree below) | 8.62 | – | 1 |
| +0AC70 | DigitalReadouts | 2 numeric readouts (h4:0036, h4:0038) via +0B0A6; redraw only on change | 0.57 | – | 1 |
| +0AA80 | RestoreOverlays | 3 masked cockpit-frame blits over the 3D view + 8 dirty-counter panels | 3.05 | – | 1 |
| +0AB24 | RestoreRect | rect descriptor → +09274 | 2.39 | – | 3 |
| +0AB18 | RestoreIfDirty | if counter≠0: counter--, +0AB24 (2 frames = both buffers) | 0.63 | – | 8 (mostly no-op) |
| +09274 | BlitRestoreRect | copy rect from source bitmap N to back buffer, cookie-cut with plane M (BLTCON0 $0FCA) or straight ($07CA) | (in +0AB24/+0AC32) | ~2.6* | ~6 |
| +0AC14 / +0AC32 | EraseNeedles | restores the previous needle bounding box (per-buffer stored) from bitmap 3 | 0.58 / 0.38 | – | 1 / 3 |
| +0B4A0 | MessagePanelRestore | countdown-gated restore of panel D09A4 | – | – | 1 |
| +0AE3C | Gunsight | 4 blitter lines at view centre (160,45), colours 27/25 | 0.80 | – | 1 |
| +0ACF0 / +0AD30 | Needles | 3 needle gauges (h4:003E, h4:0036, h4:003C) as blitter lines, colour 7 | 0.74 / 0.68 | 0.23 | 1 / 3 |
| +0B740 / +0B90E | TADSScope | clear scope by blit from art (+048EA→+02C20), rotate contacts by heading, plot dots | 1.00 / 0.90 | – | 1 (if h4:01C6=0) |
| +0AC98 | ThreeStateIndicator | redraws into source bitmap 3 only on change; marks dirty | – | – | 1 |
| +0AB3C | Tapes | bar/tape restore (+04916) + marker glyphs `{`,`|` via +0B680 | 1.42 | – | 1 |
| +0ADB6 | BarGauges | 7 bar gauges (D157D..), length moves **1 px per frame** per buffer, CPU pixels | ~0.3 | – | 1 |
| +02C20 / +02C34 | BlitCopyBitmap | rectangle copy bitmap→bitmap, 5 planes, edge masks (BLTCON0 $07CA) | 2.66 | 2.66 | ~3.6 |
| +02DC2 / +02DD8 | BlitCopyMasked | same with an A-channel mask plane ($0FCA) | – | – | – |
| +048EA / +04916 | BlitStripValue | selects source y from a value (tape/drum strip) and copies via +02C20 | 0.27–0.34 | – | – |
| +02F44 | BlitText | custom Text(): glyphs → single-plane TmpRas, then 5 per-plane blits with minterms from FgPen/BgPen | 1.22 | 1.22 | ~3.6 |
| +08842 | ClearMaskBox | blitter-clears the dirty box of the shared mask plane (D4824, chip $47AF0) | – | 0.65 | per text/poly |
| +0828A | PutPixel5 | CPU bset/bclr on all 5 chip planes (pixel colour h5:009C) | 0.30 (cockpit) | 0.82 | ~20 |
| +09B9A | SpawnEffect | while VBL countdown D42F7≠0: allocate an effect slot near the player | – | – | 1 (conditional) |
| +0BE5A | AnimateEffects | advances 6 effect animation frames | – | – | 1 |
| +0A37C | Tracers | cannon tracer dots (colour 30) with +0828A, at most every 4 VBLs | – | – | 1 |
| +0BE2C | CentreMessage | glyph/panel at (160,144) via +04916 when +0C736 is set | – | – | 0–1 |
| +04496 | SwapBuffers | show the back buffer, toggle D4BB0 | 4.50 (+0.29) | – | 1 |
| +00B7C | ShowBitmap | wait FirstScreen==ours, copy BitMap+palette into Screen, MakeScreen, RethinkDisplay | 4.31 | – | 1 |
| +00C2C | → MakeScreen | intuition −378 → graphics MakeVPort (−216) | 1.65 | – | 1 |
| +00C38 | → RethinkDisplay | intuition −390 → MrgCop (−210), LoadView (−222), **WaitTOF (−270)**, FreeCprList (−564)×2 | 2.34 | – | 1 |
| +022FA | CopyMem | 40 B BitMap + 64 B palette copies | 0.24 | – | 2 |
| +00AB8 | FindCopperColour | rescans the new copper list for COLOR00/COLOR31 moves (for VBL palette pokes) | – | – | 1 |
| +09C5C / +0AF36 | (sim) / IndicatorUpdate | sim-side; +0AF36 draws a warning light into source bitmap 3 (+048EA) and sets its dirty counter to 2 | 0.62 / 0.31 | 0.20 | 0.5 |
| +00F14 | VBL server (supervisor) | VBL counter h2:001C, +04B48 (palette flash, BPLCON1 shake, sound +011E0, timers), mouse/joystick +00FC0/+01068 | ~5 total game code | | 9/frame |

`*` The self table credits some routines to the function start before them. The "+0921C 9.13%"
self row includes +09274 (hot PCs +092F6/+092FC/+0933C/+09342 = 2.63%). +0921C itself is about
5.6%: its hot PCs +09242/+09248 alone are 5.50%.

## 3. +04288 TickRender: the interpolation and pacing core

```
0433c  move.w D154A,d1        ; step (3)
04342  add.w  D154C,d1        ; acc += step
04348  move.w d1,D154C
0434e  cmp.w  D1548,d1        ; period (6)
04354  bge.w  +043F0          ; acc >= period -> commit
04358  swap d1 / clr.w d1 / divu.w D1548,d1 / lsr #1   ; frac = acc/period (s.15)
0436c..043e2  27 words: D3904[i] = prev[i] + frac*delta[i]  (camera, 6 objects)
              1 word + 7 bytes: h4:0036.. = instruments interpolated
043e6  jsr +05C04             ; render interpolated frame
043ec  bra +0433C
043f0  commit: prev += delta, D3904 = new state, instruments = new
0444a  acc -= period; if 0: jsr +05C04 (render at the tick state)
                      else acc -= step (re-added on the next tick, no render)
04470  move.l h2:001C,d0      ; VBL counter (VBL server +00F52)
04476..04486  elapsed = now - h5:0000 ; jsr +02276(elapsed)  -> result unused
0448e  clr.w +0BA0A           ; "new this tick" mask for effect objects (copied, not lerped)
```

* Period/step ratio: 6/3 = 2 frames per tick. Key code 12 (+04EF2..+04F2C) toggles `D1548`
  between 6 and 3, which gives 1 frame per tick and no interpolation, so the game runs twice as
  fast per rendered frame. I guess this is a speed or detail toggle.
* `D154A` is never written. That makes it the natural hook for adaptive stepping.

## 4. Frame sequence (+05C04)

1. `a5`=D38F6. Map base D15DC → 94(a5).
2. **+084E2**: point RastPort D47C0 at the back buffer (h1:0064 + 40·D4BB0). The pointer also goes
   to +06980 and 0(a5).
3. **+07A1C ×2**: sin(roll 24(a5)) → 86(a5), sin(pitch 22(a5)) → 88(a5).
4. **+05F8E**: choose terrain cells and re-base the camera within the cell.
5. **+05CBE → +05D62 (×1–2)**: build the premultiplied axis tables for the current heading.
6. **+05EA4**: transform the terrain grid (111+35 vertices) using only table lookups and adds.
7. **+077B8**: clear the 3D view by painting it.
   * Rows 0..y_horizon get sky pen 16 and the rest down to row h4:0432 (=89) get ground pen 17.
     Both are full-width blitter fills over all 5 planes (+0921C). The 3D view is 320×90.
   * The wedge between the two horizon end points is filled as a triangle (+08818 / +08698×3 /
     +08B6C, shared with the 3D polygon filler).
   * Then the cockpit **ADI ball** at x 59–111, y 152–196: two blitter rect fills in pens 6/5
     (+090DA) plus the tilted wedge (+089E4×3, +08B6C).
   * Finally the horizon line in pen 18 (+08538).
8. `+08524`=3 (lines touch planes 0–3 only), then **+060A8 3D view** (other agent), then `+08524`=4.
9. **+0468C → +0489A**: moving-map MFD (123,116, 71×46). The scroll is recomputed every 8 frames.
   When it changes, the map is blitted from source bitmap 2 for 2 frames (both buffers). The
   player marker is a hardware sprite (+044DC/+04546).
10. **+06224**: render the effect objects (explosions etc.) via +0625C (guess).
11. **+0AA4C cockpit**, in this order:
    1. +0AC70 digital readouts. These draw into source bitmap 3 and only when the value changes.
    2. +0AA80 masked re-blit of the cockpit frame over the 3D view: top strip (0,0,320×5), right
       strip (304,4,32×86) and ADI bezel (56,151,56×48), from bitmap 3 with plane 4 as the
       cookie-cut mask. Then 8 dirty panels.
    3. +0AC14 erase the 3 needles.
    4. +0B4A0 message panel.
    5. +0AE3C gunsight.
    6. +0ACF0 draw the 3 needles.
    7. If h4:01C6=0: +0B740 TADS scope, +0AC98, +0AB3C tapes.
    8. +0ADB6 bar gauges.
12. `[D42F7≠0]` **+09B9A** spawn an effect. **+0BE5A** animate the effects. **+0A37C** tracers.
    `[+0C736]` **+0BE2C** centre message.
13. **+04496** swap (§5).

## 5. Display organisation and double buffering

* There is one Intuition custom screen (Screen* `D47B0`, IntuitionBase `D50B4`): 320×200 lores,
  5 planes, 32 colours.
* Five 320×200×5 BitMap structs sit in h1 at h1:0064 + 40·i. All of them are in **chip RAM**, at
  40 000 bytes each, with planes 8000 bytes apart:
  * 0: planes $16DB0.., the display buffer
  * 1: $209F0.., the display buffer
  * 2: $2A630.., source art (map)
  * 3: $34270.., source art (cockpit; also the target for instrument redraws)
  * 4: $3DEB0.., source art
  * A sixth, single-plane bitmap `D4824` (all plane pointers = $47AF0) serves as the mask/TmpRas
    for text and polygon fill.
* `D4BB0` is the back-buffer index: the one being drawn, which is shown at the next swap.
* **The cockpit is not redrawn every frame.** At mission start (+05554..+05574) the full 320×200
  cockpit (bitmap 3, descriptor D0974) is copied into both display buffers. After that, each frame:
  * The 3D view (320×90) is fully repainted.
  * The cockpit frame parts that overlap the view are re-blitted with a mask.
  * Moving instruments are erased from bitmap 3 (bounding box) and redrawn, using per-buffer saved
    state (for example the needle end points are stored at +0AF8C + D4BB0).
  * Changed static indicators/readouts are drawn once into **bitmap 3**. Each has a dirty counter
    set to 2 (+0B04C..+0B05C, h5:0056/0058), so +0AB18 copies it into each display buffer on the
    next 2 frames.
* **The swap, +04496 → +00B7C(idx):**
  ```
  00b86  movea.l D50B4,a0 / movea.l 60(a0),a0 / cmpa.l D47B0,a0 / bne +00B86  ; spin until our screen is in front
  00ba0  lea h1:0064+40*idx -> Screen+184 (sc_BitMap), 40 bytes      (+022FA)
  00bc0  D484C+64*idx -> ViewPort.ColorMap->ColorTable, 64 bytes      (both palettes identical in the dump)
  00be0  jsr +00C2C  ; MakeScreen    (intuition -378 -> MakeVPort)
  00be4  jsr +00C38  ; RethinkDisplay(intuition -390 -> MrgCop, LoadView, WaitTOF, FreeCprList x2)
  00be8  bsr +00AB8  ; re-find COLOR00/COLOR31 in the new copper list
  00bf0  move.w #$8020,DMACON
  044c2  bchg #0,D4BB1 ; flip back buffer
  ```
  This rebuilds the entire copper list every frame: 4.3% ≈ 56 k cycles ≈ 8 ms per frame on the
  68000. All of that time is in ROM.
  Kick 1.3 RethinkDisplay (ROM $FDC778) calls `MrgCop; LoadView; WaitTOF; FreeCprList(old)×2`.
  The new view starts at the next VBL, and the task sleeps until then. So swaps are synchronised
  to VBL and do not tear, but **every frame ends with a wait for the next VBL**.

## 6. Frame pacing

* **There is no explicit frame limiter in the game.** It has no WaitTOF of its own, no beam reads
  (no $DFF004/$DFF006 accesses anywhere in gamemule) and no CIA timers (the only CIA access is the
  fire buttons at $BFE0FF in +010AE). It also has no dbf delay loops.
* **The only pacing is the WaitTOF inside RethinkDisplay.** The frame time therefore rounds up to
  a whole number of fields, with a hard cap of 50 fps PAL. In the profile this wait is part of the
  4.56% STOP idle (about half a field per 9-field frame).
* The VBL counter h2:001C (incremented in the VBL server +00F52) is read only by:
  * the ignored fps meter
  * the menu delay +041FC (60-VBL units, so NTSC-style seconds)
  * the fire-release wait +0817A
* **The game speed depends on CPU speed.** One sim tick = 2 rendered frames, whatever the elapsed
  time. On the A500 that is about 2.75 ticks/s. At a 50 fps cap the same code would run about
  25 ticks/s, roughly 9× faster game time.
* What is VBL-timed (and so stays at real speed):
  * the tracer cadence (+0A434, at most every 4 VBLs)
  * the effect-spawn window D42F7 (64/128 VBLs, set at +09E22/+09E48)
  * palette flashing and BPLCON1 shake
  * sound
  * stick/mouse accumulation
* What is per frame: the bar gauges move 1 px per frame, the map re-check runs every 8 frames, and
  effects spawn one per frame while D42F7≠0.

## 7. Where the non-3D time goes (hot spots)

**A. Blitter-busy spinning (CPU idle in a `btst #6,DMACONR` loop).** This is about 21% of all
cycles, and about half of it is in my scope:

| loop | routine | % |
|---|---|---|
| +09242/+09248 | +0921C sky/ground fill | 5.50 |
| +092F6/+092FC/+0933C/+09342 | +09274 cockpit restores | 2.63 |
| +02D84/+02D8A | +02C34 bitmap copies (map, scope, tapes, text) | 2.08 |
| +09198/+0919E | +090DA ADI rect | 1.07 |
| +08626/+0862C | +08548 lines (mostly 3D) | 7.43 |
| +08D3E../+08D7A.. | +08B6C spans (3D) | ~2.1 |

```
0923a  move.b h5:009C,d3 ; pen
09240  moveq #4,d2       ; 5 planes
09242  btst #6,2(a0)     ; <- 3.75%   wait BBUSY
09248  bne.s +09242      ; <- 1.75%
0924a  move.l (a1),d0 / add.l d1,d0 / move.l d0,BLTDPT
09252  btst d2,d3 / sne d0 / ori.w #$0100,d0 / move.w d0,BLTCON0   ; D only, minterm 00/FF
0925e  clr BLTCON1, BLTDMOD / move.w d4,BLTSIZE   ; rows*64+20 words
0926c  subq.w #4,a1 / dbf d2,+09242
```
The sky/ground clear writes 90 rows × 20 words × 5 planes = 9000 words per frame. It costs about
72 k CPU cycles per frame, which is consistent with D-only blits competing with 5-plane lores
display DMA. **This time is set by the blitter and will not shrink on a faster CPU.** Across the
whole frame, the blitter-busy spin is about 38 ms per frame of OCS/AGA blitter time. That puts a
floor of about 25 fps on this scene (2 fields) for any CPU, unless the blits change.

**B. Level-3 BLIT interrupts.** The game owns the blitter (OwnBlitter at +0867C, DisownBlitter at
+0868C) but leaves INTENA.BLIT on. Every finished blit raises an interrupt: about 28.7 per field,
or about 260 per frame (each line costs 4–5 of them, one per plane). Each one runs:
* the exec L3 dispatcher (ROM $FC0D14)
* the graphics blitter handler (ROM $FC6DFA: queue empty, so it just returns)
* the exec exit path (ROM $FC0E9C) and the KickEmu hook (9fd4a2)

The PC pages attributable to this ($FC0D00, $FC0E80/$FC0EC0, $FC6D..$FC6F, 9fd4xx, exception
overhead) add up to about **11% of all cycles** (estimate), or about 550 cycles per blit. Because
the CPU usually spins until the blit is done, the handler delays the start of the next blit, so
the cost goes straight onto the frame time.

**C. The swap:** MakeScreen + RethinkDisplay take 4.3% (§5), plus up to one field of WaitTOF idle.

**D. The VBL server (supervisor, once per field):** about 5% of all cycles. The 32-bit
multiply/divide in the sound code (+0E7AC lmul 1.35%), input +01068/+00FC0, the sound sequencer
+011E0, and +04B48. This is negligible on 020+.

**E. CPU-side drawing in my scope is small:**
* +05EA4 3.0% (table-sum transform, fast RAM)
* +05D62 1.2%
* +02C34/+02F44 blit setup (mulu, masks) about 1–2% beyond their waits
* +0828A pixel RMW in chip: about 20 calls per frame, each 5 × bset/bclr on chip

## 8. Observations for 68020–68060 with fast RAM

1. **Game time runs with frame rate (most important).** Gunship needs a pacing fix before it
   speeds up visibly: the sim step is per tick, and a tick is 2 frames. The engine already
   interpolates at render time, so a cheap fix would be to make the step `D154A` adaptive:
   * set it from the measured elapsed VBLs per frame (h2:001C delta, already computed at +04470)
   * keep `D1548` as the tick length in VBL units (for example the original 2×~9 fields, or a
     chosen constant)

   Faster CPUs would then get more interpolated frames per tick instead of faster game time. This
   relies on two things the accumulator logic in §3 already does: it only renders when acc<period,
   and it commits once per call. Caveat (guess): only the camera, the instruments and the 6 effect
   objects are interpolated. Other world objects would still move in tick-rate steps (check with
   the 3D-view analysis). The VBL-timed items in §6 keep their real speed either way. The per-frame
   items (1 px per frame bar gauges, effect spawning) would become faster.
2. **Blitter-wait hazard on fast CPUs.** Every wait loop does a single `btst #6,2(a0)` only 1–3
   instructions after writing BLTSIZE: +02D84, +02EFA, +030C6, +0319A, +031E6, +08626, +088D8,
   +08BD6, +08D3E, +08D7A, +09198, +09242, +092F6, +0933C. On a 68020+ (and with the original Agnus
   BBUSY latency) the first read can still show "not busy". The next blit's registers then get
   written while the blit is running, which corrupts graphics. The ROM does the usual double read
   (`btst #6,$DFF002` twice at $FC6E1A). These loops should be patched to a proper WaitBlit (the
   standard WHDLoad treatment).
3. **A blitter-bound floor of about 38 ms per frame** for this scene (§7A). Ways to raise fps
   beyond about 25:
   * Overlap CPU work with blits instead of spinning. For example, start the sky fill before the
     +05EA4/+05D62 transforms, or queue blits.
   * Skip work: the 3D view lines already use 4 planes. If nothing in the view region ever clears
     plane 4 (guess; check the polygon filler), the plane-4 sky/ground fill could be done once
     instead of every frame (−20% of +0921C).
   * Replace the 5 per-plane line blits with fewer (single-plane mask + fill-style colour blits),
     or draw the view with the CPU into fast RAM and copy it (chunky/planar), which suits an 060.
4. **Disable INTENA.BLIT while the blitter is owned** (between +0867C and +0868C, re-enable before
   DisownBlitter or any system blit). This removes about 260 interrupts per frame: about 11% on a
   68000, and still some exec/KickEmu overhead on 020+.
5. **A cheaper swap.** Build the copper list once per buffer (or poke the BPLxPT moves / COP1LC
   directly) instead of MakeScreen + MrgCop + LoadView every frame. Drop the per-frame palette copy
   (both palettes are identical in the dump) and the copper rescan +00AB8. The spin on FirstScreen
   at +00B86 burns CPU if the screen is ever pushed back.
6. **WaitTOF serialises the frame.** With fast CPUs, frame time = work + wait to the next VBL, which
   quantises to 50/25/16.7 fps. Starting the next frame into a third buffer while waiting would
   need another 40 KB of chip RAM (the 5 existing bitmaps are all used).
7. **Memory:**
   * Code, all globals and the lookup tables are in fast RAM, which suits 020+ caches.
   * Some tables and vertex buffers are written inside the code hunk (+06ACA..+07592, +07794..,
     +08524, +0C6A0, +0C736). These are data writes only. No self-modifying instructions were seen
     in the reviewed routines, so instruction cache and copyback are fine as long as code and data
     do not share a cache line that gets executed (worth confirming).
   * All drawing targets (5 bitmaps + mask plane) are in chip RAM. CPU access to them is limited to
     +0828A pixels and blitter register setup.
8. **Cheap CPU wins (small on an 060 anyway):** mulu/divu in the blit setup and the C runtime
   lmul/ldiv (+0E7AC/+0E7CC) are slow on the 68000 only.
