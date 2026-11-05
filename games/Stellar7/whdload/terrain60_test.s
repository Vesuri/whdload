        IFD VERIFY
        IFD TERRAIN_TEST
; Compare actual installed contact hook with the copied native decrement.
; Only its following unconditional branch is temporarily made RTS.
s60_terrain_results:
        dc.b 'TR60'
        dc.w 0,0 ; cases, errors
        dc.l 0 ; checked continuous substeps
        dc.w 0,0,0 ; inactive, reset, intermittent checks
s60_terrain_native: ds.b 8
s60_terrain_render_saved: ds.l 2
s60_terrain_expected_tick: dc.l 0
s60_terrain_actors: ds.b 224
s60_terrain_energies: dc.w 1000,1,0,$8000
s60_terrain_contacts: dc.w 0,1,S60_SUBSTEPS/12,0,S60_SUBSTEPS-1,0,S60_SUBSTEPS,1,17*S60_SUBSTEPS/12,0,2*S60_SUBSTEPS,1,3*S60_SUBSTEPS,1,50*S60_SUBSTEPS/12,1
s60_terrain_test_flush:
        movem.l d0-d1/a0-a2,-(sp)
        move.l (_resload,pc),a2
        jsr (resload_FlushCache,a2)
        movem.l (sp)+,d0-d1/a0-a2
        rts
s60_terrain_test_hook:
        S60_CALL $36f8
        rts
s60_terrain_test_reference:
        move.w ($46c4-S60_DATA,a4),d5
        move.w d6,($46c4-S60_DATA,a4)
        bsr s60_terrain_native
        move.w ($46c4-S60_DATA,a4),d6
        move.w d5,($46c4-S60_DATA,a4)
        rts
s60_terrain_test_compare:
        cmp.w ($46c4-S60_DATA,a4),d6
        beq .ok
        addq.w #1,(6,a6)
.ok:    rts
s60_terrain_test_save_clock:
        lea (s60_terrain_render_saved,pc),a0
        move.l (a5),(a0)
        move.l (4,a5),(4,a0)
        rts
s60_terrain_test_check_clock:
        lea (s60_terrain_render_saved,pc),a0
        move.l (a0),d0
        cmp.l (a5),d0
        bne .bad
        move.l (4,a0),d0
        cmp.l (4,a5),d0
        beq .ok
.bad:   addq.w #1,(6,a6)
.ok:    rts
s60_test_terrain:
        move.l (s60_ticks,pc),d0
        cmp.l #TERRAIN_TEST,d0
        bne .done
        move.w (s60_terrain_results+4,pc),d0
        bne .done
        movem.l d0-d7/a0-a6,-(sp)
        lea (s60_terrain_state,pc),a5
        lea (s60_terrain_results,pc),a6
        move.w ($46c4-S60_DATA,a4),-(sp)
        move.l (s60_ticks,pc),-(sp)
        move.w (s60_phase,pc),-(sp)
        move.w (s60_logic,pc),-(sp)
        move.w (s60_running,pc),-(sp)
        move.w (s60_rendering,pc),-(sp)
        move.l (a5),-(sp)
        move.l (4,a5),-(sp)
        move.l (s60_code,pc),a0
        cmp.l #$600000a6,($36fe,a0)
        bne s60_bad
        move.w #$4e75,($36fe,a0)
        bsr s60_terrain_test_flush
        lea (s60_running,pc),a0
        move.w #1,(a0)
        moveq #0,d4
.case:
        bsr s60_terrain_reset
        move.l (a5),d0
        or.l (4,a5),d0
        beq .reset_ok
        addq.w #1,(6,a6)
.reset_ok:
        addq.w #1,(14,a6)
        moveq #0,d0
        move.w d4,d0
        divu #S60_SUBSTEPS,d0
        move.w d0,d7
        and.w #3,d7
        add.w d7,d7
        lea (s60_terrain_energies,pc),a0
        move.w (a0,d7.w),d6
        move.w d6,($46c4-S60_DATA,a4)
        swap d0
        moveq #0,d3
        move.w d0,d3
        lea (s60_phase,pc),a0
        move.w d3,(a0)
        cmp.w #4*S60_SUBSTEPS,d4
        bcs .base_ready
        add.l #$fffffff8,d3
