; VERIFY-only causal experiment: equal initial-pit retune/return event times.
; This deliberately waits on the fast machine and is NEVER normal-game policy.
; No opponent/player record, seed, counter or logical cursor is rewritten.
 IFNE TIMING_PIT_SYNC_TEST
timing_sync_retune
 move.w sr,-(sp)
 movem.l d0-d2/a0-a1,-(sp)
 move.w timing_pit_initial(pc),d0
 beq.s .done
 lea timing_sync_state+8(pc),a0
 move.l #3600,d2 ; 18 seconds from pit entry
 bsr timing_sync_wait
 lea timing_sync_state(pc),a0
 addq.l #1,24(a0)
.done
 movem.l (sp)+,d0-d2/a0-a1
 move.w (sp)+,ccr
 rts

timing_sync_return
 move.w sr,-(sp)
 movem.l d0-d2/a0-a1,-(sp)
 move.w timing_pit_initial(pc),d0
 beq.s .done
 lea timing_sync_state+16(pc),a0
 move.l #4800,d2 ; 24 seconds from pit entry
 bsr timing_sync_wait
 lea timing_sync_state(pc),a0
 addq.l #1,28(a0)
.done
 movem.l (sp)+,d0-d2/a0-a1
 move.w (sp)+,ccr
 rts

timing_sync_wait
 bsr timing_pit_clock
 sub.l timing_pit_state+24(pc),d0
 move.l d0,(a0) ; actual arrival relative to pit entry
.wait
 bsr timing_clock
 bsr timing_pit_clock
 sub.l timing_pit_state+24(pc),d0
 cmp.l d2,d0
 blo.s .wait
 move.l d0,4(a0) ; actual release; late arrivals remain visible
 rts

timing_sync_state dc.b 'PDSYNC01'
 dc.l 0,0 ; retune arrival/release
 dc.l 0,0 ; return arrival/release
 dc.l 0,0 ; retune/return visits
 ENDC
