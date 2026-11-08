; h2:1ca0 is a blocking item panel reached from h2:24d0. It uses the
; original clock for repeat timing, so freeze only private simulation time.
; Entry and the sole normal epilogue retain the original argument/frame layout.
_sim_modal_check
        move.l (_hunks+2*4,pc),a2
        cmp.l #$4e55fff0,(h2_01ca0,a2)
        bne .bad
        cmp.l #$bfec0000+((h11_05e40-$8000)&$ffff),(h2_01ca4,a2)
        bne .bad
        cmp.l #$65000000+((h2_0624a-h2_01caa)&$ffff),(h2_01ca8,a2)
        bne .bad
        cmp.l #$4ced08f4,(h2_0222e,a2)
        bne .bad
        cmp.w #$ffd8,(h2_02232,a2)
        bne .bad
        cmp.l #$4e5d4e75,(h2_02234,a2)
        bne .bad
        rts
.bad    lea (_sim_bad,pc),a0
        bra _c2p_abort

_sim_modal_install
        move.l (_hunks+2*4,pc),a2
        lea (_sim_panel_continue,pc),a0
        lea (h2_01cac,a2),a1
        move.l a1,(a0)+
        lea (h2_0624a,a2),a1
        move.l a1,(a0)+
        lea (h2_02234,a2),a1
        move.l a1,(a0)
        ; PERF_RANGE h2:01ca0 8 bit=6
        lea (h2_01ca0,a2),a0
        move.w #$4ef9,(a0)+
        lea (_sim_panel_enter,pc),a1
        move.l a1,(a0)+
        move.w #$4e71,(a0)
        ; PERF_RANGE h2:0222e 6 bit=6
        lea (h2_0222e,a2),a0
        move.w #$4ef9,(a0)+
        lea (_sim_panel_leave,pc),a1
        move.l a1,(a0)
        rts

_sim_panel_enter
        link a5,#-16
        cmpa.l (h11_05e40-$8000,a4),sp
        bcs .overflow
        movem.l d0/a0,-(sp)
        moveq #0,d0
        move.w (_sim_suspended,pc),d0
        move.l d0,a0
        addq.l #1,a0
        move.l a0,d0
        lea (_sim_suspended,pc),a0
        move.w d0,(a0)
        movem.l (sp)+,d0/a0
        IFD VERIFY
        IFD TIMING_STUDY
        bsr _timing_study_panel_paused
        ENDC
        ENDC
        move.l (_sim_panel_continue,pc),-(sp)
        rts
.overflow
        move.l (_sim_panel_overflow,pc),-(sp)
        rts

_sim_panel_leave
        IFD VERIFY
        IFD TIMING_STUDY
        bsr _timing_study_panel_returning
        ENDC
        ENDC
        movem.l d0/a0,-(sp)
        bsr _sim_input_after_modal
        moveq #0,d0
        move.w (_sim_suspended,pc),d0
        move.l d0,a0
        subq.l #1,a0
        move.l a0,d0
        lea (_sim_suspended,pc),a0
        move.w d0,(a0)
        movem.l (sp)+,d0/a0
        movem.l (-40,a5),d2/d4-d7/a3
        move.l (_sim_panel_return,pc),-(sp)
        rts

        CNOP 0,4
_sim_panel_continue dc.l 0
_sim_panel_overflow dc.l 0
_sim_panel_return dc.l 0
