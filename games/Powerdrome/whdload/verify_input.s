; Shared input-only fixtures for development and original-loader verification.
; Fixture submits an empty pilot name through the native text-entry path.
; Only the two six-byte JSRs are replaced; normal builds have neither patch.
pl_verify PL_START
 PL_PS $13772,key_ready
 PL_PS $1377c,key_return
 PL_END
key_ready moveq #-1,d0
 rts
key_return moveq #13,d0
 rts
; Whole six-byte input JSRs. Only installed for CUSTOM5=2.
; Key 3 selects the same menu item as the top-middle Practice button.
pl_practice PL_START
 PL_PS $12f6a,practice_ready
 PL_PS $130a4,practice_key
 PL_PS $13c50,pit_ready
 PL_PS $13cde,pit_key
 PL_END
practice_ready
 moveq #0,d0
 move.w practice_sent(pc),d0
 subq.w #1,d0
 rts
practice_key
 move.l a0,-(sp)
 lea practice_sent(pc),a0
 move.w #1,(a0)
 move.l (sp)+,a0
 moveq #$33,d0
 rts
pit_ready
 moveq #0,d0
 move.w pit_sent(pc),d0
 subq.w #1,d0
 rts
pit_key
 move.l a0,-(sp)
 lea pit_sent(pc),a0
 move.w #1,(a0)
 move.l (sp)+,a0
 moveq #32,d0
 rts
practice_sent dc.w 0
pit_sent dc.w 0
