; v1 CUSTOM2 bit 1: suppress unused graphics.library blitter queue IRQs.
; All original blitter waits, ownership and CPU/display barriers remain intact.
; Preserve the game entry's argc/argv registers and restore the original enable.
render_interrupt_option:
    movem.l d0/a0,-(sp)
    move.l render_options(pc),d0
    btst #1,d0
    beq.b .done
    lea render_saved_irq(pc),a0
    move.w $dff01c,d0
    and.w #$40,d0
    move.w d0,(a0)
    move.w #$40,$dff09a
.done
    movem.l (sp)+,d0/a0
    rts
render_interrupt_restore:
    move.l d0,-(sp)
    move.w render_saved_irq(pc),d0
    beq.b .done
    move.w #$8040,$dff09a
.done
    movem.l (sp)+,d0
    rts
render_saved_irq: dc.w 0
