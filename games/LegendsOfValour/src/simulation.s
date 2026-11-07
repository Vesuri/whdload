; Simulation timing: release Enhanced frame rate, developer CUSTOM2 bit 6. PAL reference.
; These constants belong together when changing the reference rate.
SIM_FIELDS_PER_TICK = 2
SIM_MOVEMENT_STEP = 10
SIM_ANIMATION_PACING = 8
SIM_VISUAL_DIVISOR = 2
SIM_FIRE_TICKS = 4
SIM_TURN_STEP = 5

_sim_install
        movem.l d0-a6,-(sp)
        move.l (_custom2,pc),d0
        btst #6,d0
        beq .done
        move.l (_custom1,pc),d0
        bne .done
        move.l (_hunks+4,pc),a2
        cmp.l #$4a2ce008,($2496,a2)
        bne .bad
        cmp.l #$6600028c,($249a,a2)
        bne .bad
        cmp.l #$4a6cdfea,($2714,a2)
        bne .bad
        cmp.l #$6700fd7c,($2718,a2)
        bne .bad
        cmp.w #$4ef9,($2b46,a2)
        bne .bad
        move.l (_hunks+5*4,pc),a0
        lea ($2358,a0),a0
        cmp.l ($2b48,a2),a0
        bne .bad
        cmp.w #$4ef9,($2be8,a2)
        bne .bad
        move.l (_h12,pc),a0
        lea ($5ea6,a0),a0
        cmp.l ($2bea,a2),a0
        bne .bad
        move.l (_h12,pc),a2
        cmp.w #$52b9,($6412,a2)
        bne .bad
        move.l (_h11,pc),a0
        lea ($4d6,a0),a0
        cmp.l ($6414,a2),a0
        bne .bad
        cmp.w #$5379,($27c4,a2)
        bne .bad
        lea ($27ba,a2),a0
        cmp.l ($27c6,a2),a0
        bne .bad
        move.l (_hunks+5*4,pc),a2
        cmp.l #$80416700,($14de,a2)
        bne .bad
        cmp.w #$021c,($14e2,a2)
        bne .bad
        cmp.l #$526c8df4,($1934,a2)
        bne .bad
        cmp.l #$302c8df4,($1938,a2)
        bne .bad
        cmp.l #$b06c8df6,($193c,a2)
        bne .bad
        cmp.w #$6d12,($1940,a2)
        bne .bad

        ; Validate the complete original compensation table before any writes.
        move.l (_h12,pc),a2
        lea ($5e7a,a2),a0
        moveq #0,d0
.check_table
        move.w d0,d1
        lsl.w #2,d1
        addq.w #8,d1
        tst.w d0
        bne .check_step
        moveq #10,d1
.check_step
        cmp.w (a0)+,d1
        bne .bad
        move.w d0,d1
        lsr.w #1,d1
        moveq #4,d2
        sub.w d1,d2
        bgt .check_pacing
        moveq #1,d2
.check_pacing
        cmp.w (a0)+,d2
        bne .bad
        addq.w #1,d0
        cmp.w #11,d0
        bne .check_table

        bsr _sim_input_check
        bsr _sim_clock_check
        IFD SIM_KEYBOARD_EXPERIMENT
        bsr _sim_keys_check
        ENDC
        IFD SIM_COMBAT_EXPERIMENT
        bsr _sim_combat_check
        ENDC
        bsr _sim_feel_check

        ; Resolve slave-owned continuation pointers. No fixed guest addresses.
        lea (_sim_target_specs,pc),a0
        lea (_sim_targets,pc),a1
        lea (_hunks,pc),a2
        moveq #(_sim_targets_end-_sim_targets)/4-1,d2
