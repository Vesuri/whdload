        IFD VERIFY
        IFD FLYING_TEST
; Native flying callback oracle: four calls versus 48 physics ticks.
; Compare full actor/RNG state at each twelfth tick and XYZ/bank at every substep.
s60_flying_results:
        dc.b 'F760'
        dc.w 0,0
        ds.b 12*16
s60_flying_case_error: dc.w 0
s60_flying_rng: ds.b 116
s60_flying_expected: ds.b 4*(112+116)
s60_flying_start: ds.l 3
s60_flying_actors: ds.b 224
s60_flying_bank_start: dc.w 0
; state, delay counter, height, initial bank, angular velocity, cooldown,
; contact flag. Twelve cases exercise descent, climb, clamp, bank and decisions.
s60_flying_cases:
        dc.w 2,0
        dc.l 400
        dc.w 0,0,0,0
        dc.w 2,0
        dc.l 225
        dc.w 15,1,0,0
        dc.w 5,0
        dc.l 700
        dc.w -20,-3,0,0
        dc.w 5,0
        dc.l 975
        dc.w 100,7,0,0
        dc.w 5,0
        dc.l 1000
        dc.w -100,-7,0,0
        dc.w 5,0
        dc.l 1100
        dc.w 32760,0,0,0
        dc.w 4,2
        dc.l 300
        dc.w -32760,0,0,0
        dc.w 0,2
        dc.l 1000
        dc.w 200,10,0,0
        dc.w 1,0
        dc.l 500
        dc.w -200,-10,0,0
        dc.w 3,0
        dc.l 200
        dc.w 0,0,10,0
        dc.w 3,0
        dc.l 200
        dc.w 0,0,0,0
        dc.w 2,0
        dc.l 300
        dc.w 0,0,0,1
s60_flying_setup:
        lea (s60_flying_actors,pc),a0
        moveq #55,d0
.clear: clr.l (a0)+
        dbf d0,.clear
        lea (s60_flying_cases,pc),a0
        move.w d5,d0
        lsl.w #4,d0
        adda.w d0,a0
        lea (s60_flying_actors,pc),a3
        move.w #11,(2,a3)
        move.b (1,a0),($59,a3)
        move.b (3,a0),($5b,a3)
        move.l (4,a0),($10,a3)
        move.w (8,a0),($16,a3)
        move.w (10,a0),($38,a3)
        move.b (13,a0),($62,a3)
        move.w #4096,($5e,a3) ; keep state 3 away from projectile allocation
        move.b #100,($55,a3)
        tst.w (14,a0)
        beq .done
        lea (112,a3),a0
        move.l a0,($66,a3)
.done:  rts
s60_flying_restore_rng:
        lea (s60_flying_rng,pc),a0
        lea ($2434-S60_DATA,a4),a1
        moveq #28,d0
.copy:  move.l (a0)+,(a1)+
        dbf d0,.copy
        rts
s60_flying_mark_error:
        lea (s60_flying_case_error,pc),a0
        move.w #1,(a0)
        rts
s60_test_flying:
        move.l (s60_ticks,pc),d0
        cmp.l #FLYING_TEST,d0
        bne .done
        move.w (s60_flying_results+4,pc),d0
        bne .done ; one fixture pass per boot, including after death/retry
        movem.l d2-d7/a2-a6,-(sp)
        lea ($2434-S60_DATA,a4),a0
        lea (s60_flying_rng,pc),a1
        moveq #28,d0
.save_rng:
        move.l (a0)+,(a1)+
        dbf d0,.save_rng
        moveq #0,d5
.case:
        lea (s60_flying_case_error,pc),a0
        clr.w (a0)
        bsr s60_flying_setup
        bsr s60_flying_restore_rng
        lea (s60_running,pc),a0
        move.w #1,(a0)
        lea (s60_flying_expected,pc),a2
        moveq #3,d6
.reference:
        move.l a3,-(sp)
        S60_CALL $f192
        addq.l #4,sp
        move.l a3,a0
        moveq #27,d0
