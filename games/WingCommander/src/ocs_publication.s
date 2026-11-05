; OCS adapter for the shared pending/drawing/displayed ownership protocol.
; Completion publishes immutable request data last; VBL releases the old front
; only after selecting the completed list. Task waits never execute in QBlit.
; OCS copinit jumps at line 12; verified game lists enable planes at >=72.
ocs_publish_queue:
        movem.l d0/a0-a1,-(sp)
        lea     OCS_DISPLAY_STATE,a0
        moveq   #0,d0
        move.w  32(a0),d0
        lea     ocs_pending_index(pc),a1
        move.w  d0,(a1)
        lsl.w   #2,d0
        move.l  8(a0,d0.w),d0
        lea     ocs_pending_plane(pc),a1
        move.l  d0,(a1)
        lea     ocs_pending_a4(pc),a1
        move.l  ocs_game_a4(pc),(a1)
        movea.l (a1),a0
        lea     ocs_target_field(pc),a1
        move.l  -$800(a0),d0
        addq.l  #1,d0
        move.l  d0,(a1)
        lea     ocs_pending(pc),a1
        move.w  #1,(a1)
        movem.l (sp)+,d0/a0-a1
        rts

; Native VBL has already advanced its clock and countdown. Preserve its ABI.
ocs_publish_irq:
        bsr.w   ocs_publish_vblank
        jsr     OCS_VBL_CALLBACK
        movem.l (sp)+,d1-d7/a1-a6
        jmp     OCS_VBL_RETURN

ocs_publish_vblank:
        movem.l d0-d7/a0-a6,-(sp)
        lea     ocs_pending(pc),a0
        tst.w   (a0)
        beq.w   .done
        movea.l ocs_pending_a4(pc),a4
        move.l  -$800(a4),d0
        sub.l   ocs_target_field(pc),d0
        bmi.w   .done
        tst.w   -$850(a4)       ; native completion nesting lock
        bpl.w   .done
        tst.w   OCS_COPPER_LOCK
        bpl.w   .done
.early:
        bsr.w   ocs_publish_beam
        cmpi.w  #16,d0
        blo.s   .early
        cmpi.w  #32,d0
        bhi.s   .late
        move.w  ocs_pending_index(pc),-(sp)
        jsr     OCS_PUBLISH_INDEX
        addq.l  #2,sp
        bsr.w   ocs_publish_beam
        cmpi.w  #40,d0
        bhi.s   .late
        move.w  d0,$dff08a      ; restart only inside the audited OCS blank
        lea     ocs_front(pc),a0
        move.l  ocs_pending_plane(pc),(a0)
        lea     ocs_display_field(pc),a0
        move.l  -$800(a4),(a0)
        lea     ocs_pending(pc),a0
        clr.w   (a0)            ; old front is reusable only now
        bra.s   .done
.late:
        lea     ocs_publish_late(pc),a0
        addq.l  #1,(a0)
.done:
        movem.l (sp)+,d0-d7/a0-a6
        rts

ocs_publish_beam:
        move.l  $dff004,d0
        move.l  $dff004,d1
        lsr.l   #8,d0
        lsr.l   #8,d1
        andi.w  #$1ff,d0
        andi.w  #$1ff,d1
        cmp.w   d0,d1
        bne.s   ocs_publish_beam
        rts

ocs_publish_wait:
        move.l  a0,-(sp)
        lea     ocs_pending(pc),a0
.wait:
        tst.w   (a0)
        bne.s   .wait
        movea.l (sp)+,a0
        rts

ocs_publish_drain:
        movem.l d0-d7/a0-a6,-(sp)
        jsr     OCS_WAIT
        bsr.w   ocs_publish_wait
        movem.l (sp)+,d0-d7/a0-a6
        rts

; Conversion rotation cannot claim the former front before publication.
ocs_publish_rotate:
        bsr.w   ocs_publish_wait
        lea     OCS_DISPLAY_STATE,a0
        move.w  30(a0),d0
        jmp     OCS_ROTATE_BODY

; Direct planar writes share the same destination ownership as conversion.
ocs_publish_clear:
        bsr.w   ocs_publish_drain
        movem.l d2-d5/a2-a3/a6,-(sp)
        lea     OCS_DISPLAY_STATE,a6
        jmp     OCS_CLEAR_BODY
ocs_publish_pixel:
        bsr.w   ocs_publish_drain
        move.l  d2,-(sp)
        lea     OCS_DISPLAY_STATE,a0
        jmp     OCS_PIXEL_BODY

; Close drains before native View/Copper destruction; the VBL is still active.
ocs_publish_close:
        bsr.w   ocs_publish_drain
        move.l  a0,-(sp)
        lea     ocs_front(pc),a0
        clr.l   (a0)
        movea.l (sp)+,a0
        move.l  a2,-(sp)
        lea     OCS_DISPLAY_STATE,a2
        jmp     OCS_CLOSE_BODY

        even
ocs_game_a4: dc.l 0
ocs_pending: dc.w 0
ocs_pending_index: dc.w 0
ocs_pending_plane: dc.l 0
ocs_pending_a4: dc.l 0
ocs_target_field: dc.l 0
ocs_display_field: dc.l 0
ocs_front: dc.l 0
ocs_publish_late: dc.l 0