.target move.w (a0)+,d0
        move.l (0,a2,d0.w),d1
        add.l (a0)+,d1
        move.l d1,(a1)+
        dbf d2,.target

        bsr _sim_input_install
        bsr _sim_clock_install
        IFD SIM_KEYBOARD_EXPERIMENT
        bsr _sim_keys_install
        ENDC
        IFD SIM_COMBAT_EXPERIMENT
        bsr _sim_combat_install
        ENDC
        bsr _sim_feel_install

        ; PERF_RANGE h1:02496 8 bit=6
        move.l (_hunks+4,pc),a2
        lea ($2496,a2),a0
        lea (_sim_loop,pc),a1
        bsr .jump
        move.w #$4e71,($249c,a2)
        ; PERF_RANGE h1:02714 8 bit=6
        lea ($2714,a2),a0
        lea (_sim_end_tick,pc),a1
        bsr .jump
        move.w #$4e71,($271a,a2)
        ; PERF_RANGE h1:02b46 6 bit=6
        lea ($2b46,a2),a0
        lea (_sim_sprites,pc),a1
        bsr .jump
        ; PERF_RANGE h1:02be8 6 bit=6
        lea ($2be8,a2),a0
        lea (_sim_display,pc),a1
        bsr .jump
        move.l (_h12,pc),a2
        ; PERF_RANGE h12:06412 6 bit=6
        lea ($6412,a2),a0
        lea (_sim_vbl,pc),a1
        bsr .jump
        ; PERF_RANGE h12:027c4 6 bit=6
        lea ($27c4,a2),a0
        lea (_sim_renderer,pc),a1
        bsr .jump
        ; The display wait still runs unchanged; normalize only its step table.
        ; PERF_RANGE h12:05e7a 44 bit=6
        lea ($5e7a,a2),a0
        moveq #10,d0
.table  move.w #SIM_MOVEMENT_STEP,(a0)+
        move.w #SIM_ANIMATION_PACING,(a0)+
        dbf d0,.table
        ; Normalize startup creation too, before the first display-clock call.
        move.l a2,a0
        adda.l #$cdd6,a0
        move.w #SIM_MOVEMENT_STEP,(a0)
        move.l (_h11,pc),a0
        move.w #SIM_ANIMATION_PACING,($df6,a0)
        move.l (_hunks+5*4,pc),a2
        ; PERF_RANGE h5:014de 6 bit=6
        lea ($14de,a2),a0
        lea (_sim_projectile_motion,pc),a1
        bsr .jump
        ; PERF_RANGE h5:01934 8 bit=6
        lea ($1934,a2),a0
        lea (_sim_animation,pc),a1
        bsr .jump
        move.w #$4e71,($193a,a2)
        move.l (_resload,pc),a2
        jsr (resload_FlushCache,a2)
.done   movem.l (sp)+,d0-a6
        rts
.jump   move.w #$4ef9,(a0)+
        move.l a1,(a0)
        rts
.bad    lea (_sim_bad,pc),a0
        bra _c2p_abort

; Called only on the enabled branch of the game's VBL clock. Keep the private
; counter separate from the saved game clock, which resting can jump forwards.
_sim_vbl
        move.l a0,-(sp)
        lea (_sim_started,pc),a0
        tst.w (a0)
        beq .game_clock
        lea (_sim_suspended,pc),a0
        tst.w (a0)
        bne .game_clock
        lea (_sim_fields,pc),a0
        addq.l #1,(a0)
.game_clock
        move.l (_h11,pc),a0
        addq.l #1,($4d6,a0)
        move.l (sp)+,a0
        move.l (_sim_vbl_continue,pc),-(sp)
        rts

; The original loop's first TST/BNE is reproduced. Waiting stays in the main
; task; VBL only counts time. Never discard overdue active simulation ticks.
_sim_loop
        movem.l d0-d1/a0,-(sp)
        lea (_sim_started,pc),a0
        tst.b ($6008-32768,a4)
        bne .exit
        tst.w (a0)
        bne .wait
        move.w #1,(a0)
        bsr _sim_input_sample
        move.l (_sim_fields,pc),d0
        sub.l #SIM_FIELDS_PER_TICK,d0
        lea (_sim_consumed,pc),a0
        move.l d0,(a0)
