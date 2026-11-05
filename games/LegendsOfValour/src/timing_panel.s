; VERIFY/TIMING_STUDY CUSTOM5 bit 13: call the native h2:1ca0 panel
; with valid record index zero from the main task, hold 600 PAL fields,
; then dismiss it by an ordinary click outside its buttons. No debugger writes.
_timing_study_panel
        movem.l d0-a6,-(sp)
        move.l (_custom5,pc),d0
        btst #13,d0
        beq .done
        move.w (_timing_study_armed,pc),d0
        beq .done
        move.w (_timing_study_panel_requested,pc),d0
        bne .done
        lea (_timing_study_panel_requested,pc),a0
        move.w #1,(a0)
        lea (_timing_study_panel_active,pc),a0
        move.w #1,(a0)
        move.l (_hunks+2*4,pc),a0
        adda.l #$1ca0,a0
        clr.l -(sp)
        jsr (a0)
        addq.l #4,sp
        move.w (_sim_suspended,pc),d0
        bne .bad
        move.l (_timing_study_panel_passes,pc),d0
        cmp.l #1,d0
        bne .bad
        lea (_timing_study_panel_active,pc),a0
        clr.w (a0)
.done   movem.l (sp)+,d0-a6
        rts
.bad    lea (_timing_study_panel_bad,pc),a0
        bra _c2p_abort

_timing_study_panel_paused
        movem.l d0/a0-a1,-(sp)
        move.w (_timing_study_panel_active,pc),d0
        beq .done
        lea (_timing_study_panel_before,pc),a0
        move.l (_sim_fields,pc),(a0)+
        move.l (_sim_consumed,pc),(a0)+
        move.l (_h11,pc),a1
        move.l ($602c,a1),(a0)+
        move.l ($4d6,a1),(a0)
        lea (_timing_study_panel_started,pc),a0
        move.w #1,(a0)
.done   movem.l (sp)+,d0/a0-a1
        rts

_timing_study_panel_input
        move.w (_timing_study_panel_started,pc),d0
        beq .done
        move.l (_h11,pc),a0
        move.l ($602c,a0),d0
        sub.l (_timing_study_panel_before+8,pc),d0
        sub.l #600,d0
        cmp.l #8,d0
        scs d0
        and.w #1,d0
        move.l (_h12,pc),a0
        move.w d0,($5292,a0)
        move.l (_h11,pc),a0
        move.l ($5eb0,a0),d0
        beq .done
        move.l d0,a0
        clr.w ($e,a0)
        clr.w ($c,a0)
.done   rts

_timing_study_panel_returning
        movem.l d0/a0-a1,-(sp)
        move.w (_timing_study_panel_active,pc),d0
        beq .done
        lea (_timing_study_panel_after,pc),a0
        move.l (_sim_fields,pc),(a0)+
        move.l (_sim_consumed,pc),(a0)+
        move.l (_h11,pc),a1
        move.l ($602c,a1),(a0)+
        move.l ($4d6,a1),(a0)
        move.l (_sim_fields,pc),d0
        cmp.l (_timing_study_panel_before,pc),d0
        bne .bad
        move.l (_sim_consumed,pc),d0
        cmp.l (_timing_study_panel_before+4,pc),d0
        bne .bad
        move.l (_timing_study_panel_after+8,pc),d0
        sub.l (_timing_study_panel_before+8,pc),d0
        cmp.l #600,d0
        bcs .bad
        move.l (_timing_study_panel_after+12,pc),d0
        sub.l (_timing_study_panel_before+12,pc),d0
        cmp.l #600,d0
        bcs .bad
        lea (_timing_study_panel_passes,pc),a0
        addq.l #1,(a0)
.done   movem.l (sp)+,d0/a0-a1
        rts
.bad    lea (_timing_study_panel_bad,pc),a0
        bra _c2p_abort

_timing_study_panel_requested dc.w 0
_timing_study_panel_active dc.w 0
_timing_study_panel_started dc.w 0
        CNOP 0,4
_timing_study_panel_before ds.l 4
_timing_study_panel_after ds.l 4
_timing_study_panel_passes dc.l 0
_timing_study_panel_bad dc.b "TIMING study: panel pause failed",0
        EVEN
