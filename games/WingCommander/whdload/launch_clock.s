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
; state advances once per tenth-second; intermediate pictures temporarily
; sample positions/viewport and restore them before the next native iteration.
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
.ready:
        moveq #0,d6
        move.w launch_exterior_hz(pc),d6
        divu.w #10,d6
        moveq #0,d7
        move.w d2,d7
        mulu.w d6,d7
        add.l launch_exterior_epoch(pc),d7
        moveq #-1,d5
.wait:
        move.l MODAL_FIELD(a4),d0
        sub.l d7,d0
        cmp.l d6,d0
        bcc.s .done
        cmp.w d5,d0
        beq.s .wait
        move.w d0,d5
        bsr.w launch_exterior_draw
        bra.s .wait
.done:
        movem.l (sp)+,d0-d7/a0-a6
        rts

; D5 elapsed fields, D6 fields/tick. Save the five pose words, scroll and
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