.wait   move.l (_sim_fields,pc),d0
        sub.l (_sim_consumed,pc),d0
        cmp.l #SIM_FIELDS_PER_TICK,d0
        bcs .wait
        lea (_sim_consumed,pc),a0
        add.l #SIM_FIELDS_PER_TICK,(a0)
        sub.l #SIM_FIELDS_PER_TICK,d0
        lea (_sim_render_tick,pc),a0
        clr.w (a0)
        cmp.l #SIM_FIELDS_PER_TICK,d0
        bcc .catchup
        move.w #1,(a0)
        bra .resume
.catchup
        lea (_sim_catchups,pc),a0
        addq.l #1,(a0)
.resume
        bsr _sim_visual_tick
        IFD VERIFY
        IFD TIMING_STUDY
        bsr _timing_study_panel
        bsr _timing_study_stall
        bsr _timing_keys_blocking
        bsr _timing_keys_exit
        bsr _timing_combat_enter
        IFD TIMING_PROJECTILE
        bsr _timing_projectile_launch
        ENDC
        ENDC
        ENDC
        bsr _sim_input_select
        bsr _sim_clock_read
        lea (_sim_started_ticks,pc),a0
        addq.l #1,(a0)
        movem.l (sp)+,d0-d1/a0
        move.l (_sim_loop_continue,pc),-(sp)
        rts
.exit   clr.w (a0)
        movem.l (sp)+,d0-d1/a0
        move.l (_sim_loop_exit,pc),-(sp)
        rts

_sim_end_tick
        move.l d0,-(sp)
        bsr _sim_clock_read
        move.l (sp)+,d0
_sim_tick_complete
        ; Read-only observers stop here, after refreshing the logical timestamp.
        move.l a0,-(sp)
        lea (_sim_completed_ticks,pc),a0
        addq.l #1,(a0)
        move.l (sp)+,a0
        tst.w ($5fea-32768,a4)
        bne .load
        move.l (_sim_loop_restart,pc),-(sp)
        rts
.load   move.l (_sim_load_continue,pc),-(sp)
        rts

; Original renderer has already saved D2-D7/A2-A6 (44 bytes). Only the main
; tick caller advances the world. Nested interaction redraws publish and draw.
_sim_renderer
        move.l (_sim_main_renderer_return,pc),d0
        cmp.l (44,sp),d0
        bne .redraw
        move.l (_sim_position,pc),a1
        jsr (a1)
        move.l (_h12,pc),a0
        subq.w #1,($27ba,a0)
        bpl .actors
        move.w #15,($27ba,a0)
        move.l (_sim_periodic,pc),a1
        jsr (a1)
.actors move.l (_sim_actors,pc),a1
        jsr (a1)
        move.l (_sim_publish,pc),a1
        jsr (a1)
        move.w (_sim_render_tick,pc),d0
        beq .skip
        move.l (_sim_render_continue,pc),-(sp)
        rts
.redraw move.l (_sim_publish,pc),a1
        jsr (a1)
        move.l (_sim_render_continue,pc),-(sp)
        rts
.skip   move.l (_sim_render_done,pc),-(sp)
        rts

; These thunks are shared with modal redraws. Skip only the main tick's drawing.
_sim_sprites
        move.l d0,-(sp)
        move.l (_sim_main_sprite_return,pc),d0
        cmp.l (4,sp),d0
        bne .draw
        move.w (_sim_render_tick,pc),d0
        beq .skip
.draw   move.l (sp)+,d0
        move.l (_sim_sprite_original,pc),-(sp)
        rts
.skip   move.l (sp)+,d0
        rts
_sim_display
        move.l d0,-(sp)
        move.l (_sim_main_display_return,pc),d0
        cmp.l (4,sp),d0
        bne .draw
        move.w (_sim_render_tick,pc),d0
        beq .skip
.draw   move.l (sp)+,d0
        move.l (_sim_display_original,pc),-(sp)
        rts
.skip   move.l (sp)+,d0
        rts

