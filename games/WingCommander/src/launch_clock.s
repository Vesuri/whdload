; Native launch tunnel: 25 script/world updates at 10 Hz. The four expanding
; layers are depth projections, sampled fractionally on each rendered picture.
launch_loop:
        movem.l d5-d7/a0-a3/a6,-(sp)
        bsr.w intro_start
.loop:
        bsr.w intro_due
        move.w d0,d7
.ticks:
        tst.w d7
        beq.s .draw
        bsr.w intro_world
        lea -8(a5),a2
        moveq #3,d3
.depth: sub.w d4,(a2)+
        dbra d3,.depth
        moveq #0,d0
        move.w d2,d0
        divu.w #5,d0
        swap d0
        tst.w d0
        bne.s .next
        addq.w #1,d4
.next:
        addq.w #1,d2
        cmpi.w #25,d2
        bhs.w .done
        subq.w #1,d7
        bra.s .ticks
.draw:
        bsr.w intro_draw
        move.b LAUNCH_COLOUR(a4),-(sp)
        pea LAUNCH_SURFACE(a4)
        bsr.w modal_bar_clear
        addq.l #6,sp
        lea -8(a5),a2
        moveq #3,d3
.layer:
        move.w (a2)+,d0
        bsr.w launch_scale
        tst.w d0
        beq.s .skip
        move.w d0,-(sp)
        clr.w -(sp)
        move.l LAUNCH_IMAGE(a4),-(sp)
        move.w MODAL_CENTRE_Y(a4),-(sp)
        move.w MODAL_CENTRE_X(a4),-(sp)
        pea LAUNCH_SURFACE(a4)
        bsr.w launch_zoom
        lea 16(sp),sp
.skip:
        dbra d3,.layer
        bsr.w launch_hud
        bsr.w intro_finish
        bsr.w modal_input
        tst.w MODAL_ABORT(a4)
        beq.w .loop
.done:
        bsr.w intro_stop
        movem.l (sp)+,d5-d7/a0-a3/a6
        bra.w launch_resume

; D0 depth, D4 speed. D0 returns scale, or zero for the native <=10 near cut.
; Debt is already in tenths of a field: denominator = depth*Hz-speed*debt.
launch_scale:
        movem.l d1-d2/a0,-(sp)
        cmpi.w #10,d0
        ble.s .hidden
        lea launch_scale(pc),a0
        adda.l #MODAL_HZ-launch_scale,a0
        moveq #0,d1
        move.w 2(a0),d1
        mulu.w d1,d0
        lea launch_scale(pc),a0
        adda.l #MODAL_CLOCK-launch_scale,a0
        move.l 4(a0),d2
        mulu.w d4,d2
        sub.l d2,d0
        move.l d1,d2
        mulu.w #10,d2
        cmp.l d2,d0
        ble.s .hidden
        move.l d0,d2
        move.l d1,d0
        mulu.w #6656,d0
        divu.w d2,d0
        andi.l #$ffff,d0
        bra.s .done
.hidden:
        moveq #0,d0
.done:
        movem.l (sp)+,d1-d2/a0
        rts

; Exterior launch is a bitmap script before mission world setup. Its native
; state advances every three display fields; intermediate pictures temporarily
; sample positions/viewport and restore them before the next native iteration.
; The native compositor draws on every other iteration (odd in stages 0/1, even
; in stage 2) and only when its frame-skip countdown expires; each drawing call
; also advances the bitmap actors once. Pictures between two native drawings
; replay the actor records saved before the last one, at a fractional position,
; so actors move every picture and keep the native picture's animation frame.
launch_exterior_wait:
        movem.l d0-d7/a0-a6,-(sp)
        lea launch_exterior_stage(pc),a0
        move.w d0,(a0)
        tst.w d2
        bne.s .ready
        bsr.w timing_rate
        lea launch_exterior_hz(pc),a0
        move.w d0,(a0)
        lea launch_exterior_epoch(pc),a0
        move.l MODAL_FIELD(a4),(a0)
        lea launch_exterior_valid(pc),a0
        clr.w (a0)
        ; Stage 2 draws before its first wait from the records saved at the end of stage 1.
        cmpi.w #2,launch_exterior_stage(pc)
        beq.s .ready
        lea launch_exterior_saved(pc),a0
        clr.w (a0)
