; Native flight draws the navigation symbol before stars/world bitmaps, so
; scene bitmaps such as nebulae cover it. Defer it to the end of that scene in
; every mode; native eligibility/projection and bitmap clipping still belong
; to the original marker routine.
waypoint_early:
        rts

waypoint_scene:
        move.w  4(sp),-(sp)
        bsr.w   waypoint_native_scene
        addq.l  #2,sp
        movem.l d0-d7/a0-a6,-(sp)
        bsr.w   waypoint_native_marker
        movem.l (sp)+,d0-d7/a0-a6
        rts
