        IFD VERIFY
        IFD DEATH_TEST
; Observe natural combat death, or inject one lethal energy value.
; Only dialog/menu inputs are supplied; cleanup/retry/new-game allocation is native.
; DEATH_DECLINE selects No and observes the native main menu before Begin.
; DEATH_NATURAL arms observation at DEATH_TEST without writing player energy.
s60_death_results:
        dc.b 'R760'
        dc.w 0,0 ; stage: 0 idle, 1 armed/lethal, 2 answered, 3 resumed; errors
        ds.l 10 ; arm/injection tick, exit tick/field, dialog start/answer,
                ; resumed field/credit/last/ticks/renders
        ds.w 9 ; resumed phase/energy/level/death, exit energy/active/death,
               ; resumed session, observed Continue dialogs
        IFD DEATH_NATURAL
        dc.b 'RN61'
        dc.l 0 ; session when armed (offset 70)
        dc.w 0 ; level when armed (offset 74)
        ENDC
        IFD DEATH_DECLINE
s60_death_menu_record:
        dc.b 'ND60'
        dc.w 0,0 ; post-death menu count, running state
        dc.l 0,0 ; menu tick, field
        dc.w 0,0 ; menu session, dialog choice
s60_test_death_menu:
        movem.l d0/a0,-(sp)
        lea (s60_death_results,pc),a0
        cmp.w #2,(4,a0)
        bne .done
        addq.w #1,(s60_death_menu_record-s60_death_results+4,a0)
        move.w (s60_running,pc),(s60_death_menu_record-s60_death_results+6,a0)
        move.l (s60_ticks,pc),(s60_death_menu_record-s60_death_results+8,a0)
        move.l ($24a8-S60_DATA,a4),(s60_death_menu_record-s60_death_results+12,a0)
        move.l (s60_sessions,pc),d0
        move.w d0,(s60_death_menu_record-s60_death_results+16,a0)
.done:  movem.l (sp)+,d0/a0
        rts
        ENDC
s60_death_error:
        addq.w #1,(6,a2)
        rts
s60_test_death:
        move.l (s60_ticks,pc),d0
        cmp.l #DEATH_TEST,d0
        bne .done
        lea (s60_death_results,pc),a0
        tst.w (4,a0)
        bne .done ; never reinject after a retry resets the simulation tick
        move.w #1,(4,a0)
        move.l d0,(8,a0)
        IFD DEATH_NATURAL
        move.l (s60_sessions,pc),(70,a0)
        move.w ($46a0-S60_DATA,a4),(74,a0)
        ELSE
        move.w #-1,($46c4-S60_DATA,a4)
        ENDC
        IFD TERRAIN_TEST
        ; Ensure retry proves clearing an occupied terrain clock, not just zero.
        lea (s60_terrain_state,pc),a0
        move.w #1,(a0)
        move.l d0,(4,a0)
        ENDC
.done:  rts
s60_test_death_exit:
        movem.l d0/a0/a2,-(sp)
        lea (s60_death_results,pc),a2
        cmp.w #1,(4,a2)
        bne .done
        move.l (s60_ticks,pc),(12,a2)
        move.l ($24a8-S60_DATA,a4),(16,a2)
        move.w ($46c4-S60_DATA,a4),(56,a2)
        moveq #0,d0
        move.b ($1e53-S60_DATA,a4),d0
        move.w d0,(58,a2)
        move.w ($1e90-S60_DATA,a4),(60,a2)
        cmp.l #DEATH_TEST+1,(12,a2)
        IFD DEATH_NATURAL
        bcs .bad
        ELSE
        bne .bad
        ENDC
        tst.w (56,a2)
        bpl .bad
        tst.w (58,a2)
        bne .bad
        cmp.w #1,(60,a2)
        beq .done
.bad:   bsr s60_death_error
.done:  movem.l (sp)+,d0/a0/a2
        rts
s60_test_death_dialog:
        ; Called from the dialog wrapper, so its first argument is at 8(sp).
        movem.l d0/a0/a2,-(sp)
        lea (s60_death_results,pc),a2
        cmp.w #1,(4,a2)
        bne .done
        lea ($2310-S60_DATA,a4),a0 ; native "CONTINUE?" text
        cmpa.l (20,sp),a0
        bne .bad
        addq.w #1,(64,a2)
        move.w (s60_running,pc),d0
        beq .done ; the scheduler must be inactive during native death/retry
