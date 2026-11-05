; FR0 diagnostic benchmarks (FASTRAM_PLAN.md FR0c/FR0d). Never production.
; Included only into tmp/build/fr0-bench-* sources by tools/fr0_build.py.
; Each measured routine is a separate global label; the trace analyzer charges
; cycles by owner label. FR0BenchEarly runs before the line-256 wait
; (mid-display), FR0BenchLate after it. Copy tests rotate one per frame, so
; every frame carries one copy plus all Fast-only kernels.
; Destination for copies: the current back bank (three planes at plane0 from
; the bank structure at ($226ae)); the no-draw variant never draws there.
FR0_COPY = 30720                ; 640 x 48 = 1920 x 16 bytes
FR0_ROWS = 215
FR0_PLANE = 48*FR0_ROWS         ; 10320

FR0BenchEarly:
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 lea (FR0Count.l,pc),a0
 move.l (a0),d0
 btst #0,d0                    ; early on even frames, late on odd ones
 bne.b FR0BenchOut
 bsr.w FR0CopySelect
 bra.b FR0BenchOut
FR0BenchLate:
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 lea (FR0Count.l,pc),a0
 move.l (a0),d0
 addq.l #1,(a0)
 btst #0,d0
 beq.b .kernels
 bsr.w FR0CopySelect
.kernels:
 bsr.w FR0Kernels
FR0BenchOut:
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 rts

; d0 = frame counter. Selects one of five copies by (d0 >> 1) mod 5.
FR0CopySelect:
 lsr.l #1,d0
 divul.l #5,d1:d0              ; d1 = remainder
 move.l $226ae.l,a0
 move.l (a0),d0                ; plane 0 of the back bank (Chip)
 add.l #15,d0
 andi.w #$fff0,d0
 move.l d0,a1                  ; Chip, 16-byte aligned, inside the bank
 lea (FR0Buffer.l,pc),a0
 move.l a0,d0
 add.l #15,d0
 andi.w #$fff0,d0
 move.l d0,a0                  ; Fast, 16-byte aligned
 lsl.w #1,d1
 move.w .table(pc,d1.w),d1
 jmp .table(pc,d1.w)
.table:
 dc.w FR0CopyMoveL-.table
 dc.w FR0CopyMovem-.table
 dc.w FR0CopyMove16-.table
 dc.w FR0CopyVisible-.table
 dc.w FR0ReadChip-.table

; Fast -> Chip, move.l unrolled x8 (32 bytes per iteration).
FR0CopyMoveL:
 move.w #FR0_COPY/32-1,d7
.l:
 move.l (a0)+,(a1)+
 move.l (a0)+,(a1)+
 move.l (a0)+,(a1)+
 move.l (a0)+,(a1)+
 move.l (a0)+,(a1)+
 move.l (a0)+,(a1)+
 move.l (a0)+,(a1)+
 move.l (a0)+,(a1)+
 dbra d7,.l
 rts

; Fast -> Chip, 12-register movem (48 bytes per iteration).
FR0CopyMovem:
 move.w #FR0_COPY/48-1,d7
.l:
 movem.l (a0)+,d0-d6/a2-a6
 movem.l d0-d6/a2-a6,(a1)
 lea 48(a1),a1
 dbra d7,.l
 rts

; Fast -> Chip, move16 (68040/060 only; otherwise skipped).
FR0CopyMove16:
 lea start(pc),a2
 suba.l #FF1_HOST_CODE_SIZE,a2
 move.l FF1_HOST_ATTN(a2),d0
 andi.l #$88,d0                ; AFF_68040 | AFF_68060
 beq.b .done
 move.w #FR0_COPY/64-1,d7
.l:
 dc.w $f620,$9000              ; move16 (a0)+,(a1)+
 dc.w $f620,$9000
 dc.w $f620,$9000
 dc.w $f620,$9000
 dbra d7,.l
.done:
 rts

; Fast -> Chip, displayed part only: 3 planes x 200 rows x 40 bytes at +4.
FR0CopyVisible:
 addq.l #4,a0
 addq.l #4,a1
 move.w #3*200-1,d7
