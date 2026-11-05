        IFD VERIFY
        IFD RADIUS_TEST
        IFND RADIUS_TWIN
        FAIL "RADIUS_TEST requires RADIUS_TWIN"
        ENDC
s60_radius_numerators:
        dc.l 0,1,-1,100,-100,$7fffffff,$80000000,$12345678
        dc.l 65534,65535,65536,$00fffffe,$00ffffff,$01000000,65537,$1fffffff
s60_radius_denominators:
        dc.l $40000000,$7fffffff,$80000000,$c0000000
s60_radius_shifts: dc.w 0,1,7,8,16
s60_radius_small_numerators: dc.l 0,1,100,127,128,65535,$00fffffe,$00ffffff
s60_radius_small_denominators: dc.l 1,-1,7,-7,128,-128,32767,-32768
s60_test_radius:
        move.l (s60_ticks,pc),d0
        cmp.l #RADIUS_TEST,d0
        bne .done
        move.w (s60_radius_results+12,pc),d0
        bne .done
        movem.l d2-d7/a2-a6,-(sp)
        move.w ($5dd2-S60_DATA,a4),-(sp)
        subq.l #8,sp
        move.l sp,a2
        moveq #0,d5
.loop:  move.w d5,d0
        and.w #15,d0
        lsl.w #2,d0
        lea (s60_radius_numerators,pc),a0
        move.l (0,a0,d0.w),(a2)
        move.w d5,d0
        lsr.w #4,d0
        and.w #3,d0
        lsl.w #2,d0
        lea (s60_radius_denominators,pc),a0
        move.l (0,a0,d0.w),(4,a2)
        move.w d5,d0
        lsr.w #6,d0
        add.w d0,d0
        lea (s60_radius_shifts,pc),a0
        move.w (0,a0,d0.w),($5dd2-S60_DATA,a4)
        bsr .run
        addq.w #1,d5
        cmp.w #320,d5
        bne .loop
        move.w #7,($5dd2-S60_DATA,a4)
        moveq #0,d5
.small: move.w d5,d0
        and.w #7,d0
        lsl.w #2,d0
        lea (s60_radius_small_numerators,pc),a0
        move.l (a0,d0.w),(a2)
        move.w d5,d0
        lsr.w #3,d0
        lsl.w #2,d0
        lea (s60_radius_small_denominators,pc),a0
        move.l (a0,d0.w),(4,a2)
        bsr .run
        addq.w #1,d5
        cmp.w #64,d5
        bne .small
        addq.l #8,sp
        move.w (sp)+,($5dd2-S60_DATA,a4)
        movem.l (sp)+,d2-d7/a2-a6
.done:  rts
.run:
        move.l (s60_radius_results+8,pc),d6
        move.l a2,-(sp)
        bsr s60_radius_twin
        addq.l #4,sp
        lea (s60_radius_results,pc),a0
        addq.w #1,(12,a0)
        cmp.l (8,a0),d6
        beq .return
        addq.w #1,(14,a0)
.return: rts

        ENDC
        ENDC
