; Controlled player motion at field cadence. Fuel, timers, throttle commands,
; collisions and all other objects remain world-owned.
translation_allowed:
        moveq   #0,d0
        cmpi.w  #12,5888(a4)
        bne.s   .done
        cmpi.w  #8,-18280(a4)
        beq.s   .done
        tst.w   -29978(a4)
        bne.s   .done
        cmpi.w  #-1,5478(a4)
        beq.s   .yes
        cmpi.w  #1,5478(a4)
        beq.s   .yes
        cmpi.w  #3,5478(a4)
        bne.s   .done
.yes:
        moveq   #1,d0
.done:
        rts

translation_reset:
        lea     translation_active(pc),a0
        clr.w   (a0)
        lea     translation_remainders(pc),a0
        moveq   #5,d0
.clear:
        clr.l   (a0)+
        dbra    d0,.clear
        rts

; D0 signed full-tick increment, D7 Hz, A0 carried remainder. Quotient split
; avoids overflowing increment*10; normalise to division toward zero.
translation_fraction:
        move.l  d0,d1
        divs.l  d7,d0
        move.l  d0,d2
        muls.l  d7,d2
        sub.l   d2,d1
        muls.l  #10,d0
        muls.l  #10,d1
        add.l   (a0),d1
        move.l  d1,d2
        divs.l  d7,d1
        move.l  d1,d3
        muls.l  d7,d3
        sub.l   d3,d2
        add.l   d1,d0
        beq.s   .store
        bmi.s   .negative
        tst.l   d2
        bpl.s   .store
        subq.l  #1,d0
        add.l   d7,d2
        bra.s   .store
.negative:
        tst.l   d2
        ble.s   .store
        addq.l  #1,d0
        sub.l   d7,d2
.store:
        move.l  d2,(a0)+
        rts

translation_field:
        movem.l d0-d7/a0-a6,-(sp)
        tst.w   timing_active(pc)
        beq.w   .inactive
        bsr.w   translation_allowed
        tst.w   d0
        beq.w   .inactive
        lea     translation_active(pc),a0
        move.w  #1,(a0)
        bsr.w   translation_acceleration
        lea     translation_remainders+12(pc),a0
        lea     4508(a4),a1
        ; D:9d6c = A4+7534, native velocity in fixed8 units/world tick.
        lea     7534(a4),a2
        move.l  timing_hz(pc),d7
        moveq   #2,d4
.axis:
        move.l  (a2)+,d0
        bsr.w   translation_fraction
        add.l   d0,(a1)+
        dbra    d4,.axis
        lea     translation_fields(pc),a0
        addq.l  #1,(a0)
        bra.s   .done
.inactive:
        bsr.w   translation_reset
.done:
        movem.l (sp)+,d0-d7/a0-a6
        rts

; Native E:7f78 acceleration solver, with its original local-frame ABI.
; Construct its desired velocity without executing fuel/action/timer effects.
translation_acceleration:
        link    a5,#-24
        movem.l d2-d5,-(sp)
        lea     translation_saved_effect(pc),a0
        move.b  15082(a4),(a0)
        moveq   #0,d2
        clr.l   -24(a5)
        clr.l   -20(a5)
        clr.l   -16(a5)
        move.l  6592(a4),d0      ; set speed (D:99be)
        cmpi.w  #3,5478(a4)
        beq.s   .braking
        cmpi.w  #1,5478(a4)
        bne.s   .target
        move.w  6136(a4),d0
        muls.w  #104,d0
        lea     -11354(a4),a0
        move.w  22(a0,d0.l),d0
        add.w   d0,d0
        addi.w  #40,d0
        ext.l   d0
        lsl.l   #8,d0
        bra.s   .target
.braking:
        moveq   #0,d0
.target:
        pea     -12(a5)
        move.l  d0,-(sp)
        pea     8522(a4)        ; forward vector D:a148
        move.l  timing_game(pc),a6
        jsr     $2b7f0(a6)
        lea     12(sp),sp
        lea     translation_preview(pc),a0
        move.w  #1,(a0)
        move.l  timing_game(pc),-(sp)
        addi.l  #$7f78,(sp)
        rts                     ; native epilogue returns to translation_field