; The object builder also serves modal redraws. Project paused objects at their
; current positions there, without applying a second physics or animation step.
_sim_projectile_motion
        move.l d2,-(sp)
        move.l (_sim_main_builder_return,pc),d2
        cmp.l (4,a5),d2
        bne .static
        move.l (sp)+,d2
        or.w d1,d0
        beq .vertical
        move.l (_sim_projectile_move,pc),-(sp)
        rts
.vertical
        move.l (_sim_projectile_vertical,pc),-(sp)
        rts
.static move.l (sp)+,d2
        move.l (_sim_projectile_static,pc),-(sp)
        rts
_sim_animation
        move.l d0,-(sp)
        move.l (_sim_main_builder_return,pc),d0
        cmp.l (4,a5),d0
        bne .skip
        move.l (sp)+,d0
        addq.w #1,($df4-32768,a4)
        move.w ($df4-32768,a4),d0
        ; Compare and branch here: pushing the continuation destroys CCR.
        ; The old adapter skipped CMP and entered BLT with address flags.
        cmp.w ($df6-32768,a4),d0
        blt .hold
        move.l (_sim_animation_continue,pc),-(sp)
        rts
.hold   move.l (_sim_animation_skip,pc),-(sp)
        rts
.skip   move.l (sp)+,d0
        move.l (_sim_animation_skip,pc),-(sp)
        rts

_sim_bad dc.b "Simulation: unexpected game code",0
        EVEN
_sim_suspended dc.w 0
_sim_started dc.w 0
_sim_render_tick dc.w 1
        CNOP 0,4
_sim_fields dc.l 0
_sim_consumed dc.l 0
_sim_started_ticks dc.l 0
_sim_completed_ticks dc.l 0
_sim_catchups dc.l 0
_sim_targets
_sim_loop_continue dc.l 0
_sim_loop_exit dc.l 0
_sim_loop_restart dc.l 0
_sim_load_continue dc.l 0
_sim_main_renderer_return dc.l 0
_sim_main_builder_return dc.l 0
_sim_main_sprite_return dc.l 0
_sim_main_display_return dc.l 0
_sim_render_continue dc.l 0
_sim_render_done dc.l 0
_sim_actors dc.l 0
_sim_publish dc.l 0
_sim_periodic dc.l 0
_sim_position dc.l 0
_sim_vbl_continue dc.l 0
_sim_sprite_original dc.l 0
_sim_display_original dc.l 0
_sim_projectile_move dc.l 0
_sim_projectile_vertical dc.l 0
_sim_projectile_static dc.l 0
_sim_animation_continue dc.l 0
_sim_animation_skip dc.l 0
_sim_targets_end
_sim_target_specs
        dc.w 1*4
        dc.l $249e
        dc.w 1*4
        dc.l $2728
        dc.w 1*4
        dc.l $2496
        dc.w 1*4
        dc.l $271c
        dc.w 1*4
        dc.l $2632
        dc.w 1*4
        dc.l $2636
        dc.w 1*4
        dc.l $2646
        dc.w 1*4
        dc.l $2656
        dc.w 12*4
        dc.l $27e6
        dc.w 12*4
        dc.l $2802
        dc.w 12*4
        dc.l $140e6
        dc.w 12*4
        dc.l $fc12
        dc.w 12*4
        dc.l $15b1a
        dc.w 12*4
        dc.l $2720
        dc.w 12*4
        dc.l $6418
        dc.w 5*4
        dc.l $2358
        dc.w 12*4
        dc.l $5ea6
        dc.w 5*4
        dc.l $14e4
        dc.w 5*4
        dc.l $16fe
        dc.w 5*4
        dc.l $173e
        dc.w 5*4
        dc.l $1942
        dc.w 5*4
        dc.l $1954

        INCLUDE "simulation_input.s"

        INCLUDE "simulation_clock.s"

        IFD SIM_KEYBOARD_EXPERIMENT
        INCLUDE "simulation_keyboard.s"
        ENDC
        INCLUDE "simulation_feel.s"

        IFD SIM_COMBAT_EXPERIMENT
        INCLUDE "simulation_combat.s"
        ENDC
