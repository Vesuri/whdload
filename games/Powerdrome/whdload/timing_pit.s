; WORLD20 rescue boundary. Physical clocks and native repairs continue in the pit.
; One native pit call frame is retained, matching the displaced BSR exactly.
timing_pit_call
 bsr timing_pit_enter
 bsr timing_pit_native
 bsr timing_pit_leave
 move.w #0,$dc(a6)
 bra.w timing_pit_continue

timing_pit_enter
 move.w sr,-(sp)
 movem.l d0-d1/a0-a1,-(sp)
 bsr timing_world_restore
 lea timing_state(pc),a1
 clr.w timing_started-timing_state(a1)
 lea timing_pit_state(pc),a0
 move.w #1,8(a0)
 clr.w 10(a0)
 addq.l #1,12(a0)
 moveq #0,d0
 move.w timing_orientation_left-timing_state(a1),d0
 add.l d0,36(a0)
 move.l timing_phase-timing_state(a1),d0
 add.l d0,40(a0)
 move.w timing_input_write-timing_state(a1),d0
 sub.w timing_input_read-timing_state(a1),d0
 and.l #TIMING_INPUT_MASK,d0
 lsr.l #4,d0
 add.l d0,44(a0)
 bsr timing_world_input_disable
 moveq #0,d0
 move.w timing_key_write(pc),d0
 sub.w timing_key_read(pc),d0
 and.w #TIMING_KEY_MASK,d0
 lsr.w #3,d0
 add.l d0,48(a0)
 moveq #0,d0
 move.w timing_engine_count-timing_state(a1),d0
 sub.w timing_engine_read-timing_state(a1),d0
 add.l d0,52(a0)
 bsr timing_pit_clock
 move.l d0,24(a0)
 bsr timing_session_clear_work
 movem.l (sp)+,d0-d1/a0-a1
 move.w (sp)+,ccr
 rts

timing_pit_leave
 move.w sr,-(sp)
 movem.l d0-d1/a0-a1,-(sp)
 lea timing_pit_state(pc),a0
 addq.l #1,16(a0)
 bsr timing_pit_finish
 move.w #1,10(a0)
 movem.l (sp)+,d0-d1/a0-a1
 move.w (sp)+,ccr
 rts

timing_pit_abort
 move.w sr,-(sp)
 movem.l d0-d1/a0-a1,-(sp)
 lea timing_pit_state(pc),a0
 tst.w 8(a0)
 beq.s .done
 addq.l #1,20(a0)
 bsr timing_pit_finish
.done
 clr.w 10(a0)
 movem.l (sp)+,d0-d1/a0-a1
 move.w (sp)+,ccr
 rts

timing_pit_finish
 bsr timing_pit_clock
 move.l d0,28(a0)
 sub.l 24(a0),d0
 add.l d0,32(a0)
 clr.w 8(a0)
 move.w #1,60(a0)
 rts

timing_pit_clock
 move.l perf_game(pc),a1
 move.l $48fe(a1),d0
 sub.l timing_input_paused_fields(pc),d0
 lsl.l #2,d0
 ; Queue-clear helper expects a1 to address timing_state.
 lea timing_state(pc),a1
 rts

timing_pit_is_retiring
 move.l d0,-(sp)
 move.w timing_pit_retiring(pc),d0
 movem.l (sp)+,d0
 rts

timing_pit_native dc.w $4ef9
 dc.l 0
timing_pit_continue dc.w $4ef9
 dc.l 0

timing_pit_state dc.b 'PDPIT001'
 dc.w 0 ; active native pit sequence
timing_pit_retiring dc.w 0 ; returning through the interrupted world tail
 dc.l 0 ; entries
 dc.l 0 ; normal returns
 dc.l 0 ; nonlocal exits
 dc.l 0 ; entry unpaused VBL time
 dc.l 0 ; exit unpaused VBL time
 dc.l 0 ; cumulative modal time units
 dc.l 0 ; assigned interrupted/unstarted world steps discarded
 dc.l 0 ; allocator phase/debt discarded (clock units)
 dc.l 0 ; pending input events discarded
 dc.l 0 ; pending centering keys discarded
 dc.l 0 ; pending engine presentation discarded
 dc.l 0 ; interrupted world tails retired, not completed ticks
timing_pit_rebase dc.w 0 ; preserve world/heat streams during next initialization
 dc.w 0
