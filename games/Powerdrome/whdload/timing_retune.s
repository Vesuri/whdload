; Drain historical pit opponents before the native departure speed mutation.
; The fixed cutoff is the retune event time, not time spent doing catch-up.
timing_pit_retune
 move.w sr,-(sp)
 movem.l d0-d7/a0-a6,-(sp)
 IFD VERIFY
 lea timing_retune_state(pc),a0
 move.w 60(sp),18(a0)
 ENDC
 move.w timing_pit_state+8(pc),d0
 beq.w .done
 move.w timing_pit_opponent_state+8(pc),d0
 beq.w .done
 bsr timing_clock
 bsr timing_pit_clock
 lea timing_retune_state(pc),a0
 move.l d0,12(a0)
 move.w #1,8(a0)
 addq.l #1,20(a0)
 move.l perf_game(pc),a1
 move.l $f96(a1),d1
 sub.l d0,d1
 lea timing_pit_opponent_state(pc),a0
 move.l d1,56(a0)
.batch
 bsr timing_pit_opponent_allocate
.step
 bsr timing_pit_opponent_test_due
 beq.s .batch_done
 bsr timing_pit_opponent_begin
 bsr timing_pit_opponent_direct
 move.w timing_retune_state+10(pc),d0
 bne.s .won
 bsr timing_pit_opponent_end
 bra.s .step
.batch_done
 move.l timing_pit_opponent_state+24(pc),d0
 cmp.l #TIMING_PERIOD,d0
 bhs.s .batch
 bra.s .finished
.won
 ; The winning native body returned early, not a completed world update.
 ; Keep its mutations and restore ownership, but retire all remaining work.
 bsr timing_pit_opponent_restore
 lea timing_pit_opponent_state(pc),a1
 lea timing_retune_state(pc),a0
 moveq #0,d0
 move.w 12(a1),d0
 add.l d0,32(a0)
 move.l 24(a1),d0
 add.l d0,36(a0)
 clr.w 12(a1)
 clr.l 24(a1)
.finished
 lea timing_retune_state(pc),a0
 clr.w 8(a0)
.done
 movem.l (sp)+,d0-d7/a0-a6
 move.w (sp)+,ccr
 IFD VERIFY
 bsr timing_retune_flags
 ENDC
 bsr timing_retune_native
 move.w #0,$f6(a6)
 bra.w timing_retune_continue

; Native D606 has only a TST/BEQ. Retain its decisions outside this boundary.
; During catch-up, record the first winning opponent instead of unwinding the
; pit helper stack. The flat pit-return dispatcher delivers the same result.
timing_retune_result_gate
 move.l a0,-(sp)
 lea timing_retune_state(pc),a0
 tst.w 8(a0)
 beq.s .native
 tst.w 10(a0)
 bne.s .deferred
 move.w #1,10(a0)
 move.w (a5),16(a0)
 addq.l #1,24(a0)
.deferred
 movea.l (sp)+,a0
 ; Native D7F0 is the opponent-body RTS; do not update later opponents.
 bra.w timing_pit_opponent_empty
.native
 movea.l (sp)+,a0
 tst.w $da(a6)
 beq.w timing_retune_native_result
 bra.w timing_retune_modal_result

; Entered by BRA after the native pit RTS, with no helper return address.
timing_retune_deliver_result
 lea timing_retune_state(pc),a0
 addq.l #1,40(a0)
 bsr timing_pit_is_initial
 bne.s .initial
 ; Rescue is inside CA3E: discard its original return, as D616 would.
 addq.l #4,sp
.initial
 move.w #0,$dc(a6)
 move.w timing_retune_state+16(pc),d0
 bra.w timing_retune_result

 IFD VERIFY
; Read guest flags directly: the 030 debugger SR can report stale lazy flags.
timing_retune_flags
 move.w sr,-(sp)
 move.l a0,-(sp)
 lea timing_retune_state(pc),a0
 move.w 4(sp),28(a0)
 movea.l (sp)+,a0
 move.w (sp)+,ccr
 rts
 ENDC

timing_retune_native dc.w $4ef9
 dc.l 0
timing_retune_continue dc.w $4ef9
 dc.l 0
timing_retune_modal_result dc.w $4ef9
 dc.l 0
timing_retune_native_result dc.w $4ef9
 dc.l 0
timing_retune_result dc.w $4ef9
 dc.l 0

timing_retune_state dc.b 'PDRETUNE'
 dc.w 0 ; boundary catch-up active
 dc.w 0 ; deferred race result pending
 dc.l 0 ; fixed unpaused cutoff
 dc.w 0 ; first winning opponent id
 dc.w 0 ; VERIFY guest input CCR
 dc.l 0 ; retune boundaries drained
 dc.l 0 ; deferred race results captured
 dc.w 0 ; VERIFY guest restored CCR
 dc.w 0
 dc.l 0 ; assigned opponent updates retired at first result (includes partial)
 dc.l 0 ; unassigned opponent time retired at first result
 dc.l 0 ; deferred results delivered from flat pit return

 IFNE TIMING_RETUNE_RESULT_TEST
; VERIFY-only branch-outcome injection. Native race-result decision, winner id,
; stack restoration and all remaining cleanup still execute unchanged.
timing_retune_test_finish
 move.l d0,-(sp)
 move.w timing_retune_state+8(pc),d0
 beq.s .move
 move.w timing_pit_initial(pc),d0
 IFEQ TIMING_RETUNE_RESULT_TEST-1
 beq.s .move
 ELSE
 bne.s .move
 ENDC
 movem.l (sp)+,d0
 moveq #-1,d0
 bra.w timing_retune_test_result
.move
 movem.l (sp)+,d0
 move.w $16(a5),d5
 tst.w $48(a5)
 bpl.w timing_retune_test_move
 asr.w #1,d5
 bra.w timing_retune_test_move

timing_retune_test_result dc.w $4ef9
 dc.l 0
timing_retune_test_move dc.w $4ef9
 dc.l 0
 ENDC
