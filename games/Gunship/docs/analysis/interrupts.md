# Gunship: interrupts, supervisor time and how the game uses the blitter

Scope: the 26% of cycles spent in supervisor mode, and how the flight renderer uses the blitter.
Game code is given as gamemule hunk-0 offsets (`+xxxxx`, base $985CD8). ROM addresses are given as
`$FCxxxx` (KS 1.3 copy at $935000). Sources: static disassembly of `tmp/prof/flight1-mem`, plus
dynamic counts from the first 100 fields of `tmp/prof/flight1` (chunks 000-019, about 11 game
frames, A500 68000) and the same 100 fields of `tmp/prof/a1200` (68020, about 20 frames). The scripts
I used were throwaway copies outside the repository (`blits.py`, `irq.py`). Anything that is not certain is
marked **guess**.

## 1. Summary

* **The game makes no blitter-queue calls.** No QBlit (-276) or QBSBlit (-294) appears anywhere in the
  game, and it installs no BLIT interrupt of its own. Note that graphics LVO -282 is InitArea, not
  QBSBlit. On entering flight the game calls **OwnBlitter + WaitBlit** (+0867C, called from +05546,
  +049B0/+049BC, +04A32 and +0A8DC) and keeps the blitter until it leaves flight (DisownBlitter
  +0868C, called from +04992, +04A20, +05622 and +0A826). While it owns the blitter, every draw
  routine **writes the blitter registers directly**. Each one busy-waits on DMACONR BBUSY before it
  starts a blit and runs **one blit per bitplane** (5 planes, sometimes 4).
* **The ~28 BLIT interrupts per field are a side effect.** graphics.library leaves INTENA.BLIT
  enabled. The dynamic INTENAR value read at $FC0D22 is `$60EC`, which has BLIT set. So every time a
  game blit finishes, a level-3 interrupt runs: exec $FC0D14 dispatches to graphics' handler $FC6DFA,
  which finds the queue empty (`GfxBase->blthd == 0` and `BeamSync == 0`), acknowledges and returns
  through exec ExitIntr $FC0E9C and a KickEmu hook at $9FD4A2. Nothing useful is done.
  This costs about **520 cycles per BLIT entry** plus about 46 cycles of exception overhead, which
  comes to **~10% of all A500 cycles**. On the A1200 trace it is 645 cycles at 14 MHz, ~11.6%.
* The rest of the level-3 time is **one VERTB per field costing ~12,600 cycles (~8.9%)**. That is the
  game's own VERTB server +00F14 (input, music, sound effects, sprite, frame counter) plus the
  gameport.device, timer.device and graphics VBL servers. So the "~1000 cycles per level-3 entry"
  figure in CONTEXT.md is an average of two very different cases: BLIT is ~520 per entry, VERTB
  ~12,600.
* **$FC090E is exec's privilege-violation handler** (vector $20), which implements exec
  `Supervisor()`. In KS 1.3, `Wait()` reaches `Switch` through it. Its 4.9% therefore covers task
  switches, and **includes the 4.6% STOP idle**, which is the task asleep in `WaitTOF` called from
  Intuition `RethinkDisplay` during the buffer swap.
* **The task spends 20.6% of all A500 cycles spinning on BBUSY**, and **47% on the A1200**. The
  blitter is busy for 28% of the time on the A500 and 58% on the A1200. 70% of BLIT interrupts arrive
  while the task is in a BBUSY spin loop, so the blitter sits idle for the whole ~520+ cycle
  interrupt before the next blit can start. On a faster CPU the renderer is blitter-bound. Each frame
  is about 250 blits, and the blitter alone takes ~51-59 ms per frame. On top of that come the
  per-blit interrupt gaps and the wait for the next VBL. That puts the ceiling at about 3 fields per
  frame, ~16 fps, however fast the CPU is.

## 2. Exception vectors and interrupt servers (from the dump)

| vector | target | meaning |
|---|---|---|
| $20 priv. violation | $FC090E | exec Supervisor() trap (Wait->Switch->dispatch/STOP) |
| $64 L1 | $FC0C8E | TBE/DSKBLK/SOFTINT (SOFTINT = exec $FC13BC) |
| $68 L2 | $FC0CE2 | PORTS (ciaa.resource) |
| $6C L3 | $FC0D14 | COPER/VERTB/BLIT |
| $70 L4 | $FC0D6C | AUD0-3 (audio.device $FC35E4) |
| $74/$78 | $FC0DFA/$FC0E40 | L5 (RBF/DSKSYNC), L6 (EXTER) |

