        IFD VERIFY
        IFD HEADING_TEST
        IFEQ HEADING_FAST
        FAIL "HEADING_TEST requires HEADING_FAST=1"
        ENDC
s60_heading_results:
        dc.b 'H761'
        dc.w 0,0
s60_heading_values:
        dc.l -131072,-65536,-65535,-512,-1,0,1,512,65535,65536,131072
; Compare all fifteen register outputs from equal inputs/stack arguments.
; CCR equivalence is established by the identical final ASL.W in the fast path;
; this isolated fixture does not compare flags or validate full encounters.
s60_heading_compare:
        movem.l d0-d7/a0-a6,-(sp)
        move.l (68,sp),-(sp)
        move.l (68,sp),-(sp)
        movem.l (8,sp),d0-d7/a0-a6
        bsr s60_heading_native
        movem.l d0-d7/a0-a6,-(sp)
        move.l (136,sp),-(sp)
        move.l (136,sp),-(sp)
        movem.l (76,sp),d0-d7/a0-a6
        bsr s60_heading
        movem.l d0-d7/a0-a6,-(sp)
        move.l sp,a0
        lea (68,sp),a1
        moveq #14,d0
        moveq #0,d2
.loop:  move.l (a0)+,d1
        cmp.l (a1)+,d1
        beq .same
        moveq #1,d2
.same:  dbf d0,.loop
        lea (s60_heading_results,pc),a0
        addq.w #1,(4,a0)
        add.w d2,(6,a0)
        movem.l (136,sp),d0-d7/a0-a6
        lea (196,sp),sp
        rts
s60_test_heading:
        move.l (s60_ticks,pc),d0
        cmp.l #HEADING_TEST,d0
        bne .done
        move.w (s60_heading_results+4,pc),d0
        bne .done
        movem.l d2-d7/a2-a6,-(sp)
        moveq #0,d6
.x:     moveq #0,d7
.z:     lea (s60_heading_values,pc),a0
        move.l (a0,d7.w),-(sp)
        move.l (a0,d6.w),-(sp)
        move.l #$a55a1234,d0
        move.l #$5aa54321,d1
        bsr s60_heading_compare
        addq.l #8,sp
        addq.w #4,d7
        cmp.w #44,d7
        bne .z
        addq.w #4,d6
        cmp.w #44,d6
        bne .x
        moveq #0,d6
.octant:
        moveq #0,d7
.index: move.l d7,d2
        move.l #512,d3
        btst #2,d6
        beq .axes
        exg d2,d3
.axes:  btst #0,d6
        beq .x_sign
        neg.l d2
.x_sign:
        btst #1,d6
        beq .z_sign
        neg.l d3
.z_sign:
        move.l d3,-(sp)
        move.l d2,-(sp)
        move.l #$a55a1234,d0
        move.l #$5aa54321,d1
        bsr s60_heading_compare
        addq.l #8,sp
        addq.w #1,d7
        cmp.w #512,d7
        bne .index
        addq.w #1,d6
        cmp.w #8,d6
        bne .octant
        movem.l (sp)+,d2-d7/a2-a6
.done:  rts
        ENDC
        ENDC
