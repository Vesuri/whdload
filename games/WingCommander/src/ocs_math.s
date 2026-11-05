; E1 exact shortcuts for OCS signed 24.8 multiplication. Native fallback keeps
; its full-range magnitude/truncate/sign semantics, including INT_MIN.
ocs_multiply:
        move.l 4(sp),d0
        beq.w .zero
        move.l 8(sp),d1
        beq.w .zero
        cmpi.l #256,d0
        beq.w .other
        cmpi.l #-256,d0
        beq.w .negative_other
        cmpi.l #256,d1
        beq.w .unit_scratch
        cmpi.l #-256,d1
        beq.w .negative
        movea.l d2,a0
        movea.l d3,a1
        move.l d0,d2
        eor.l d1,d2
        tst.l d0
        bpl.s .positive_x
        neg.l d0
.positive_x:
        tst.l d1
        bpl.s .positive_y
        neg.l d1
.positive_y:
        cmp.l d1,d0
        bls.s .ordered
        exg d0,d1
.ordered:
        cmpi.l #65535,d0
        bhi.s .fallback
        move.l d1,d3
        swap d3
        mulu.w d0,d3
        mulu.w d1,d0
        move.l d0,d1
        swap d1
        andi.l #65535,d1
        lsr.l #8,d0
        lsl.l #8,d3
        add.l d3,d0
        tst.l d2
        bpl.s .restore
        neg.l d0
.restore:
        move.l a0,d2
        move.l a1,d3
        bra.s .scratch
.fallback:
        move.l a0,d2
        move.l a1,d3
        bra.w ocs_multiply_native
.other: move.l d1,d0
        bra.s .unit_scratch
.negative_other:
        move.l d1,d0
.negative:
        neg.l d0
.unit_scratch:
        move.l d0,d1
        bpl.s .unit_abs
        neg.l d1
.unit_abs:
        andi.l #65535,d1
        lsr.l #8,d1
        bra.s .scratch
.zero:  moveq #0,d0
        moveq #0,d1
.scratch:
        movea.l d4,a0
        movea.l d5,a1
        movea.l d6,a6
        tst.l d6
        rts

; The native unsigned ratio computes exactly eight quotient bits. Unrolling
; removes the DBRA and uses immediate bit numbers, with no approximation.
; Entry D0=max, D1=min, D2=0, D3=7; native continuation owns table and rounding.
ocs_distance_ratio:
        add.l d1,d1
        cmp.l d0,d1
        bcs.s .skip7
        sub.l d0,d1
        bset #7,d2
.skip7:
        add.l d1,d1
        cmp.l d0,d1
        bcs.s .skip6
        sub.l d0,d1
        bset #6,d2
.skip6:
        add.l d1,d1
        cmp.l d0,d1
        bcs.s .skip5
        sub.l d0,d1
        bset #5,d2
.skip5:
        add.l d1,d1
        cmp.l d0,d1
        bcs.s .skip4
        sub.l d0,d1
        bset #4,d2
.skip4:
        add.l d1,d1
        cmp.l d0,d1
        bcs.s .skip3
        sub.l d0,d1
        bset #3,d2
.skip3:
        add.l d1,d1
        cmp.l d0,d1
        bcs.s .skip2
        sub.l d0,d1
        bset #2,d2
.skip2:
        add.l d1,d1
        cmp.l d0,d1
        bcs.s .skip1
        sub.l d0,d1
        bset #1,d2
.skip1:
        add.l d1,d1
        cmp.l d0,d1
        bcs.s .skip0
        sub.l d0,d1
        bset #0,d2
.skip0:
        moveq #-1,d3
        jmp OCS_RATIO_RETURN

; O:2b950 is a strict radius predicate, not a distance return. Reject an
; axis-separated pair before its two approximate hypotenuse calculations.
; Limit all magnitudes to <2^30 so native positive corrections cannot wrap.
; Wide/exceptional coordinates retain native behaviour, including overflow.
ocs_radius:
        movem.l d2-d3,-(sp)
        movea.l 12(sp),a1
        move.l (a1)+,d0
        bpl.s .x
        neg.l d0
.x:     move.l (a1)+,d2
        bpl.s .y
        neg.l d2
.y:     move.l (a1)+,d3
        bpl.s .z
        neg.l d3
.z:     cmpi.l #$40000000,d0
        bhs.s .native
        cmpi.l #$40000000,d2
        bhs.s .native
        cmpi.l #$40000000,d3
        bhs.s .native
        move.l 16(sp),d1
        lsl.l #8,d1
        cmp.l d1,d0
        bhs.s .reject
        cmp.l d1,d2
        bhs.s .reject
        cmp.l d1,d3
        bhs.s .reject
.native:
        movem.l (sp)+,d2-d3
        bra.w ocs_radius_native
.reject:
        movem.l (sp)+,d2-d3
        moveq #0,d0
        rts

; O:1574e collision pair preparation. Keep the native ordered scan, class
; table, self exclusion and first-hit return. Fuse only its vector subtraction
; and radius setup, preserving all three native scratch components.
ocs_collision_pair:
        movea.l d7,a0
        lea 12584(a4),a6
        move.l (a2),d0
        sub.l (a0)+,d0
        move.l d0,(a6)+
        move.l 4(a2),d0
        sub.l (a0)+,d0
        move.l d0,(a6)+
        move.l 8(a2),d0
        sub.l (a0)+,d0
        move.l d0,(a6)+
        move.w d2,d0
        add.w d0,d0
        lea 4746(a4),a0
        move.w (a0,d0.w),d6
        add.w -2(a5),d6
        cmpi.w #12,d4
        bne.s .radius
        cmpi.w #12,d5
        bne.s .radius
        asr.w #1,d6
.radius:
        movea.w d6,a0
        move.l a0,-(sp)
        pea 12584(a4)
        jsr OCS_RADIUS
        jmp OCS_COLLISION_RESULT
