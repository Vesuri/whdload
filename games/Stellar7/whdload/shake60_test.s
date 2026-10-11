        IFD VERIFY
        IFD SHAKE_TEST
s60_shake_results:
        dc.b 'H760'
        dc.w 0,0,0,0 ; completed, failed cases, refresh errors, reset errors
        ds.w 4
s60_shake_case_error: dc.w 0
s60_shake_cases: dc.w 8,0,8,255,2,127,1,31
s60_shake_expected: ds.b 8*124
s60_shake_gates:
        dc.l $4226
        dc.w $4ef9
        dc.l $3cee
        dc.w $2007
        dc.l $3d1c
        dc.w $2007
        dc.l $c586
        dc.w $7001
        dc.l 0
s60_shake_gate:
        movem.l d1-d3/a0-a2,-(sp)
        move.w d0,d1
        lea (s60_shake_gates,pc),a1
.next:  move.l (a1)+,d2
        beq .flush
        move.w (a1)+,d3
        move.l (s60_code,pc),a0
        adda.l d2,a0
        tst.w d1
        beq .restore
        cmp.w (a0),d3
        bne s60_bad
        move.w #$4e75,(a0)
        bra .next
.restore:
        move.w d3,(a0)
        bra .next
.flush:
        move.l (_resload,pc),a2
        jsr (resload_FlushCache,a2)
        movem.l (sp)+,d1-d3/a0-a2
        rts
s60_shake_setup:
        bsr s60_shake_reset
        lea (s60_shake_cases,pc),a0
        move.w d5,d0
        lsl.w #2,d0
        adda.w d0,a0
        move.w (a0),($026a-S60_DATA,a4)
        move.b (3,a0),($3558-S60_DATA,a4)
        move.l #$00070009,($7156-S60_DATA,a4)
        rts
s60_shake_snapshot:
        move.w ($026a-S60_DATA,a4),(a1)+
        move.w ($3558-S60_DATA,a4),(a1)+
        move.l ($7156-S60_DATA,a4),(a1)+
        lea ($2434-S60_DATA,a4),a0
        moveq #28,d0
.copy:  move.l (a0)+,(a1)+
        dbf d0,.copy
        rts
s60_shake_error:
        lea (s60_shake_case_error,pc),a0
        move.w #1,(a0)
        rts
s60_shake_compare:
        move.w ($026a-S60_DATA,a4),d0
        cmp.w (a2),d0
        bne s60_shake_error
        move.w ($3558-S60_DATA,a4),d0
        cmp.w (2,a2),d0
        bne s60_shake_error
        move.l ($7156-S60_DATA,a4),d0
        cmp.l (4,a2),d0
        bne s60_shake_error
        lea (8,a2),a1
        lea ($2434-S60_DATA,a4),a0
        moveq #28,d0
.rng:   move.l (a0)+,d1
        cmp.l (a1)+,d1
        bne s60_shake_error
        dbf d0,.rng
        rts
s60_test_shake:
        move.l (s60_ticks,pc),d0
        cmp.l #SHAKE_TEST,d0
        bne .done
        movem.l d2-d7/a2-a6,-(sp)
        move.l (s60_shake_state,pc),-(sp)
        move.l (s60_shake_state+4,pc),-(sp)
        move.l (s60_ticks,pc),-(sp)
        move.w ($026a-S60_DATA,a4),-(sp)
        move.w ($3558-S60_DATA,a4),-(sp)
        move.l ($7156-S60_DATA,a4),-(sp)
        moveq #1,d0
        bsr s60_shake_gate
        moveq #0,d5
.case:
        lea (s60_shake_case_error,pc),a0
        clr.w (a0)
        bsr s60_shake_setup
        lea (s60_shake_expected,pc),a3
        moveq #7,d6
.native:
        S60_CALL $40ae
        move.l a3,a1
        bsr s60_shake_snapshot
        adda.w #124,a3
        dbf d6,.native
        bsr s60_shake_setup
        move.w d5,d0
        mulu #5,d0
        add.l #203,d0
        cmp.w #1,d5
        bne .set_tick
        moveq #-16,d0
.set_tick:
        lea (s60_ticks,pc),a0
        move.l d0,(a0)
        lea (s60_shake_expected,pc),a2
        moveq #7,d6
.period:
        moveq #11,d7
.tick:
        bsr s60_shake_update
        bsr s60_shake_update ; duplicate update must not draw random numbers
        lea (s60_rendering,pc),a0
        move.w #1,(a0)
        bsr s60_shake_update
        lea (s60_rendering,pc),a0
        clr.w (a0)
        bsr s60_shake_compare
        lea (s60_ticks,pc),a0
        addq.l #1,(a0)
        dbf d7,.tick
        adda.w #124,a2
        dbf d6,.period
        lea (s60_shake_results,pc),a0
        addq.w #1,(4,a0)
        move.w (s60_shake_case_error,pc),d0
        add.w d0,(6,a0)
        move.w d5,d1
        add.w d1,d1
        move.w d0,(12,a0,d1.w)
        addq.w #1,d5
        cmp.w #4,d5
        bne .case
        bsr s60_shake_refresh_test
        moveq #0,d0
        bsr s60_shake_gate
        move.l (sp)+,($7156-S60_DATA,a4)
        move.w (sp)+,($3558-S60_DATA,a4)
        move.w (sp)+,($026a-S60_DATA,a4)
        lea (s60_ticks,pc),a0
        move.l (sp)+,(a0)
        lea (s60_shake_state,pc),a0
        move.l (sp)+,(4,a0)
        move.l (sp)+,(a0)
        movem.l (sp)+,d2-d7/a2-a6
.done:  rts
s60_shake_refresh_test:
        moveq #0,d5
.path:
        ; Seed an identical pending value with an active, not-yet-due clock.
        lea (s60_shake_state,pc),a2
        move.l #10,(a2)
        move.w #8,(4,a2)
        move.w #1,(6,a2)
        move.w #8,($026a-S60_DATA,a4)
        lea (s60_ticks,pc),a0
        move.l #15,(a0)
        tst.w d5
        bne .positive
        S60_CALL $3ce6
        bra .written
.positive:
        S60_CALL $3d14
.written:
        tst.l (a2)
        bne .bad_refresh
        tst.l (4,a2)
        bne .bad_refresh
        bsr s60_shake_update
        cmp.w #7,($026a-S60_DATA,a4)
        bne .bad_refresh
        cmp.l #15,(a2)
        bne .bad_refresh
        cmp.w #7,(4,a2)
        bne .bad_refresh
        cmp.w #1,(6,a2)
        beq .next
.bad_refresh:
        lea (s60_shake_results,pc),a0
        addq.w #1,(8,a0)
.next:  addq.w #1,d5
        cmp.w #2,d5
        bne .path
        ; Actual menu reset fragment writes 1 then calls native $40ae directly.
        move.w ($3558-S60_DATA,a4),d3
        S60_CALL $c57a
        tst.w ($026a-S60_DATA,a4)
        bne .bad_reset
        tst.l ($7156-S60_DATA,a4)
        bne .bad_reset
        cmp.w ($3558-S60_DATA,a4),d3
        bne .bad_reset
        bsr s60_shake_update
        tst.l (a2)
        bne .bad_reset
        tst.l (4,a2)
        beq .done
.bad_reset:
        lea (s60_shake_results,pc),a0
        addq.w #1,(10,a0)
.done:  rts
        ENDC
        ENDC
