; Race-only fine-path ownership of INTENA.BLIT. Native drawing is synchronous.
; Remember the entry bit even when initially clear; a later re-enable must not
; replace that saved state. Pause/modal/epoch teardown returns the exact bit.
; The immutable preset is the sole difference in equal-layout acceptance arms.
FF1FineBlitAcquire:
 move.w ccr,-(sp)
 tst.w FF1FineBlitControl(pc)
 beq.b .done
 tst.w FF1FineBlitActive(pc)
 beq.b .first
 ; Most draws already own the bit. A byte read of INTENAR's low byte
 ; tests BLIT without borrowing a data/address register.
 btst #6,$dff01d
 beq.b .done
.clear:
 move.w #$0040,$dff09a
.done:
 move.w (sp)+,ccr
 rts
.first:
 movem.l d0/a0,-(sp)
 move.w $dff01c,d0
 andi.w #$0040,d0
 lea (FF1FineBlitActive.l,pc),a0
 move.w #1,(a0)
 move.w d0,2(a0)
 tst.w d0
 movem.l (sp)+,d0/a0
 bne.b .clear
 bra.b .done

FF1FineBlitRestore:
 move.w ccr,-(sp)
 movem.l d0/a0,-(sp)
 lea (FF1FineBlitActive.l,pc),a0
 tst.w (a0)
 beq.b .done
 move.w 2(a0),d0
 beq.b .clear
 ori.w #$8000,d0
 bra.b .write
.clear:
 moveq #$40,d0
.write:
 move.w d0,$dff09a
 clr.l (a0)
.done:
 movem.l (sp)+,d0/a0
 move.w (sp)+,ccr
 rts
FF1FineBlitControl: dc.w 1
FF1FineBlitActive: dc.w 0
FF1FineBlitSaved: dc.w 0
