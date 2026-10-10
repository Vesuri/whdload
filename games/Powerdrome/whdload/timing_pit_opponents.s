; One opponent timeline across ordinary flight and same-session rescue pits.
; Preserve the single native call frame, including nonlocal result exits.
timing_pit_opponents
 move.l a0,-(sp)
 move.l perf_game(pc),a0
 adda.l #$cedc,a0
 cmpa.l 4(sp),a0
 movea.l (sp)+,a0
 beq.s .flight
 move.l a0,-(sp)
 move.l perf_game(pc),a0
 adda.l #$e3c0,a0
 cmpa.l 4(sp),a0
 movea.l (sp)+,a0
 bne.w .native
 move.l d0,-(sp)
 move.w timing_pit_state+8(pc),d0
 movem.l (sp)+,d0
 beq.w .native
 bra.s .scheduled
.flight
 move.l d0,-(sp)
 move.w timing_world_state+8(pc),d0
 movem.l (sp)+,d0
 beq.w .native
.scheduled
 bsr timing_pit_opponent_allocate
 bsr timing_pit_opponent_test_due
 beq.s .no_update
 ; Replace the original return slot, not the native stack depth. Nonlocal
 ; exits therefore still see exactly the frame created by their native caller.
 move.l a0,-(sp)
 lea timing_pit_opponent_state(pc),a0
 move.l 4(sp),60(a0)
 lea .returned(pc),a0
 move.l a0,4(sp)
 movea.l (sp)+,a0
.next
 bsr timing_pit_opponent_begin
 bra.s .native
.returned
 bsr timing_pit_opponent_end
 bsr timing_pit_opponent_test_due
 beq.s .finished
 pea .returned(pc)
 bra.s .next
.finished
 move.l timing_pit_opponent_state+60(pc),-(sp)
.no_update
 rts
.native
 move.w $340(a6),d7
 bmi.w timing_pit_opponent_empty
 bra.w timing_pit_opponent_body

timing_pit_opponent_test_due
 move.l d0,-(sp)
 move.w timing_pit_opponent_due(pc),d0
 movem.l (sp)+,d0
 rts

timing_pit_opponent_initialize
 ; Entry changes clock source, not the existing deadline, phase or remainder.
 move.l a0,-(sp)
 lea timing_retune_state(pc),a0
 clr.l 8(a0)
 lea timing_pit_opponent_state(pc),a0
 addq.l #1,48(a0)
 movea.l (sp)+,a0
 rts

timing_opponent_initial_pit
 movem.l d0-d1/a0,-(sp)
 lea timing_pit_opponent_state(pc),a0
 clr.w 8(a0)
 tst.w $be(a6)
 bne.s .done
 move.w #1,8(a0)
 clr.w 10(a0)
 clr.w 12(a0)
 clr.w 64(a0)
 clr.w 66(a0)
 move.w $60(a6),d1
 addq.w #1,d1
 move.w d1,14(a0)
 move.w d1,132(a0)
 move.l timing_pit_state+24(pc),d0
 move.l d0,16(a0)
 add.l #TIMING_PERIOD,d0
 move.l d0,20(a0)
 move.l d0,52(a0)
 clr.l 24(a0)
 clr.l 28(a0)
 clr.l 32(a0)
.done
 movem.l (sp)+,d0-d1/a0
 rts

timing_opponent_flight_initialize
 movem.l d0/a0,-(sp)
 lea timing_pit_opponent_state(pc),a0
 tst.w 8(a0)
 bne.s .done
 tst.w $be(a6)
 bne.s .done
 move.w #1,8(a0)
 clr.w 10(a0)
 clr.w 12(a0)
 clr.w 64(a0)
 clr.w 66(a0)
 move.w timing_control_phase(pc),14(a0)
 move.w 14(a0),132(a0)
 move.l timing_world20_clock(pc),d0
 move.l d0,20(a0)
 move.l d0,52(a0)
 sub.l #TIMING_PERIOD,d0
 move.l d0,16(a0)
 clr.l 24(a0)
 clr.l 28(a0)
 clr.l 32(a0)
.done
 movem.l (sp)+,d0/a0
 rts

timing_pit_opponent_allocate
 move.w sr,-(sp)
 movem.l d0-d2/a0-a1,-(sp)
 bsr timing_clock
 bsr timing_pit_clock
 lea timing_pit_opponent_state(pc),a0
 move.w timing_retune_state+8(pc),d1
 bne.s .retune_clock
 tst.w 64(a0)
 bne.s .flush_clock
 ; Native epoch is measured against physical time even when scheduling a
 ; historical world deadline. Never subtract the delayed world cursor here.
 move.l perf_game(pc),a1
 move.l $f96(a1),d2
 sub.l d0,d2
 move.l d2,56(a0)
 move.w timing_world_state+8(pc),d1
 beq.s .clock_ready
 move.l timing_world20_clock(pc),d0
 bra.s .clock_ready
.retune_clock
 move.l timing_retune_state+12(pc),d0
 bra.s .clock_ready
.flush_clock
 ; Drain only through the captured native pit-return instant. Subsequent flight
 ; allocations account for elapsed drain/return time using this same ledger.
 move.l timing_pit_state+28(pc),d0
.clock_ready
 move.l d0,d1
 sub.l 16(a0),d1
 move.l d0,16(a0)
 add.l d1,24(a0)
 clr.w 12(a0)
