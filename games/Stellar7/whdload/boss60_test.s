        IFD VERIFY
        IFD BOSS_TEST
; Native boss oracle: 34 callback cases, eighteen coupled braking sequences,
; and eight curved exit rollback/replay cases (not a trajectory pace oracle).
; Native-reference cases compare four updates with 48 physics ticks. Curved
; cases check speed/pitch and spatial rollback/replay consistency separately.
s60_boss_results:
        dc.b 'B767'
        dc.w 0,0
        ds.b 60*16
s60_boss_case_error: dc.w 0
s60_boss_rng: ds.b 116
s60_boss_expected: ds.b 4*244
s60_boss_start: ds.l 3
s60_boss_actors: ds.b 336
s60_boss_animation: dc.w 0
s60_boss_saved_allocator: dc.l 0
s60_boss_pitch_start: dc.w 0
s60_boss_linear_y: dc.w 0
s60_boss_bank_start: dc.w 0
; level, type, state, counter, height.l, bank, yaw, target yaw, pitch,
; distance.l, speed, cooldown, contact, padding: 32 bytes per case.
s60_boss_cases:
        dc.w 2,44,1,14
        dc.l 800
        dc.w 0,0,4096,0
        dc.l 10000
        dc.w 0,7,0,0
        dc.w 2,44,1,14
        dc.l 550
        dc.w 0,0,4096,0
        dc.l 10000
        dc.w 0,7,0,0
        dc.w 2,44,1,14
        dc.l 501
        dc.w 0,0,4096,0
        dc.l 10000
        dc.w 0,7,0,0
        dc.w 2,44,1,14
        dc.l 500
        dc.w 0,0,4096,0
        dc.l 10000
        dc.w 0,7,0,0
        dc.w 2,44,2,0
        dc.l 1950
        dc.w 0,0,4096,0
        dc.l 10000
        dc.w 0,7,0,0
        dc.w 2,44,2,0
        dc.l 2099
        dc.w 0,0,4096,0
        dc.l 10000
        dc.w 0,7,0,0
        dc.w 2,44,2,0
        dc.l 2100
        dc.w 0,0,4096,0
        dc.l 10000
        dc.w 0,7,0,0
        dc.w 2,44,0,0
        dc.l 1000
        dc.w 0,0,4096,0
        dc.l 10000
        dc.w 0,7,0,0
        dc.w 2,44,0,0
        dc.l 2200
        dc.w 0,0,4096,0
        dc.l 10000
        dc.w 0,7,0,0
        dc.w 4,44,1,0
        dc.l 1000
        dc.w 0,0,4096,0
        dc.l 10000
        dc.w 0,7,0,0
        dc.w 4,44,1,0
        dc.l 1000
        dc.w 0,0,-4096,0
        dc.l 10000
        dc.w 0,7,0,0
        dc.w 4,44,1,0
        dc.l 1000
        dc.w 0,8192,12288,0
        dc.l 10000
        dc.w 0,7,0,0
        dc.w 4,44,1,0
        dc.l 1000
        dc.w 0,-8192,-12288,0
        dc.l 10000
        dc.w 0,7,0,0
        dc.w 4,44,1,0
        dc.l 1000
        dc.w 0,16384,20480,0
        dc.l 10000
        dc.w 0,7,0,0
        dc.w 4,44,1,0
        dc.l 1000
        dc.w 0,-32768,-28672,0
        dc.l 10000
        dc.w 0,7,0,0
        dc.w 4,44,1,0
        dc.l 800
        dc.w 0,8192,12288,0
        dc.l 10000
        dc.w 0,7,1,0
        dc.w 4,44,1,0
        dc.l 1000
        dc.w 32760,0,4096,0
        dc.l 3000
        dc.w 0,7,0,0
        dc.w 4,44,1,0
        dc.l 1000
        dc.w -32760,0,4096,0
        dc.l 30000
        dc.w 0,7,0,0
        dc.w 0,7,4,0
        dc.l 1000
        dc.w 0,0,4096,0
        dc.l 10000
        dc.w 0,7,0,0
        dc.w 0,7,4,0
        dc.l 1000
        dc.w -32760,0,4096,32760
        dc.l 10000
        dc.w 0,7,0,0
        dc.w 0,7,4,0
        dc.l 1000
        dc.w 32760,0,4096,-32760
        dc.l 10000
        dc.w 0,7,0,0
        dc.w 0,7,0,0
        dc.l 1000
        dc.w 100,0,4096,0
        dc.l 2000
        dc.w 0,7,0,0
        dc.w 0,7,0,0
        dc.l 1000
        dc.w 0,0,4096,0
        dc.l 500
        dc.w 400,7,0,0
        dc.w 0,44,0,0
        dc.l 1000
        dc.w 100,0,4096,0
        dc.l 10000
        dc.w 0,7,0,0
        dc.w 1,44,0,0
        dc.l 1000
        dc.w 100,0,4096,0
        dc.l 10000
        dc.w 0,7,0,0
        dc.w 3,44,0,0
        dc.l 1000
        dc.w 100,0,4096,0
        dc.l 10000
        dc.w 0,7,0,0
        dc.w 5,44,0,0
        dc.l 1000
        dc.w 100,0,4096,0
        dc.l 10000
        dc.w 0,7,1,0
        dc.w 6,44,0,0
        dc.l 1000
        dc.w 100,0,4096,0
        dc.l 10000
        dc.w 0,7,0,0
        dc.w 0,44,0,0
        dc.l 499
        dc.w 123,0,4096,0
        dc.l 10000
        dc.w 0,7,0,0
        dc.w 0,44,0,0
        dc.l 500
        dc.w 123,0,4096,0
        dc.l 10000
        dc.w 0,7,0,0