ExecBase IntVects: BLIT goes to code $FC6DFA with data GfxBase $976E1E. VERTB and the other server
interrupts go to exec's server-chain walker $FC1338. The VERTB server list, in priority order:

1. graphics VBL server, pri 10, code $FC6D48
2. gameport.device, pri 0, code $FE5824
3. timer.device, pri 0, code $FE935A
4. **the game, pri -60, node $980100, code +00F14**, installed through the AddIntServer stub +0EDDE

The game has no other interrupt code. The keyboard handler at +00E42..+00EE6 is an input.device
handler, so it runs in the input task, not in an interrupt.

Level-3 dispatcher, `$FC0D14`:

```
$FC0D14 movem.l d0-d1/a0-a1/a5-a6,-(sp)
        lea $dff000,a0 ; movea.l 4,a6
        move.w 28(a0),d1        ; INTENAR  (= $60EC in the trace: BLIT enabled)
        btst #14,d1 ; beq exit
        and.w 30(a0),d1         ; & INTREQR
        btst #6,d1 ; beq ...    ; BLIT first
        movem.l 156(a6),a1/a5   ; IntVects[BLIT] -> a1=GfxBase, a5=$FC6DFA
        pea -36(a6) ; jmp (a5)  ; return via ExitIntr ($FC0E9C -> jsr $9FD4A2 KickEmu, resched check, rte)
```

graphics BLIT handler, `$FC6DFA`:

```
$FC6DFA move.w #$0040,$9c(a0)   ; ack INTREQ.BLIT
        move.l 58(a1),d0        ; GfxBase->blthd
        beq $FC6F96             ; empty -> check BeamSync(162); 0 -> rts.  INTENA.BLIT NOT disabled here
        ...                     ; (queue path: call node function, unlink, cleanup; disables INTENA.BLIT only
                                ;  when the queue drains, $FC6E76 move.w #$0040,INTENA)
```

The graphics handler only clears INTENA.BLIT when a non-empty queue drains. It never touches it in
the empty-queue path. So once INTENA.BLIT has been enabled, every blit the game starts while owning
the blitter produces a useless interrupt. **Guess:** it was enabled by an earlier OS blit or by
graphics init. The trace only shows that it is set throughout flight.

## 3. The game's blit routines

All of these routines use the same pattern, shown here for the line drawer:

```
+0860C .. per-plane loop (d7 = planes-1 from +08524/$98E1FC)
+08626 btst #6,2(a0)    ; wait BBUSY   <- hottest instruction in the game, 4.9% of all cycles
+0862C bne.s +08626
+0862E move.l a1,$50(a0) ... move.w d2,$40(a0) BLTCON0 ; d6,$42 BLTCON1 (octant table +08530)
       move.w #$8000,$74 BLTADAT ; #-1,$72 BLTBDAT ; mods $64/$62/$60/$66
+0866E move.w d3,$58(a0) BLTSIZE ((len+1)<<6|2)
+08672 dbf d7,+0860C
```

None of the routines waits after its last blit, except the polygon fill at +08D7A. Every routine
waits once before each blit, using a single `btst`.

Blitter-start sites (where BLTSIZE is written) and wait loops. Sizes are from the trace.
Per frame = per 10 A500 fields.

