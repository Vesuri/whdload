; Relative motion is accumulated independently of the game's destructive read.
; History stores cumulative positions; selecting a tick takes their difference.
_sim_mouse_check
        move.l (_h12,pc),a2
        cmp.w #$d379,(h12_06460,a2)
        bne .bad
        cmp.w #$d579,(h12_06466,a2)
        bne .bad
        move.l (_h11,pc),a0
        lea (h11_008d2,a0),a0
        cmp.l (h12_06462,a2),a0
        bne .bad
        addq.l #2,a0
        cmp.l (h12_06468,a2),a0
        bne .bad
        move.l (_hunks+5*4,pc),a2
        cmp.l #$302c0000+((h11_008d2-$8000)&$ffff),(h5_01e64,a2)
        bne .bad
        cmp.l #$d16c0000+((h11_08c28-$8000)&$ffff),(h5_01e68,a2)
        bne .bad
        cmp.w #$6c06,(h5_01e6c,a2)
        bne .bad
        cmp.w #$4ef9,(h5_026b0,a2)
        bne .bad
        move.l (_h12,pc),a0
        lea (h12_05288,a0),a0
        cmp.l (h5_026b2,a2),a0
        bne .bad
        move.l (_hunks+4,pc),a2
        cmp.l #$39400000+((h11_008d4-$8000)&$ffff),(h1_026b6,a2)
        bne .bad
        cmp.l #$39400000+((h11_008d2-$8000)&$ffff),(h1_026ba,a2)
        bne .bad
        rts
.bad    lea (_sim_bad,pc),a0
        bra _c2p_abort

_sim_mouse_install
        move.l (_h12,pc),a2
        lea (_sim_mouse_vbl_done,pc),a0
        lea (h12_0646c,a2),a1
        move.l a1,(a0)
        ; PERF_RANGE h12:06460 12 bit=6
        lea (h12_06460,a2),a0
        move.w #$4ef9,(a0)+
        lea (_sim_mouse_vbl,pc),a1
        move.l a1,(a0)+
        move.w #$4e71,(a0)+
        move.w #$4e71,(a0)+
        move.w #$4e71,(a0)+
        move.l (_hunks+5*4,pc),a2
        lea (_sim_mouse_negative,pc),a0
        lea (h5_01e6e,a2),a1
        move.l a1,(a0)+
        lea (h5_01e74,a2),a1
        move.l a1,(a0)+
        lea (h5_01ea6,a2),a1
        move.l a1,(a0)+
        lea (h5_01ec0,a2),a1
        move.l a1,(a0)
        ; PERF_RANGE h5:01e64 8 bit=6
        move.w #$4ef9,(h5_01e64,a2)
        lea (_sim_mouse_step,pc),a0
        move.l a0,(h5_01e66,a2)
        move.w #$4e71,(h5_01e6a,a2)
        ; PERF_RANGE h5:026b0 6 bit=6
        move.w #$4ef9,(h5_026b0,a2)
        lea (_sim_mouse_buttons,pc),a0
        move.l a0,(h5_026b2,a2)
        move.l (_hunks+4,pc),a2
        lea (_sim_mouse_reset_done,pc),a0
        lea (h1_026be,a2),a1
        move.l a1,(a0)
        ; PERF_RANGE h1:026b6 8 bit=6
        move.w #$4ef9,(h1_026b6,a2)
        lea (_sim_mouse_reset,pc),a0
        move.l a0,(h1_026b8,a2)
        move.w #$4e71,(h1_026bc,a2)
        rts

_sim_mouse_vbl
        move.l a0,-(sp)
        move.l (_h11,pc),a0
        add.w d1,(h11_008d2,a0)
        add.w d2,(h11_008d4,a0)
        lea (_sim_started,pc),a0
        tst.w (a0)
        beq .done
        lea (_sim_suspended,pc),a0
        tst.w (a0)
        bne .done
        move.l (_h12,pc),a0
        adda.l #h12_0a0c3,a0
        tst.b (a0)
        beq .done
        lea (_sim_mouse_position,pc),a0
        add.w d1,(a0)
        add.w d2,(2,a0)
.done   move.l (sp)+,a0
        move.l (_sim_mouse_vbl_done,pc),-(sp)
        rts

; Called with D0/D1/A0 saved by the selector, on every tick even outside mouse
; look. Entering mouse look explicitly clears this tick's delta, like the game.
_sim_mouse_select
        lea (_sim_mouse_previous,pc),a0
        move.w (_sim_tick_input+10,pc),d0
        move.w d0,d1
        sub.w (a0),d1
        move.w d0,(a0)+
        move.w d1,(2,a0)
        move.w (_sim_tick_input+12,pc),d0
        move.w d0,d1
        sub.w (a0),d1
        move.w d0,(a0)
        move.w d1,(4,a0)
        rts

; h5:01e58 has one relocated caller, h1:02aaa, called at h1:026e4.
; Reproduce ADD and its BGE inside the adapter so no returned CCR is needed.
_sim_mouse_step
        move.w (_sim_tick_motion,pc),d0
        add.w d0,(h11_08c28-$8000,a4)
        bge .positive
        move.l (_sim_mouse_negative,pc),-(sp)
        rts
.positive
        move.l (_sim_mouse_positive,pc),-(sp)
        rts

_sim_mouse_buttons
        move.l (_sim_mouse_buttons_first,pc),d0
        cmp.l (sp),d0
        beq .historical
        move.l (_sim_mouse_buttons_second,pc),d0
        cmp.l (sp),d0
        bne .native
.historical
        moveq #0,d0
        move.w (_sim_tick_input+8,pc),d0
        rts
.native move.l (_sim_input_buttons_original,pc),-(sp)
        rts

_sim_mouse_reset
        move.w d0,(h11_008d4-$8000,a4)
        move.w d0,(h11_008d2-$8000,a4)
        move.l a0,-(sp)
        lea (_sim_tick_motion,pc),a0
        clr.l (a0)
        move.l (sp)+,a0
        move.l (_sim_mouse_reset_done,pc),-(sp)
        rts

        CNOP 0,4
_sim_mouse_vbl_done dc.l 0
_sim_mouse_negative dc.l 0
_sim_mouse_positive dc.l 0
_sim_mouse_buttons_first dc.l 0
_sim_mouse_buttons_second dc.l 0
_sim_mouse_reset_done dc.l 0
_sim_mouse_position dc.w 0,0
_sim_mouse_previous dc.w 0,0
_sim_tick_motion dc.w 0,0