.ready:
        moveq #0,d4
        bsr.w launch_exterior_call
        beq.s .schedule
        move.w MODAL_COUNTDOWN(a4),d0
        cmp.w MODAL_COUNTDOWN+2(a4),d0
        bne.s .schedule
        ; The native compositor drew this iteration's picture before this wait.
        moveq #1,d4
        lea launch_exterior_valid(pc),a0
        move.w launch_exterior_saved(pc),(a0)
        lea launch_exterior_saved(pc),a0
        clr.w (a0)
        move.w d2,d0
        mulu.w #150,d0
        lea launch_exterior_last(pc),a0
        move.w d0,(a0)
.schedule:
        moveq #0,d6
        move.w #150,d6
        moveq #0,d7
        move.w d2,d7
        mulu.w d6,d7
        moveq #-1,d5
        tst.w d4
        beq.s launch_exterior_idle
        moveq #0,d5             ; the native picture is this interval's first sample
; Global so the native check can advance its field clock while waiting.
launch_exterior_idle:
        move.l MODAL_FIELD(a4),d0
        sub.l launch_exterior_epoch(pc),d0
        mulu.w #50,d0
        sub.l d7,d0
        cmp.l d6,d0
        bcc.s .done
        cmp.w d5,d0
        beq.s launch_exterior_idle
        move.w d0,d5
        bsr.w launch_exterior_draw
        bra.s launch_exterior_idle
.done:
        ; Save the records the next native drawing starts from.
        addq.w #1,d2
        cmpi.w #1,launch_exterior_stage(pc)
        bne.s .next
        cmpi.w #27,d2
        beq.s .save
.next:
        bsr.w launch_exterior_call
        beq.s .exit
        cmpi.w #22,d2
        bne.s .countdown
        cmpi.w #2,launch_exterior_stage(pc)
        beq.s .save
.countdown:
        cmpi.w #1,MODAL_COUNTDOWN(a4)
        bgt.s .exit
.save:
        lea EXT_ACTORS(a4),a0
        lea launch_exterior_stage(pc),a1
        adda.l #landing_actor_previous-launch_exterior_stage,a1
        moveq #29,d0
.copy:
        move.l (a0)+,(a1)+
        dbra d0,.copy
        lea launch_exterior_saved(pc),a0
        move.w #1,(a0)
.exit:
        movem.l (sp)+,d0-d7/a0-a6
        rts

; D2 iteration -> Z clear when the native loop calls the compositor on it.
launch_exterior_call:
        move.w d2,d0
        andi.w #1,d0
        cmpi.w #2,launch_exterior_stage(pc)
        bne.s .test
        eori.w #1,d0
.test:
        tst.w d0
        rts

; D2 iteration, D5 elapsed units (x50). Live actor records are already saved by
; the caller. Replace them with the records the native compositor advances into
; the last native picture, offset by velocity * time since it / native period.
; Before a stage's first native picture, the live records lead into the next.
launch_exterior_actors:
        movem.l d0-d4/a0-a1,-(sp)
        moveq #0,d3
        move.w MODAL_COUNTDOWN+2(a4),d3
        bgt.s .period
        moveq #1,d3
.period:
        mulu.w #300,d3
        lea EXT_ACTORS(a4),a1
        move.w d5,d1
        tst.w launch_exterior_valid(pc)
        bne.s .replay
        subi.w #150,d1
        bra.s .clamp