| routine | BLTSIZE @ | wait @ | what | BLTCON0 | blits/frame | typical size (words x rows) | A500 blit time (median/mean cycles) |
|---|---|---|---|---|---|---|---|
| +08548 line (+08538 clipped entry) | +0866E | +08626 | line mode, one blit per plane, colour via minterm $FA (set) / $0A (clear) on A=$8000 | $xB0A/$xBFA, BLTCON1 LINE (no SING) | ~113 | 2 x len (len 9..320) | 714 / 1323 |
| +08842 polygon scratch clear | +088F2 | +088D8 | D-only clear of polygon bbox in 1-plane scratch $47AF0 | $0100 | ~11 | bbox | 348 / 655 |
| +08B6C/+08BA8 polygon fill | +08D72 | +08BD6, +08D3E, +08D7A | **CPU** writes spans (from table +08D88, built by +08698/+089E4/+08928) into the chip scratch plane with an unrolled `move.w d2,(a2)+` loop, then the blitter copies scratch to each plane as a mask (A=scratch, C=D=plane), then waits for the end | $0B0A/$0BFA | ~31 | bbox (1x6 .. 20x22) | 810 / 1307 |
| +0921C band fill (sky/ground) | +09268 | +09242 | D-only full-width rows, $00 or $FF per plane: background clear | $0100/$01FF | ~8 (2 bands x 5 planes, shown as ~0.9 per field) | 20 x 45..46 | **8274 / 9129** |
| +090DA rectangle | +091CE | +09198 | C/D with first/last-word masks, B = colour constant | $03CA | ~9 | 4 x 23 | 1222 / 1043 |
| +09274 masked image (cockpit) | +0932C / +09370 | +092F6 / +0933C | cookie-cut from BitMap array $97FE74 (A = mask plane, B = source, C/D = dest) / variant with constant B | $0FCA / $07CA | ~14 / ~22 | 2x86, 4x48, 20x5 / 1x20, 4x12 | 1838 / 410 (median) |
| +02C34 / +02F44 BitMap-to-BitMap blit (BltBitMap-like, with shift) | +02DB2 / +02F26 | +02D84 / +02EFA | instrument and cockpit images | per-call minterm | ~19 | 2x8, 4x48, 6x46 | 688 / 1889 |
| +03100..+03234 text | +03202 | +0319A, +031E6 | font glyph row (B=font, C/D=plane), pens $97FFE4/5, minterm table +0323E | $x7x2.. | ~19 | 1x5, 2x5 (5-row font) | 270 |

Totals, measured over the first 100 fields:

| | A500 (68000, 7 MHz) | A1200 (68020) |
|---|---|---|
| game frames | 11 (0.11/field, ~5.5 fps) | 20 (~10 fps) |
| blits per frame | ~250 | ~250 |
| BLIT interrupts per frame | ~256 (the extra ~6 are probably OS blits; **guess**) | ~256 |
| blitter busy (BLTSIZE write to BLIT interrupt) | **28.1%** of all cycles (≈51 ms per frame) | **58.4%** (≈59 ms per frame) |
| task spinning on BBUSY (sum of the wait loops above) | **20.6%** | **47.1%** |

Largest spin loops, as % of all cycles (A500 / A1200):

| wait loop | routine | A500 | A1200 |
|---|---|---|---|
| +08626/+0862C | line | 7.3% | 7.4% |
| +09242/+09248 | band | 5.3% | 19.1% |
| +08D3E/+08D44/+08D7A | polygon | 2.6% | 7.8% |
| +02D84/+02D8A | BltBitMap-like | 2.1% | 5.1% |
| +092F6/+092FC | cookie | 1.8% | 3.7% |
| +09198 | rect | 1.0% | 2.0% |

* **Chaining:** none. No blit is started from the interrupt. The CPU starts every blit itself after
  spinning. The only CPU/blitter overlap is when the CPU computes the next primitive while the last
  blit of the previous one is still running. Interrupt-to-next-BLTSIZE: median **594 cycles**, and
  the BLIT handler itself takes ~520. So for back-to-back plane blits, the blitter is idle almost
  exactly as long as the interrupt takes. Example: a typical line plane blit lasts ~714 cycles, then
  ~600 cycles pass before the next one starts.
* **Drain before swap:** nothing explicit. The frame ends with +04496 calling +00B7C. That routine
  busy-waits until `IntuitionBase->FirstScreen` is the game screen, copies the drawn BitMap
  (`$97FE74 + n*40`) into `screen->BitMap`, copies 64 bytes of colours, then calls MakeScreen and
  RethinkDisplay (+00C2C/+00C38). RethinkDisplay reaches `WaitTOF` (graphics -270) through ROM
  $FE04F4. The several thousand cycles of copper-list work plus the VBL wait mean any last blit has
  long finished before the new view is shown. That is implicit, not guaranteed.
* 3D window clip is x 0..319, y 0..89 (`$9951D8..`). Bitmaps are 320x200x5, three of them at
  $16DB0, $209F0 and $2A630 (BitMap structs at $97FE74 + n*40). The polygon scratch plane is at
  $47AF0. All of this is in chip RAM.

## 4. VERTB: what runs per field (~12,600 cycles/field on A500 = 8.9%)

The game server `+00F14`:

