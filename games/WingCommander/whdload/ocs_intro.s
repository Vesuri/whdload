; OCS world intro uses the flight scheduler and bounded presentation, without
; enabling flight input, player integration, simulator events or fault polling.
intro_start:
        movem.l d0-d7/a0-a6,-(sp)
        bsr.w timing_rate
        lea ocs_clock_hz(pc),a0
        move.l d0,(a0)
        bsr.w ocs_clock_rebase
        lea intro_active(pc),a0
        move.w #1,(a0)
        bsr.w ocs_prediction_snapshot
        movem.l (sp)+,d0-d7/a0-a6
        rts
intro_stop:
        movem.l d0-d7/a0-a6,-(sp)
        bsr.w timing_scene_end
        bsr.w ocs_publish_drain
        lea intro_active(pc),a0
        clr.w (a0)
        bsr.w ocs_clock_rebase
        movem.l (sp)+,d0-d7/a0-a6
        rts

; Sample once per batch; feed at most one tick's fields to the common clock.
; Four issued ticks maximum. Excess time remains behind the cursor, not dropped.
intro_due:
        movem.l d1-d5/a0,-(sp)
        move.l -2048(a4),d4
        moveq #0,d5
.next:
        move.l d4,d0
        sub.l ocs_clock_state(pc),d0
        beq.s .done
        move.l ocs_clock_hz(pc),d1
        divu.w #10,d1
        cmp.l d1,d0
        bls.s .advance
        move.l d1,d0
.advance:
        add.l ocs_clock_state(pc),d0
        move.l ocs_clock_hz(pc),d1
        moveq #1,d2
        lea ocs_clock_state(pc),a0
        bsr.w timing_advance
        add.w d0,d5
        cmpi.w #4,d5
        blo.s .next
.done:
        moveq #0,d0
        move.w d5,d0
        movem.l (sp)+,d1-d5/a0
        rts

intro_world:
        movem.l d0-d7/a0-a6,-(sp)
        jsr OCS_WORLD
        jsr OCS_FLASH
        jsr OCS_GEOMETRY
        moveq #0,d0
        tst.l 2308(a4)
        beq.s .arg
        moveq #1,d0
.arg:
        move.w d0,-(sp)
        jsr OCS_DEBRIS
        addq.l #2,sp
        jsr OCS_FLAMES
        bsr.w ocs_exhaust_capture
        jsr OCS_ATTACHMENTS
        tst.l 2308(a4)
        beq.s .snapshot
        move.w 2272(a4),-(sp)
        move.w 2268(a4),2272(a4)
        jsr OCS_ASTEROIDS
        move.w (sp)+,2272(a4)
.snapshot:
        bsr.w ocs_prediction_snapshot
        lea ocs_intro_completed(pc),a0
        addq.l #1,(a0)
intro_world_done:
        movem.l (sp)+,d0-d7/a0-a6
        rts

intro_flash_draw:
        tst.w intro_active(pc)
        bne.s .done
        jmp OCS_FLASH
.done: rts
intro_draw:
        movem.l d0-d7/a0-a6,-(sp)
        bsr.w ocs_prediction_begin
        lea intro_game_seed(pc),a0
        move.l -4196(a4),(a0)
        move.l ocs_clock_render_seed(pc),-4196(a4)
        move.w #1,-32592(a4)
        jsr OCS_INTRO_DRAW
        movem.l (sp)+,d0-d7/a0-a6
        rts
intro_finish:
        movem.l d0-d7/a0-a6,-(sp)
        jsr OCS_FINISH
        lea ocs_clock_render_seed(pc),a0
        move.l -4196(a4),(a0)
        move.l intro_game_seed(pc),-4196(a4)
        bsr.w ocs_prediction_end
        movem.l (sp)+,d0-d7/a0-a6
        rts
intro_credits_update:
        movem.l d0-d7/a0-a6,-(sp)
        tst.w intro_active(pc)
        bne.s .ready
        bsr.w intro_start
.ready:
        bsr.w intro_due
        move.w d0,d4
.loop:
        tst.w d4
        beq.s .done
        bsr.w intro_world
        subq.w #1,d4
        bra.s .loop
.done:
        movem.l (sp)+,d0-d7/a0-a6
        rts
intro_credits_end:
        bsr.w intro_stop
        tst.b d3
        beq.s .repeat
        jmp OCS_INTRO_EXIT
.repeat:
        jmp OCS_INTRO_REPEAT
        cnop 0,4
ocs_intro_completed: dc.l 0
intro_game_seed: dc.l 0
