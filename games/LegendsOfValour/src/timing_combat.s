; VERIFY/TIMING_STUDY bit 28: enter the native combat caller with actor 43.
; Observe original combat iterations; request its ordinary space-key escape
; after 32 polls. No actor health, AI script, or damage values are fabricated.
_timing_combat_install
        move.l (_custom5,pc),d0
        btst #28,d0
        beq .done
        move.l (_hunks+9*4,pc),a2
        IFND SIM_COMBAT_EXPERIMENT
        cmp.l #$202ce02c,($1b2,a2)
        bne .bad
        cmp.w #$5880,($1b6,a2)
        bne .bad
        cmp.l #$48ed0001,($1b8,a2)
        bne .bad
        cmp.w #$ffc2,($1bc,a2)
        bne .bad
        ENDC
        cmp.w #$4ef9,($618,a2)
        bne .bad
        move.l (_hunks+4,pc),a0
        lea ($1eb6,a0),a0
        cmp.l ($61a,a2),a0
        bne .bad
        lea (_timing_combat_poll_original,pc),a1
        move.l a0,(a1)
        lea ($1be,a2),a0
        move.l a0,(_timing_combat_continue-_timing_combat_poll_original,a1)
        IFND SIM_COMBAT_EXPERIMENT
        lea (_timing_combat_step,pc),a0
        move.w #$4ef9,($1b2,a2)
        move.l a0,($1b4,a2)
        ENDC
        lea (_timing_combat_poll,pc),a0
        move.l a0,($61a,a2)
.done   rts
.bad    lea (_timing_combat_bad,pc),a0
        bra _c2p_abort

_timing_combat_enter
        movem.l d0-a6,-(sp)
        move.l (_custom5,pc),d0
        btst #28,d0
        beq .done
        move.w (_timing_study_armed,pc),d0
        beq .done
        lea (_timing_combat_requested,pc),a0
        tst.w (a0)
        bne .done
        move.w #1,(a0)
        move.w (_sim_render_tick,pc),-(sp)
        lea (_sim_render_tick,pc),a0
        move.w #1,(a0)              ; measure every original combat render
        move.w ($60be-32768,a4),-(sp)
        move.l (_custom5,pc),d0
        btst #29,d0
        beq .auto
        clr.w ($60be-32768,a4)      ; manual attack option, restored on return
.auto
        ; Include h12's pause/re-enable envelope around the C combat wrapper.
        ; Select an existing actor, preserving its live health and script data.
        move.l (_h12,pc),a0
        adda.l #$9716,a0
        move.w (a0),-(sp)
        move.w #-15214+43*128,(a0)
        move.l (_h12,pc),a1
        adda.l #$10b8c,a1
        move.l (_h12,pc),a0
        adda.l #$de5e,a0
        jsr (a1)
        move.l (_h12,pc),a0
        adda.l #$9716,a0
        move.w (sp)+,(a0)
        move.w (sp)+,($60be-32768,a4)
        lea (_sim_render_tick,pc),a0
        move.w (sp)+,(a0)
        lea (_timing_combat_returned,pc),a0
        move.w #1,(a0)
.done   movem.l (sp)+,d0-a6
        rts

_timing_combat_step
        bsr _timing_combat_record
        move.l ($602c-32768,a4),d0
        addq.l #4,d0
        movem.l d0,(-62,a5)
        move.l (_timing_combat_continue,pc),-(sp)
        rts

_timing_combat_record
        movem.l d0-d2/a0-a1,-(sp)
        lea (_timing_combat_steps,pc),a0
        move.l (a0),d0
        bne .epoch_set
        move.l (_h11,pc),a1
        move.l ($602c,a1),(_timing_combat_firstfield-_timing_combat_steps,a0)
.epoch_set
        addq.l #1,(a0)
        cmp.l #64,d0
        bcc .done
        move.l d0,d2
        mulu.w #32,d0
        lea (_timing_combat_steps,pc),a0
        adda.l #_timing_combat_records-_timing_combat_steps,a0
        adda.w d0,a0
        move.l (_h11,pc),a1
        move.l ($602c,a1),(a0)+
        move.l ($4d6,a1),(a0)+
        move.l (_sim_fields,pc),(a0)+
        move.l (_sim_consumed,pc),(a0)+
        move.l d5,(a0)+
        move.l d6,(a0)+
        move.l d7,(a0)+
        moveq #0,d0
        move.b (111,a3),d0
        move.w d0,(a0)+
        move.l (_h12,pc),a1
        adda.l #$a0c3,a1
        move.b (a1),(a0)+
        move.b (110,a3),(a0)
        IFD SIM_COMBAT_EXPERIMENT
        mulu.w #20,d2
        lea (_timing_combat_steps,pc),a0
        adda.l #_timing_combat_clock_records-_timing_combat_steps,a0
        adda.w d2,a0
        move.l (_sim_combat_field,pc),(a0)+
        move.l (_sim_combat_deadline,pc),(a0)+
        lea (_sim_combat_input,pc),a1
        move.l (a1)+,(a0)+
        move.l (a1)+,(a0)+
        move.l (a1)+,(a0)+
        ENDC
.done   movem.l (sp)+,d0-d2/a0-a1
        rts

_timing_combat_poll
        move.l (_custom5,pc),d0
        btst #30,d0
        bne .native
        move.l (_timing_combat_steps,pc),d0
        cmp.l #32,d0
        bcs .native
        moveq #32,d0
        rts
.native move.l (_timing_combat_poll_original,pc),-(sp)
        rts
_timing_combat_bad dc.b "Combat study: unexpected game code",0
        EVEN
_timing_combat_requested dc.w 0
_timing_combat_returned dc.w 0
        CNOP 0,4
_timing_combat_steps dc.l 0
_timing_combat_firstfield dc.l 0
_timing_combat_continue dc.l 0
_timing_combat_poll_original dc.l 0

; Manual-input fixture: four-field attack-button presses every 32 fields,
; starting eight fields after the first combat iteration. Runs before sampling.
_timing_combat_input
        move.l (_timing_combat_steps,pc),d0
        beq .done
        move.w (_timing_combat_returned,pc),d0
        bne .done
        move.l (_h11,pc),a0
        move.l ($602c,a0),d0
        sub.l (_timing_combat_firstfield,pc),d0
        and.l #31,d0
        subq.l #8,d0
        cmp.l #4,d0
        scs d1
        and.w #1,d1
        move.l ($5eb0,a0),a0
        move.w #174,($e,a0)
        move.w #150,($c,a0)
        move.l (_h12,pc),a0
        move.w d1,($5292,a0)
.done   rts