; Positive acceleration at the signed speed-word boundary. Each case runs
; four native intervals, checking every published substep and native endpoint.
        dc.w 0,7,4,0
        dc.l 1000
        dc.w 0,0,4096,0
        dc.l 10000
        dc.w 32717,7,0,0
        dc.w 0,7,4,0
        dc.l 1000
        dc.w 0,0,4096,0
        dc.l 10000
        dc.w 32718,7,0,0
        dc.w 0,7,4,0
        dc.l 1000
        dc.w 0,0,4096,32760
        dc.l 10000
        dc.w 32742,7,0,0
        dc.w 0,7,4,0
        dc.l 1000
        dc.w 0,0,4096,-32760
        dc.l 10000
        dc.w 32763,7,0,0
s60_boss_setup:
        lea (s60_boss_actors,pc),a0
        moveq #83,d0
.clear: clr.l (a0)+
        dbf d0,.clear
        lea (s60_boss_animation,pc),a0
        clr.w (a0)
        lea (s60_boss_cases,pc),a0
        move.w d5,d0
        lsl.w #5,d0
        adda.w d0,a0
        move.w (a0),($46a0-S60_DATA,a4)
        move.w #1,($1e96-S60_DATA,a4) ; level 4 does not fire
        clr.w ($43b2-S60_DATA,a4) ; no live projectile scan
        move.w #300,($473c-S60_DATA,a4)
        lea (s60_boss_actors,pc),a3
        move.w (2,a0),(2,a3)
        move.b (5,a0),($59,a3)
        move.b (7,a0),($5b,a3)
        move.l (8,a0),($10,a3)
        move.w (12,a0),($16,a3)
        move.w (14,a0),($18,a3)
        move.w (16,a0),($5e,a3)
        move.w (18,a0),($14,a3)
        move.l (20,a0),($50,a3)
        move.w (24,a0),($40,a3)
        move.b (27,a0),($61,a3)
        move.b #100,($55,a3)
        lea (112,a3),a1
        move.w #7,(2,a1)
        move.l a1,($1e4c-S60_DATA,a4) ; block optional projectile spawns
        tst.w (28,a0)
        beq .no_contact
        move.l a1,($66,a3)
.no_contact:
        lea (224,a3),a1
        move.l a1,($43c4-S60_DATA,a4)
        lea (s60_boss_animation,pc),a1
        move.l a1,($1e,a3)
        rts