.save_actor:
        move.l (a0)+,(a2)+
        dbf d0,.save_actor
        lea ($2434-S60_DATA,a4),a0
        moveq #28,d0
.save_state:
        move.l (a0)+,(a2)+
        dbf d0,.save_state
        dbf d6,.reference
        bsr s60_flying_setup
        bsr s60_flying_restore_rng
        lea (s60_running,pc),a0
        move.w #1,(a0)
        bsr s60_motion_record
        lea (s60_flying_results+8,pc),a5
        move.w d5,d0
        lsl.w #4,d0
        adda.w d0,a5
        move.w (2,a3),(a5)
        lea (s60_flying_expected,pc),a2
        moveq #0,d6
.period:
        lea (s60_flying_start,pc),a0
        move.l (8,a3),(a0)+
        move.l (12,a3),(a0)+
        move.l (16,a3),(a0)
        lea (s60_flying_bank_start,pc),a0
        move.w ($16,a3),(a0)
        moveq #1,d7
.tick:
        move.l (s60_code,pc),a1
        adda.l #$f192,a1
        bsr s60_ai
        tst.w d6
        bne .position
        cmp.w #1,d7
        bne .sixth
        move.l ($10,a3),(4,a5)
.sixth: cmp.w #(S60_SUBSTEPS+1)/2,d7
        bne .position
        move.l ($10,a3),(8,a5)
.position:
        moveq #0,d2
.axis:
        lea (s60_flying_start,pc),a0
        move.l (a0,d2.w),d3
        move.l (8,a2,d2.w),d0
        sub.l d3,d0
        muls d7,d0
        divs #S60_SUBSTEPS,d0
        ext.l d0
        add.l d3,d0
        cmp.l (8,a3,d2.w),d0
        beq .next_axis
        bsr s60_flying_mark_error
.next_axis:
        addq.w #4,d2
        cmp.w #12,d2
        bne .axis
        move.w ($16,a2),d0
        sub.w (s60_flying_bank_start,pc),d0
        muls d7,d0
        divs #S60_SUBSTEPS,d0
        add.w (s60_flying_bank_start,pc),d0
        cmp.w ($16,a3),d0
        beq .bank_ok
        bsr s60_flying_mark_error
.bank_ok:
        addq.w #1,d7
        cmp.w #S60_SUBSTEPS+1,d7
        bne .tick
        move.l a3,a0
        move.l a2,a1
        moveq #27,d2
.check_actor:
        move.l (a0)+,d0
        cmp.l (a1)+,d0
        beq .actor_ok
        bsr s60_flying_mark_error
        ; mark_error uses A0; recover the next source address from remaining words.
        move.l a3,a0
        moveq #28,d0
        sub.w d2,d0
        lsl.w #2,d0
        adda.w d0,a0
.actor_ok:
        dbf d2,.check_actor
        lea ($2434-S60_DATA,a4),a0
        moveq #28,d2
.check_rng:
        move.l (a0)+,d0
        cmp.l (a1)+,d0
        beq .rng_ok
        bsr s60_flying_mark_error
        lea ($2434-S60_DATA,a4),a0
        moveq #29,d0
        sub.w d2,d0
        lsl.w #2,d0
        adda.w d0,a0
.rng_ok:
        dbf d2,.check_rng
        adda.w #228,a2
        addq.w #1,d6
        cmp.w #4,d6
        bne .period
        move.l ($10,a3),(12,a5)
        move.w (s60_flying_case_error,pc),d0
        move.w d0,(2,a5)
        lea (s60_flying_results,pc),a0
        add.w d0,(6,a0)
        addq.w #1,(4,a0)
        move.l a6,a0
        moveq #(S60_REC/4)-1,d0
.forget: clr.l (a0)+
        dbf d0,.forget
        addq.w #1,d5
        cmp.w #12,d5
        bne .case
        bsr s60_flying_restore_rng
        movem.l (sp)+,d2-d7/a2-a6
.done:  rts
        ENDC
        ENDC
