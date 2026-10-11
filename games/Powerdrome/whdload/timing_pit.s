; WORLD20 initial/rescue pit boundaries. Native pit call depth is retained.
timing_initial_pit_call
 bsr timing_initial_pit_enter
 bra.s timing_pit_run
timing_pit_call
 bsr timing_pit_enter
timing_pit_run
 bsr timing_pit_native
 bsr timing_pit_leave
 move.l d0,-(sp)
 move.w timing_retune_state+10(pc),d0
 movem.l (sp)+,d0
 bne.w timing_retune_deliver_result
 tst.w d0
 bne.s .continue
 bsr timing_pit_is_initial
 bne.s .continue
 ; Flat dispatcher: no extra helper frame survives a native opponent call.
 bsr timing_pit_opponent_save_return
.flush_batch
 bsr timing_pit_opponent_allocate
.flush_step
 bsr timing_pit_opponent_test_due
 beq.s .batch_done
 bsr timing_pit_opponent_begin
 bsr timing_pit_opponent_direct
 bsr timing_pit_opponent_end
 bra.s .flush_step
.batch_done
 move.l d0,-(sp)
 move.l timing_pit_opponent_state+24(pc),d0
 cmp.l #TIMING_PERIOD,d0
 movem.l (sp)+,d0
 bhs.s .flush_batch
 bsr timing_pit_opponent_restore_return
.continue
 bsr timing_pit_is_initial
 bne.s .initial_return
 move.w #0,$dc(a6)
 bra.w timing_pit_continue
.initial_return
 ; No world-call frame exists yet. Let the first world allocation drain the
 ; departure tail, where native opponent nonlocal exits have their proper stack.
 move.w #0,$dc(a6)
 bra.w timing_initial_pit_continue

timing_initial_pit_enter
 move.w sr,-(sp)
 movem.l d0-d1/a0-a1,-(sp)
 bsr timing_player_lap_invalidate
 bsr timing_world_restore
 lea timing_state(pc),a1
 clr.w timing_started-timing_state(a1)
 bsr timing_world_input_disable
 bsr timing_session_clear_work
 lea timing_pit_state(pc),a0
 move.w #1,8(a0)
 clr.w 10(a0)
 clr.w 60(a0)
 move.w #1,62(a0)
 addq.l #1,12(a0)
 bsr timing_pit_clock
 move.l d0,24(a0)
 ; A new race owns a fresh world stream before opponents first move in its pit.
 lea timing_world_state(pc),a1
 IFEQ TIMING_WORLD_SEED+1
 move.w $62(a6),d1
 ELSE
 move.w #TIMING_WORLD_SEED,d1
 ENDC
 move.w d1,26(a1)
 move.w d1,28(a1)
 bsr timing_opponent_initial_pit
 bsr timing_pit_opponent_initialize
 movem.l (sp)+,d0-d1/a0-a1
 move.w (sp)+,ccr
 rts

timing_pit_enter
 move.w sr,-(sp)
 movem.l d0-d1/a0-a1,-(sp)
 bsr timing_world_restore
 lea timing_state(pc),a1
 clr.w timing_started-timing_state(a1)
 lea timing_pit_state(pc),a0
 move.w #1,8(a0)
 clr.w 10(a0)
 clr.w 62(a0)
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
 bsr timing_pit_opponent_initialize
 bsr timing_session_clear_work
 movem.l (sp)+,d0-d1/a0-a1
 move.w (sp)+,ccr
 rts

timing_pit_leave
 move.w sr,-(sp)
 movem.l d0-d1/a0-a1,-(sp)
 IFNE TIMING_PIT_SYNC_TEST
 bsr timing_sync_return
 ENDC
 lea timing_pit_state(pc),a0
 addq.l #1,16(a0)
 bsr timing_pit_finish
 tst.w 62(a0)
 bne.s .initial
 move.w #1,10(a0)
.initial
 movem.l (sp)+,d0-d1/a0-a1
 move.w (sp)+,ccr
 rts

timing_pit_abort
 move.w sr,-(sp)
 movem.l d0-d1/a0-a1,-(sp)
 bsr timing_pit_opponent_restore
 lea timing_retune_state(pc),a0
 clr.l 8(a0)
 lea timing_pit_opponent_flushing(pc),a0
 clr.w (a0)
 lea timing_pit_state(pc),a0
 tst.w 8(a0)
 beq.s .done
 addq.l #1,20(a0)
 bsr timing_pit_finish
.done
 clr.w 10(a0)
 clr.w 62(a0)
 movem.l (sp)+,d0-d1/a0-a1
 move.w (sp)+,ccr
 rts

timing_pit_finish
 bsr timing_pit_clock
 move.l d0,28(a0)
 sub.l 24(a0),d0
 add.l d0,32(a0)
 clr.w 8(a0)
 tst.w 62(a0)
 bne.s .initial
 move.w #1,60(a0)
.initial
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

timing_pit_is_initial
 move.l d0,-(sp)
 move.w timing_pit_initial(pc),d0
 movem.l (sp)+,d0
 rts

timing_initial_pit_continue dc.w $4ef9
 dc.l 0
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
timing_pit_initial dc.w 0 ; adopt initial-pit opponent/RNG timeline at first flight

 INCLUDE timing_pit_opponents.s
