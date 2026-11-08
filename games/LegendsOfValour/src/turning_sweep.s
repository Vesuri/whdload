; VERIFY bit 21: exercise all 360 headings through the actual wall ray walker
; once per supported view, at the current fixed position. No actor update is
; called. Restore the heading and let the enclosing pass redraw the real view.
_turn_sweep_rays
        movem.l d0-a6,-(sp)
        move.l (_custom5,pc),d0
        btst #21,d0
        beq .done
        move.l (_turn_active,pc),d0
        beq .done
        move.l (_h12,pc),a0
        move.w (h12_0002e,a0),d0
        moveq #0,d1
        cmp.w #80,d0
        beq .view
        moveq #1,d1
        cmp.w #112,d0
        beq .view
        moveq #2,d1
        cmp.w #192,d0
        bne .done
.view
        lea (_turn_sweep_mask,pc),a0
        btst d1,(a0)
        bne .done
        bset d1,(a0)
        lea (_turn_sweep_view,pc),a0
        lsl.w #2,d1
        move.w d1,(a0)
        move.l (_h11,pc),a0
        move.l a0,a1
        adda.l #$8000,a1
        lea (_turn_sweep_heading,pc),a2
        move.w (h11_08c22-$8000,a1),(a2)
        move.l (h11_05fc2,a0),a1
        lea (_turn_sweep_guards,pc),a2
        move.l (-4,a1),(a2)+
        move.l (20000,a1),(a2)
        lea (_turn_sweep_angle,pc),a0
        clr.w (a0)
.next
        move.l (_h11,pc),a0
        adda.l #$8000,a0
        move.w (_turn_sweep_angle,pc),(h11_08c22-$8000,a0)
        movem.l (sp),d0-a6
        bsr _turn_ray_original
        move.l (_h11,pc),a0
        move.l (h11_05fc2,a0),a0
        move.l (_turn_sweep_guards,pc),d0
        cmp.l (-4,a0),d0
        bne .bad
        move.l (_turn_sweep_guards+4,pc),d0
        cmp.l (20000,a0),d0
        bne .bad
        lea (_turn_sweep_angle,pc),a0
        addq.w #1,(a0)
        cmp.w #360,(a0)
        bcs .next
        move.l (_h11,pc),a0
        adda.l #$8000,a0
        move.w (_turn_sweep_heading,pc),(h11_08c22-$8000,a0)
        move.w (_turn_sweep_view,pc),d0
        lea (_turn_sweep_counts,pc),a0
        move.l #360,(a0,d0.w)
.done   movem.l (sp)+,d0-a6
        rts
.bad    lea (_turn_sweep_bad,pc),a0
        bra _c2p_abort
_turn_sweep_mask dc.w 0
_turn_sweep_heading dc.w 0
_turn_sweep_angle dc.w 0
_turn_sweep_view dc.w 0
_turn_sweep_counts dc.l 0,0,0
_turn_sweep_guards dc.l 0,0
_turn_sweep_bad dc.b "1 degree turning: full-angle ray sweep overwrote buffer guards",0
        EVEN