; Native allocation returns null only inside the isolated fixture. Handlers
; tested here check that result; real allocation is restored before gameplay.
s60_boss_test_gate:
        movem.l d0/a0-a1/a2,-(sp)
        move.l (s60_code,pc),a0
        adda.l #$913c,a0
        lea (s60_boss_saved_allocator,pc),a1
        tst.w d0
        beq .restore
        move.l (a0),(a1)
        move.l #$70004e75,(a0)
        bra .flush
.restore:
        move.l (a1),(a0)
.flush:
        move.l (_resload,pc),a2
        jsr (resload_FlushCache,a2)
        movem.l (sp)+,d0/a0-a1/a2
        rts
s60_boss_restore_rng:
        lea (s60_boss_rng,pc),a0
        lea ($2434-S60_DATA,a4),a1
        moveq #28,d0
.copy:  move.l (a0)+,(a1)+
        dbf d0,.copy
        rts
s60_boss_mark_error:
        lea (s60_boss_case_error,pc),a0
        move.w #1,(a0)
        rts
s60_test_boss:
        move.l (s60_ticks,pc),d0
        cmp.l #BOSS_TEST,d0
        bne .done
        move.w (s60_boss_results+4,pc),d0
        bne .done ; a native retry resets ticks, not this once-only fixture
        movem.l d2-d7/a2-a6,-(sp)
        move.w ($46a0-S60_DATA,a4),-(sp)
        move.w ($1e96-S60_DATA,a4),-(sp)
        move.w ($43b2-S60_DATA,a4),-(sp)
        move.w ($473c-S60_DATA,a4),-(sp)
        move.l ($1e4c-S60_DATA,a4),-(sp)
        move.l ($43c4-S60_DATA,a4),-(sp)
        moveq #1,d0
        bsr s60_boss_test_gate
        lea ($2434-S60_DATA,a4),a0
        lea (s60_boss_rng,pc),a1
        moveq #28,d0
.save_rng:
        move.l (a0)+,(a1)+
        dbf d0,.save_rng
        moveq #0,d5
.case:
        lea (s60_boss_case_error,pc),a0
        clr.w (a0)
        bsr s60_boss_setup
        bsr s60_boss_restore_rng
        lea (s60_running,pc),a0
        move.w #1,(a0)
        lea (s60_boss_expected,pc),a2
        moveq #3,d6
.reference:
        move.l a3,-(sp)
        S60_CALL $10904
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
        move.w (s60_boss_animation,pc),(a2)+
        move.w ($473c-S60_DATA,a4),(a2)+
        lea (s60_boss_actors+232,pc),a0
        move.l (a0)+,(a2)+
        move.l (a0)+,(a2)+
        move.l (a0)+,(a2)+
        dbf d6,.reference
        bsr s60_boss_setup
        bsr s60_boss_restore_rng
        lea (s60_running,pc),a0
        move.w #1,(a0)
        bsr s60_motion_record
        lea (s60_boss_results+8,pc),a5
        move.w d5,d0
        lsl.w #4,d0
        adda.w d0,a5
        move.w (2,a3),(a5)
        lea (s60_boss_expected,pc),a2
        moveq #0,d6
.period:
        lea (s60_boss_start,pc),a0
        move.l (8,a3),(a0)+
        move.l (12,a3),(a0)+
        move.l (16,a3),(a0)
        lea (s60_boss_bank_start,pc),a0
        move.w ($16,a3),(a0)
        lea (s60_boss_pitch_start,pc),a0
        move.w ($14,a3),(a0)
        lea (s60_boss_linear_y,pc),a0
        move.w #1,(a0)
        cmp.w #2,($46a0-S60_DATA,a4)
        bne .linear_y
        tst.b ($59,a3)
        bne .linear_y
        clr.w (a0) ; native state-0 clamp is immediate, not a trajectory
.linear_y:
        lea (s60_boss_speed_start,pc),a0
        move.w ($40,a3),(a0)
        lea (s60_boss_speed_delta,pc),a0
        clr.w (a0)
        cmp.w #7,(2,a3)
        bne .speed_selected
        cmp.b #1,($59,a3)
        bne .exit_speed
        move.w #-5,(a0)
        bra .speed_selected
