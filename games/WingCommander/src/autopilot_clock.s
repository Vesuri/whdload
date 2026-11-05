; The waypoint fly-by alone uses the world clock. The subsequent fast-travel
; and arrival transaction stays native and runs after prediction is restored.
; Arguments: camera word, subject word, native duration in fields.
autopilot_scene:
        movem.l d2-d7/a2-a3,-(sp)
        moveq #0,d6
        move.w 40(sp),d6
        add.l MODAL_FIELD(a4),d6
        move.w 38(sp),-(sp)
        move.w 38(sp),-(sp)
        bsr.w autopilot_camera
        addq.l #4,sp
        bsr.w intro_start
.loop:
        bsr.w intro_due
        move.w d0,d7
.ticks:
        tst.w d7
        beq.s .draw
        bsr.w intro_world
        subq.w #1,d7
        bra.s .ticks
.draw:
        move.l d6,d0
        sub.l MODAL_FIELD(a4),d0
        ble.s .done
        bsr.w intro_draw
        bsr.w autopilot_overlay
        bsr.w intro_finish
        bra.s .loop
.done:
        bsr.w intro_stop
        movem.l (sp)+,d2-d7/a2-a3
        rts

autopilot_entry:
        bsr.w autopilot_scene
        addq.l #6,sp
        bra.w autopilot_resume
