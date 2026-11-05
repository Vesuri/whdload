; OCS flight adapter. Native world units; field time and audio remain native.
; Shared timing_advance receives at most one tick's fields at a time, so its
; drop/stall policy is unreachable. Unserviced fields remain behind the cursor.
ocs_clock_loop:
        movem.l d0-d7/a0-a6,-(sp)
        bsr.w timing_rate
        lea ocs_clock_hz(pc),a0
        move.l d0,(a0)
        ; Initial native update loads assets outside the measured flight epoch.
        jsr OCS_FLIGHT_INPUT
        cmpi.w #-1,d0
        beq.w ocs_clock_quit_label
        tst.w -32596(a4)
        bne.w ocs_clock_leave_label
        bsr.w ocs_clock_tick
        bsr.w ocs_clock_rebase
        lea ocs_clock_active(pc),a0
        move.w #1,(a0)
ocs_clock_loop_label:
        tst.w -32596(a4)
        bne.w ocs_clock_leave_label
        bsr.w ocs_clock_batch
        tst.w -32596(a4)
        bne.w ocs_clock_leave_label
        ; Keep servicing bounded batches when overdue; never drop simulation.
        move.l -2048(a4),d0
        sub.l ocs_clock_state(pc),d0
        move.l ocs_clock_hz(pc),d1
        divu.w #10,d1
        cmp.l d1,d0
        bhs.s ocs_clock_loop_label
        move.l ocs_clock_dirty(pc),d0
        cmp.l ocs_clock_draw_every(pc),d0
        blo.s ocs_clock_loop_label
        bsr.w ocs_clock_draw
ocs_clock_iteration:
        bra.s ocs_clock_loop_label
ocs_clock_quit_label:
        move.w #5,-32596(a4)
ocs_clock_leave_label:
        bsr.w ocs_clock_rebase
        lea ocs_clock_active(pc),a0
        clr.w (a0)
        movem.l (sp)+,d0-d7/a0-a6
        jmp OCS_FLIGHT_EXIT

; At most four completed ticks per call. No sampled device history is invented:
; native queues/edges consume once; held controls are sampled at each tick.
; D3 replaces this explicitly bounded, tick-rate input policy.
ocs_clock_batch:
        movem.l d2-d7/a2-a6,-(sp)
        moveq #4,d7
.next:
        move.l -2048(a4),d0
        sub.l ocs_clock_state(pc),d0
        beq.w .done
        lea ocs_clock_backlog_max(pc),a0
        cmp.l (a0),d0
        bls.s .bounded
        move.l d0,(a0)
.bounded:
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
        tst.l d0
        beq.s .next
        lea ocs_clock_cancel(pc),a0
        clr.w (a0)
        jsr OCS_FLIGHT_INPUT
        cmpi.w #-1,d0
        bne.s .input_ok
        move.w #5,-32596(a4)
.input_ok:
        tst.w ocs_clock_cancel(pc)
        bne.s .done
        tst.w -32596(a4)
        bne.s .done
        bsr.w ocs_clock_tick
        subq.w #1,d7
        bne.s .next
        move.l -2048(a4),d0
        sub.l ocs_clock_state(pc),d0
        beq.s .done
        lea ocs_clock_overload_batches(pc),a0
        addq.l #1,(a0)
.done:
        movem.l (sp)+,d2-d7/a2-a6
        rts

ocs_clock_rebase:
        movem.l d0-d3/a0,-(sp)
        lea ocs_clock_state(pc),a0
        move.l -2048(a4),d0
        move.l ocs_clock_hz(pc),d1
        moveq #0,d2
        bsr.w timing_advance
        move.l -2048(a4),d0
        move.l ocs_clock_hz(pc),d1
        moveq #1,d2
        bsr.w timing_advance
        lea ocs_clock_cancel(pc),a0
        move.w #1,(a0)
        movem.l (sp)+,d0-d3/a0
        rts

; All allocation-bearing scene preparation runs at world cadence. The renderer
; consumes its result, without a second geometry-history update or RNG draw.
ocs_clock_tick:
        movem.l d0-d7/a0-a6,-(sp)
        jsr OCS_WORLD
        jsr OCS_GEOMETRY
        moveq #0,d0
        tst.l 2308(a4)
        beq.s .debris
        moveq #1,d0
.debris:
        move.w d0,-(sp)
        jsr OCS_DEBRIS
        addq.l #2,sp
        jsr OCS_FLAMES
        jsr OCS_ATTACHMENTS
        tst.l 2308(a4)
        beq.s .messages
        ; Cleanup rotates through twenty slots by world time, not the number
        ; of intermediate pictures (which can alias the modulo-20 selection).
        move.w 2272(a4),-(sp)
        move.w 2268(a4),2272(a4)
        jsr OCS_ASTEROIDS
        move.w (sp)+,2272(a4)
