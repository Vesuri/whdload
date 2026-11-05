; Native-cadence combat clock, included with SIM_COMBAT_EXPERIMENT and CUSTOM2
; bit 6. World time remains paused by the native combat caller. One combat
; step occupies two 25 Hz world ticks; overdue steps retain native ordering.
SIM_COMBAT_FIELDS = SIM_FIELDS_PER_TICK*2
_sim_combat_check
        move.l (_hunks+9*4,pc),a2
        cmp.l #$202ce02c,($1b2,a2)
        bne .bad
        cmp.w #$5880,($1b6,a2)
        bne .bad
        cmp.l #$48ed0001,($1b8,a2)
        bne .bad
        cmp.w #$ffc2,($1bc,a2)
        bne .bad
        cmp.l #$4ced0cfc,($5dc,a2)
        bne .bad
        cmp.w #$ff8c,($5e0,a2)
        bne .bad
        cmp.l #$4e55ffe4,(a2)
        bne .bad
        cmp.l #$bfecde40,(4,a2)
        bne .bad
        cmp.l #$650005de,(8,a2)
        bne .bad
        cmp.l #$206cdeb0,($408,a2)
        bne .bad
        cmp.l #$3028000e,($40c,a2)
        bne .bad
        cmp.l #$48c03228,($410,a2)
        bne .bad
        cmp.l #$000c48c1,($414,a2)
        bne .bad
        lea (.specs,pc),a0
        lea (_hunks,pc),a1
        moveq #3,d2
.next   move.w (a0)+,d0
        cmp.w #$4ef9,(0,a2,d0.w)
        bne .bad
        move.w (a0)+,d1
        move.l (0,a1,d1.w),d1
        add.l (a0)+,d1
        cmp.l (2,a2,d0.w),d1
        bne .bad
        dbf d2,.next
        rts
.specs  dc.w $642,12*4
        dc.l $27bc
        dc.w $62a,5*4
        dc.l $2358
        dc.w $5fa,5*4
        dc.l $59e
        dc.w $64e,12*4
        dc.l $5ea6
.bad    lea (_sim_bad,pc),a0
        bra _c2p_abort

_sim_combat_install
        move.l (_hunks+9*4,pc),a2
        lea (_sim_combat_targets,pc),a0
        lea (.offsets,pc),a1
        moveq #3,d2
.target move.w (a1)+,d0
        move.l (2,a2,d0.w),(a0)+
        dbf d2,.target
        lea ($1b8,a2),a1
        move.l a1,(a0)+
        lea ($5e2,a2),a1
        move.l a1,(a0)+
        lea ($c,a2),a1
        move.l a1,(a0)+
        lea ($5e8,a2),a1
        move.l a1,(a0)+
        lea ($418,a2),a1
        move.l a1,(a0)
        lea (_sim_combat_ring_address,pc),a0
        move.l a0,a1
        adda.l #_sim_combat_ring-_sim_combat_ring_address,a1
        move.l a1,(a0)
        ; PERF_RANGE h9:00408 16 bit=6
        lea ($408,a2),a0
        lea (_sim_combat_pointer,pc),a1
        bsr .jump
        moveq #4,d0
.nops   move.w #$4e71,(a0)+
        dbf d0,.nops
        ; PERF_RANGE h9:001b2 6 bit=6
        lea ($1b2,a2),a0
        lea (_sim_combat_step,pc),a1
        bsr .jump
        ; PERF_RANGE h9:005dc 6 bit=6
        lea ($5dc,a2),a0
        lea (_sim_combat_leave,pc),a1
        bsr .jump
        ; PERF_RANGE h9:00000 8 bit=6
        move.l a2,a0
        lea (_sim_combat_overlay,pc),a1
        bsr .jump
        move.w #$4e71,(6,a2)
        ; PERF_RANGE h9:00642 6 bit=6
        lea ($642,a2),a0
        lea (_sim_combat_world,pc),a1
        bsr .jump
        ; PERF_RANGE h9:0062a 6 bit=6
        lea ($62a,a2),a0
        lea (_sim_combat_sprites,pc),a1
        bsr .jump
        ; PERF_RANGE h9:005fa 6 bit=6
        lea ($5fa,a2),a0
        lea (_sim_combat_enemy,pc),a1
        bsr .jump
        ; PERF_RANGE h9:0064e 6 bit=6
        lea ($64e,a2),a0
        lea (_sim_combat_display,pc),a1
.jump   move.w #$4ef9,(a0)+
        move.l a1,(a0)+
        rts
.offsets dc.w $642,$62a,$5fa,$64e

_sim_combat_step
        movem.l d1/a0,-(sp)
        lea (_sim_combat_active,pc),a0
        tst.w (a0)
        bne .next
        move.w #1,(a0)
        bsr _sim_combat_sample
        move.l ($602c-32768,a4),d0
        bra .start
.next   move.l (_sim_combat_deadline,pc),d0
.start  move.l d0,(_sim_combat_field-_sim_combat_active,a0)
.wait   move.l ($602c-32768,a4),d1
        sub.l d0,d1
        bmi .wait
        move.w #1,(_sim_combat_render-_sim_combat_active,a0)
        cmp.l #SIM_COMBAT_FIELDS,d1
        bcs .deadline
        clr.w (_sim_combat_render-_sim_combat_active,a0)
        addq.l #1,(_sim_combat_catchups-_sim_combat_active,a0)
.deadline
        add.l #SIM_COMBAT_FIELDS,d0
        move.l d0,(_sim_combat_deadline-_sim_combat_active,a0)
        addq.l #1,(_sim_combat_steps-_sim_combat_active,a0)
        bsr _sim_combat_select
        move.l (_sim_combat_deadline,pc),d0
        movem.l (sp)+,d1/a0
        IFD VERIFY
        IFD TIMING_STUDY
        bsr _timing_combat_record
        ENDC
        ENDC
        move.l (_sim_combat_step_continue,pc),-(sp)
        rts

