; VERIFY-only comparison of the real native separation loop at $3740.
; Fake actors isolate geometry; globals are restored before normal play resumes.
; A bounded watchdog records failure and separates the fake pair after 64 tries.
        IFD VERIFY
        IFD COLLISION_TEST
s60_collision_results:
        dc.b 'C760'
        dc.w 0,0 ; completed cases, failed cases
        ds.b 4*44 ; speed, expected/actual calls, forced, positions, bounce, padding
s60_collision_mode: dc.w 0
s60_collision_calls: dc.w 0
s60_collision_forced: dc.w 0
s60_collision_speeds: dc.w 0,1,-1,12
s60_collision_actors: ds.b 224
s60_collision_install:
        move.l (s60_code,pc),a1
        cmp.l #$7e00be79,($37a6,a1)
        bne s60_bad
        rts
; Temporarily return at the two-byte loop initializer while the isolated
; fragment is called. Normal loop-back branches still enter unchanged $37a8.
s60_collision_gate:
        move.l (s60_code,pc),a0
        move.w d0,($37a6,a0)
        movem.l a2,-(sp)
        move.l (_resload,pc),a2
        jsr (resload_FlushCache,a2)
        movem.l (sp)+,a2
        rts
s60_collision_probe:
        move.w (s60_collision_mode,pc),d0
        beq .done
        lea (s60_collision_calls,pc),a0
        addq.w #1,(a0)
        cmp.w #64,(a0)
        bls .done
        move.w #1,(2,a0)
        lea (s60_collision_actors,pc),a0
        move.l #1000,(8,a0) ; watchdog makes the native overlap test false
.done:  rts
s60_collision_setup:
        lea (s60_collision_actors,pc),a0
        moveq #55,d0
.clear: clr.l (a0)+
        dbf d0,.clear
        lea (s60_collision_actors,pc),a3
        move.l #20,(4,a3)
        move.l #20,(116,a3)
        move.w #1,(114,a3)
        lea (s60_collision_speeds,pc),a0
        move.w (a0,d5.w),($40,a3)
        lea (s60_collision_calls,pc),a0
        clr.l (a0)
        rts
s60_collision_run:
        lea (s60_collision_actors+112,pc),a3
        S60_TAIL $3740
s60_test_collision:
        move.l (s60_ticks,pc),d0
        cmp.l #COLLISION_TEST,d0
        bne .done
        move.w (s60_collision_results+4,pc),d0
        bne .done ; a native retry resets ticks, not this once-only fixture
        movem.l d2-d7/a2-a6,-(sp)
        move.l ($43c0-S60_DATA,a4),-(sp)
        move.w ($1e9e-S60_DATA,a4),-(sp)
        move.w ($026c-S60_DATA,a4),-(sp)
        move.l (s60_knock_state,pc),-(sp)
        move.w (s60_knock_state+4,pc),-(sp)
        lea (s60_collision_actors,pc),a0
        move.l a0,($43c0-S60_DATA,a4)
        move.w #1,($1e9e-S60_DATA,a4) ; avoid unrelated collision sound
        move.w #$4e75,d0
        bsr s60_collision_gate
        lea (s60_collision_results+8,pc),a2
        moveq #0,d5
.case:
        bsr s60_collision_setup
        move.w ($40,a3),(a2)
        lea (s60_running,pc),a0
        clr.w (a0) ; original undo for the reference loop
        lea (s60_collision_mode,pc),a0
        move.w #2,(a0)
        bsr s60_collision_run
        move.w (s60_collision_calls,pc),(2,a2)
        lea (s60_collision_actors,pc),a3
        move.l (8,a3),(8,a2)
        move.l (12,a3),(12,a2)
        move.l (16,a3),(16,a2)
        move.w ($40,a3),(32,a2)
        bsr s60_collision_setup
        bsr s60_motion_record
        move.w #1,(56,a6)
        move.w #2,(58,a6)
        move.w #3,(60,a6)
        move.w #7,(14,a6)
        move.w #8,(16,a6)
        move.w #9,(18,a6)
        clr.l (20,a6)
        move.w ($40,a3),d0
        ext.l d0
        divs #S60_SUBSTEPS,d0
        ext.l d0
        move.l d0,(24,a6)
        clr.l (28,a6)
        lea (s60_running,pc),a0
        move.w #1,(a0)
        lea (s60_collision_mode,pc),a0
        move.w #1,(a0)
        bsr s60_collision_run
        move.w (s60_collision_calls,pc),(4,a2)
        move.w (s60_collision_forced,pc),(6,a2)
        lea (s60_collision_actors,pc),a3
        move.l (8,a3),(20,a2)
        move.l (12,a3),(24,a2)
        move.l (16,a3),(28,a2)
        move.w ($40,a3),(34,a2)
        moveq #0,d2
.compare:
        move.l (8,a2,d2.w),d0
        cmp.l (20,a2,d2.w),d0
        bne .failed
        addq.w #4,d2
        cmp.w #12,d2
        bne .compare
        move.w (2,a2),d0
        cmp.w (4,a2),d0
        bne .failed
        move.w (32,a2),d0
        cmp.w (34,a2),d0
        bne .failed
        cmp.w #1,(14,a6)
        bne .failed
        cmp.w #2,(16,a6)
        bne .failed
        cmp.w #3,(18,a6)
        bne .failed
        tst.w (6,a2)
        bne .failed
        ; Ordinary undo must still reverse exactly one fractional displacement.
        move.w #2,(36,a2)
        move.l #100,(8,a3)
        move.l #200,(12,a3)
        move.l #300,(16,a3)
        move.l #2,(20,a6)
        move.l #-3,(24,a6)
        move.l #4,(28,a6)
        move.w #7,(14,a6)
        move.w #8,(16,a6)
        move.w #9,(18,a6)
        move.l a3,-(sp)
        S60_CALL $87ea
        addq.l #4,sp
        cmp.l #98,(8,a3)
        bne .failed
        cmp.l #203,(12,a3)
        bne .failed
        cmp.l #296,(16,a3)
        bne .failed
        cmp.w #1,(14,a6)
        bne .failed
        cmp.w #2,(16,a6)
        bne .failed
        cmp.w #3,(18,a6)
        bne .failed
        move.w #1,(36,a2)
        bra .passed
.failed:
        lea (s60_collision_results+6,pc),a0
        addq.w #1,(a0)
.passed:
        lea (s60_collision_results+4,pc),a0
        addq.w #1,(a0)
        move.l a6,a0
        moveq #(S60_REC/4)-1,d0
.forget: clr.l (a0)+
        dbf d0,.forget
        addq.w #2,d5
        adda.w #44,a2
        cmp.w #8,d5
        bne .case
        lea (s60_collision_mode,pc),a0
        clr.w (a0)
        lea (s60_knock_state,pc),a0
        move.w (sp)+,(4,a0)
        move.l (sp)+,(a0)
        move.w (sp)+,($026c-S60_DATA,a4)
        move.w (sp)+,($1e9e-S60_DATA,a4)
        move.l (sp)+,($43c0-S60_DATA,a4)
        move.w #$7e00,d0
        bsr s60_collision_gate
        movem.l (sp)+,d2-d7/a2-a6
.done:  rts
        ENDC
        ENDC