.exit_speed:
        cmp.b #4,($59,a3)
        bne .speed_selected
        move.w #50,(a0)
.speed_selected:
        moveq #1,d7
.tick:
        move.l (s60_code,pc),a1
        adda.l #$10904,a1
        bsr s60_ai
        move.w (s60_boss_speed_delta,pc),d0
        beq .speed_checked
        muls d7,d0
        divs #12,d0
        add.w (s60_boss_speed_start,pc),d0
        cmp.w ($40,a3),d0
        beq .speed_checked
        bsr s60_boss_mark_error
.speed_checked:
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
        lea (s60_boss_start,pc),a0
        move.l (a0,d2.w),d3
        move.l (8,a2,d2.w),d0
        cmp.w #8,d2
        bne .linear_axis
        move.w (s60_boss_linear_y,pc),d1
        beq .axis_compare
.linear_axis:
        sub.l d3,d0
        muls d7,d0
        divs #12,d0
        ext.l d0
        add.l d3,d0
.axis_compare:
        cmp.l (8,a3,d2.w),d0
        beq .next_axis
        bsr s60_boss_mark_error
.next_axis:
        addq.w #4,d2
        cmp.w #12,d2
        bne .axis
        move.w ($16,a2),d0
        sub.w (s60_boss_bank_start,pc),d0
        muls d7,d0
        divs #12,d0
        add.w (s60_boss_bank_start,pc),d0
        cmp.w ($16,a3),d0
        beq .bank_ok
        bsr s60_boss_mark_error
.bank_ok:
        move.w ($14,a2),d0
        sub.w (s60_boss_pitch_start,pc),d0
        muls d7,d0
        divs #12,d0
        add.w (s60_boss_pitch_start,pc),d0
        cmp.w ($14,a3),d0
        beq .pitch_ok
        bsr s60_boss_mark_error
.pitch_ok:
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
        bsr s60_boss_mark_error
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
        bsr s60_boss_mark_error
        lea ($2434-S60_DATA,a4),a0
        moveq #29,d0
        sub.w d2,d0
        lsl.w #2,d0
        adda.w d0,a0
.rng_ok:
        dbf d2,.check_rng
        move.w (s60_boss_animation,pc),d0
        cmp.w (a1)+,d0
        bne .global_error
        move.w ($473c-S60_DATA,a4),d0
        cmp.w (a1)+,d0
        bne .global_error
        lea (s60_boss_actors+232,pc),a0
        moveq #2,d2
.aim:   move.l (a0)+,d0
        cmp.l (a1)+,d0
        bne .global_error
        dbf d2,.aim
        bra .globals_ok
.global_error:
        bsr s60_boss_mark_error
.globals_ok:
        adda.w #244,a2
        addq.w #1,d6
        cmp.w #4,d6
        bne .period
        move.l ($10,a3),(12,a5)
        move.w (s60_boss_case_error,pc),d0
        move.w d0,(2,a5)
        lea (s60_boss_results,pc),a0
        add.w d0,(6,a0)
        addq.w #1,(4,a0)
        move.l a6,a0
        moveq #(S60_REC/4)-1,d0
.forget: clr.l (a0)+
        dbf d0,.forget
        addq.w #1,d5
        cmp.w #34,d5
        bne .case
        bsr s60_boss_test_acceleration
        bsr s60_boss_test_exit_rollback
        bsr s60_boss_restore_rng
        moveq #0,d0
        bsr s60_boss_test_gate
        move.l (sp)+,($43c4-S60_DATA,a4)
        move.l (sp)+,($1e4c-S60_DATA,a4)
        move.w (sp)+,($473c-S60_DATA,a4)
        move.w (sp)+,($43b2-S60_DATA,a4)
        move.w (sp)+,($1e96-S60_DATA,a4)
        move.w (sp)+,($46a0-S60_DATA,a4)
        movem.l (sp)+,d2-d7/a2-a6
.done:  rts