```
+00F14 movem.l d0-a6,$9869AC        ; save to absolute area
+00F1C lea $dff000,a0 ; move.w #$0400,d0
+00F26 btst #2,2(a0) ; beq ; bset #15,d0  ; remember BLTPRI (blitter-nasty) state
+00F38 move.w #$0400,$96(a0)        ; clear BLTPRI while the server runs
+00F3E IntuitionBase->FirstScreen == game screen? else skip
+00F52 addq.l #1,$97EE1C            ; field counter (the game's clock)
+00F60 jsr +04B48                   ; sound effects/engine, timers $9923FC-$992401, sprite anim (+045B0), music (+0127A..)
+00FA0 jsr +01068                   ; joystick: JOY1DAT $DFF00C, fire via CIA-A PRA, keys from input handler table $98693C
+00FAC restore BLTPRI ; movem.l restore ; moveq #0,d0 ; rts
```

The game never sets BLTPRI (its only DMACON writes are bitplane and sprite enables at
+00BF0..+00C1A, +035C4, +037AA and +039E8). So the BLTPRI save and restore is defensive or a leftover
(**guess**).

Approximate breakdown per VERTB entry, A500, cycles:

| part | cycles |
|---|---|
| Lattice 32x32 multiply helper +0E7AC (called through jump stub +0423C; mostly `index*40` from the music code) | 1556 |
| music channel driver +011E0..+01574 (C code, a4-relative) | ~1350 |
| server body and joystick (+00F14..+011DC) | ~1650 |
| sound effects and sprite (+04B48..+04Dxx) | ~1040 |
| gameport.device ($FE58xx/$FE5Axx) | ~1060 |
| timer.device ($FE93xx/$FE94xx) | ~850 |
| exec server chain ($FC13xx) | ~510 |
| graphics VBL ($FC6Dxx) | ~350 |
| entry/exit | ~300 |

Game code in supervisor totals ≈ 7,700 cycles/field (5.4%). That includes the part attributed to
level 4 when an audio interrupt preempts the VERTB server. On the A1200 the VERTB costs 8,581 cycles
at 14 MHz (3.0%).

The other game "supervisor" addresses listed in CONTEXT.md are all VERTB-server code:

* +0E7A0..+0E7D0 is the multiply helper.
* +00F10..+011F0 is the server, input and the start of the music driver.
* +01560..+015B0 is the music driver.
* +04230 is the jump stubs (+0423C → +0E7AC).
* +04610 is the sprite part of +045B0, which calls ChangeSprite (-420) and MoveSprite (-426) from
  the interrupt.

The other interrupts are small:

* **L4 audio** ($FC0D6C, audio.device AUD0-3 at $FC35E4): ~0.3-0.5 entries/field. Its own code is
  small. Much of its measured 1.4% is VERTB game code it preempted.
* **L1** ($FC0C8E, SOFTINT via exec $FC13BC; timer.device or input task signalling): ~0.3/field,
  ~0.3-0.5%.
* **L2 PORTS** (ciaa.resource, keyboard) and **L6** were not significant in the sample. No disk
  interrupts during flight (WHDLoad PRELOAD).
* The keyboard reaches the game through an input.device handler (+00E42..+00EE6: `ie_Code` up/down
  bit and a key table at $98693C). It runs in the input task, not in an interrupt.

## 5. $FC090E and the STOP idle

`$FC090E` is vector $20, privilege violation. It checks whether the faulting PC is exec's
`Supervisor()` stub ($FC08E6/$FC08F6) and, if so, jumps to the user routine in supervisor mode. KS
1.3 `Wait()` uses this to reach `Switch` ($FC0F1C), whose dispatcher sleeps in `stop #$2000` at
**$FC0F90** when no task is ready.

So the $FC090E time (0.5 entries/field, 4.9%) is task switching plus idle. The idle comes from the
game task waiting in RethinkDisplay → WaitTOF, about half a field per frame on average (≈5% at 10
fields/frame). The non-idle part is ~770 cycles/entry (~0.3%). Other tasks (input.device at
$FE612E/$FE619A, which issues the timer.device BeginIO calls the attribution charged to the game's
stack) also run through this path.

## 6. CPU-speed and timing dependence

1. **Single-read BBUSY waits right after BLTSIZE (fast-CPU hazard, guess based on known Agnus
   behaviour).** All 12 wait loops are a single `btst #6,2(a0)` with no dummy DMACONR read. The ROM
   (e.g. $FC6E1A/$FC6E22 in the BLIT handler, $FC5A60 WaitBlit) and the KickEmu WaitBlit patch ($9FD4EC) read twice. On a 68000
   there are always several instructions between a BLTSIZE write and the next test. On a 68030/040/060
   running from cache, the loop back (for example +08672 `dbf` to +08626) can sample BBUSY before
   Agnus has set it. The game would then overwrite the registers of a blit that is still starting, and
   lines, planes or polygons would be corrupted. This is the usual slave fix: replace each wait with
   `tst.b $dff002` followed by the loop (or a WaitBlit-style routine), for example by patching the 12
   sites listed in section 3.
