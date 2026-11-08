; Timestamp pointer/buttons at the end of VBL, after native debounce or VERIFY
; tape input. The main tick reads its own historical sample, never a later frame.
; Console ownership and historical delivery are in simulation_keyboard.s.
SIM_INPUT_SLOTS = 512
SIM_INPUT_STRIDE = 16

_sim_input_check
        bsr _sim_modal_check
        bsr _sim_mouse_check
        move.l (_h12,pc),a2
        cmp.l #$205f4cdf,(h12_06484,a2)
        bne .bad
        cmp.w #$7fff,(h12_06488,a2)
        bne .bad
        move.l (_hunks+4,pc),a2
        cmp.w #$4ef9,(h1_02b8e,a2)
        bne .bad
        move.l (_h12,pc),a0
        lea (h12_05288,a0),a0
        cmp.l (h1_02b90,a2),a0
        bne .bad
        cmp.l #$6100f4a0,(h1_026ea,a2)
        bne .bad
        cmp.l #$206c0000+((h11_05eb0-$8000)&$ffff),(h1_026ee,a2)
        bne .bad
        cmp.l #$3028000e,(h1_026f2,a2)
        bne .bad
        cmp.l #$48c03228,(h1_026f6,a2)
        bne .bad
        cmp.l #$000c48c1,(h1_026fa,a2)
        bne .bad
        move.l (_hunks+5*4,pc),a2
        cmp.w #$4ef9,(h5_0266e,a2)
        bne .bad
        move.l (_hunks+2*4,pc),a0
        lea (h2_04678,a0),a0
        cmp.l (h5_02670,a2),a0
        bne .bad
        rts
.bad    lea (_sim_bad,pc),a0
        bra _c2p_abort

_sim_input_install
        bsr _sim_modal_install
        lea (_sim_tick_input,pc),a1
        adda.l #_sim_input_ring-_sim_tick_input,a1
        lea (_sim_input_ring_address,pc),a0
        move.l a1,(a0)
        move.l (_hunks+2*4,pc),a0
        lea (h2_04678,a0),a0
        lea (_sim_options_original,pc),a1
        move.l a0,(a1)
        move.l (_hunks+5*4,pc),a2
        ; PERF_RANGE h5:0266e 6 bit=6
        move.w #$4ef9,(h5_0266e,a2)
        lea (_sim_options,pc),a0
        move.l a0,(h5_02670,a2)
        IFD VERIFY
        IFD TIMING_STUDY
        ; Identical-build legacy-input control for the field-pulse experiment.
        move.l (_custom5,pc),d0
        btst #10,d0
        bne .done
        ENDC
        ENDC
        lea (_sim_input_enabled,pc),a0
        move.w #1,(a0)
        bsr _sim_mouse_install
        move.l (_h12,pc),a2
        lea (_sim_input_vbl_done,pc),a0
        lea (h12_0648a,a2),a1
        move.l a1,(a0)
        lea (_sim_input_buttons_original,pc),a0
        lea (h12_05288,a2),a1
        move.l a1,(a0)
        ; PERF_RANGE h12:06484 6 bit=6
        move.w #$4ef9,(h12_06484,a2)
        lea (_sim_input_vbl,pc),a0
        move.l a0,(h12_06486,a2)
        move.l (_hunks+4,pc),a2
        lea (_sim_input_buttons_return,pc),a0
        lea (h1_02674,a2),a1
        move.l a1,(a0)
        lea (_sim_input_pointer_done,pc),a0
        lea (h1_026fe,a2),a1
        move.l a1,(a0)
        ; PERF_RANGE h1:02b8e 6 bit=6
        move.w #$4ef9,(h1_02b8e,a2)
        lea (_sim_input_buttons,pc),a0
        move.l a0,(h1_02b90,a2)
        ; PERF_RANGE h1:026ea 20 bit=6
        lea (h1_026ea,a2),a0
        move.w #$4ef9,(a0)+
        lea (_sim_input_pointer,pc),a1
        move.l a1,(a0)+
        moveq #6,d0
.nops   move.w #$4e71,(a0)+
        dbf d0,.nops
.done   rts

