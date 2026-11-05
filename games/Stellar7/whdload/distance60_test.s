        IFD VERIFY
        IFD DISTANCE_TEST
        IFND DISTANCE_TWIN
        FAIL "DISTANCE_TEST requires DISTANCE_TWIN"
        ENDC
s60_distance_inputs: ds.l 4
s60_distance_values:
        dc.l $80000000,$80000001,-65536,-100,-9,-8,-1,0
        dc.l 1,7,8,9,100,65535,$7ffffffe,$7fffffff
s60_test_distance:
        move.l (s60_ticks,pc),d0
        cmp.l #DISTANCE_TEST,d0
        bne .done
        move.w (s60_distance_results+12,pc),d0
        bne .done
        movem.l d2-d7/a2-a6,-(sp)
        moveq #0,d5
.case:  lea (s60_distance_inputs,pc),a2
        clr.l (a2)
        clr.l (4,a2)
        cmp.w #256,d5
        bcs .values
        move.l #$7ffffff0,(a2)
        move.l #$80000010,(4,a2)
.values:
        move.w d5,d0
        and.w #15,d0
        lsl.w #2,d0
        lea (s60_distance_values,pc),a0
        move.l (a0,d0.w),d1
        add.l (a2),d1
        move.l d1,(8,a2)
        move.w d5,d0
        lsr.w #4,d0
        and.w #15,d0
        lsl.w #2,d0
        move.l (a0,d0.w),d1
        add.l (4,a2),d1
        move.l d1,(12,a2)
        move.l (s60_distance_results+8,pc),d6
        pea (8,a2)
        move.l a2,-(sp)
        bsr s60_distance_twin
        addq.l #8,sp
        lea (s60_distance_results,pc),a0
        addq.w #1,(12,a0)
        cmp.l (8,a0),d6
        beq .next
        addq.w #1,(14,a0)
.next:  addq.w #1,d5
        cmp.w #512,d5
        bne .case
        movem.l (sp)+,d2-d7/a2-a6
.done:  rts
        ENDC
        ENDC