; Coupled native movement-before-AI oracle. Eighteen fixed-direction braking sequences
; compare complete actor bytes every twelve ticks, and speed on each tick.
; Includes zero crossings, reverse motion, signed wrap, diagonal and pitched directions.
s60_boss_speed_cases:
        dc.w 400,0,0
        dc.w 20,0,0
        dc.w 5,0,0
        dc.w 0,0,0
        dc.w -100,0,0
        dc.w 1,0,0
        dc.w 400,8192,0
        dc.w 400,-8192,0
        dc.w 20,12345,0
        dc.w 5,8192,0
        dc.w -100,-12345,0
        dc.w 1,32760,0
        dc.w -32768,0,0
        dc.w -32766,8192,0
        dc.w 32767,12345,0
        dc.w 400,8192,8192
        dc.w 20,-12345,-4096
        dc.w -100,4096,16384
s60_boss_speed_start: dc.w 0
s60_boss_speed_delta: dc.w 0
s60_boss_speed_setup:
        lea (s60_boss_actors,pc),a3
        move.l a3,a0
        moveq #27,d0
.clear: clr.l (a0)+
        dbf d0,.clear
        move.w #7,(2,a3)
        move.b #1,($59,a3)
        move.b #80,($5b,a3)
        move.b #100,($55,a3)
        move.l #10000,($50,a3)
        lea (s60_boss_speed_cases,pc),a0
        move.w d5,d0
        mulu #6,d0
        adda.w d0,a0
        move.w (a0),($40,a3)
        move.w (2,a0),($18,a3)
        move.w (4,a0),($14,a3)
        rts
s60_boss_test_move:
        move.l a3,-(sp)
        bsr s60_move
s60_boss_test_move_return:
        addq.l #4,sp
        rts
s60_boss_test_acceleration:
        moveq #0,d5
.case:
        lea (s60_boss_case_error,pc),a0
        clr.w (a0)
        bsr s60_boss_speed_setup
        lea (s60_boss_expected,pc),a2
        moveq #3,d6
.native:
        move.l a3,-(sp)
        bsr s60_move_native
        S60_CALL $10904
        addq.l #4,sp
        move.l a3,a0
        moveq #27,d0
.save:  move.l (a0)+,(a2)+
        dbf d0,.save
        dbf d6,.native
        bsr s60_boss_speed_setup
        bsr s60_motion_record
        lea (s60_boss_results+8+34*16,pc),a5
        move.w d5,d0
        lsl.w #4,d0
        adda.w d0,a5
        move.w #7,(a5)
        lea (s60_boss_expected,pc),a2
        moveq #0,d6
.period:
        lea (s60_boss_speed_start,pc),a0
        move.w ($40,a3),(a0)
        lea (s60_boss_speed_delta,pc),a0
        clr.w (a0)
        cmp.b #1,($59,a3)
        bne .no_brake
        move.w #-5,(a0)
.no_brake:
        moveq #1,d7
.tick:
        bsr s60_boss_test_move
        tst.w d5
        bne .rollback_checked
        tst.w d6
        bne .rollback_checked
        cmp.w #1,d7
        bne .rollback_checked
        move.l (12,a3),-(sp)
        move.w (118,a6),-(sp)
        move.l a3,-(sp)
        bsr s60_undo
        addq.l #4,sp
        tst.l (12,a3)
        bne .rollback_error
        tst.w (118,a6)
        beq .rollback_ok
.rollback_error:
        bsr s60_boss_mark_error
.rollback_ok:
        bsr s60_boss_test_move
        move.w (sp)+,d0
        cmp.w (118,a6),d0
        beq .remainder_ok
        bsr s60_boss_mark_error
.remainder_ok:
        move.l (sp)+,d0
        cmp.l (12,a3),d0
        beq .rollback_checked
        bsr s60_boss_mark_error
.rollback_checked:
        move.l (s60_code,pc),a1
        adda.l #$10904,a1
        bsr s60_ai
        move.w (s60_boss_speed_delta,pc),d0
        muls d7,d0
        divs #12,d0
        add.w (s60_boss_speed_start,pc),d0
        cmp.w ($40,a3),d0
        beq .speed_ok
        bsr s60_boss_mark_error
