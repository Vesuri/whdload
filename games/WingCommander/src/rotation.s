; Rotated bitmaps (CD32 E:2d746): centred tables and a pinned hotspot.
;
; The native renderer rotates by shears: columns floor(i*C), rows floor(j*R),
; a horizontal shear per row floor(r*SC) and a vertical Bresenham shear over
; the columns, every table starting at phase 0 on the image's edge, and the
; image placed from the floored rotated corner. Each degree therefore moves
; the image against its centre by up to two pixels. Here each table starts at
; the phase that rounds it symmetrically about the hotspot's centre, and the
; centre handed to the native code is shifted so the hotspot lands on the
; requested pixel. The clipped path gets the phases and the origin that put
; every pixel where the unclipped draw puts it. The native code still builds
; and clips everything; the box it tests for "fully inside" is widened by two
; pixels so a draw whose phases move it a pixel takes the clipped path.
;
; Renderer context (2d746's -116(a5)): 10 scale, 16 corner quadrant, 26 C,
; 30 sin*cos, 32 tan, 34 sec-1, 40/42 corner, 44/46 direction codes,
; 60-66 visible source rectangle (clipped), 76/80 rotated C/S, 84 rows-1,
; 92/94 origin, 56 origin address, 106 reversed shear. Frame: four words,
; the extents left/up/right/down of the hotspot.

; E:2d7d6, replacing jsr E_2dc9c(ctx, scale, angle, flags); d2 = frame.
rot_setup:
        movea.l timing_game(pc),a0
        move.w  12(sp),-(sp)
        move.l  10(sp),-(sp)
        move.l  10(sp),-(sp)
        jsr     E_2dc9c(a0)
        lea     10(sp),sp
        movem.l d0-d7/a0-a3,-(sp)
        movea.l 48+4(sp),a2
        movea.l 8(a5),a3
        movea.l d2,a1
        bsr.s   rot_centre
        movem.l (sp)+,d0-d7/a0-a3
        rts

; a1 frame, a2 context, a3 destination, a5 the renderer's frame (12/14 x, y).
rot_centre:
        lea     rot_p1(pc),a0           ; native phases unless centred
        moveq   #5-1,d0
.clear:
        clr.l   (a0)+
        dbf     d0,.clear
        lea     rot_on(pc),a0
        clr.w   (a0)
        movea.l timing_game(pc),a0
        move.l  a2,-(sp)
        move.l  a3,-(sp)
        jsr     E_2e374(a0)             ; context 30-54 (idempotent)
        addq.l  #8,sp
        move.l  26(a2),d4               ; C
        ble.w   .done
        moveq   #0,d5
        move.w  10(a2),d5               ; scale
        beq.w   .done
        moveq   #0,d0
        move.w  34(a2),d0
        mulu.w  d5,d0
        lsr.l   #8,d0
        lsl.l   #8,d5
        add.l   d0,d5                   ; R = scale*sec
        lea     rot_p1(pc),a0
        move.w  (a1),d0                 ; columns: hotspot w0
        bsr.w   rot_phase
        move.l  d1,(a0)+                ; p1
        move.w  d0,d6                   ; k1
        move.l  d5,d4
        move.w  2(a1),d0                ; rows: hotspot w1
        bsr.w   rot_phase
        move.l  d1,(a0)+                ; p2
        move.w  d0,d7                   ; r_h
        move.w  2(a1),d0
        add.w   6(a1),d0
        addq.w  #1,d0
        ext.l   d0
        muls.l  d5,d0
        add.l   d1,d0
        swap    d0
        addq.w  #1,d0                   ; N
        move.w  d0,rot_n-rot_p3(a0)
        moveq   #0,d3
        move.w  30(a2),d3               ; SC
        move.w  d7,d1                   ; shear row of the hotspot
        tst.b   106(a2)
        beq.s   .forward
        move.w  d0,d1
        subq.w  #1,d1
        sub.w   d7,d1
.forward:
        ext.l   d1
        muls.l  d3,d1
        move.l  #$8000,d2
        sub.l   d1,d2
        andi.l  #$ffff,d2               ; p3
        move.l  d2,(a0)+
        add.l   d2,d1
        swap    d1
        add.w   d1,d6                   ; X_h
        moveq   #0,d4
        move.w  32(a2),d4
        cmpi.w  #-1,d4
        bne.s   .tan
        addq.l  #1,d4                   ; t
.tan:
        move.w  d6,d1
        ext.l   d1
        muls.l  d4,d1
        move.l  #$8000,d2
        sub.l   d1,d2
        andi.l  #$ffff,d2               ; p4
        move.l  d2,(a0)+
        move.l  d2,(a0)+                ; the Bresenham start of the unclipped path
        add.l   d2,d1
        swap    d1                      ; c_h
        movem.w d1/d6-d7,-(sp)          ; c_h, X_h, r_h
        moveq   #0,d6                   ; origin offsets of the reversed shear
        moveq   #0,d7
        tst.b   106(a2)
        beq.s   .adjusted
        move.w  rot_n(pc),d0
        subq.w  #1,d0
        ext.l   d0
        muls.l  d3,d0
        add.l   rot_p3(pc),d0
        swap    d0                      ; sh(0)
        move.w  d0,d1
        ext.l   d1
        muls.l  d4,d1
        add.l   rot_p4(pc),d1
        swap    d1                      ; its vertical steps
        neg.w   d0
        move.w  d1,-(sp)
        move.w  44(a2),d1
        lea     rot_step1(pc),a0
        bsr.w   rot_add
        move.w  (sp)+,d0
        neg.w   d0
        move.w  46(a2),d1
        bsr.w   rot_add
.adjusted:
        lea     rot_ox(pc),a0
        move.w  d6,(a0)+
        move.w  d7,(a0)
        move.w  (a1),d0                 ; the rotated corner (E:2de40)
        neg.w   d0
        btst    #2,17(a2)
        beq.s   .quadrant
        neg.w   d0
.quadrant:
        ext.l   d0
        move.w  2(a1),d1
        neg.w   d1
        ext.l   d1
        move.l  d0,d2
        muls.l  76(a2),d2
        move.l  d1,d3
        muls.l  80(a2),d3
        sub.l   d3,d2
        swap    d2
        add.w   d2,d6
        muls.l  80(a2),d0
        muls.l  76(a2),d1
        add.l   d1,d0
        swap    d0
        add.w   d0,d7
        lea     rot_step1(pc),a0
        move.w  4(sp),d0                ; r_h along the row direction
        move.w  46(a2),d1
        bsr.s   rot_add
        move.w  2(sp),d0                ; X_h along the column direction
        move.w  44(a2),d1
        bsr.s   rot_add
        lea     rot_step2(pc),a0
        move.w  (sp),d0                 ; c_h vertical steps
        move.w  44(a2),d1
        bsr.s   rot_add
        addq.l  #6,sp
        lea     rot_x(pc),a0
        move.w  12(a5),(a0)+
        move.w  14(a5),(a0)
        sub.w   d6,12(a5)               ; the hotspot lands on (x, y)
        sub.w   d7,14(a5)
        move.w  10(a2),d0               ; clipped-table margin: 4 + scale/256
        lsr.w   #8,d0
        addq.w  #4,d0
        lea     rot_m(pc),a0
        move.w  d0,(a0)
        lea     rot_on(pc),a0
        move.w  #1,(a0)
.done:
        rts

; d0.w hotspot index, d4 step: d1 = phase (-(2h+1)*step/2 mod 1),
; d0.w = the pixel the hotspot's centre falls on.
rot_phase:
        ext.l   d0
        add.l   d0,d0
        addq.l  #1,d0
        muls.l  d4,d0
        asr.l   #1,d0
        move.l  d0,d1
        neg.l   d1
        andi.l  #$ffff,d1
        add.l   d1,d0
        swap    d0
        subq.w  #1,d0
        rts

; (d6, d7) += d0.w * direction d1 (0-7) of table a0.
rot_add:
        lsl.w   #2,d1
        tst.w   (a0,d1.w)
        beq.s   .y
        bpl.s   .xp
        sub.w   d0,d6
        bra.s   .y
.xp:
        add.w   d0,d6
.y:
        tst.w   2(a0,d1.w)
        beq.s   .r
        bpl.s   .yp
        sub.w   d0,d7
        rts
.yp:
        add.w   d0,d7
.r:
        rts

; E:2d7fe, replacing jsr E_30722(box, clip): widen the box by two pixels.
rot_clip:
        tst.w   rot_on(pc)
        beq.s   .native
        movea.l 4(sp),a0
        subq.w  #2,(a0)
        subq.w  #2,2(a0)
        addq.w  #2,4(a0)
        addq.w  #2,6(a0)
.native:
        movea.l timing_game(pc),a0
        jmp     E_30722(a0)

; E:2d85c, replacing jsr E_2e130(dst, ctx, x, y): the clipped path's visible
; source rectangle, estimated about the requested centre, where the hotspot
; now lands, not the shifted centre handed to the native code.
rot_visible:
        tst.w   rot_on(pc)
        beq.s   .native
        move.w  rot_x(pc),12(sp)
        move.w  rot_y(pc),14(sp)
.native:
        movea.l timing_game(pc),a0
        jmp     E_2e130(a0)

; Table starts. E:2e40c and E:2e4a6 columns, E:2e434 and E:2e512 rows: each
; replaces moveq #0 and the next instruction.
rot_col_full:
        move.l  rot_p1(pc),d2
        move.l  26(a2),d3
        rts
rot_row_full:
        move.l  rot_p2(pc),d2
        move.w  34(a2),d0
        rts
rot_col_clip:
        tst.w   rot_on(pc)
        beq.s   .native
        move.l  d0,-(sp)
        move.w  rot_m(pc),d0            ; E:2e130 leaves no margin at the start
        sub.w   d0,60(a2)
        bpl.s   .rows
        clr.w   60(a2)
.rows:
        sub.w   d0,62(a2)
        bpl.s   .margin
        clr.w   62(a2)
.margin:
        move.l  (sp)+,d0
.native:
        move.l  rot_p1(pc),d4
        move.l  26(a2),d6
        rts
rot_row_clip:
        move.l  rot_p2(pc),d4
        move.w  34(a2),d0
        rts

; E:2e4d6 (move.w d0,d5; move.w (a2),d7; addq.w #1,d7) and E:2e556
; (add.w d0,d5; move.w 2(a2),d7): the clipped tables' upper clamps. The native
; end is the visible width times the raw cosine, which is one short at 0
; degrees and drops the last column or row; centred phases can also end a table
; a pixel later. The rows are clipped exactly afterwards (E:2db66), so a later
; clamp only stops cutting real columns and rows.
rot_col_end:
        move.w  d0,d5
        tst.w   rot_on(pc)
        beq.s   .native
        add.w   rot_m(pc),d5
.native:
        move.w  (a2),d7
        addq.w  #1,d7
        rts
rot_row_end:
        add.w   d0,d5
        tst.w   rot_on(pc)
        beq.s   .native
        move.w  rot_m(pc),d0            ; rows are up to 1.42 times longer
        add.w   d0,d5
        lsr.w   #1,d0
        add.w   d0,d5
.native:
        move.w  2(a2),d7
        rts

; E:2e7c4, replacing move.l #-$10000,d6: the Bresenham start.
rot_bres_start:
        move.l  rot_bres(pc),d6
        subi.l  #$10000,d6
        rts

; E:2e470, replacing clr.l -(sp); move.l a2,-(sp); jsr E_2e71e(pc) (8 bytes):
; the unclipped shear starts at p3.
rot_shear_full:
        movea.l (sp)+,a0
        move.l  rot_p3(pc),-(sp)
        tst.w   rot_on(pc)
        bne.s   .phase
        clr.l   (sp)
.phase:
        move.l  a2,-(sp)
        move.l  a0,-(sp)
        movea.l timing_game(pc),a0
        jmp     E_2e71e(a0)

; E:2e5ac, replacing andi.l #$ffff,d0: the clipped shear phase in d0, the
; Bresenham phase and the origin that match the unclipped draw.
rot_shear_clip:
        tst.w   rot_on(pc)
        bne.s   .centred
        andi.l  #$ffff,d0
        rts
.centred:
        movem.l d1-d7/a0-a1,-(sp)
        moveq   #16,d7
        moveq   #0,d1
        move.w  34(a2),d1
        move.w  62(a2),d0
        ext.l   d0
        mulu.l  d1,d0
        lsr.l   d7,d0
        add.w   62(a2),d0
        move.w  d0,d5                   ; first visible row (as E:2e498)
        moveq   #0,d1
        move.w  20(a2),d1
        move.w  60(a2),d0
        ext.l   d0
        mulu.l  d1,d0
        lsr.l   d7,d0
        move.w  d0,d4                   ; first visible column (as E:2e498)
        move.w  d5,d0
        tst.b   106(a2)
        beq.s   .forward
        move.w  rot_n(pc),d0
        sub.w   84(a2),d0
        subq.w  #1,d0
        sub.w   d5,d0                   ; N - N' - first row
.forward:
        ext.l   d0
        moveq   #0,d1
        move.w  30(a2),d1
        muls.l  d1,d0
        add.l   rot_p3(pc),d0
        move.l  d0,d3
        andi.l  #$ffff,d3               ; q
        swap    d0
        add.w   d0,d4                   ; the column offset
        moveq   #0,d1
        move.w  32(a2),d1
        cmpi.w  #-1,d1
        bne.s   .tan
        addq.l  #1,d1
.tan:
        move.w  d4,d0
        ext.l   d0
        muls.l  d1,d0
        add.l   rot_p4(pc),d0
        move.l  d0,d1
        andi.l  #$ffff,d1
        lea     rot_bres(pc),a0
        move.l  d1,(a0)
        swap    d0
        move.w  d0,d2                   ; its vertical steps
        move.w  40(a2),d6
        move.w  42(a2),d7
        add.w   rot_ox(pc),d6
        add.w   rot_oy(pc),d7
        lea     rot_step1(pc),a0
        move.w  d5,d0
        move.w  46(a2),d1
        bsr.w   rot_add
        move.w  d4,d0
        move.w  44(a2),d1
        bsr.w   rot_add
        lea     rot_step2(pc),a0
        move.w  d2,d0
        move.w  44(a2),d1
        bsr.w   rot_add
        lea     rot_fx(pc),a0
        move.w  d6,(a0)+
        move.w  d7,(a0)
        move.l  d3,d0
        movem.l (sp)+,d1-d7/a0-a1
        rts

; E:2e5c6, replacing move.l 56(sp),-(sp); jsr E_2e658(pc) (8 bytes): the
; clipped origin.
rot_origin_clip:
        movea.l (sp)+,a0
        move.l  56(sp),-(sp)
        move.l  a0,-(sp)
        tst.w   rot_on(pc)
        bne.s   .centred
        movea.l timing_game(pc),a0
        jmp     E_2e658(a0)
.centred:
        movem.l d0-d1/a0-a1,-(sp)
        movea.l 16+4(sp),a1             ; destination
        move.w  rot_fx(pc),92(a2)
        move.w  rot_fy(pc),94(a2)
        move.w  rot_fy(pc),d0           ; address as E:2e658
        sub.w   26(a1),d0
        muls.w  20(a1),d0
        movea.w rot_fx(pc),a0
        add.l   a0,d0
        move.w  26(a1),d1
        ext.l   d1
        lsl.l   #2,d1
        movea.l (a1),a0
        add.l   (a0,d1.l),d0
        move.l  d0,56(a2)
        movem.l (sp)+,d0-d1/a0-a1
        rts

; Direction codes 0-7 as (x, y): E:2e2e4 (the major step) and E:2e32c (the minor).
rot_step1:      dc.w 1,0, 0,1, 0,1, -1,0, -1,0, 0,-1, 0,-1, 1,0
rot_step2:      dc.w 0,1, 1,0, -1,0, 0,1, 0,-1, -1,0, 1,0, 0,-1
        cnop    0,4
rot_p1:         dc.l 0
rot_p2:         dc.l 0
rot_p3:         dc.l 0
rot_p4:         dc.l 0
rot_bres:       dc.l 0
rot_n:          dc.w 0
rot_ox:         dc.w 0
rot_oy:         dc.w 0
rot_fx:         dc.w 0
rot_fy:         dc.w 0
rot_on:         dc.w 0
rot_m:          dc.w 0
rot_x:          dc.w 0
rot_y:          dc.w 0
