; Commit targeting from the authoritative player/camera and object positions
; once at a world boundary. Renderer projections cannot select a future target.
timing_target_tick:
        movem.l d0-d7/a0-a6,-(sp)
        bsr.w   timing_player_camera
        move.l  timing_game(pc),a6
        jsr     $2a086(a6)
        bsr.w   timing_geometry_history
        move.w  4434(a4),-(sp)
        move.w  4430(a4),4434(a4)
        bsr.w   timing_target_original
        move.w  (sp)+,4434(a4)
        movem.l (sp)+,d0-d7/a0-a6
        rts

timing_target_draw:
        tst.w   timing_active(pc)
        bne.s   .done
        bra.w   timing_target_original
.done:
        rts

; Simulator score countdown is world-owned; the native draw branch skips its
; exit transition when enabled. Native/modal flags are the original countdown.
timing_sim_score_draw:
        tst.w   timing_active(pc)
        bne.s   .done
        addq.l  #1,4480(a4)
        subq.w  #1,4474(a4)
.done:
        rts

; Clock ownership at the ordinary flight boundary. Native/modal paths retain
; their original counters. These adapters do not predict any world objects.
timing_emission_clock:
        tst.w   timing_in_world(pc)
        beq.s   .native
        move.w  4430(a4),d0
        bra.s   .mask
.native:
        move.w  4434(a4),d0
.mask:
        andi.w  #3,d0
        rts

; Cockpit subsystem fault/repair polling was also called from HUD drawing.
; It consumes gameplay RNG and may change damaged-system state: world-owned.
timing_systems_draw:
        tst.w   timing_active(pc)
        bne.s   .done
        move.l  timing_game(pc),-(sp)
        addi.l  #$af84,(sp)
.done:
        rts

timing_message_draw:
        tst.w   timing_active(pc)
        bne.s   .done
        move.l  timing_game(pc),-(sp)
        addi.l  #$22a0,(sp)
.done:
        rts

; The simulator's end countdown also lived after the renderer. Run its native
; tail once per world tick, including its position/exit transition exactly once.
timing_sim_draw:
        tst.w   timing_active(pc)
        bne.s   .done
        bra.s   timing_sim_update
.done:
        rts
timing_sim_update:
        tst.w   -29986(a4)
        beq.s   .done
        move.l  timing_game(pc),-(sp)
        addi.l  #$536,(sp)
.done:
        rts

; HUD selection is visual state. Consume elapsed world ticks at its next draw;
; an expired indicator changes once then uses the native reload. Missed pictures
; are coalesced, never replayed as extra gameplay or draw work.
timing_selection:
        move.l  d0,-(sp)
        tst.w   timing_active(pc)
        beq.s   .native
        move.w  timing_selection_delta(pc),d0
        sub.w   d0,12972(a4)
        bra.s   .result
.native:
        subq.w  #1,12972(a4)
.result:
        bgt.s   .waiting
        move.l  (sp)+,d0
        move.l  timing_game(pc),-(sp)
        addi.l  #$4b1e,(sp)
        rts
.waiting:
        move.l  (sp)+,d0
        move.l  timing_game(pc),-(sp)
        addi.l  #$4c56,(sp)
        rts

timing_portrait_clock:
        tst.w   timing_active(pc)
        beq.s   .native
        btst    #0,4431(a4)
        rts
.native:
        btst    #0,4435(a4)
        rts

timing_portrait_random:
        tst.w   timing_active(pc)
        beq.s   .native
        move.w  timing_visual_random(pc),d0
        rts
.native:
        move.l  timing_game(pc),-(sp)
        addi.l  #$2cb86,(sp)
        rts

; Advance an independent visual RNG at the fixed tick even if no picture is
; drawn. Use the native range routine with private seed, restoring the gameplay
; seed before returning. Interrupt work does not call the gameplay RNG.
timing_presentation_tick:
        movem.l d0-d1/a0-a1/a6,-(sp)
        move.l  -4326(a4),-(sp)
        move.l  timing_visual_seed(pc),-4326(a4)
        move.w  #7,-(sp)
        clr.w   -(sp)
        move.l  timing_game(pc),a6
        jsr     $2cb86(a6)
        addq.l  #4,sp
        lea     timing_visual_random(pc),a0
        move.w  d0,(a0)
        lea     timing_visual_seed(pc),a0
        move.l  -4326(a4),(a0)
        move.l  (sp)+,-4326(a4)
        move.l  timing_game(pc),a6
        jsr     $22a0(a6)
        tst.w   -29986(a4)
        beq.s   .no_score
        tst.w   -32626(a4)
        bgt.s   .no_score
        addq.l  #1,4480(a4)
        subq.w  #1,4474(a4)
        bgt.s   .no_score
        move.w  #4,-32628(a4)
.no_score:
        bsr.w   timing_sim_update
        move.l  timing_game(pc),a6
        jsr     $af84(a6)
        movem.l (sp)+,d0-d1/a0-a1/a6
        rts

        cnop    0,4
timing_visual_seed: dc.l $12345678
timing_visual_random: dc.w 0
timing_selection_last: dc.w 0
timing_selection_delta: dc.w 0

        cnop 0,4
timing_render_seed: dc.l $6d2b79f5