.base_ready:
        moveq #0,d2
        moveq #0,d7
.step:
        move.l d3,d0
        add.l d2,d0
        lea (s60_ticks,pc),a0
        move.l d0,(a0)
        move.w d2,d0
        and.w #1,d0
        lea (s60_logic,pc),a0
        move.w d0,(a0)
        lea (s60_terrain_actors,pc),a3
        tst.w d0
        beq .actor_ready
        adda.w #112,a3
.actor_ready:
        bsr s60_terrain_test_save_clock
        lea (s60_rendering,pc),a0
        move.w #1,(a0)
        bsr s60_terrain_test_hook
        bsr s60_terrain_test_compare ; render must neither damage nor consume time
        bsr s60_terrain_test_check_clock
        lea (s60_rendering,pc),a0
        clr.w (a0)
        tst.w d7
        bne .not_due
        bsr s60_terrain_test_reference
        lea (s60_terrain_expected_tick,pc),a0
        move.l (s60_ticks,pc),(a0)
        moveq #S60_SUBSTEPS,d7
.not_due:
        bsr s60_terrain_test_hook
        bsr s60_terrain_test_hook ; duplicate contact at this tick
        bsr s60_terrain_test_compare
        cmp.w #1,(a5)
        bne .clock_bad
        move.l (s60_terrain_expected_tick,pc),d0
        cmp.l (4,a5),d0
        beq .clock_ok
.clock_bad:
        addq.w #1,(6,a6)
.clock_ok:
        addq.l #1,(8,a6)
        subq.w #1,d7
        addq.w #1,d2
        cmp.w #3*S60_SUBSTEPS,d2
        bne .step
        addq.w #1,(4,a6)
        addq.w #1,d4
        cmp.w #8*S60_SUBSTEPS,d4
        bne .case
        ; Gaps need elapsed-time comparison, not a count of contact calls.
        bsr s60_terrain_reset
        move.w #1000,d6
        move.w d6,($46c4-S60_DATA,a4)
        lea (s60_terrain_contacts,pc),a2
        moveq #7,d7
.contact:
        moveq #0,d0
        move.w (a2)+,d0
        lea (s60_ticks,pc),a0
        move.l d0,(a0)
        tst.w (a2)+
        beq .no_reference
        bsr s60_terrain_test_reference
.no_reference:
        bsr s60_terrain_test_hook
        bsr s60_terrain_test_hook
        bsr s60_terrain_test_compare
        addq.w #1,(16,a6)
        dbf d7,.contact
        ; Outside simulation every call remains native, even with rendering set.
        bsr s60_terrain_test_save_clock
        lea (s60_running,pc),a0
        clr.w (a0)
        lea (s60_rendering,pc),a0
        move.w #1,(a0)
        lea (s60_terrain_energies,pc),a2
        moveq #3,d7
.inactive:
        move.w (a2)+,d6
        move.w d6,($46c4-S60_DATA,a4)
        bsr s60_terrain_test_reference
        bsr s60_terrain_test_hook
        bsr s60_terrain_test_compare
        bsr s60_terrain_test_check_clock
        addq.w #1,(12,a6)
        dbf d7,.inactive
        move.l (s60_code,pc),a0
        move.w #$6000,($36fe,a0)
        bsr s60_terrain_test_flush
        move.l (sp)+,(4,a5)
        move.l (sp)+,(a5)
        lea (s60_rendering,pc),a0
        move.w (sp)+,(a0)
        lea (s60_running,pc),a0
        move.w (sp)+,(a0)
        lea (s60_logic,pc),a0
        move.w (sp)+,(a0)
        lea (s60_phase,pc),a0
        move.w (sp)+,(a0)
        lea (s60_ticks,pc),a0
        move.l (sp)+,(a0)
        move.w (sp)+,($46c4-S60_DATA,a4)
        movem.l (sp)+,d0-d7/a0-a6
.done:  rts
        ENDC
        ENDC
