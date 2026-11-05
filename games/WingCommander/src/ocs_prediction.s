; OCS field samples: clock.l, native port-one record[10], keys[128], producer.w.
; The producer publishes only complete records; overflow is counted, never a
; reason to discard authoritative clock debt. Missing fields use the last held
; sample explicitly, without replaying its consumable pulses or commands.
OI_SIZE equ 144
ocs_input_record:
        movem.l d0-d7/a0-a6,-(sp)
        WC_PUSH_CCR
        movea.l ocs_game_a4(pc),a4
        tst.w ocs_clock_active(pc)
        beq.w .done
        moveq #0,d0
        move.w ocs_input_head(pc),d0
        move.w d0,d1
        addq.w #1,d1
        andi.w #63,d1
        cmp.w ocs_input_tail(pc),d1
        beq.w .full
        mulu.w #OI_SIZE,d0
        lea ocs_input_ring(pc),a2
        adda.l d0,a2
        move.l -2048(a4),(a2)+
        move.l a2,-(sp)
        move.w #1,-(sp)
        jsr OCS_PAD
        addq.l #6,sp
        clr.b 9(a2)
        lea 10(a2),a2
        move.l a2,-(sp)
        jsr OCS_KEYS
        addq.l #4,sp
        move.w -2036(a4),128(a2)
        lea ocs_input_head(pc),a0
        ; Native providers may clobber D1. Publish from the original head.
        move.w (a0),d0
        addq.w #1,d0
        andi.w #63,d0
        move.w d0,(a0)
        bra.s .done
.full:
        lea ocs_input_overflows(pc),a0
        addq.l #1,(a0)
.done:
        move.w (sp)+,ccr
        movem.l (sp)+,d0-d7/a0-a6
        rts

; One chronological field. A future sample stays queued while missing fields
; advance with last known held controls; no future input is applied early.
ocs_input_take:
        movem.l d1-d3/a0-a2,-(sp)
        moveq #0,d0
        move.w ocs_input_tail(pc),d0
        cmp.w ocs_input_head(pc),d0
        beq.s .empty
        mulu.w #OI_SIZE,d0
        lea ocs_input_ring(pc),a0
        adda.l d0,a0
        move.l ocs_clock_state(pc),d1
        addq.l #1,d1
        cmp.l (a0),d1
        beq.s .copy
        move.l (a0),d2
        sub.l d1,d2
        bpl.s .gap
        ; Stale field after a modal cut: consume it without gameplay work.
        bsr.s .advance
        bra.s .empty
.copy:
        lea ocs_input_sample(pc),a1
        moveq #35,d2
.copy_loop:
        move.l (a0)+,(a1)+
        dbra d2,.copy_loop
        bsr.s .advance
        moveq #1,d0
        bra.s .done
.gap:
        lea ocs_input_missing(pc),a0
        addq.l #1,(a0)
        lea ocs_input_sample(pc),a0
        move.l d1,(a0)
        clr.w 10(a0)
        moveq #1,d0
        bra.s .done
.empty:
        moveq #0,d0
.done:
        movem.l (sp)+,d1-d3/a0-a2
        rts
.advance:
        lea ocs_input_tail(pc),a1
        addq.w #1,(a1)
        andi.w #63,(a1)
        rts

ocs_input_pad:
        tst.w ocs_input_replay(pc)
        beq.s .native
        lea ocs_input_sample+4(pc),a0
        movea.l 6(sp),a1
        move.l (a0)+,(a1)+
        move.l (a0)+,(a1)+
        move.b (a0),(a1)
        rts
.native: jmp OCS_PAD
ocs_input_keys:
        tst.w ocs_input_replay(pc)
        beq.s .native
        lea ocs_input_sample+14(pc),a0
        movea.l 4(sp),a1
        moveq #31,d0
.copy:  move.l (a0)+,(a1)+
        dbra d0,.copy
        rts
.native: jmp OCS_KEYS
ocs_input_command:
        tst.w ocs_input_replay(pc)
        beq.s .native
        move.w -2038(a4),d0
        cmp.w ocs_input_sample+142(pc),d0
        bne.s .native
        moveq #-1,d0
        rts
.native: jmp OCS_INPUT