.bad:   bsr s60_death_error
.done:  movem.l (sp)+,d0/a0/a2
        rts
s60_test_death_poll:
        move.l a0,-(sp)
        lea (s60_death_results,pc),a0
        move.l ($24a8-S60_DATA,a4),d0
        tst.l (20,a0)
        bne .elapsed
        move.l d0,(20,a0)
.elapsed:
        sub.l (20,a0),d0
        cmp.l #60,d0
        bcs .wait
        move.l ($24a8-S60_DATA,a4),(24,a0)
        move.w #2,(4,a0)
        IFD DEATH_DECLINE
        IFD DEATH_BAD_DECLINE
        moveq #1,d0 ; negative control: retry instead of returning to the menu
        ELSE
        moveq #2,d0 ; native No selection; the original game returns to its menu
        ENDC
        move.w d0,(s60_death_menu_record-s60_death_results+18,a0)
        ELSE
        moveq #1,d0 ; select Yes using the native dialog polling result
        ENDC
        bra .done
.wait:  moveq #0,d0
.done:  move.l (sp)+,a0
        move.l d0,d7 ; displaced MOVE.L D0,D7
        rts
s60_death_zero_regions:
        dc.w s60_star_remainders-s60_death_results,100
        dc.w s60_jump_state-s60_death_results,6
        dc.w s60_cooldown_state-s60_death_results,6
        dc.w s60_power_state-s60_death_results,10
        dc.w s60_knock_state-s60_death_results,3
        dc.w s60_pickup_state-s60_death_results,8
        dc.w s60_shake_state-s60_death_results,4
        dc.w s60_terrain_state-s60_death_results,4
        IFNE HUD_CLOCK
        dc.w s60_hud_state-s60_death_results,3
        ENDC
        dc.w 0,0
s60_test_death_resume:
        movem.l d0-d2/a0-a2,-(sp)
        lea (s60_death_results,pc),a2
        cmp.w #2,(4,a2)
        bne .done
        move.w #3,(4,a2)
        IFD DEATH_DECLINE
        cmp.w #1,(s60_death_menu_record-s60_death_results+4,a2)
        beq .menu_seen
        bsr s60_death_error
.menu_seen:
        ENDC
        move.l ($24a8-S60_DATA,a4),(28,a2)
        move.l (s60_credit,pc),(32,a2)
        move.l (s60_last,pc),(36,a2)
        move.l (s60_ticks,pc),(40,a2)
        move.l (s60_renders,pc),(44,a2)
        move.w (s60_phase,pc),(48,a2)
        move.w ($46c4-S60_DATA,a4),(50,a2)
        move.w ($46a0-S60_DATA,a4),(52,a2)
        move.w ($1e90-S60_DATA,a4),(54,a2)
        move.l (s60_sessions,pc),d0
        move.w d0,(62,a2)
        IFD DEATH_NATURAL
        move.l (70,a2),d1
        addq.l #1,d1
        cmp.l d1,d0
        ELSE
        cmp.l #2,d0
        ENDC
        bne .bad
        tst.l (40,a2)
        bne .bad
        tst.l (44,a2)
        bne .bad
        tst.w (48,a2)
        bne .bad
        cmp.w #680,(50,a2)
        bne .bad
        IFD DEATH_DECLINE
        tst.w (52,a2)
        ELSE
        IFD DEATH_NATURAL
        move.w (74,a2),d0
        cmp.w (52,a2),d0
        ELSE
        tst.w (52,a2)
        ENDC
        ENDC
        bne .bad
        tst.w (54,a2)
        bne .bad
        moveq #0,d0
        move.w (s60_field_hz,pc),d0
        cmp.l (32,a2),d0
        bne .bad
        cmp.w #1,(64,a2)
        beq .state
.bad:   bsr s60_death_error
.state: move.l (s60_motion_table,pc),a0
        move.w #S60_SLOTS*S60_REC/2-1,d0
        bsr .zero
        lea (s60_death_zero_regions,pc),a1
.region:
        move.w (a1)+,d0
        beq .done
        move.l a2,a0
        adda.w d0,a0
        move.w (a1)+,d0
        subq.w #1,d0
        bsr .zero
        bra .region
.zero:  moveq #0,d1
.word:  or.w (a0)+,d1
        dbf d0,.word
        tst.w d1
        bne s60_death_error
        rts
.done:  movem.l (sp)+,d0-d2/a0-a2
        rts
        ENDC
        ENDC