.speed_ok:
        tst.w d6
        bne .next
        cmp.w #1,d7
        bne .sixth
        move.l (12,a3),(4,a5)
.sixth: cmp.w #6,d7
        bne .next
        move.l (12,a3),(8,a5)
.next:  addq.w #1,d7
        cmp.w #13,d7
        bne .tick
        move.l a3,a0
        move.l a2,a1
        moveq #27,d2
.compare:
        move.l (a0)+,d0
        cmp.l (a1)+,d0
        beq .same
        bsr s60_boss_mark_error
        move.l a3,a0
        moveq #28,d0
        sub.w d2,d0
        lsl.w #2,d0
        adda.w d0,a0
.same:  dbf d2,.compare
        adda.w #112,a2
        addq.w #1,d6
        cmp.w #4,d6
        bne .period
        move.l (12,a3),(12,a5)
        move.w (s60_boss_case_error,pc),d0
        move.w d0,(2,a5)
        lea (s60_boss_results,pc),a0
        add.w d0,(6,a0)
        addq.w #1,(4,a0)
        move.l a6,a0
        moveq #(S60_REC/4)-1,d0
.clear_record:
        clr.l (a0)+
        dbf d0,.clear_record
        addq.w #1,d5
        cmp.w #18,d5
        bne .case
        rts
; Coupled curved exits: published speed/pitch have independent closed-form
; expectations. Every tick checks spatial rollback and exact move replay,
; including all actor/record bytes after restoring the replay angular inputs.
; Rollback itself preserves completed rotation. This does not establish trajectory pace.
s60_boss_exit_cases:
        dc.w 0,0,0
        dc.w 400,8192,8192
        dc.w -100,-12345,-4096
        dc.w 1,4096,16384
        dc.w 32717,0,0
        dc.w 32718,8192,32760
        dc.w 32742,-8192,-32760
        dc.w 32763,12345,8192
s60_boss_exit_before: ds.b 24
s60_boss_exit_saved: ds.b 112+S60_REC
        IFD BOSS_PATH_TEST
s60_boss_path_results:
        dc.b 'BP60'
        dc.w 8,48
        ds.l 8*48*3
        ENDC
s60_boss_test_exit_rollback:
        moveq #0,d5
.case:
        lea (s60_boss_case_error,pc),a0
        clr.w (a0)
        bsr s60_boss_speed_setup
        move.b #4,($59,a3)
        lea (s60_boss_exit_cases,pc),a2
        move.w d5,d0
        mulu #6,d0
        adda.w d0,a2
        move.w (a2),($40,a3)
        move.w (2,a2),($18,a3)
        move.w (4,a2),($14,a3)
        bsr s60_motion_record
        lea (s60_boss_results+8+52*16,pc),a5
        move.w d5,d0
        lsl.w #4,d0
        adda.w d0,a5
        move.w #7,(a5)
        moveq #1,d7
.tick:
        lea (s60_boss_exit_before,pc),a0
        move.l (8,a3),(a0)+
        move.l (12,a3),(a0)+
        move.l (16,a3),(a0)+
        move.l (20,a3),(a0)+
        move.w (24,a3),(a0)+
        move.l (8,a6),(a0)+
        move.w (12,a6),(a0)+
        bsr s60_boss_test_move
        lea (s60_boss_exit_saved,pc),a1
        move.l a3,a0
        moveq #27,d0
.save_actor:
        move.l (a0)+,(a1)+
        dbf d0,.save_actor
        move.l a6,a0
        moveq #(S60_REC/4)-1,d0
.save_record:
        move.l (a0)+,(a1)+
        dbf d0,.save_record
        move.l a3,-(sp)
        bsr s60_undo
        addq.l #4,sp
        IFD BOSS_BAD_EXIT_ROLLBACK
        addq.l #1,(8,a3)
        ENDC
        lea (s60_boss_exit_before,pc),a1
        lea (8,a3),a0
        moveq #2,d2
