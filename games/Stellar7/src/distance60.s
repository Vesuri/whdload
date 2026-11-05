; Native signed approximate distance: max(abs(dx),abs(dz)) + (3*min >> 3).
; Retain long wrap, MIN_LONG absolute value, and final D0/D1/condition codes.
s60_distance_native: ds.b 14
s60_distance_install:
        move.l (s60_code,pc),a1
        lea ($4388,a1),a0
        lea (s60_distance_native,pc),a3
        move.l #$48e70730,d0
        move.l #$266f0018,d1
        bsr s60_draw_trampoline
        lea (s60_distance_patches,pc),a0
        jsr (resload_Patch,a2)
        rts
s60_distance_patches:
        PL_START
        IFD VERIFY
        IFD DISTANCE_TWIN
        PL_P $4388,s60_distance_twin
        ELSE
        PL_P $4388,s60_distance
        ENDC
        ELSE
        PL_P $4388,s60_distance
        ENDC
        PL_NOP $438e,2
        PL_END
s60_distance:
        movem.l d2/a0-a1,-(sp)
        move.l (16,sp),a0
        move.l (20,sp),a1
        move.l (a1),d0
        sub.l (a0),d0
        bpl .x_abs
        neg.l d0
.x_abs: move.l (4,a1),d1
        sub.l (4,a0),d1
        bpl .z_abs
        neg.l d1
.z_abs: cmp.l d1,d0
        ble .ordered
        exg d0,d1
.ordered:
        move.l d0,d2
        add.l d0,d0
        add.l d2,d0
        asr.l #3,d0
        add.l d0,d1
        move.l d1,d0
        movem.l (sp)+,d2/a0-a1
        rts
        IFD VERIFY
        IFD DISTANCE_TWIN
s60_distance_results: dc.b 'G760'
        dc.l 0,0
        dc.w 0,0
s60_distance_twin:
        movem.l d2-d7/a0-a6,-(sp)
        move.l (56,sp),a2
        move.l (60,sp),a3
        move.l a3,-(sp)
        move.l a2,-(sp)
        bsr s60_distance_native
        addq.l #8,sp
        move.l d0,d6
        move.l d1,d7
        move.l a3,-(sp)
        move.l a2,-(sp)
        bsr s60_distance
        addq.l #8,sp
        cmp.l d6,d0
        bne .error
        cmp.l d7,d1
        beq .done
.error: lea (s60_distance_results,pc),a0
        addq.l #1,(8,a0)
.done:  lea (s60_distance_results,pc),a0
        addq.l #1,(4,a0)
        move.l d7,d1
        move.l d6,d0
        movem.l (sp)+,d2-d7/a0-a6
        rts
        ENDC
        ENDC
