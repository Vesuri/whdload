        IFD VERIFY
        IFD SHOT_TEST
        IFEQ SHOT_FAST
        FAIL "SHOT_TEST requires SHOT_FAST=1"
        ENDC
s60_shot_results: dc.b 'Q760'
        dc.w 0,0
s60_shot_list_save: ds.l 256
s60_shot_actors: ds.b 4*112
s60_shot_counts: dc.w 0,1,4,256
; All register outputs are compared. The source preserves subtraction order,
; inclusive bounds and final X behavior; flags are not captured by this fixture.
s60_shot_compare:
        movem.l d0-d7/a0-a6,-(sp)
        move.l (64,sp),-(sp)
        movem.l (4,sp),d0-d7/a0-a6
        bsr s60_shot_native
        movem.l d0-d7/a0-a6,-(sp)
        move.l (128,sp),-(sp)
        movem.l (68,sp),d0-d7/a0-a6
        bsr s60_shot_scan
        movem.l d0-d7/a0-a6,-(sp)
        move.l sp,a0
        lea (64,sp),a1
        moveq #14,d0
        moveq #0,d2
.loop:  move.l (a0)+,d1
        cmp.l (a1)+,d1
        beq .same
        moveq #1,d2
.same:  dbf d0,.loop
        lea (s60_shot_results,pc),a0
        addq.w #1,(4,a0)
        add.w d2,(6,a0)
        movem.l (128,sp),d0-d7/a0-a6
        lea (188,sp),sp
        rts
s60_test_shot:
        move.l (s60_ticks,pc),d0
        cmp.l #SHOT_TEST,d0
        bne .done
        move.w (s60_shot_results+4,pc),d0
        bne .done
        movem.l d2-d7/a2-a6,-(sp)
        move.w ($43b2-S60_DATA,a4),-(sp)
        lea ($3fb2-S60_DATA,a4),a0
        lea (s60_shot_list_save,pc),a1
        move.w #255,d0
.save:  move.l (a0)+,(a1)+
        dbf d0,.save
        moveq #0,d5
.case:  lea (s60_shot_actors,pc),a0
        moveq #111,d0
.clear: clr.l (a0)+
        dbf d0,.clear
        lea (s60_shot_actors,pc),a3
        lea (112,a3),a2
        lea (224,a3),a5
        lea (336,a3),a6
        move.l #20,(4,a3)
        move.l #20,(4,a2)
        move.l #20,(4,a5)
        move.l #20,(4,a6)
        move.w d5,d0
        and.w #3,d0
        add.w d0,d0
        lea (s60_shot_counts,pc),a0
        move.w (a0,d0.w),d7
        move.w d7,($43b2-S60_DATA,a4)
        lea ($3fb2-S60_DATA,a4),a0
        move.w #255,d0
.fill:  move.l a2,(a0)+
        dbf d0,.fill
        lea ($3fb2-S60_DATA,a4),a0
        move.l a5,(4,a0)
        move.l a6,(8,a0)
        IFD SCAN_FLAG_TEST
        cmp.w #64,d5
        bcs .original_case
        move.w #1,($43b2-S60_DATA,a4)
        move.w d5,d0
        sub.w #64,d0
        move.b d0,($54,a2)
        bra .check
.original_case:
        ENDC
        move.w d5,d6
        lsr.w #2,d6
        cmp.w #1,d6
        bne .p2
        move.l a2,($6a,a3) ; first overlapping owner skipped
.p2:    cmp.w #2,d6
        bne .p3
        move.l a2,($6a,a3)
        move.l a2,(4,a0)
        move.l a2,(8,a0)
.p3:    cmp.w #3,d6
        bne .p4
        move.w #7,(2,a3)
.p4:    cmp.w #4,d6
        bne .p5
        move.w #7,(2,a2)
        move.w #7,(2,a5)
        move.w #7,(2,a6)
.p5:    cmp.w #5,d6
        bne .p6
        move.b #$fc,($54,a2)
        move.b #$fd,($54,a5)
.p6:    cmp.w #6,d6
        bne .p7
        move.l a3,(a0) ; native scan intentionally includes self
.p7:    cmp.w #7,d6
        bne .p8
        move.l #100,(8,a2)
        move.l #100,(8,a6)
        move.l a2,(4,a0)
        tst.w d7
        beq .p8
        move.w d7,d0
        subq.w #1,d0
        lsl.w #2,d0
        move.l a5,(a0,d0.w) ; only final entry overlaps
.p8:    cmp.w #8,d6
        bne .p9
        move.l #$7fffffff,(4,a3)
        move.l #$7fffffff,(4,a2)
.p9:    cmp.w #9,d6
        bne .p10
        move.l #$80000000,(8,a2)
.p10:   cmp.w #10,d6
        bne .p11
        move.l #21,(4,a3)
        move.l #20,(8,a2) ; odd radius sum, inclusive boundary
.p11:   cmp.w #11,d6
        bne .p12
        move.l #21,(8,a2)
        move.l #21,(8,a5)
        move.l #21,(8,a6)
.p12:   cmp.w #12,d6
        bne .p13
        move.l #$80000000,(12,a2)
.p13:   cmp.w #13,d6
        bne .p14
        move.l #$80000000,(16,a2)
.p14:   cmp.w #14,d6
        bne .p15
        move.l a2,($6a,a3)
        move.b #$fc,($54,a5)
        move.b #$fd,($54,a6)
.p15:   cmp.w #15,d6
        bne .check
        move.l #-1,(4,a3)
        clr.l (4,a2)
        clr.l (4,a5)
        clr.l (4,a6)
.check: move.l a3,-(sp)
        move.l #$a55a1234,d0
        move.l #$5aa54321,d1
        bsr s60_shot_compare
        addq.l #4,sp
        addq.w #1,d5
        IFD SCAN_FLAG_TEST
        cmp.w #320,d5
        ELSE
        cmp.w #64,d5
        ENDC
        bne .case
        lea (s60_shot_list_save,pc),a0
        lea ($3fb2-S60_DATA,a4),a1
        move.w #255,d0
.restore:
        move.l (a0)+,(a1)+
        dbf d0,.restore
        move.w (sp)+,($43b2-S60_DATA,a4)
        movem.l (sp)+,d2-d7/a2-a6
.done:  rts
        ENDC
        ENDC