ocs_prediction_rebase:
        movem.l d0/a0,-(sp)
        lea ocs_exhaust_valid(pc),a0
        clr.w (a0)
        lea ocs_acceleration_valid(pc),a0
        clr.w (a0)
        lea ocs_input_tail(pc),a0
        move.w ocs_input_head(pc),(a0)
        lea ocs_input_replay(pc),a0
        clr.w (a0)
        lea ocs_input_pulses(pc),a0
        clr.w (a0)
        bsr.w timing_prediction_reset
        lea timing_angle_remainder(pc),a0
        clr.l (a0)+
        clr.l (a0)+
        clr.l (a0)
        movem.l (sp)+,d0/a0
        rts

; Field controls advance independently of the render budget. Only renderer
; extrapolation may be skipped; authoritative player policy never changes.
ocs_prediction_field:
        movem.l d0-d7/a0-a6,-(sp)
        lea ocs_input_replay(pc),a0
        move.w #1,(a0)
        lea ocs_input_pulses(pc),a0
        move.w ocs_input_sample+10(pc),d0
        or.w d0,(a0)
        jsr OCS_INPUT_PREPARE
        bsr.w timing_preview_controls
        bsr.w timing_player_field
.done:
        movem.l (sp)+,d0-d7/a0-a6
        rts
ocs_prediction_input:
        bsr.w timing_player_camera
        lea ocs_input_geometry(pc),a0
        move.w #1,(a0)
        jsr OCS_GEOMETRY
        lea ocs_input_geometry(pc),a0
        clr.w (a0)
        lea ocs_input_sample+10(pc),a0
        move.w ocs_input_pulses(pc),d0
        or.w d0,(a0)
        lea ocs_input_pulses(pc),a0
        clr.w (a0)
        jmp OCS_FLIGHT_INPUT

 ; Native O:29114 reads class through A0+D0.l and sets Z. Input needs
; geometry of collidable/action objects (>3), not decorative sky directions.
; The full world/render pass still projects every native class.
ocs_input_geometry_class:
        move.l a1,-(sp)
        movea.l a0,a1
        adda.l d0,a1
        move.w (a1),d4
        movea.l (sp)+,a1
        tst.w ocs_input_geometry(pc)
        beq.s .native
        cmpi.w #3,d4
        bhi.s .native
        moveq #0,d4
.native:
        tst.w d4
        rts
ocs_input_geometry: dc.w 0

ocs_prediction_snapshot:
        lea ocs_acceleration_valid(pc),a0
        clr.w (a0)
        move.w ocs_prediction_mode(pc),d0
        beq.s .auto
        subq.w #1,d0
        lea ocs_prediction_wanted(pc),a0
        move.w d0,(a0)
.auto:
        lea ocs_prediction_fast(pc),a0
        move.w ocs_prediction_wanted(pc),(a0)
        tst.w ocs_prediction_fast(pc)
        beq.s .slow
        bra.w timing_scene_snapshot
.slow:
        lea timing_scene_valid(pc),a0
        clr.w (a0)
        bra.w projectile_reset

; Earliest candidate publication includes measured drawing/conversion service
; and an outstanding publication. Bound is shared: one tick plus two fields.
; Queue uses max(ready+1, forecast), never publishes a forecast early.
release_predict:
.sample:
        move.l -2048(a4),d0
        moveq #0,d1
        move.w ocs_pending(pc),d1
        cmp.l -2048(a4),d0
        bne.s .sample
        add.l ocs_prediction_cost(pc),d0
        addq.l #1,d0
        add.l d1,d0
        lea release_render_time(pc),a0
        move.l d0,(a0)+
        move.l ocs_clock_state(pc),(a0)+
        move.l ocs_clock_state+4(pc),(a0)+
        sub.l ocs_clock_state(pc),d0
        mulu.w #10,d0
        add.l ocs_clock_state+4(pc),d0
        move.l d0,d6
        move.l ocs_clock_hz(pc),d7
        move.l d7,d0
        addi.l #20,d0
        cmp.l d0,d6
        bls.s .bounded
        move.l d0,d6
.bounded:
        move.l d6,(a0)
        rts

ocs_prediction_begin:
        bsr.w ocs_publish_drain
        lea ocs_prediction_queued(pc),a0
        clr.w (a0)
        lea ocs_prediction_start(pc),a0
        move.l -2048(a4),(a0)
        tst.w ocs_prediction_fast(pc)
        beq.s .done
        bsr.w timing_scene_begin
        lea ocs_prediction_queued(pc),a0
        move.w #1,(a0)
        ; Project the staged poses without spawning or random work.
        jsr OCS_GEOMETRY
        bsr.w ocs_exhaust_draw
