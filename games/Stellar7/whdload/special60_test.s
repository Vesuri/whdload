        IFD VERIFY
        IFD SPECIAL_TEST
; Native callback oracle: four original calls versus 48 physics ticks.
; Compare full actor/RNG state at each twelfth tick and XYZ at every substep.
s60_special_results:
        dc.b 'T760'
        dc.w 0,0
        ds.b 12*16
s60_special_case_error: dc.w 0
s60_special_rng: ds.b 116
s60_special_expected: ds.b 4*(112+116)
s60_special_start: ds.l 3
s60_special_actors: ds.b 224
; type, charge counter, height, contact (0:none,1:obstacle,2:player), heading,
; forward speed, animation byte.
s60_special_cases:
        dc.w 13,0
        dc.l 200
        dc.w 0,0,0,0
        dc.w 13,0
        dc.l 10
        dc.w 0,0,0,0
        dc.w 13,0
        dc.l 980
        dc.w 1,0,0,0
        dc.w 13,0
        dc.l 100
        dc.w 1,0,0,0
        dc.w 47,3
        dc.l 100
        dc.w 0,0,100,0
        dc.w 47,1
        dc.l 25
        dc.w 0,512,100,0
        dc.w 47,0
        dc.l 50
        dc.w 0,1024,0,3
        dc.w 48,14
        dc.l 100
        dc.w 0,0,0,0
        dc.w 48,1
        dc.l 25
        dc.w 0,0,0,0
        dc.w 48,0
        dc.l 50
        dc.w 0,0,0,0
        dc.w 13,0
        dc.l 100
        dc.w 2,0,0,0
        dc.w 2,0
        dc.l 100
        dc.w 0,0,0,0
s60_special_setup:
        lea (s60_special_actors,pc),a0
        moveq #55,d0
.clear: clr.l (a0)+
        dbf d0,.clear
        lea (s60_special_cases,pc),a0
        move.w d5,d0
        lsl.w #4,d0
        adda.w d0,a0
        lea (s60_special_actors,pc),a3
        move.w (a0),(2,a3)
        move.b (3,a0),($5b,a3)
        move.l (4,a0),($10,a3)
        move.w (10,a0),($18,a3)
        move.w (10,a0),($5e,a3)
        move.w (12,a0),($40,a3)
        move.b (15,a0),($56,a3)
        move.b #100,($55,a3)
        move.l #3000,(8,a3)
        move.l #2000,(12,a3)
        move.w #1,(114,a3)
        move.w (8,a0),d0
        beq .done
        cmp.w #2,d0
        beq .player
        lea (112,a3),a0
        move.l a0,($66,a3)
        rts
.player:
        move.l ($43c0-S60_DATA,a4),($66,a3)
.done:  rts
s60_special_restore_rng:
        lea (s60_special_rng,pc),a0
        lea ($2434-S60_DATA,a4),a1
        moveq #28,d0
.copy:  move.l (a0)+,(a1)+
        dbf d0,.copy
        rts
s60_special_mark_error:
        lea (s60_special_case_error,pc),a0
        move.w #1,(a0)
        rts
s60_test_special:
        move.l (s60_ticks,pc),d0
        cmp.l #SPECIAL_TEST,d0
        bne .done
        move.w (s60_special_results+4,pc),d0
        bne .done ; one fixture pass per boot, including after death/retry
        movem.l d2-d7/a2-a6,-(sp)
        lea ($2434-S60_DATA,a4),a0
        lea (s60_special_rng,pc),a1
        moveq #28,d0
.save_rng:
        move.l (a0)+,(a1)+
        dbf d0,.save_rng
        moveq #0,d5
.case:
        lea (s60_special_case_error,pc),a0
        clr.w (a0)
        bsr s60_special_setup
        bsr s60_special_restore_rng
        lea (s60_running,pc),a0
        clr.w (a0)
        lea (s60_special_expected,pc),a2
        moveq #3,d6
.reference:
        move.l a3,-(sp)
        S60_CALL $f328
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
        bsr s60_special_setup
        bsr s60_special_restore_rng
        lea (s60_running,pc),a0
        move.w #1,(a0)
        bsr s60_motion_record
        lea (s60_special_results+8,pc),a5
        move.w d5,d0
        lsl.w #4,d0
        adda.w d0,a5
        move.w (2,a3),(a5)
        lea (s60_special_expected,pc),a2
        moveq #0,d6
.period:
        lea (s60_special_start,pc),a0
        move.l (8,a3),(a0)+
        move.l (12,a3),(a0)+
        move.l (16,a3),(a0)
        moveq #1,d7
.tick:
        move.l (s60_code,pc),a1
        adda.l #$f328,a1
        bsr s60_ai
        tst.w d6
        bne .position
        cmp.w #1,d7
        bne .sixth
        move.l ($10,a3),(4,a5)
.sixth: cmp.w #6,d7
        bne .position
        move.l ($10,a3),(8,a5)
.position:
        moveq #0,d2
.axis:
        lea (s60_special_start,pc),a0
        move.l (a0,d2.w),d3
        move.l (8,a2,d2.w),d0
        sub.l d3,d0
        muls d7,d0
        divs #12,d0
        ext.l d0
        add.l d3,d0
        cmp.l (8,a3,d2.w),d0
        beq .next_axis
        bsr s60_special_mark_error
.next_axis:
        addq.w #4,d2
        cmp.w #12,d2
        bne .axis
        addq.w #1,d7
        cmp.w #13,d7
        bne .tick
        move.l a3,a0
        move.l a2,a1
        moveq #27,d2
.check_actor:
        move.l (a0)+,d0
        cmp.l (a1)+,d0
        beq .actor_ok
        bsr s60_special_mark_error
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
        bsr s60_special_mark_error
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
        move.w (s60_special_case_error,pc),d0
        move.w d0,(2,a5)
        lea (s60_special_results,pc),a0
        add.w d0,(6,a0)
        addq.w #1,(4,a0)
        move.l a6,a0
        moveq #(S60_REC/4)-1,d0
.forget: clr.l (a0)+
        dbf d0,.forget
        addq.w #1,d5
        cmp.w #12,d5
        bne .case
        bsr s60_special_restore_rng
        movem.l (sp)+,d2-d7/a2-a6
.done:  rts
        ENDC
        ENDC