translation_world_owned:
        moveq   #0,d0
        tst.w   timing_in_world(pc)
        beq.s   .done
        tst.w   d2
        bne.s   .done
        tst.w   translation_active(pc)
        beq.s   .done
        bra.w   translation_allowed
.done:
        rts

; Replaces E:807a's MOVE/MULS. Preview applies a fractional native delta;
; the scheduled world keeps native bookkeeping but cannot apply it a second time.
translation_velocity:
        tst.w   timing_scene_velocity_preview(pc)
        bne.w   timing_scene_velocity_result
        tst.w   translation_preview(pc)
        bne.s   .fraction
        movem.l d0-d1,-(sp)
        bsr.w   translation_world_owned
        tst.w   d0
        movem.l (sp)+,d0-d1
        bne.w   .world_done
.native:
        move.w  d2,d0
        muls.w  #12,d0
        move.l  timing_game(pc),-(sp)
        addi.l  #$8080,(sp)
        rts
.world_done:
        lea     -24(a5),a0
        lea     15150(a4),a1
        move.l  (a0)+,(a1)+
        move.l  (a0)+,(a1)+
        move.l  (a0)+,(a1)+
        bra.w   translation_epilogue
.fraction:
        move.b  translation_saved_effect(pc),15082(a4)
        lea     translation_preview(pc),a0
        clr.w   (a0)
        lea     translation_remainders(pc),a0
        lea     -24(a5),a1
        lea     7534(a4),a2
        lea     translation_last_acceleration(pc),a3
        move.l  timing_hz(pc),d7
        moveq   #2,d4
.axis:
        move.l  (a1)+,d0
        move.l  d0,(a3)+
        bsr.w   translation_fraction
        add.l   d0,(a2)+
        dbra    d4,.axis
translation_epilogue:
        move.l  timing_game(pc),-(sp)
        addi.l  #$80ea,(sp)
        rts

; Replaces E:80b6's MOVE/MULS. Non-player and non-controlled paths are native.
translation_position:
        movem.l d0-d1,-(sp)
        bsr.w   translation_world_owned
        tst.w   d0
        movem.l (sp)+,d0-d1
        bne.s   translation_epilogue
        move.w  d2,d0
        muls.w  #12,d0
        move.l  timing_game(pc),-(sp)
        addi.l  #$80bc,(sp)
        rts
        cnop 0,4
translation_active: dc.w 0
translation_preview: dc.w 0
translation_remainders: dcb.l 6,0
translation_last_acceleration: dcb.l 3,0
translation_fields: dc.l 0
translation_saved_effect: dc.w 0

        ifne FRAME_STATS
; Observe the real world boundary, not a reconstructed trajectory. No gameplay
; writes: collision and camera code see the already-committed field position.
translation_tick_begin:
        movem.l d0/a0-a1,-(sp)
        lea     translation_tick_valid(pc),a0
        clr.w   (a0)
        tst.w   translation_active(pc)
        beq.s   .done
        bsr.w   translation_allowed
        tst.w   d0
        beq.s   .done
        move.w  #1,(a0)
        lea     translation_tick_pose(pc),a0
        lea     4508(a4),a1
        move.l  (a1)+,(a0)+
        move.l  (a1)+,(a0)+
        move.l  (a1)+,(a0)+
        lea     5240(a4),a1      ; camera position, slot 61
        move.l  (a1)+,(a0)+
        move.l  (a1)+,(a0)+
        move.l  (a1)+,(a0)+
.done:
        movem.l (sp)+,d0/a0-a1
        rts
translation_tick_end:
        movem.l d0-d1/a0-a2,-(sp)
        tst.w   translation_tick_valid(pc)
        beq.s   .done
        bsr.w   translation_allowed
        tst.w   d0
        beq.s   .done
        lea     translation_ticks_checked(pc),a0
        addq.l  #1,(a0)
        lea     translation_tick_pose(pc),a0
        lea     4508(a4),a1
        lea     translation_position_corrections(pc),a2
        bsr.s   .compare
        lea     5240(a4),a1
        lea     translation_camera_corrections(pc),a2
        bsr.s   .compare