.l:
 movem.l (a0)+,d0-d6/a2-a4
 movem.l d0-d6/a2-a4,(a1)
 lea 8(a0),a0
 lea 48(a1),a1
 dbra d7,.l
 rts

; Chip -> Fast (shadow resync cost), 12-register movem.
FR0ReadChip:
 exg a0,a1
 move.w #FR0_COPY/48-1,d7
.l:
 movem.l (a0)+,d0-d6/a2-a6
 movem.l d0-d6/a2-a6,(a1)
 lea 48(a1),a1
 dbra d7,.l
 rts

; ---- FR0d kernels: rough prototypes, all in the Fast buffer ----
; Order mirrors one frame: background fills, road-edge lines into the fill
; plane, the descending fill, one-row spans, then the cookie-cuts.
FR0Kernels:
 lea (FR0Buffer.l,pc),a0
 move.l a0,d0
 add.l #15,d0
 andi.w #$fff0,d0
 move.l d0,a5                  ; a5 = plane 0 of the Fast shadow
 bsr.w FR0KBackground
 bsr.w FR0KLines
 bsr.w FR0KFill
 bsr.w FR0KSpans
 bsr.w FR0KCar
 bsr.w FR0KCockpit
 rts

; Six D-only fills: 6 x (33 rows x 48 bytes x 3 planes) = 198 rows. Plane 0
; (the road fill plane) is cleared; planes 1-2 get alternating colours.
FR0KBackground:
 moveq #6-1,d6
 move.l a5,a4
.fill:
 move.l a4,a6
 moveq #3-1,d7
.plane:
 moveq #0,d0
 cmpi.w #2,d7
 beq.b .c                      ; first pass is plane 0: always clear
 btst #0,d6
 beq.b .c
 moveq #-1,d0
.c:
 move.l d0,d1
 move.l d0,d2
 move.l d0,d3
 move.l d0,d4
 move.l d0,d5
 move.l d0,a0
 move.l d0,a1
 move.l d0,a2
 move.l d0,a3
 swap d7
 move.w #33-1,d7
.row:
 movem.l d0-d5/a0-a3,(a6)       ; 40 bytes
 move.l d0,40(a6)
 move.l d0,44(a6)
 lea 48(a6),a6
 dbra d7,.row
 lea FR0_PLANE-33*48(a6),a6
 swap d7
 dbra d7,.plane
 lea 33*48(a4),a4
 dbra d6,.fill
 rts

; 50 steep road-edge lines, one dot per row (blitter ONEDOT, XOR), rows
; 97..199 of plane 0: 50 x 103 = 5150 dots.
FR0KLines:
 lea 97*48(a5),a4
 moveq #50-1,d6
 move.l #$00300000,d0          ; x = 48.0
.line:
 move.l a4,a0
 move.l d6,d1
 sub.l #25,d1
 asl.l #8,d1
 asl.l #2,d1                   ; dx = (i-25)/64 pixel per row (16.16)
 move.l d0,d4
 move.w #103-1,d7
.dot:
 move.l d4,d2
 swap d2
 move.w d2,d3
 lsr.w #3,d3
 not.b d2
 bchg d2,(a0,d3.w)
 add.l d1,d4
 lea 48(a0),a0
 dbra d7,.dot
 add.l #$00050000,d0           ; next start x, 48..300
 cmpi.l #$012c0000,d0
 blo.b .next
 move.l #$00300000,d0
.next:
 dbra d6,.line
 rts

; Descending exclusive-style fill, 24 words x 103 rows (plane 0, rows
; 97..199). Zero longs take a fast path; others do a 32-bit prefix XOR.
FR0KFill:
 lea 200*48(a5),a0             ; end of row 199
 move.w #103-1,d7
.row:
 moveq #0,d6                   ; carry (0 or -1)
 moveq #12-1,d5
.long:
 move.l -(a0),d0
 bne.b .edge
 move.l d6,(a0)
 dbra d5,.long
 dbra d7,.row
 rts
