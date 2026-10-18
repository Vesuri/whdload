; Native flight draws the navigation symbol before stars/world bitmaps. Defer
; only enhanced flight to the end of that scene; native eligibility/projection
; and bitmap clipping still belong to the original marker routine.
waypoint_early:
        tst.w   WAYPOINT_ACTIVE(pc)
        beq.w   waypoint_native_marker
        rts

waypoint_scene:
        move.w  4(sp),-(sp)
        bsr.w   waypoint_native_scene
        addq.l  #2,sp
        movem.l d0-d7/a0-a6,-(sp)
        tst.w   WAYPOINT_ACTIVE(pc)
        beq.s   .done
        bsr.w   waypoint_native_marker
.done:
        movem.l (sp)+,d0-d7/a0-a6
        rts