.next
 cmp.l #TIMING_PERIOD,24(a0)
 blo.s .done
 cmp.w #32,12(a0)
 bhs.s .done
 sub.l #TIMING_PERIOD,24(a0)
 addq.w #1,12(a0)
 addq.l #1,28(a0)
 bra.s .next
.done
 movem.l (sp)+,d0-d2/a0-a1
 move.w (sp)+,ccr
 rts

timing_pit_opponent_begin
 move.w sr,-(sp)
 movem.l d0/a0,-(sp)
 lea timing_pit_opponent_state(pc),a0
 move.w #1,10(a0)
 move.l $5e(a6),40(a0)
 move.w $62(a6),44(a0)
 clr.w 66(a0)
 move.w timing_world_state+8(pc),d0
 bne.s .rng_ready
 move.w #1,66(a0)
 move.w timing_world_state+26(pc),$62(a6)
.rng_ready
 moveq #0,d0
 move.w 14(a0),d0
 move.l d0,$5e(a6)
 move.w #TIMING_PERIOD,$21c(a6)
 move.l 20(a0),d0
 add.l 56(a0),d0
 move.l d0,36(a0)
 movem.l (sp)+,d0/a0
 move.w (sp)+,ccr
 rts

timing_pit_opponent_end
 move.w sr,-(sp)
 move.l a0,-(sp)
 bsr timing_pit_opponent_restore
 lea timing_pit_opponent_state(pc),a0
 add.l #TIMING_PERIOD,20(a0)
 addq.w #1,14(a0)
 addq.l #1,32(a0)
 subq.w #1,12(a0)
 movem.l (sp)+,a0
 move.w (sp)+,ccr
 rts

; Also used by the native nonlocal result/session exits.
timing_pit_opponent_restore
 move.w sr,-(sp)
 movem.l a0-a1,-(sp)
 lea timing_pit_opponent_state(pc),a0
 tst.w 10(a0)
 beq.s .done
 tst.w 66(a0)
 beq.s .counter_only
 lea timing_world_state(pc),a1
 move.w $62(a6),26(a1)
 move.w 44(a0),$62(a6)
.counter_only
 clr.w 66(a0)
 move.l 40(a0),$5e(a6)
 clr.w 10(a0)
.done
 movem.l (sp)+,a0-a1
 move.w (sp)+,ccr
 rts

; MOVE.L wrappers reproduce NZVC and preserve X and every other register.
timing_pit_clock_d7
 move.l a0,-(sp)
 lea timing_pit_opponent_state(pc),a0
 tst.w 10(a0)
 beq.s .native
 move.l 36(a0),d7
 bra.s .done
.native
 move.l perf_game(pc),a0
 move.l $f96(a0),d7
.done
 movem.l (sp)+,a0
 rts

timing_pit_clock_d0
 move.l a0,-(sp)
 lea timing_pit_opponent_state(pc),a0
 tst.w 10(a0)
 beq.s .native
 move.l 36(a0),d0
 bra.s .done
.native
 move.l perf_game(pc),a0
 move.l $f96(a0),d0
.done
 movem.l (sp)+,a0
 rts

; Save the native pit return registers in private storage, not an extra stack
; frame: an opponent completion may unwind directly to the native result path.
timing_pit_opponent_save_return
 move.w sr,-(sp)
 move.l a0,-(sp)
 lea timing_pit_opponent_saved(pc),a0
 movem.l d0-d7/a1-a6,(a0)
 move.l (sp),56(a0)
 move.w 4(sp),60(a0)
 lea timing_pit_opponent_state(pc),a0
 move.w #1,64(a0)
 move.l perf_game(pc),a0
 move.l $f96(a0),d0
 sub.l timing_pit_state+28(pc),d0
 lea timing_pit_opponent_state(pc),a0
 move.l d0,56(a0)
 movea.l (sp)+,a0
 addq.l #2,sp
 rts

timing_pit_opponent_restore_return
 lea timing_pit_opponent_state(pc),a0
 clr.w 64(a0)
 lea timing_pit_opponent_saved(pc),a0
 move.w 60(a0),ccr
 movem.l (a0),d0-d7/a1-a6
 movea.l 56(a0),a0
 rts

timing_pit_opponent_direct dc.w $4ef9
 dc.l 0
timing_pit_opponent_body dc.w $4ef9
 dc.l 0
timing_pit_opponent_empty dc.w $4ef9
 dc.l 0

timing_pit_opponent_state dc.b 'PDPOPP01'
 dc.w 0 ; initialized
 dc.w 0 ; native opponent body owns counter/RNG/clock view
timing_pit_opponent_due dc.w 0
 dc.w 0 ; logical opponent counter phase
 dc.l 0 ; last sampled unpaused VBL time
 dc.l 0 ; next logical opponent deadline
 dc.l 0 ; retained unassigned time debt
 dc.l 0 ; assigned updates (cumulative)
 dc.l 0 ; completed updates (cumulative)
 dc.l 0 ; native-epoch clock for this logical update
 dc.l 0 ; saved presentation counter
 dc.w 0 ; saved presentation RNG
 dc.w 0
 dc.l 0 ; visits initialized
 dc.l 0 ; first ordinary-flight opponent deadline
 dc.l 0 ; native clock minus unpaused VBL clock at allocation
 dc.l 0 ; original native return address during a scheduled opponent call
timing_pit_opponent_flushing dc.w 0
 dc.w 0 ; owns a temporary presentation-to-world RNG swap
timing_pit_opponent_saved ds.b 64
 dc.w 0 ; initial opponent counter phase for this ordinary session
 dc.w 0
