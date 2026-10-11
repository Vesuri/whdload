        IFD VERIFY
        IFD CONTACT_TEST
; Exercise real patched call sites. Disable only fixture sound/animation helpers
; and return immediately after the call-site cleanup; restore every word.
s60_contact_results:
        dc.b 'D762'
        dc.w 0,0,0 ; completed paths, effect errors, clock isolation errors
        dc.w 0,0 ; allowed sound calls, fixture active
s60_contact_actors: ds.b 224
s60_contact_gates:
        dc.l $3740
        dc.w $2079
        dc.l $3830
        dc.w $6048
        dc.l $35ae
        dc.w $4a40
        dc.l $38b8
        dc.w $4a40
        dc.l $3cbe
        dc.w $265f
        dc.l $3596
        dc.w $4a79
        dc.l $3a0a
        dc.w $48e7
        dc.l $9986
        dc.w $4ef9
        dc.l 0
s60_contact_gate:
        movem.l d1-d3/a0-a2,-(sp)
        move.w d0,d1
        lea (s60_contact_gates,pc),a1
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
s60_contact_test_call:
        cmp.w #4,d5
        bne .ordinary
        move.l a3,-(sp)
        S60_TAIL $3cb8
.ordinary:
        cmp.w #2,d5
        bcc .health
        move.w #-25,-(sp)
        tst.w d5
        bne .second
        S60_TAIL $373a
.second:
        S60_TAIL $382a
.health:
        move.w #5,-(sp)
        cmp.w #2,d5
        beq .shield
        move.w #10,(sp)
        move.l a3,-(sp)
        S60_TAIL $38b2
.shield:
        move.l a3,-(sp)
        S60_TAIL $35a8
s60_contact_test_sound:
        move.l #21,-(sp)
        S60_TAIL $3590
s60_contact_setup:
        move.w #1000,($46c4-S60_DATA,a4)
        clr.w ($026a-S60_DATA,a4)
        move.w #1,(2,a3)
        move.b #100,($55,a3)
        cmp.w #4,d5
        bne .done
        move.w #44,(2,a3)
        lea (112,a3),a0
        move.l a0,($66,a3)
        move.w #1,(2,a0)
        move.b #100,($55,a0)
.done:  rts
s60_contact_error:
        lea (s60_contact_results,pc),a0
        addq.w #1,(6,a0)
        rts
s60_contact_forget:
        bsr s60_motion_record
        move.l a6,a0
        moveq #(S60_REC/4)-1,d0
.clear: clr.l (a0)+
        dbf d0,.clear
        rts
s60_test_contact:
        move.l (s60_ticks,pc),d0
        cmp.l #CONTACT_TEST,d0
        bne .done
        move.w (s60_contact_results+4,pc),d0
        bne .done ; one fixture pass per boot, including after death/retry
        movem.l d2-d7/a2-a6,-(sp)
        move.l (s60_shake_state,pc),-(sp)
        move.l (s60_shake_state+4,pc),-(sp)
        move.l (s60_ticks,pc),-(sp)
        move.l ($43c0-S60_DATA,a4),-(sp)
        move.w ($46a0-S60_DATA,a4),-(sp)
        clr.w ($46a0-S60_DATA,a4)
        lea (s60_contact_actors+112,pc),a0
        move.l a0,($43c0-S60_DATA,a4)
        move.w ($46c4-S60_DATA,a4),-(sp)
        move.w ($026a-S60_DATA,a4),-(sp)
        move.w ($1e90-S60_DATA,a4),-(sp)
        move.w ($1e9e-S60_DATA,a4),-(sp)
        clr.w ($1e90-S60_DATA,a4)
        move.w #1,($1e9e-S60_DATA,a4) ; negative damage must bypass shield
        lea (s60_contact_results,pc),a0
        move.w #1,(12,a0)
        moveq #1,d0
        bsr s60_contact_gate
        lea (s60_contact_actors,pc),a3
        moveq #0,d5
.case:
        bsr s60_contact_setup
        lea (s60_running,pc),a0
        clr.w (a0)
        moveq #3,d6
.reference:
        bsr s60_contact_test_call
        dbf d6,.reference
        move.w ($46c4-S60_DATA,a4),d4
        moveq #0,d3
        move.b ($55,a3),d3
        cmp.w #4,d5
        bne .native_expected
        move.b (112+$55,a3),d3
        cmp.w #20,d3
        bne .native_boss_error
        cmp.w #600,d4
        beq .native_done
.native_boss_error:
        bsr s60_contact_error
        bra .native_done
.native_expected:
        ; Independent endpoint expectations also catch argument/cleanup errors.
        cmp.w #2,d5
        bcc .native_health
        cmp.w #600,d4
        beq .native_done
        bsr s60_contact_error
        bra .native_done
.native_health:
        moveq #80,d0
        cmp.w #2,d5
        beq .native_check
        moveq #60,d0
