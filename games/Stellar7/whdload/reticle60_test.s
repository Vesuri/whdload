        IFD VERIFY
        IFD RETICLE_TEST
        IFEQ RETICLE_CLOCK
        FAIL "RETICLE_TEST requires RETICLE_CLOCK=1"
        ENDC
s60_reticle_results: dc.b 'RT60'
        dc.w 0,0,0 ; cases, failures, comparisons
s60_reticle_counters: dc.w 0,1,7,8,15,16,$fff8,$ffff
s60_reticle_flush:
        movem.l d0-d1/a0-a2,-(sp)
        move.l (_resload,pc),a2
        jsr (resload_FlushCache,a2)
        movem.l (sp)+,d0-d1/a0-a2
        rts
s60_test_reticle:
        movem.l d0-d7/a0-a6,-(sp)
        move.w (s60_reticle_results+4,pc),d0
        bne .done
        move.l (s60_ticks,pc),d0
        cmp.l #RETICLE_TEST,d0
        bne .done
        lea (s60_reticle_results,pc),a3
        move.l (s60_code,pc),a5
        adda.l #$bd02,a5
        move.l (a5),-(sp)
        move.l (4,a5),-(sp)
        move.l (20,a5),-(sp)
        move.w ($1e96-S60_DATA,a4),-(sp)
        move.w ($46e0-S60_DATA,a4),-(sp)
        move.w ($43b2-S60_DATA,a4),-(sp)
        move.w (s60_running,pc),-(sp)
        move.w (s60_rendering,pc),-(sp)
        move.w (s60_logic,pc),-(sp)
        ; The original prologue pushes D2. Return immediately after its
        ; native cache update, before any rasterization, in both arms.
        move.l #$241f4e75,(20,a5)
        clr.w ($43b2-S60_DATA,a4) ; native empty-list oracle returns false
        moveq #0,d5
.case:  move.w d5,d0
        and.w #7,d0
        add.w d0,d0
        lea (s60_reticle_counters,pc),a0
        move.w (a0,d0.w),($1e96-S60_DATA,a4)
        move.b #1,($46e0-S60_DATA,a4)
        move.l (s60_reticle_original,pc),(a5)
        move.l (s60_reticle_original+4,pc),(4,a5)
        bsr s60_reticle_flush
        S60_CALL $bd00 ; real original gate and target test
        moveq #0,d6
        move.b ($46e0-S60_DATA,a4),d6
        move.l (20,sp),(a5)
        move.l (16,sp),(4,a5)
        bsr s60_reticle_flush
        move.w d5,d0
        lsr.w #3,d0
        and.w #1,d0
        lea (s60_running,pc),a0
        move.w d0,(a0)
        move.w d5,d0
        lsr.w #4,d0
        and.w #1,d0
        lea (s60_rendering,pc),a0
        move.w d0,(a0)
        move.w d5,d0
        lsr.w #5,d0
        and.w #1,d0
        lea (s60_logic,pc),a0
        move.w d0,(a0)
        move.b #1,($46e0-S60_DATA,a4)
        bsr s60_reticle_update
        moveq #1,d7
        btst #3,d5
        beq .update_expected
        btst #4,d5
        bne .update_expected
        btst #5,d5
        beq .update_expected
        move.w d6,d7
.update_expected:
        bsr .check
        move.b #1,($46e0-S60_DATA,a4)
        S60_CALL $bd00 ; installed draw hook, same early return
        moveq #1,d7
        btst #3,d5
        bne .draw_expected
        move.w d6,d7
.draw_expected:
        bsr .check
        addq.w #1,(4,a3)
        addq.w #1,d5
        cmp.w #64,d5
        bcs .case
        lea (s60_logic,pc),a0
        move.w (sp)+,(a0)
        lea (s60_rendering,pc),a0
        move.w (sp)+,(a0)
        lea (s60_running,pc),a0
        move.w (sp)+,(a0)
        move.w (sp)+,($43b2-S60_DATA,a4)
        move.w (sp)+,($46e0-S60_DATA,a4)
        move.w (sp)+,($1e96-S60_DATA,a4)
        move.l (sp)+,(20,a5)
        move.l (sp)+,(4,a5)
        move.l (sp)+,(a5)
        bsr s60_reticle_flush
.done:  movem.l (sp)+,d0-d7/a0-a6
        rts
.check: addq.w #1,(8,a3)
        cmp.b ($46e0-S60_DATA,a4),d7
        beq .checked
        addq.w #1,(6,a3)
.checked: rts
        ENDC
        ENDC