.replay:
        move.w d2,d0
        mulu.w #150,d0
        add.w d0,d1
        sub.w launch_exterior_last(pc),d1
        lea launch_exterior_stage(pc),a0
        adda.l #landing_actor_previous-launch_exterior_stage,a0
        moveq #29,d0
.copy:
        move.l (a0)+,(a1)+
        dbra d0,.copy
        lea EXT_ACTORS(a4),a1
.clamp:
        cmp.w d3,d1
        ble.s .low
        move.w d3,d1
.low:
        move.w d3,d0
        neg.w d0
        cmp.w d0,d1
        bge.s .records
        move.w d0,d1
.records:
        moveq #4,d4
.pose:
        move.w 4(a1),d0
        muls.w d1,d0
        divs.w d3,d0
        add.w d0,(a1)
        move.w 6(a1),d0
        muls.w d1,d0
        divs.w d3,d0
        add.w d0,2(a1)
        lea 24(a1),a1
        dbra d4,.pose
        movem.l (sp)+,d0-d4/a0-a1
        rts

; D5 elapsed field units (x50), D6 units/tick (150). Save the five pose words, scroll and
; native draw countdown and bitmap actors; repeated compositor calls must not
; commit the native actor routine's position/script advances.
launch_exterior_draw:
        movem.l d0-d7/a0-a6,-(sp)
        lea EXT_ACTORS(a4),a0
        moveq #29,d0
.save_actors:
        move.l (a0)+,-(sp)
        dbra d0,.save_actors
        move.l EXT_POSITION(a4),-(sp)
        move.l EXT_POSITION+4(a4),-(sp)
        move.w EXT_POSITION+8(a4),-(sp)
        move.w EXT_SCROLL(a4),-(sp)
        move.w MODAL_COUNTDOWN(a4),-(sp)
        bsr.w launch_exterior_actors
        cmpi.w #2,launch_exterior_stage(pc)
        beq.s .depart
        move.w d5,d0
        mulu.w #4,d0
        divu.w d6,d0
        subq.w #4,d0
        add.w d0,EXT_POSITION(a4)
        tst.w launch_exterior_stage(pc)
        bne.s .scroll
        ; DIVU leaves its remainder in the upper word. The independent Y
        ; division must not inherit the X division's remainder as dividend.
        moveq #0,d0
        move.w d5,d0
        add.w d0,d0
        divu.w d6,d0
        neg.w d0
        addq.w #2,d0
        add.w d0,EXT_POSITION+2(a4)
.scroll:
        addq.w #1,EXT_SCROLL(a4)
        move.w #128,-(sp)
        bra.s .pose
.depart:
        move.w d2,d0
        mulu.w d6,d0
        add.w d5,d0
        mulu.w #128,d0
        move.w d6,d1
        mulu.w #22,d1
        divu.w d1,d0
        neg.w d0
        addi.w #128,d0
        bpl.s .positive
        moveq #0,d0
.positive:
        move.w d0,-(sp)
.pose:
        bsr.w launch_exterior_pose
        addq.l #2,sp
        move.w #1,MODAL_COUNTDOWN(a4)
        bsr.w launch_exterior_native
        move.w (sp)+,MODAL_COUNTDOWN(a4)
        move.w (sp)+,EXT_SCROLL(a4)
        move.w (sp)+,EXT_POSITION+8(a4)
        move.l (sp)+,EXT_POSITION+4(a4)
        move.l (sp)+,EXT_POSITION(a4)
        lea EXT_ACTORS+120(a4),a0
        moveq #29,d0
.restore_actors:
        move.l (sp)+,-(a0)
        dbra d0,.restore_actors
        movem.l (sp)+,d0-d7/a0-a6
        rts
launch_exterior_stage: dc.w 0
launch_exterior_hz: dc.w 50
launch_exterior_epoch: dc.l 0
launch_exterior_last: dc.w 0
launch_exterior_valid: dc.w 0
launch_exterior_saved: dc.w 0
