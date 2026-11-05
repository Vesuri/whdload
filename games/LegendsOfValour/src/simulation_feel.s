; Visual cadence and button sensitivity are independent of world motion.
_sim_feel_check
        move.l (_hunks+4,pc),a2
        cmp.w #$4ef9,($2ae6,a2)
        bne .bad
        move.l (_h12,pc),a0
        lea ($6b54,a0),a0
        cmp.l ($2ae8,a2),a0
        bne .bad
        cmp.l #$397c000f,($218,a2)
        bne .bad
        cmp.l #$397c000a,($248,a2)
        bne .bad
        cmp.l #$397c000a,($278,a2)
        bne .bad
        cmp.l #$397c000f,($2d2,a2)
        bne .bad
        IFD SIM_FIRE_EXPERIMENT
        move.l (_hunks+5*4,pc),a2
        cmp.w #$4ef9,($2698,a2)
        bne .bad
        move.l (_hunks+2*4,pc),a0
        cmp.l ($269a,a2),a0
        bne .bad
        ENDC
        move.l (_h12,pc),a2
        adda.l #$14224,a2
        cmp.l #$1030402a,(a2)
        bne .bad
        cmp.l #$d130402b,(4,a2)
        bne .bad
        cmp.l #$6400000c,(8,a2)
        bne .bad
        rts
.bad    lea (_sim_bad,pc),a0
        bra _c2p_abort

_sim_feel_install
        move.l (_hunks+4,pc),a2
        ; PERF_RANGE h1:0021a 2 bit=6
        move.w #SIM_TURN_STEP,($21a,a2)
        ; PERF_RANGE h1:0024a 2 bit=6
        move.w #SIM_TURN_STEP,($24a,a2)
        ; PERF_RANGE h1:0027a 2 bit=6
        move.w #SIM_TURN_STEP,($27a,a2)
        ; PERF_RANGE h1:002d4 2 bit=6
        move.w #SIM_TURN_STEP,($2d4,a2)
        lea (_sim_texture_original,pc),a0
        move.l ($2ae8,a2),(a0)
        ; PERF_RANGE h1:02ae6 6 bit=6
        lea (_sim_texture,pc),a0
        move.l a0,($2ae8,a2)
        move.l (_h12,pc),a2
        adda.l #$14224,a2
        lea (_sim_actor_animation_next,pc),a0
        lea (22,a2),a1
        move.l a1,(a0)+              ; h12:1423a no frame advance
        lea (12,a2),a1
        move.l a1,(a0)               ; h12:14230 frame advance
        ; PERF_RANGE h12:14224 8 bit=6
        move.w #$4ef9,(a2)
        lea (_sim_actor_animation,pc),a0
        move.l a0,(2,a2)
        move.w #$4e71,(6,a2)
        IFD SIM_FIRE_EXPERIMENT
        move.l (_hunks+5*4,pc),a2
        lea (_sim_fire_original,pc),a0
        move.l ($269a,a2),(a0)+
        lea ($2e0,a2),a1
        move.l a1,(a0)+
        lea ($300,a2),a1
        move.l a1,(a0)+
        lea ($314,a2),a1
        move.l a1,(a0)
        ; PERF_RANGE h5:02698 6 bit=6
        lea (_sim_fire_choice,pc),a0
        move.l a0,($269a,a2)
        ENDC
        rts

_sim_visual_tick
        IFD SIM_FIRE_EXPERIMENT
        lea (_sim_fire_count,pc),a0
        addq.w #1,(a0)
        cmp.w #SIM_FIRE_TICKS,(a0)
        bcs .visual
        clr.w (a0)
        moveq #0,d0
        move.w (_sim_fire_seed,pc),d0
        mulu.w #25173,d0
        add.w #13849,d0
        move.w d0,(_sim_fire_seed-_sim_fire_count,a0)
        and.l #$ffff,d0
        move.w d0,d1
        and.w #1,d1
        move.w d1,(_sim_fire_binary-_sim_fire_count,a0)
        lsr.w #1,d0
        and.w #1,d0
        move.w d0,(_sim_fire_light-_sim_fire_count,a0)
        moveq #0,d0
        move.w (_sim_fire_seed,pc),d0
        divu.w #3,d0
        swap d0
        move.w d0,(_sim_fire_ternary-_sim_fire_count,a0)
.visual
        ENDC
        lea (_sim_visual_count,pc),a0
        addq.w #1,(a0)
        clr.w (_sim_visual_due-_sim_visual_count,a0)
        cmp.w #SIM_VISUAL_DIVISOR,(a0)
        bcs .done
        clr.w (a0)
        move.w #1,(_sim_visual_due-_sim_visual_count,a0)
.done   rts

_sim_texture
        move.l d0,-(sp)
        move.w (_sim_visual_due,pc),d0
        beq .skip
        move.l (sp)+,d0
        move.l (_sim_texture_original,pc),-(sp)
        rts
.skip   move.l (sp)+,d0
        rts

_sim_actor_animation
        move.l d0,-(sp)
        move.w (_sim_visual_due,pc),d0
        beq .skip
        move.l (sp)+,d0
        move.b (42,a0,d4.w),d0
        add.b d0,(43,a0,d4.w)
        bcc .next
        move.l (_sim_actor_animation_advance,pc),-(sp)
        rts
.skip   move.l (sp)+,d0
.next   move.l (_sim_actor_animation_next,pc),-(sp)
        rts

_sim_visual_count dc.w 0
_sim_visual_due dc.w 0
        CNOP 0,4
_sim_texture_original dc.l 0
_sim_actor_animation_next dc.l 0
_sim_actor_animation_advance dc.l 0

; Only the three cosmetic calls inside h5:0292 are intercepted. Their
; stack arguments and normal return addresses remain intact. Other RNG users
; retain the original routine. Rendering does not advance the private RNG.
_sim_fire_choice
        move.l (_sim_fire_three_return,pc),d0
        cmp.l (sp),d0
        beq .three
        move.l (_sim_fire_two_return,pc),d0
        cmp.l (sp),d0
        beq .two
        move.l (_sim_fire_light_return,pc),d0
        cmp.l (sp),d0
        beq .light
        move.l (_sim_fire_original,pc),-(sp)
        rts
.three  moveq #0,d0
        move.w (_sim_fire_ternary,pc),d0
        bra .done
.two    moveq #0,d0
        move.w (_sim_fire_binary,pc),d0
        bra .done
.light  moveq #0,d0
        move.w (_sim_fire_light,pc),d0
.done
        IFD VERIFY
        move.l a0,-(sp)
        lea (_sim_fire_draw_calls,pc),a0
        addq.l #1,(a0)
        move.l (sp)+,a0
        ENDC
        rts

_sim_fire_count dc.w 0
_sim_fire_seed dc.w $5a17
_sim_fire_ternary dc.w 0
_sim_fire_binary dc.w 0
_sim_fire_light dc.w 0
        CNOP 0,4
_sim_fire_original dc.l 0
_sim_fire_three_return dc.l 0
_sim_fire_two_return dc.l 0
_sim_fire_light_return dc.l 0
        IFD VERIFY
_sim_fire_draw_calls dc.l 0
        ENDC
