; VERIFY-only single simulation stall after 200 completed 20-ms world steps.
; Called inside timing_frame's saved CCR/d0-d2/a0-a1 envelope. IRQs continue;
; no simulation state, clocks, input queues or debt are rewritten by the fixture.
 IFNE TIMING_STALL_TEST
timing_stall_test
 lea timing_stall_state(pc),a1
 tst.l 8(a1)
 bne.s .done
 move.l timing_world20_state+16(pc),d0
 cmp.l #200,d0
 blo.s .done
 move.w timing_started(pc),d0
 beq.s .done
 move.w timing_pit_state+8(pc),d0
 bne.s .done
 move.l #1,8(a1)
 move.l perf_game(pc),a0
 move.l $48fe(a0),d0
 move.l d0,12(a1)
 move.l timing_world20_clock(pc),20(a1)
 move.l timing_ticks(pc),24(a1)
 ; PAL VBL is 20 ms: 250 ms releases at the first field at/after it (260 ms).
.wait
 move.l $48fe(a0),d1
 sub.l d0,d1
 cmp.l #(TIMING_STALL_TEST+19)/20,d1
 blo.s .wait
 move.l $48fe(a0),16(a1)
.done
 rts

timing_stall_state dc.b 'PDSTALL1'
 dc.l 0 ; injection count (one per process; restarting does not reinject)
 dc.l 0,0 ; start/end physical PAL field counters
 dc.l 0,0 ; logical world cursor and allocated tick count at entry
 dc.l TIMING_STALL_TEST ; requested milliseconds
 ENDC