2. **The spin loop slows the blitter on faster CPUs.** BLTPRI is off. The task polls DMACONR as fast
   as it can, and each poll is a chip-bus cycle the blitter has to give up. On the A1200 trace the band
   blit took ~9,700 7-MHz-equivalent cycles against ~9,100 on the A500, and total blitter-busy time per
   frame went up from ~51 ms to ~59 ms. Setting BLTPRI while owning the blitter, or polling less often,
   would help. The CPU runs from fast RAM and has nothing else to do while it waits.
3. **Interrupt per blit.** Disabling INTENA.BLIT while the game owns the blitter removes ~256
   interrupts per frame: ~10-12% CPU on 68000 and 68020. More importantly it removes a ~500-600
   cycle (7 MHz) blitter-idle gap after almost every plane blit. Each entry reads INTENAR and INTREQR
   and writes INTREQ, which are chip-bus accesses, so the cost per interrupt does not shrink much on
   fast CPUs. On the A1200 it is still ~46 µs. The flag could be restored at DisownBlitter. graphics'
   DisownBlitter ($FC64D4) re-enables it itself when the queue is non-empty. **Guess:** safe, because
   the queue is empty for the whole flight.
4. **Frame pacing.** The frame is quantised to whole fields by WaitTOF inside RethinkDisplay, with
   only two buffers. Game time is measured in fields: +04470 computes the field delta since the last
   frame (`$97EE1C - $97FF48`) and passes it to +02276, which keeps a 3-frame average scaled by 60000.
   **Guess:** the simulation is time-based, so a faster machine gives smoother play, not faster play.
   $99010C (incremented per VBL) throttles the cockpit update at +0A392 to once per ≥4 fields. +04208
   is a busy delay on the field counter (60 fields per unit), used outside flight. +08182 waits for one
   field tick next to the protection checksum code (+08140).

## 7. Implications for faster CPUs (68020-68060, fast RAM)

* On a 68000 the renderer is CPU-bound: geometry is ~42% of cycles, and the blitter is busy only 28%
  of the time. Already on the 68020 it is **blitter- and interrupt-bound**: 47% spinning plus 11.6%
  in the BLIT interrupt, against ~25% real CPU work in the task. Faster CPUs will barely raise the
  frame rate beyond ~10-16 fps unless the blitter model changes.
* Blitter time per frame (A500 numbers, ~51 ms in total):

  | blit kind | share of blitter time |
  |---|---|
  | lines | ~41% |
  | band clears | ~20% (≈8-9 blits of 920 words, about 1.3 ms each, held back by 5-plane bitplane DMA) |
  | polygons (clear + fill) | ~13% |
  | cockpit, text and image blits | the rest |

  The 5-blits-per-primitive structure multiplies setup and interrupt cost.
* Cheapest wins, in order:
  1. Mask INTENA.BLIT during flight, or patch the BLIT handler path.
  2. Fix the BBUSY waits for safety: a dummy read, or a jsr to a common wait routine.
  3. Set BLTPRI during flight, so the blitter is not slowed by the CPU's polling.
  4. Do the full-width band clears (+0921C) with the CPU (`move.l`/`movem` into chip RAM). On AGA and
     A3000/A4000 32-bit chip RAM this is ≥2x the speed of a 16-bit D-only blit and needs no
     interrupt. Alternatively, clear only the 3D window rows that need it.
* A larger change: render the 3D window (320x90x5, 18 KB) with the CPU into a fast-RAM planar (or
  chunky with c2p) buffer, then copy it to chip RAM once per frame. That removes ~200 blits per frame,
  all the spin-waiting and the per-blit interrupts. The polygon path already fills spans with the CPU
  (into chip RAM, at +08C3C), and only uses the blitter to spread the 1-plane mask over 5 planes. On a
  68040/060 a chip copy of 18 KB takes a few ms, compared with ~51 ms of blitter time now.
* Triple buffering, or swapping bitplane pointers in the VERTB server instead of MakeScreen +
  RethinkDisplay + WaitTOF, would save the ~4.5% MakeScreen/RethinkDisplay CPU cost and the average
  half-field idle wait per frame. This matters more at 3-5 fields per frame on fast CPUs.