.done:  rts
ocs_prediction_end:
        bsr.w timing_scene_end
        move.l ocs_prediction_cost(pc),d0
        ; Leave one field for input/world overhead; slow-path fallback retains
        ; authoritative ticks and avoids prediction until measured cost improves.
        addq.l #2,d0
        move.l ocs_clock_hz(pc),d1
        divu.w #10,d1
        lea ocs_prediction_wanted(pc),a0
        cmp.w d1,d0
        blo.s .fast
        clr.w (a0)
        rts
.fast:  move.w #1,(a0)
        rts

ocs_prediction_completed:
        movem.l d0/a0,-(sp)
        tst.w ocs_clock_active(pc)
        beq.s .done
        movea.l ocs_game_a4(pc),a0
        move.l -2048(a0),d0
        sub.l ocs_prediction_start(pc),d0
        lea ocs_prediction_cost(pc),a0
        move.l d0,(a0)
.done:
        movem.l (sp)+,d0/a0
        rts
ocs_prediction_queued: dc.w 0

 ; A zero native acceleration can be reused within one world interval when
; heading, velocity, model, action and set speed are unchanged. World/modal
; boundaries invalidate it before any damage/action/engine changes can enter.
ocs_acceleration_cached:
        movem.l d0-d2/a0-a2,-(sp)
        lea ocs_acceleration_key(pc),a1
        move.l 4430(a4),d0
        cmp.l (a1)+,d0
        bne.s .solve
        move.w 3316(a4),d0
        cmp.w (a1)+,d0
        bne.s .solve
        move.w 3974(a4),d0
        cmp.w (a1)+,d0
        bne.s .solve
        lea 5372(a4),a0
        moveq #2,d0
.velocity:
        cmpm.l (a0)+,(a1)+
        bne.s .solve
        dbra d0,.velocity
        lea 6360(a4),a0
        moveq #2,d0
.basis:
        cmpm.l (a0)+,(a1)+
        bne.s .solve
        dbra d0,.basis
        tst.w ocs_acceleration_valid(pc)
        beq.s .solve
        lea ocs_acceleration_hits(pc),a0
        addq.l #1,(a0)
        bra.s .done
.solve:
        ; Capture pre-solve inputs. Only zero-result solves are reusable, so
        ; the velocity remains identical after a cached solve.
        lea ocs_acceleration_key(pc),a1
        move.l 4430(a4),(a1)+
        move.w 3316(a4),(a1)+
        move.w 3974(a4),(a1)+
        lea 5372(a4),a0
        move.l (a0)+,(a1)+
        move.l (a0)+,(a1)+
        move.l (a0)+,(a1)+
        lea 6360(a4),a0
        move.l (a0)+,(a1)+
        move.l (a0)+,(a1)+
        move.l (a0)+,(a1)+
        bsr.w translation_acceleration
        lea ocs_acceleration_valid(pc),a0
        clr.w (a0)
        move.l translation_last_acceleration(pc),d0
        or.l translation_last_acceleration+4(pc),d0
        or.l translation_last_acceleration+8(pc),d0
        bne.s .done
        move.w #1,(a0)
.done:
        movem.l (sp)+,d0-d2/a0-a2
        rts
        cnop 0,4
ocs_acceleration_key: dcb.b 32,0
ocs_acceleration_hits: dc.l 0
ocs_acceleration_valid: dc.w 0

ocs_projectile_gun:
        movem.l d0-d3/a0-a1,-(sp)
        move.w d2,d0
        bsr.w projectile_created
        movem.l (sp)+,d0-d3/a0-a1
        move.w d2,d0
        jmp OCS_GUN_RETURN

        cnop 0,4
ocs_prediction_start: dc.l 0
ocs_prediction_cost: dc.l 1
ocs_prediction_fast: dc.w 0
ocs_prediction_wanted: dc.w 0
ocs_prediction_mode: dc.w 0 ; 0 measured, 1 off, 2 diagnostic forced
ocs_input_replay: dc.w 0
ocs_input_head: dc.w 0
ocs_input_tail: dc.w 0
ocs_input_pulses: dc.w 0
        cnop 0,4
ocs_input_overflows: dc.l 0
ocs_input_missing: dc.l 0
release_render_time: dcb.l 4,0
ocs_input_sample: dcb.b OI_SIZE,0
ocs_input_ring: dcb.b OI_SIZE*64,0
