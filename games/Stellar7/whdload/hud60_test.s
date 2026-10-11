        IFD VERIFY
        IFD HUD_TEST
        IFEQ HUD_CLOCK
        FAIL "HUD_TEST requires HUD_CLOCK=1"
        ENDC
s60_hud_results: dc.b 'HT60'
        dc.w 0,0 ; cases, failures
        dc.l 0 ; checked substeps
        dc.w 0,0,0 ; render, inactive, hide/reappear checks
s60_hud_positions: dc.w 128,132,154,176,180,$7fff,$8000,-1
s60_hud_steps: dc.w 4,-4,0,$7fff
s60_hud_test_flush:
        movem.l d0-d1/a0-a2,-(sp)
        move.l (_resload,pc),a2
        jsr (resload_FlushCache,a2)
        movem.l (sp)+,d0-d1/a0-a2
        rts
s60_hud_reference:
        move.l ($1f5c-S60_DATA,a4),d7
        move.l d6,($1f5c-S60_DATA,a4)
        bsr s60_hud_native
        move.l ($1f5c-S60_DATA,a4),d6
        move.l d7,($1f5c-S60_DATA,a4)
        rts
s60_hud_check:
        cmp.l ($1f5c-S60_DATA,a4),d6
        beq .done
        addq.w #1,(6,a5)
.done:  rts
s60_test_hud:
        movem.l d0-d7/a0-a6,-(sp)
        move.w (s60_hud_results+4,pc),d0
        bne .done
        move.l (s60_ticks,pc),d0
        cmp.l #HUD_TEST,d0
        bne .done
        lea (s60_hud_results,pc),a5
        lea (s60_hud_state,pc),a6
        move.l (s60_ticks,pc),-(sp)
        move.l ($1f5c-S60_DATA,a4),-(sp)
        move.w ($1e72-S60_DATA,a4),-(sp)
        move.w (s60_running,pc),-(sp)
        move.w (s60_rendering,pc),-(sp)
        move.l (a6),-(sp)
        move.w (4,a6),-(sp)
        move.l (s60_code,pc),a0
        adda.l #$c3ea,a0
        cmp.w #$3039,(a0)
        bne s60_bad
        move.w #$4e75,(a0) ; return before rasterization, both hook modes
        bsr s60_hud_test_flush
        moveq #0,d5
.case:  bsr s60_hud_reset
        lea (s60_running,pc),a0
        move.w #1,(a0)
        lea (s60_rendering,pc),a0
        clr.w (a0)
        move.w #51,($1e72-S60_DATA,a4)
        btst #5,d5
        beq .seed
        move.w #50,($1e72-S60_DATA,a4)
.seed:  move.w d5,d0
        and.w #7,d0
        add.w d0,d0
        lea (s60_hud_positions,pc),a0
        move.w (a0,d0.w),($1f5c-S60_DATA,a4)
        move.w d5,d0
        lsr.w #3,d0
        and.w #3,d0
        add.w d0,d0
        lea (s60_hud_steps,pc),a0
        move.w (a0,d0.w),($1f5e-S60_DATA,a4)
        move.l ($1f5c-S60_DATA,a4),d6
        moveq #0,d4
.tick:  move.l #$fffffff0,d0
        add.l d5,d0
        add.l d4,d0
        lea (s60_ticks,pc),a0
        move.l d0,(a0)
        btst #5,d5
        bne .update
        move.l d4,d0
        divu #12,d0
        swap d0
        tst.w d0
        bne .update
        bsr s60_hud_reference
.update:
        bsr s60_hud_update
        bsr s60_hud_check
        bsr s60_hud_update ; repeated call in the same tick must not advance
        bsr s60_hud_check
        move.l (a6),d2
        move.w (4,a6),d3
        lea (s60_rendering,pc),a0
        move.w #1,(a0)
        bsr s60_hud_update
        S60_CALL $c3ba
        S60_CALL $c3ba
        bsr s60_hud_check
        cmp.l (a6),d2
        bne .clock_bad
        cmp.w (4,a6),d3
        beq .render_ok
.clock_bad:
        addq.w #1,(6,a5)
.render_ok:
        addq.w #1,(12,a5)
        lea (s60_rendering,pc),a0
        clr.w (a0)
        addq.l #1,(8,a5)
        addq.w #1,d4
        cmp.w #36,d4
        bne .tick
        lea (s60_running,pc),a0
        clr.w (a0)
        bsr s60_hud_update
        bsr s60_hud_check
        bsr s60_hud_reference
        S60_CALL $c3ba ; inactive callers retain the native step
        bsr s60_hud_check
        addq.w #1,(14,a5)
        lea (s60_running,pc),a0
        move.w #1,(a0)
        move.w #50,($1e72-S60_DATA,a4)
        bsr s60_hud_update
        move.l (a6),d0
        moveq #0,d1
        move.w (4,a6),d1
        or.l d1,d0
        beq .reset_ok
        addq.w #1,(6,a5)
.reset_ok:
        move.w #51,($1e72-S60_DATA,a4)
        bsr s60_hud_reference
        bsr s60_hud_update ; immediate on reappearance, even at same tick
        bsr s60_hud_check
        addq.w #1,(16,a5)
        addq.w #1,(4,a5)
        addq.w #1,d5
        cmp.w #64,d5
        bne .case
        move.l (s60_code,pc),a0
        adda.l #$c3ea,a0
        move.w #$3039,(a0)
        bsr s60_hud_test_flush
        move.w (sp)+,(4,a6)
        move.l (sp)+,(a6)
        lea (s60_rendering,pc),a0
        move.w (sp)+,(a0)
        lea (s60_running,pc),a0
        move.w (sp)+,(a0)
        move.w (sp)+,($1e72-S60_DATA,a4)
        move.l (sp)+,($1f5c-S60_DATA,a4)
        lea (s60_ticks,pc),a0
        move.l (sp)+,(a0)
.done:  movem.l (sp)+,d0-d7/a0-a6
        rts
        ENDC
        ENDC