.check_position:
        move.l (a0)+,d0
        cmp.l (a1)+,d0
        beq .position_ok
        movem.l a0-a1,-(sp)
        lea (s60_boss_case_error,pc),a0
        bset #0,(1,a0)
        movem.l (sp)+,a0-a1
.position_ok:
        dbf d2,.check_position
        ; Native collision rollback is spatial: completed rotation stays.
        lea (s60_boss_exit_saved+20,pc),a1
        cmpm.l (a0)+,(a1)+ ; A0 is actor+20 after the XYZ check
        bne .rotation_error
        cmpm.w (a0)+,(a1)+
        bne .rotation_error
        lea (8,a6),a0
        lea (s60_boss_exit_saved+112+8,pc),a1
        cmpm.l (a0)+,(a1)+
        bne .rotation_error
        cmpm.w (a0)+,(a1)+
        beq .rotation_ok
.rotation_error:
        lea (s60_boss_case_error,pc),a0
        bset #5,(1,a0)
.rotation_ok:
        ; Restore only angular inputs to repeat the same movement experiment.
        ; The wrapper itself must have restored all spatial fractions.
        lea (s60_boss_exit_before+12,pc),a0
        move.l (a0)+,(20,a3)
        move.w (a0)+,(24,a3)
        move.l (a0)+,(8,a6)
        move.w (a0)+,(12,a6)
        bsr s60_boss_test_move
        lea (s60_boss_exit_saved,pc),a1
        move.l a3,a0
        moveq #27,d2
.check_actor:
        move.l (a0)+,d0
        cmp.l (a1)+,d0
        beq .actor_ok
        movem.l a0-a1,-(sp)
        lea (s60_boss_case_error,pc),a0
        bset #1,(1,a0)
        movem.l (sp)+,a0-a1
.actor_ok:
        dbf d2,.check_actor
        move.l a6,a0
        moveq #(S60_REC/4)-1,d2
.check_record:
        move.l (a0)+,d0
        cmp.l (a1)+,d0
        beq .record_ok
        movem.l a0-a1,-(sp)
        lea (s60_boss_case_error,pc),a0
        bset #2,(1,a0)
        movem.l (sp)+,a0-a1
.record_ok:
        dbf d2,.check_record
        move.l (s60_code,pc),a1
        adda.l #$10904,a1
        bsr s60_ai
        move.w d7,d0
        mulu #50,d0
        divu #12,d0
        add.w (a2),d0
        cmp.w ($40,a3),d0
        beq .speed_ok
        lea (s60_boss_case_error,pc),a0
        bset #3,(1,a0)
.speed_ok:
        move.w d7,d0
        mulu #12,d0
        add.w (4,a2),d0
        cmp.w ($14,a3),d0
        beq .pitch_ok
        lea (s60_boss_case_error,pc),a0
        bset #4,(1,a0)
.pitch_ok:
        IFD BOSS_PATH_TEST
        move.w d5,d0
        mulu #48,d0
        add.w d7,d0
        subq.w #1,d0
        mulu #12,d0
        lea (s60_boss_path_results+8,pc),a0
        adda.w d0,a0
        move.l (8,a3),(a0)+
        move.l (12,a3),(a0)+
        move.l (16,a3),(a0)+
        ENDC
        cmp.w #1,d7
        bne .sixth
        move.l (12,a3),(4,a5)
.sixth: cmp.w #6,d7
        bne .next
        move.l (12,a3),(8,a5)
.next:  addq.w #1,d7
        cmp.w #49,d7
        bne .tick
        move.l (12,a3),(12,a5)
        move.w (s60_boss_case_error,pc),d0
        move.w d0,(2,a5)
        lea (s60_boss_results,pc),a0
        tst.w d0
        beq .case_passed
        addq.w #1,(6,a0)
.case_passed:
        addq.w #1,(4,a0)
        move.l a6,a0
        moveq #(S60_REC/4)-1,d0
.clear_record:
        clr.l (a0)+
        dbf d0,.clear_record
        addq.w #1,d5
        cmp.w #8,d5
        bne .case
        rts
        ENDC
        ENDC
