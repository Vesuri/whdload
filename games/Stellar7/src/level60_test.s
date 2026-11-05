        IFD VERIFY
        IFD LEVEL_TEST
        IFD DEATH_TEST
        IFND DEATH_NATURAL
        FAIL "LEVEL_TEST and injected DEATH_TEST must run separately"
        ELSE
        IFLE DEATH_TEST-LEVEL_TEST
        FAIL "DEATH_NATURAL must arm after the requested level transitions"
        ENDC
        ENDC
        ENDC
        IFND LEVEL_LAST
LEVEL_LAST = 1
        ENDC
        IFLT LEVEL_LAST-1
        FAIL "LEVEL_LAST must be 1..6"
        ENDC
        IFGT LEVEL_LAST-6
        FAIL "LEVEL_LAST must be 1..6"
        ENDC
; Request level exits until LEVEL_LAST: normally at update end, or at native
; $2b4e with LEVEL_EARLY. Cleanup, loading and level increment remain native.
; LEVEL_OBSERVE instead records an inactive, non-death update without writing
; game/private simulation state. It observes ordinary +1 level transitions.
; This is not by itself a boss-kill or collision-trigger oracle.
        IFD LEVEL_OBSERVE
        IFD LEVEL_EARLY
        FAIL "LEVEL_OBSERVE must observe the completed update"
        ENDC
        ENDC
        IFD LEVEL_EARLY
s60_test_level_early:
        bsr s60_test_level
        tst.b ($1e53-S60_DATA,a4) ; replay displaced TST for native BEQ $2b54
        rts
        ENDC
s60_level_results:
        IFD LEVEL_OBSERVE
        dc.b 'W762'
        ELSE
        dc.b 'W761'
        ENDC
        dc.w 0,0 ; stage, errors
        ds.l 8 ; trigger/exit ticks, exit/resume fields, last/credit/ticks/renders
        ds.w 4 ; exit/resume level, phase, death
        ds.l 2 ; old/new session
        ds.w 2 ; resumed energy, exit active
        dc.w 0,LEVEL_LAST ; completed transitions, requested destination
        ds.b 6*60 ; full result record for each transition, preserving earlier checks
s60_level_regions:
        dc.w s60_star_remainders-s60_level_results,100
        dc.w s60_jump_state-s60_level_results,6
        dc.w s60_cooldown_state-s60_level_results,6
        dc.w s60_power_state-s60_level_results,10
        dc.w s60_knock_state-s60_level_results,3
        dc.w s60_pickup_state-s60_level_results,8
        dc.w s60_shake_state-s60_level_results,4
        dc.w s60_terrain_state-s60_level_results,4
        dc.w 0,0
s60_level_error:
        addq.w #1,(6,a2)
        rts
s60_test_level:
        movem.l d0/a0,-(sp)
        move.l (s60_ticks,pc),d0
        IFD LEVEL_OBSERVE
        tst.b ($1e53-S60_DATA,a4)
        bne .done
        tst.w ($1e90-S60_DATA,a4)
        bne .done
        ELSE
        cmp.l #LEVEL_TEST,d0
        bne .done
        ENDC
        lea (s60_level_results,pc),a0
        cmp.w #LEVEL_LAST,($46a0-S60_DATA,a4)
        bge .done
        tst.w (4,a0)
        beq .request
        cmp.w #3,(4,a0)
        bne .done
.request:
        move.w #1,(4,a0)
        move.l d0,(8,a0)
        move.w ($46a0-S60_DATA,a4),(40,a0)
        move.l (s60_sessions,pc),(48,a0)
        IFND LEVEL_OBSERVE
        lea (s60_terrain_state,pc),a0
        move.w #1,(a0)
        move.l d0,(4,a0) ; populate a real private clock before transition
        clr.b ($1e53-S60_DATA,a4)
        ENDC
.done:  movem.l (sp)+,d0/a0
        rts
s60_test_level_exit:
        movem.l d0/a2,-(sp)
        lea (s60_level_results,pc),a2
        cmp.w #1,(4,a2)
        bne .done
        move.w #2,(4,a2)
        move.l (s60_ticks,pc),(12,a2)
        move.l ($24a8-S60_DATA,a4),(16,a2)
        moveq #0,d0
        move.b ($1e53-S60_DATA,a4),d0
        move.w d0,(58,a2)
        bne .bad
        tst.w ($1e90-S60_DATA,a4)
        bne .bad
        IFD LEVEL_OBSERVE
        move.l (8,a2),d0
        addq.l #1,d0
        cmp.l (12,a2),d0
        ELSE
        cmp.l #LEVEL_TEST+1,(12,a2)
        ENDC
        beq .done
.bad:   bsr s60_level_error
.done:  movem.l (sp)+,d0/a2
        rts
s60_test_level_resume:
        movem.l d0-d2/a0-a2,-(sp)
        lea (s60_level_results,pc),a2
        cmp.w #2,(4,a2)
        bne .done
        move.w #3,(4,a2)
        move.l ($24a8-S60_DATA,a4),(20,a2)
        move.l (s60_last,pc),(24,a2)
        move.l (s60_credit,pc),(28,a2)
        move.l (s60_ticks,pc),(32,a2)
        move.l (s60_renders,pc),(36,a2)
        move.w ($46a0-S60_DATA,a4),(42,a2)
        move.w (s60_phase,pc),(44,a2)
        move.w ($1e90-S60_DATA,a4),(46,a2)
        move.l (s60_sessions,pc),(52,a2)
        move.w ($46c4-S60_DATA,a4),(56,a2)
        move.l (48,a2),d0
        addq.l #1,d0
        cmp.l (52,a2),d0
        bne .bad
        move.w (40,a2),d0
        addq.w #1,d0
        cmp.w (42,a2),d0
        bne .bad
        tst.l (32,a2)
        bne .bad
        tst.l (36,a2)
        bne .bad
        tst.w (44,a2)
        bne .bad
        tst.w (46,a2)
        bne .bad
        moveq #0,d0
        move.w (s60_field_hz,pc),d0
        cmp.l (28,a2),d0
        beq .state
.bad:   bsr s60_level_error
.state: move.l (s60_motion_table,pc),a0
        move.w #S60_SLOTS*S60_REC/2-1,d0
        bsr .zero
        lea (s60_level_regions,pc),a1
.region:
        move.w (a1)+,d0
        beq .record
        move.l a2,a0
        adda.w d0,a0
        move.w (a1)+,d0
        subq.w #1,d0
        bsr .zero
        bra .region
.record:
        moveq #0,d0
        move.w (60,a2),d0
        cmp.w #6,d0
        bcs .save
        bsr s60_level_error
        bra .done
.save:  mulu #60,d0
        lea (64,a2),a0
        adda.l d0,a0
        move.l a2,a1
        moveq #14,d1
.copy:  move.l (a1)+,(a0)+
        dbf d1,.copy
        addq.w #1,(60,a2)
        bra .done
.zero:  moveq #0,d1
.word:  or.w (a0)+,d1
        dbf d0,.word
        tst.w d1
        bne s60_level_error
        rts
.done:  movem.l (sp)+,d0-d2/a0-a2
        rts
        ENDC
        ENDC