_sim_input_vbl
        IFD SIM_COMBAT_EXPERIMENT
        bsr _sim_combat_sample
        ENDC
        bsr _sim_input_sample
        move.l (sp)+,a0
        movem.l (sp)+,d0-a6
        move.l (_sim_input_vbl_done,pc),-(sp)
        rts

_sim_input_sample
        movem.l d0-d2/a0-a2,-(sp)
        move.w (_sim_input_enabled,pc),d0
        beq .done
        move.w (_sim_started,pc),d0
        beq .done
        move.w (_sim_suspended,pc),d0
        bne .done
        move.l (_h12,pc),a2
        move.l a2,a0
        adda.l #h12_0a0c3,a0
        tst.b (a0)
        beq .done
        move.l (_h11,pc),a0
        move.l (h11_05eb0,a0),a1
        move.l a1,d0
        beq .done
        move.l (_sim_fields,pc),d0
        move.w d0,d1
        and.w #SIM_INPUT_SLOTS-1,d1
        lsl.w #4,d1
        move.l (_sim_input_ring_address,pc),a0
        adda.w d1,a0
        move.l d0,(a0)
        move.w ($e,a1),(4,a0)
        move.w ($c,a1),(6,a0)
        move.w (h12_05292,a2),(8,a0)
        move.w (_sim_mouse_position,pc),(10,a0)
        move.w (_sim_mouse_position+2,pc),(12,a0)
.done   movem.l (sp)+,d0-d2/a0-a2
        rts

_sim_input_select
        movem.l d0-d1/a0-a1,-(sp)
        move.w (_sim_input_enabled,pc),d0
        beq .done
        move.l (_sim_consumed,pc),d0
        move.w d0,d1
        and.w #SIM_INPUT_SLOTS-1,d1
        lsl.w #4,d1
        move.l (_sim_input_ring_address,pc),a0
        adda.w d1,a0
        cmp.l (a0),d0
        bne .overrun
.copy
        lea (_sim_tick_input,pc),a1
        move.l (a0)+,(a1)+
        move.l (a0)+,(a1)+
        move.l (a0)+,(a1)+
        move.l (a0)+,(a1)+
        ; A modal reader has already consumed button transitions through this
        ; boundary. Do not reopen it from older queued held-button samples.
        ; Keep all active simulation ticks and relative motion; only buttons
        ; already consumed by the live UI are suppressed.
        lea (_sim_tick_ui_cleared,pc),a0
        clr.w (a0)
        lea (_sim_ui_until,pc),a0
        tst.w (4,a0)
        beq .motion
        move.l (a0),d0
        sub.l (_sim_consumed,pc),d0
        bmi .ui_passed
        lea (_sim_tick_input+8,pc),a1
        IFD VERIFY
        tst.w (a1)
        beq .ui_clear
        lea (_sim_ui_suppressed,pc),a0
        addq.l #1,(a0)
.ui_clear
        ENDC
        clr.w (a1)
        lea (_sim_tick_ui_cleared,pc),a0
        move.w #1,(a0)
        bra .motion
.ui_passed
        clr.w (4,a0)
.motion bsr _sim_mouse_select
.done   movem.l (sp)+,d0-d1/a0-a1
        rts
.overrun
        ; A long interaction/stall can outlive the finite history. Resynchronize
        ; explicitly instead of aborting or replaying unknown input. Discard the
        ; unrecoverable elapsed interval and relative motion, never invent it.
        movem.l d2/a6,-(sp)
        move.l 4.w,a6
        jsr (_LVODisable,a6)
        bsr _sim_input_sample
        move.l (_sim_fields,pc),d0
        lea (_sim_consumed,pc),a0
        move.l d0,(a0)
        move.w d0,d1
        and.w #SIM_INPUT_SLOTS-1,d1
        lsl.w #4,d1
        move.l (_sim_input_ring_address,pc),a0
        adda.w d1,a0
        lea (_sim_tick_input,pc),a1
        move.l (a0)+,(a1)+
        move.l (a0)+,(a1)+
        move.l (a0)+,(a1)+
        move.l (a0)+,(a1)+
        lea (_sim_tick_ui_cleared,pc),a0
        clr.w (a0)
        lea (_sim_mouse_previous,pc),a0
        move.l (_sim_tick_input+10,pc),(a0)
        lea (_sim_tick_motion,pc),a0
        clr.l (a0)
        lea (_sim_input_recoveries,pc),a0
        addq.l #1,(a0)
        jsr (_LVOEnable,a6)
        movem.l (sp)+,d2/a6
        bra .done