.native_check:
        cmp.w d0,d3
        beq .native_done
        bsr s60_contact_error
.native_done:
        bsr s60_contact_setup
        lea (s60_running,pc),a0
        move.w #1,(a0)
        moveq #1,d7
.tick:
        lea (s60_ticks,pc),a0
        move.l #CONTACT_TEST-1,d0
        add.l d7,d0
        move.l d0,(a0)
        bsr s60_contact_test_call
        ; Native nonlethal actor damage and suppressed calls both return zero.
        cmp.w #4,d5
        beq .check_effect ; callback has no defined return value
        cmp.w #2,d5
        bcs .check_effect
        tst.w d0
        beq .check_effect
        bsr s60_contact_error
.check_effect:
        moveq #0,d0
        move.w d7,d0
        subq.w #1,d0
        divu #12,d0
        addq.w #1,d0
        cmp.w #4,d5
        beq .boss_effect
        cmp.w #2,d5
        bcc .health_effect
        mulu #100,d0
        move.w #1000,d1
        sub.w d0,d1
        cmp.w ($46c4-S60_DATA,a4),d1
        bne .effect_error
        cmp.w #8,($026a-S60_DATA,a4)
        beq .next_tick
        bra .effect_error
.boss_effect:
        move.w d0,d2
        mulu #20,d0
        moveq #100,d1
        sub.w d0,d1
        cmp.b (112+$55,a3),d1
        bne .effect_error
        mulu #100,d2
        move.w #1000,d1
        sub.w d2,d1
        cmp.w ($46c4-S60_DATA,a4),d1
        beq .next_tick
        bra .effect_error
.health_effect:
        moveq #5,d1
        cmp.w #2,d5
        beq .amount
        moveq #10,d1
.amount:
        mulu d1,d0
        moveq #100,d1
        sub.w d0,d1
        cmp.b ($55,a3),d1
        beq .next_tick
.effect_error:
        bsr s60_contact_error
.next_tick:
        addq.w #1,d7
        cmp.w #49,d7
        bne .tick
        cmp.w ($46c4-S60_DATA,a4),d4
        bne .end_error
        cmp.w #4,d5
        beq .end_boss
        cmp.b ($55,a3),d3
        beq .end_ok
        bra .end_error
.end_boss:
        cmp.b (112+$55,a3),d3
        beq .end_ok
.end_error:
        bsr s60_contact_error
.end_ok:
        bsr s60_contact_forget
        lea (s60_contact_results,pc),a0
        addq.w #1,(4,a0)
        addq.w #1,d5
        cmp.w #5,d5
        bne .case
        ; Preview calls must not consume the shield hit; after it, sound waits.
        bsr s60_contact_test_sound
        bsr s60_contact_test_sound
        moveq #2,d1
        bsr s60_contact_due
        cmp.w #1,d0
        bne .clock_error
        bsr s60_contact_test_sound
        lea (s60_ticks,pc),a0
        add.l #12,(a0)
        bsr s60_contact_test_sound
        ; Same actor/path is throttled; another path/actor is independent.
        moveq #0,d1
        bsr s60_contact_due
        cmp.w #1,d0
        bne .clock_error
        bsr s60_contact_due
        tst.w d0
        bne .clock_error
        moveq #1,d1
        bsr s60_contact_due
        cmp.w #1,d0
        bne .clock_error
        lea (s60_contact_actors+112,pc),a3
        moveq #0,d1
        bsr s60_contact_due
        cmp.w #1,d0
        bne .clock_error
        lea (s60_ticks,pc),a0
        move.l #-1,(a0)
        bsr s60_contact_due
        cmp.w #1,d0
        bne .clock_error
        lea (s60_ticks,pc),a0
        move.l #11,(a0)
        bsr s60_contact_due
        cmp.w #1,d0
        beq .restore
.clock_error:
        lea (s60_contact_results,pc),a0
        addq.w #1,(8,a0)
.restore:
        lea (s60_contact_actors,pc),a3
        bsr s60_contact_forget
        lea (s60_contact_actors+112,pc),a3
        bsr s60_contact_forget
        move.w (sp)+,($1e9e-S60_DATA,a4)
        move.w (sp)+,($1e90-S60_DATA,a4)
        move.w (sp)+,($026a-S60_DATA,a4)
        move.w (sp)+,($46c4-S60_DATA,a4)
        move.w (sp)+,($46a0-S60_DATA,a4)
        move.l (sp)+,($43c0-S60_DATA,a4)
        lea (s60_ticks,pc),a0
        move.l (sp)+,(a0)
        lea (s60_contact_results,pc),a0
        clr.w (12,a0)
        moveq #0,d0
        bsr s60_contact_gate
        lea (s60_shake_state,pc),a0
        move.l (sp)+,(4,a0)
        move.l (sp)+,(a0)
        movem.l (sp)+,d2-d7/a2-a6
.done:  rts
        ENDC
        ENDC
