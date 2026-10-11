        IFD VERIFY
        IFD KNOCK_TEST
; Compare native knockback speed/pending impulse at four twelve-tick boundaries.
; While active, speed must equal the native interval's speed on every substep;
; once inactive, allow the existing input quantization and check its endpoint.
s60_knock_results:
        dc.b 'K760'
        dc.w 0,0,0 ; completed, errors, same-value refresh errors
s60_knock_cases:
        dc.w 160,10,-160,10,1,10,-1,-10,32767,10,-32768,-10,0,10,0,-10
s60_knock_expected: ds.w 8
s60_knock_actor: ds.b 112
s60_knock_gate:
        move.l (s60_code,pc),a0
        move.w d0,($2b38,a0)
        move.l (_resload,pc),a2
        jsr (resload_FlushCache,a2)
        rts
s60_knock_error:
        lea (s60_knock_results,pc),a0
        addq.w #1,(6,a0)
        rts
s60_test_knock:
        move.l (s60_ticks,pc),d0
        cmp.l #KNOCK_TEST,d0
        bne .done
        movem.l d2-d7/a2-a6,-(sp)
        move.l ($43c0-S60_DATA,a4),-(sp)
        move.w ($026c-S60_DATA,a4),-(sp)
        move.l (s60_knock_state,pc),-(sp)
        move.w (s60_knock_state+4,pc),-(sp)
        move.l (s60_code,pc),a0
        cmp.l #$610009f4,($2b38,a0)
        bne s60_bad
        move.w #$4e75,d0
        bsr s60_knock_gate
        lea (s60_knock_actor,pc),a3
        move.l a3,($43c0-S60_DATA,a4)
        moveq #0,d5
.case:
        lea (s60_knock_cases,pc),a0
        move.w d5,d0
        lsl.w #2,d0
        adda.w d0,a0
        move.w (a0),d2
        move.w (2,a0),d3
        move.w d2,($026c-S60_DATA,a4)
        move.w #100,($40,a3)
        lea (s60_knock_expected,pc),a6
        moveq #3,d6
.reference:
        add.w d3,($40,a3)
        S60_CALL $2b0c
        move.w ($40,a3),(a6)+
        move.w ($026c-S60_DATA,a4),(a6)+
        dbf d6,.reference
        bsr s60_knock_reset
        move.w d2,($026c-S60_DATA,a4)
        move.w #100,($40,a3)
        move.w #123,($38,a3)
        lea (s60_knock_expected,pc),a6
        moveq #0,d6
.period:
        move.w ($026c-S60_DATA,a4),d4 ; nonzero means input is overridden
        moveq #1,d7
.tick:
        move.w d7,d0
        muls d3,d0
        divs #12,d0
        move.w d0,d1
        move.w d7,d0
        subq.w #1,d0
        muls d3,d0
        divs #12,d0
        sub.w d0,d1
        add.w d1,($40,a3)
        bsr s60_knock_update
        tst.w d4
        bne .check_speed
        cmp.w #12,d7
        bne .check_pending
.check_speed:
        move.w ($40,a3),d0
        cmp.w (a6),d0
        beq .check_pending
        bsr s60_knock_error
.check_pending:
        move.w ($026c-S60_DATA,a4),d0
        cmp.w (2,a6),d0
        beq .check_turn
        bsr s60_knock_error
.check_turn:
        cmp.w #123,($38,a3)
        beq .next_tick
        bsr s60_knock_error
.next_tick:
        addq.w #1,d7
        cmp.w #13,d7
        bne .tick
        addq.l #4,a6
        addq.w #1,d6
        cmp.w #4,d6
        bne .period
        lea (s60_knock_results,pc),a0
        addq.w #1,(4,a0)
        addq.w #1,d5
        cmp.w #8,d5
        bne .case
        ; A fresh hit equals the published pending impulse; value polling alone
        ; cannot distinguish it. Exercise the actual replacement store hook.
        bsr s60_knock_reset
        move.w #100,($026c-S60_DATA,a4)
        moveq #5,d6
.refresh_start:
        bsr s60_knock_update
        dbf d6,.refresh_start
        move.w #50,($40,a3)
        move.l a3,a0
        bsr s60_knock_collision
        bsr s60_knock_update
        lea (s60_knock_results,pc),a0
        cmp.w #50,($40,a3)
        bne .refresh_error
        cmp.w #25,($026c-S60_DATA,a4)
        bne .refresh_error
        move.w (s60_knock_state,pc),d0
        cmp.w #11,d0
        beq .restore
.refresh_error:
        addq.w #1,(8,a0)
.restore:
        lea (s60_knock_state,pc),a0
        move.w (sp)+,(4,a0)
        move.l (sp)+,(a0)
        move.w (sp)+,($026c-S60_DATA,a4)
        move.l (sp)+,($43c0-S60_DATA,a4)
        move.w #$6100,d0
        bsr s60_knock_gate
        movem.l (sp)+,d2-d7/a2-a6
.done:  rts
        ENDC
        ENDC

        IFD VERIFY
        IFD KNOCK_PLAY
; Trigger an impulse through the collision setter during the real input route.
; This bypasses impact geometry, which is covered by COLLISION_TEST.
s60_test_knock_play:
        move.l (s60_ticks,pc),d0
        cmp.l #KNOCK_PLAY,d0
        bne .done
        move.l ($43c0-S60_DATA,a4),a0
        move.w #-160,($40,a0)
        bsr s60_knock_collision
.done:  rts
        ENDC
        ENDC