_sim_input_buttons
        move.l (_sim_input_buttons_return,pc),d0
        cmp.l (sp),d0
        bne .native
        moveq #0,d0
        move.w (_sim_tick_input+8,pc),d0
        rts
.native move.l (_sim_input_buttons_original,pc),-(sp)
        rts

_sim_input_pointer
        move.w (_sim_tick_input+4,pc),d0
        move.w d0,(h11_06036-$8000,a4)
        ext.l d0
        move.w (_sim_tick_input+6,pc),d1
        move.w d1,(h11_06038-$8000,a4)
        ext.l d1
        ; Buttons the live UI already consumed are neither a press nor a release.
        move.l d0,-(sp)
        move.w (_sim_tick_ui_cleared,pc),d0
        bne .consumed
        move.w (_sim_tick_input+8,pc),d0
        bsr _click_filter
        bra .store
.consumed
        move.w (_sim_tick_input+8,pc),d0
.store
        move.w d0,(h11_0603a-$8000,a4)
        move.l (sp)+,d0
        move.l (h11_05eb0-$8000,a4),a0
        move.l (_sim_input_pointer_done,pc),-(sp)
        rts

; The options routine takes no stack arguments. Retain its native clocks and
; input while excluding this modal interval from the gameplay accumulator.
_sim_options
        IFD VERIFY
        move.l a0,-(sp)
        lea (_sim_options_entries,pc),a0
        addq.l #1,(a0)
        move.l (_sim_consumed,pc),(4,a0)
        move.l (sp)+,a0
        ENDC
        move.l a0,-(sp)
        lea (_sim_suspended,pc),a0
        addq.w #1,(a0)
        move.l (sp)+,a0
        pea .returned(pc)
        move.l (_sim_options_original,pc),-(sp)
        rts
.returned
        IFD VERIFY
        move.l a0,-(sp)
        lea (_sim_options_returns,pc),a0
        addq.l #1,(a0)
        move.l (_sim_consumed,pc),(4,a0)
        move.l (sp)+,a0
        ENDC
        move.l a0,-(sp)
        bsr _sim_input_after_modal
        lea (_sim_suspended,pc),a0
        subq.w #1,(a0)
        move.l (sp)+,a0
        rts

_sim_input_enabled dc.w 0
_sim_tick_ui_cleared dc.w 0
_sim_input_bad dc.b "Simulation: input history exceeded",0
        CNOP 0,4
_sim_input_vbl_done dc.l 0
_sim_input_buttons_original dc.l 0
_sim_input_buttons_return dc.l 0
_sim_input_pointer_done dc.l 0
_sim_options_original dc.l 0
_sim_input_ring_address dc.l 0
_sim_tick_input ds.b SIM_INPUT_STRIDE

        INCLUDE "simulation_mouse.s"

        INCLUDE "simulation_modal.s"

        CNOP 0,4
_sim_input_recoveries dc.l 0

        IFD VERIFY
        CNOP 0,4
_sim_options_entries dc.l 0
_sim_options_entry_tick dc.l 0
_sim_options_returns dc.l 0
_sim_options_return_tick dc.l 0
        ENDC

; Called before dropping the outermost suspension, while _sim_fields is stable.
; Future active fields keep ordinary input semantics. No time is discarded.
_sim_input_after_modal
        move.l a0,-(sp)
        lea (_sim_suspended,pc),a0
        cmp.w #1,(a0)
        bne .done
        bsr _sim_input_mark_ui
.done   move.l (sp)+,a0
        rts

; Also used by combat's native world-clock pause, without _sim_suspended.
_sim_input_mark_ui
        move.l a0,-(sp)
        lea (_sim_ui_until,pc),a0
        move.l (_sim_fields,pc),(a0)
        move.w #1,(4,a0)
        move.l (sp)+,a0
        rts
        CNOP 0,4
_sim_ui_until dc.l 0
_sim_ui_pending dc.w 0
        IFD VERIFY
        CNOP 0,4
_sim_ui_suppressed dc.l 0
        ENDC
