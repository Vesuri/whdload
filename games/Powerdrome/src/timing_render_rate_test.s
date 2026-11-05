; VERIFY-only presentation pacing; the normal allocator services all elapsed work.
; Called with CCR/d0-d2/a0-a1 saved by timing_frame. No added SR instruction.
; Starts after 200 world updates. Late rendering rebases presentation deadlines
; only: no simulation/input clock, state or debt is changed by this fixture.
 IFNE TIMING_RENDER_HZ_TEST
timing_render_rate_test
 lea timing_render_rate_state(pc),a1
 move.l timing_world20_state+16(pc),d0
 cmp.l #200,d0
 blo.w .done
 move.w timing_started(pc),d0
 beq.w .done
 move.w timing_pit_state+8(pc),d0
 bne.w .done
 move.l perf_game(pc),a0
 move.l $48fe(a0),d0
 move.l d0,24(a1) ; actual arrival field
 tst.l 8(a1)
 bne.s .next
 move.l #1,8(a1)
 move.l d0,16(a1) ; pacing origin
 move.l d0,28(a1) ; first release is immediate
 move.l #TIMING_RENDER_HZ_TEST-1,36(a1)
 bra.s .release
.next
 move.l #1,56(a1) ; next deadline may still be waiting at capture endpoint
 ; Ceil(n*50/hz) differences without division: 15 Hz emits 4,3,3 fields.
 move.l 36(a1),d1
 add.l #50,d1
 moveq #0,d2
.divide
 cmp.l #TIMING_RENDER_HZ_TEST,d1
 blo.s .period
 sub.l #TIMING_RENDER_HZ_TEST,d1
 addq.l #1,d2
 bra.s .divide
.period
 move.l d1,36(a1)
 add.l 32(a1),d2 ; previous actual release + rational period
 move.l d2,28(a1)
.wait
 move.l $48fe(a0),d0
 cmp.l d2,d0
 blo.s .wait
 move.l d0,d1
 sub.l 24(a1),d1
 add.l d1,40(a1) ; total physical fields held by pacing
 move.l d0,d1
 sub.l d2,d1
 beq.s .release
 add.l d1,52(a1) ; cumulative lateness for independent elapsed-time identity
 addq.l #1,44(a1) ; arrival/release late; never conceal missed deadlines
 cmp.l 48(a1),d1
 bls.s .release
 move.l d1,48(a1)
.release
 clr.l 56(a1)
 move.l d0,32(a1)
 addq.l #1,20(a1)
.done
 rts

timing_render_rate_state dc.b 'PDRATE01'
 dc.l 0 ; initialized
 dc.l TIMING_RENDER_HZ_TEST
 dc.l 0 ; first release/origin, physical fields
 dc.l 0 ; release count
 dc.l 0 ; most recent arrival
 dc.l 0 ; most recent deadline
 dc.l 0 ; most recent release
 dc.l 0 ; rational remainder, 0..hz-1
 dc.l 0 ; total physical fields spent waiting
 dc.l 0 ; late release count
 dc.l 0 ; maximum lateness, fields
 dc.l 0 ; cumulative lateness, fields
 dc.l 0 ; deadline pending at a paused capture endpoint
 ENDC
