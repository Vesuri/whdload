; v1 CUSTOM2 bit 1: suppress unused graphics.library blitter queue IRQs and
; give the blitter bus priority (DMACON BLTPRI): the CPU only polls BBUSY while
; a shape blit runs, so its DMACONR reads no longer take the blitter's slots.
; Faster on both the 68000 and 68020+ machines measured.
; All original blitter waits, ownership and CPU/display barriers remain intact.
; Preserve the game entry's argc/argv registers and restore the original enables.
render_interrupt_option:
    movem.l d0/a0,-(sp)
    move.l render_options(pc),d0
    btst #1,d0
    beq.b .no_priority
    lea render_saved_priority(pc),a0
    move.w $dff002,(a0)
    and.w #$400,(a0)
    move.w #$8400,$dff096
.no_priority
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
    move.l render_options(pc),d0
    btst #1,d0
    beq.b .no_priority
    move.w render_saved_priority(pc),d0
    bne.b .no_priority
    move.w #$0400,$dff096
.no_priority
    move.w render_saved_irq(pc),d0
    beq.b .done
    move.w #$8040,$dff09a
.done
    movem.l (sp)+,d0
    rts
render_saved_irq: dc.w 0
render_saved_priority: dc.w 0