_sim_combat_leave
        bsr _sim_input_mark_ui
        move.l a0,-(sp)
        lea (_sim_combat_active,pc),a0
        clr.w (a0)
        move.w #1,(_sim_combat_render-_sim_combat_active,a0)
        move.l (sp)+,a0
        movem.l (-116,a5),d2-d7/a2-a3
        move.l (_sim_combat_leave_continue,pc),-(sp)
        rts

; Only the h9-local drawing entries are gated. RNG, attack-script advances,
; health changes, sound and damage calculation remain in the native loop.
_sim_combat_world
        move.l a0,-(sp)
        lea (_sim_combat_render,pc),a0
        tst.w (a0)
        move.l (sp)+,a0
        beq .skip
        move.l (_sim_combat_world_original,pc),-(sp)
.skip   rts
_sim_combat_sprites
        move.l a0,-(sp)
        lea (_sim_combat_render,pc),a0
        tst.w (a0)
        move.l (sp)+,a0
        beq .skip
        move.l (_sim_combat_sprites_original,pc),-(sp)
.skip   rts
_sim_combat_enemy
        move.l a0,-(sp)
        lea (_sim_combat_render,pc),a0
        tst.w (a0)
        move.l (sp)+,a0
        beq .skip
        move.l (_sim_combat_enemy_original,pc),-(sp)
.skip   rts
_sim_combat_display
        move.l a0,-(sp)
        lea (_sim_combat_render,pc),a0
        tst.w (a0)
        move.l (sp)+,a0
        beq .skip
        move.l (_sim_combat_display_original,pc),-(sp)
.skip   rts
_sim_combat_overlay
        move.l a0,-(sp)
        lea (_sim_combat_render,pc),a0
        tst.w (a0)
        move.l (sp)+,a0
        beq .skip
        link a5,#-28
        cmpa.l ($5e40-32768,a4),sp
        bcs .overflow
        move.l (_sim_combat_overlay_continue,pc),-(sp)
        rts
.overflow
        move.l (_sim_combat_overflow,pc),-(sp)
.skip   rts

_sim_combat_active dc.w 0
_sim_combat_render dc.w 1
        CNOP 0,4
_sim_combat_field dc.l 0
_sim_combat_deadline dc.l 0
_sim_combat_steps dc.l 0
_sim_combat_catchups dc.l 0
_sim_combat_targets
_sim_combat_world_original dc.l 0
_sim_combat_sprites_original dc.l 0
_sim_combat_enemy_original dc.l 0
_sim_combat_display_original dc.l 0
_sim_combat_step_continue dc.l 0
_sim_combat_leave_continue dc.l 0
_sim_combat_overlay_continue dc.l 0
_sim_combat_overflow dc.l 0
_sim_combat_pointer_continue dc.l 0
_sim_combat_ring_address dc.l 0
_sim_combat_recoveries dc.l 0
_sim_combat_input ds.b 12

; A separate elapsed-field ring remains live while the ordinary world is paused.
_sim_combat_sample
        movem.l d0-d1/a0-a2,-(sp)
        move.w (_sim_combat_active,pc),d0
        beq .done
        move.l (_h11,pc),a2
        move.l ($5eb0,a2),a1
        move.l a1,d0
        beq .done
        move.l ($602c,a2),d0
        move.w d0,d1
        and.w #511,d1
        mulu.w #12,d1
        move.l (_sim_combat_ring_address,pc),a0
        adda.w d1,a0
        move.w ($e,a1),(4,a0)
        move.w ($c,a1),(6,a0)
        move.l (_h12,pc),a1
        move.w ($5292,a1),(8,a0)
        move.l d0,(a0)              ; publish field tag last
.done   movem.l (sp)+,d0-d1/a0-a2
        rts

_sim_combat_select
        movem.l d0-d1/a0-a1/a6,-(sp)
        move.l (_sim_combat_field,pc),d0
.find   move.w d0,d1
        and.w #511,d1
        mulu.w #12,d1
        move.l (_sim_combat_ring_address,pc),a0
        adda.w d1,a0
        cmp.l (a0),d0
        bne .recover
        lea (_sim_combat_input,pc),a1
        move.l (a0)+,(a1)+
        move.l (a0)+,(a1)+
        move.l (a0)+,(a1)+
        movem.l (sp)+,d0-d1/a0-a1/a6
        rts
.recover
        ; Same explicit finite-history policy as world input: rebase only when
        ; the requested history has actually been overwritten by a long stall.
        move.l 4.w,a6
        jsr (_LVODisable,a6)
        bsr _sim_combat_sample
        move.l (_h11,pc),a0
        move.l ($602c,a0),d0
        lea (_sim_combat_field,pc),a0
        move.l d0,(a0)
        move.l d0,d1
        add.l #SIM_COMBAT_FIELDS,d1
        move.l d1,(_sim_combat_deadline-_sim_combat_field,a0)
        addq.l #1,(_sim_combat_recoveries-_sim_combat_field,a0)
        jsr (_LVOEnable,a6)
        move.l (_sim_combat_field,pc),d0
        bra .find

_sim_combat_pointer
        move.w (_sim_combat_input+4,pc),d0
        move.w d0,($6036-32768,a4)
        ext.l d0
        move.w (_sim_combat_input+6,pc),d1
        move.w d1,($6038-32768,a4)
        ext.l d1
        move.l a0,-(sp)
        lea (_sim_combat_input,pc),a0
        move.w (8,a0),($603a-32768,a4)
        move.l (sp)+,a0
        move.l (_sim_combat_pointer_continue,pc),-(sp)
        rts
