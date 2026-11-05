; Opt-in C4 race-only ownership of the blitter-finished interrupt enable.
; Native drawing uses synchronous blits; pause restores the entry state before
; entering modal code. Exit, unload and fault also release ownership.
; CPU-only state belongs to the existing public owner. No DMA addresses change.
FF1C4BlitAcquire:
 movem.l d0/a0,-(sp)
 move.w C4BlitEnabled(pc),d0
 beq.b .done
 lea C4BlitOwned(pc),a0
 tst.w (a0)
 bne.b .done
 move.w $dff01c,d0
 andi.w #$0040,d0
 beq.b .done
 move.w d0,(a0)
 move.w d0,$dff09a
.done:
 movem.l (sp)+,d0/a0
 rts
FF1C4BlitRestore:
 movem.l d0/a0,-(sp)
 lea C4BlitOwned(pc),a0
 move.w (a0),d0
 beq.b .done
 clr.w (a0)
 ori.w #$8000,d0
 move.w d0,$dff09a
.done:
 movem.l (sp)+,d0/a0
 rts
C4BlitEnabled: dc.w 0
C4BlitOwned: dc.w 0