.edge:
 move.l d0,d1
 add.l d1,d1
 eor.l d1,d0
 move.l d0,d1
 lsl.l #2,d1
 eor.l d1,d0
 move.l d0,d1
 lsl.l #4,d1
 eor.l d1,d0
 move.l d0,d1
 lsl.l #8,d1
 eor.l d1,d0
 move.l d0,d1
 swap d1
 clr.w d1
 eor.l d1,d0
 eor.l d6,d0
 move.l d0,(a0)
 tst.l d0
 smi d6
 extb.l d6
 dbra d5,.long
 dbra d7,.row
 rts

; 37 one-row spans, 24 words x 3 planes each, masked edge words.
FR0KSpans:
 lea 60*48(a5),a4
 moveq #37-1,d6
.span:
 move.l a4,a0
 moveq #3-1,d5
.plane:
 moveq #0,d0
 btst d5,d6
 beq.b .c
 moveq #-1,d0
.c:
 move.w (a0),d1                ; left edge word
 and.w #$f000,d1
 move.w d0,d2
 and.w #$0fff,d2
 or.w d2,d1
 move.w d1,(a0)
 lea 2(a0),a1
 move.w d0,(a1)+               ; 22 interior words: 1 word + 10 longs + 1 word
 move.l d0,(a1)+
 move.l d0,(a1)+
 move.l d0,(a1)+
 move.l d0,(a1)+
 move.l d0,(a1)+
 move.l d0,(a1)+
 move.l d0,(a1)+
 move.l d0,(a1)+
 move.l d0,(a1)+
 move.l d0,(a1)+
 move.w d0,(a1)+
 move.w (a1),d1                ; right edge word
 and.w #$000f,d1
 move.w d0,d2
 and.w #$fff0,d2
 or.w d2,d1
 move.w d1,(a1)
 lea FR0_PLANE(a0),a0
 dbra d5,.plane
 lea 48(a4),a4
 dbra d6,.span
 rts

; Shifted cookie-cut with colour expansion merged, three planes per word:
;   D_p = (C_p & ~m) | (m & colour_p)
; d4 = words per row (incl. the shift word), d5 = rows, d3 = shift,
; a4 = mask (words), a6 = destination in plane 0, d6 = colour (3 bits).
FR0KCar:
 moveq #6,d4
 moveq #40,d5
 moveq #5,d3
 moveq #5,d6
 lea 110*48+10(a5),a6
 bra.b FR0Cookie
FR0KCockpit:
 moveq #13,d4                  ; 12 source words + shift word
 moveq #57,d5
 moveq #3,d3
 moveq #6,d6
 lea 143*48+8(a5),a6
FR0Cookie:
 lea (FR0Mask.l,pc),a4
 moveq #0,d0
 btst #0,d6
 beq.b .p0
 moveq #-1,d0
.p0:
 moveq #0,d1
 btst #1,d6
 beq.b .p1
 moveq #-1,d1
.p1:
 moveq #0,d2
 btst #2,d6
 beq.b .p2
 moveq #-1,d2
.p2:
 move.l d0,a1                  ; colour masks
 move.l d1,a2
 move.l d2,a3
 subq.w #1,d5
.row:
 move.l a6,a0
 moveq #0,d7                   ; previous mask word (high half)
 move.w d4,d6
 subq.w #1,d6
.word:
 swap d7
 move.w (a4)+,d7               ; d7 = prev:cur
 move.l d7,d1
 lsr.l d3,d1                   ; m in the low word
 move.w (a0),d2                ; D = C ^ ((C ^ colour) & m)
 move.l a1,d0
 eor.w d2,d0
 and.w d1,d0
 eor.w d0,d2
 move.w d2,(a0)
 move.w FR0_PLANE(a0),d2
 move.l a2,d0
 eor.w d2,d0
 and.w d1,d0
 eor.w d0,d2
 move.w d2,FR0_PLANE(a0)
 move.w 2*FR0_PLANE(a0),d2
 move.l a3,d0
 eor.w d2,d0
 and.w d1,d0
 eor.w d0,d2
 move.w d2,2*FR0_PLANE(a0)
 addq.l #2,a0
 dbra d6,.word
 lea 48(a6),a6
 dbra d5,.row
 rts

FR0Count: dc.l 1