.messages:
        jsr OCS_MESSAGE
        bsr.w ocs_clock_score
        bsr.w ocs_clock_sim_native
        move.w 2272(a4),-(sp)
        move.w 2268(a4),2272(a4)
        jsr OCS_TARGET
        move.w (sp)+,2272(a4)
        jsr OCS_FAULTS
        lea ocs_clock_completed(pc),a0
        addq.l #1,(a0)
        lea ocs_clock_dirty(pc),a0
        addq.l #1,(a0)
ocs_clock_tick_done:
        movem.l (sp)+,d0-d7/a0-a6
        rts

ocs_clock_score:
        tst.w -29962(a4)
        beq.s .done
        tst.w -32594(a4)
        bgt.s .done
        addq.l #1,2318(a4)
        subq.w #1,2312(a4)
        bgt.s .done
        move.w #4,-32596(a4)
.done:
        rts

ocs_clock_draw:
        movem.l d0-d7/a0-a6,-(sp)
        ; Cosmetic HUD randomness must not perturb the authoritative stream.
        move.l -4196(a4),-(sp)
        move.l ocs_clock_render_seed(pc),-4196(a4)
        jsr OCS_DRAW
        bsr.w ocs_clock_target_draw
        lea ocs_clock_render_seed(pc),a0
        move.l -4196(a4),(a0)
        move.l (sp)+,-4196(a4)
        lea ocs_clock_dirty(pc),a0
        clr.l (a0)
        lea ocs_clock_drawn(pc),a0
        addq.l #1,(a0)
        movem.l (sp)+,d0-d7/a0-a6
        rts

ocs_clock_scene_draw:
        tst.w ocs_clock_active(pc)
        beq.s .native
        jsr OCS_SORT
        jmp OCS_RASTER
.native:
        jmp OCS_SCENE
ocs_clock_message_draw:
        tst.w ocs_clock_active(pc)
        bne.s .done
        jmp OCS_MESSAGE
.done: rts
ocs_clock_asteroids_draw:
        tst.w ocs_clock_active(pc)
        bne.s .done
        jmp OCS_ASTEROIDS
.done: rts
ocs_clock_faults_draw:
        tst.w ocs_clock_active(pc)
        bne.s .done
        jmp OCS_FAULTS
.done: rts
ocs_clock_target_draw:
        tst.w ocs_clock_active(pc)
        bne.s .done
        ; Original O:4460 PC-relative target call, followed by fault polling.
        jsr OCS_TARGET
.done:
        jmp OCS_SYSTEMS_BODY
ocs_clock_sim_draw:
        tst.w ocs_clock_active(pc)
        beq.s ocs_clock_sim_native
        rts
ocs_clock_sim_native:
        tst.w -29962(a4)
        beq.s .done
        jmp OCS_SIM_BODY
.done: rts
ocs_clock_score_draw:
        tst.w ocs_clock_active(pc)
        bne.s .active
        addq.l #1,2318(a4)
        subq.w #1,2312(a4)
        rts
.active:
        ; Original BGT must skip the draw-owned exit store too.
        moveq #1,d0
        rts
ocs_clock_emission:
        tst.w ocs_clock_active(pc)
        beq.s .native
        move.w 2268(a4),d0
        bra.s .mask
.native:
        move.w 2272(a4),d0
.mask:
        andi.w #3,d0
        rts
ocs_clock_selection:
        move.l d0,-(sp)
        tst.w ocs_clock_active(pc)
        beq.s .native
        move.l ocs_clock_dirty(pc),d0
        sub.w d0,10426(a4)
        bra.s .result
.native:
        subq.w #1,10426(a4)
.result:
        bgt.s .waiting
        move.l (sp)+,d0
        jmp OCS_SELECTION_READY
.waiting:
        move.l (sp)+,d0
        jmp OCS_SELECTION_WAIT

        cnop 0,4
ocs_clock_state: dcb.b 28,0
ocs_clock_hz: dc.l 50
ocs_clock_completed: dc.l 0
ocs_clock_drawn: dc.l 0
ocs_clock_draw_every: dc.l 1
ocs_clock_dirty: dc.l 0
ocs_clock_backlog_max: dc.l 0
ocs_clock_overload_batches: dc.l 0
ocs_clock_render_seed: dc.l $6d2b79f5
ocs_clock_active: dc.w 0
ocs_clock_cancel: dc.w 0