.done:
        movem.l (sp)+,d0-d1/a0-a2
        rts
.compare:
        moveq   #0,d1
        moveq   #2,d0
.axis:
        cmpm.l  (a0)+,(a1)+
        beq.s   .same
        moveq   #1,d1
.same:
        dbra    d0,.axis
        add.l   d1,(a2)
        rts
        cnop 0,4
translation_tick_valid: dc.w 0
        cnop 0,4
translation_tick_pose: dcb.l 6,0
translation_ticks_checked: dc.l 0
translation_position_corrections: dc.l 0
translation_camera_corrections: dc.l 0
        endif

; C3: predict thrust toward the already-predicted heading. The original solver
; retains inertia/engine capability. No AI, RNG, fuel or timer routine is run.
; Normal, afterburn and braking thrust are forecast while their action is stable.
; Action expiry and scripted motion retain current velocity until the world tick.
timing_scene_velocity:
        tst.w   d4
        beq.s   .done
        cmpi.w  #10,d4
        bhs.s   .done
        lea     5888(a4),a0
        cmpi.w  #11,(a0,d4.w*2)
        blo.s   .done
        lea     5478(a4),a0
        move.w  (a0,d4.w*2),d0
        cmpi.w  #-1,d0
        beq.s   .stage
        cmpi.w  #1,d0
        beq.s   .timer
        cmpi.w  #3,d0
        bne.s   .done
.timer:
        lea     15126(a4),a0
        cmpi.w  #1,(a0,d4.w*2)
        ble.s   .done
.stage:
        lea     14932(a4),a0
        cmpi.w  #1,(a0,d4.w*2)
        beq.s   .done
        movem.l d0-d7/a0-a6,-(sp)
        bsr.s   timing_scene_velocity_solve
        movem.l (sp)+,d0-d7/a0-a6
.done:
        rts

timing_scene_velocity_solve:
        link    a5,#-24
        movem.l d2-d5,-(sp)
        move.w  d4,d2
        lea     timing_scene_velocity_preview(pc),a0
        move.w  #1,(a0)
        lea     15082(a4),a1
        move.b  (a1,d2.w),2(a0)
        clr.l   -24(a5)
        clr.l   -20(a5)
        clr.l   -16(a5)
        lea     6592(a4),a0
        move.l  (a0,d2.w*4),d0
        lea     5478(a4),a0
        cmpi.w  #3,(a0,d2.w*2)
        beq.s   .brake
        cmpi.w  #1,(a0,d2.w*2)
        bne.s   .target
        lea     6136(a4),a0
        move.w  (a0,d2.w*2),d0
        muls.w  #104,d0
        lea     -11354(a4),a0
        move.w  22(a0,d0.l),d0
        add.w   d0,d0
        addi.w  #40,d0
        ext.l   d0
        lsl.l   #8,d0
        bra.s   .target
.brake:
        moveq   #0,d0
.target:
        pea     -12(a5)
        move.l  d0,-(sp)
        lea     8522(a4),a0
        adda.w  d5,a0
        move.l  a0,-(sp)
        move.l  timing_game(pc),a6
        jsr     $2b7f0(a6)
        lea     12(sp),sp
        move.l  timing_game(pc),-(sp)
        addi.l  #$7f78,(sp)
        rts

timing_scene_velocity_result:
        lea     timing_scene_velocity_preview(pc),a0
        clr.w   (a0)
        lea     15082(a4),a1
        move.b  2(a0),(a1,d2.w)
        move.w  d2,d0
        mulu.w  #12,d0
        lea     7534(a4),a2
        adda.w  d0,a2
        lea     -24(a5),a3
        moveq   #2,d3
.axis:
        move.l  (a3)+,d0
        bsr.w   timing_scene_scale
        add.l   d0,(a2)+
        dbra    d3,.axis
        bra.w   translation_epilogue
        cnop 0,4
timing_scene_velocity_preview: dc.w 0,0
