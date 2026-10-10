; Development-only engine state cadence. Presentation calls are queued in order.
; Main context owns both producer and consumer; no engine mutation runs in VBL.
timing_engine_tick
 move.w sr,-(sp)
 movem.l d0-d7/a0-a6,-(sp)
 lea timing_engine_state(pc),a0
 move.w #1,timing_engine_active-timing_engine_state(a0)
 addq.l #1,timing_engine_ticks-timing_engine_state(a0)
 pea .returned(pc)
 btst #1,$139(a6)
 bra.w timing_engine_native_entry
.returned
 lea timing_engine_state(pc),a0
 clr.w timing_engine_active-timing_engine_state(a0)
 movem.l (sp)+,d0-d7/a0-a6
 move.w (sp)+,ccr
 rts

timing_engine_cooling
 moveq #0,d0
 move.w timing_control_phase(pc),d0
 and.w #3,d0
 bne.w timing_engine_native_cooling_branch
 move.l a0,-(sp)
 lea timing_engine_state(pc),a0
 addq.l #1,timing_engine_coolings-timing_engine_state(a0)
 movea.l (sp)+,a0
 tst.w d0
 bra.w timing_engine_native_cooling_branch

timing_engine_footer
 move.l d0,-(sp)
 move.w timing_engine_active(pc),d0
 movem.l (sp)+,d0
 beq.s .render
 rts
.render
 move.l $5e(a6),d0
 and.w #7,d0
 bra.w timing_engine_native_footer

; Each call site also replays the whole instruction displaced after its BSR.
timing_engine_flash_left
 move.l d0,-(sp)
 moveq #1,d0
 bsr timing_engine_enqueue
 move.l (sp)+,d0
 ori.w #2,$138(a6)
 bra.w timing_engine_after_flash_left
timing_engine_flash_right
 move.l d0,-(sp)
 moveq #1,d0
 bsr timing_engine_enqueue
 move.l (sp)+,d0
 ori.w #1,$138(a6)
 bra.w timing_engine_after_flash_right

timing_engine_hud_left
 move.l d0,-(sp)
 moveq #2,d0
 bsr timing_engine_enqueue
 move.l (sp)+,d0
 move.l perf_game(pc),a3
 lea $3b45(a3),a3
 bra.w timing_engine_after_hud_left
timing_engine_hud_right
 move.l d0,-(sp)
 moveq #2,d0
 bsr timing_engine_enqueue
 move.l (sp)+,d0
 move.l perf_game(pc),a3
 lea $3b60(a3),a3
 bra.w timing_engine_after_hud_right

timing_engine_message_left
 move.l d0,-(sp)
 moveq #3,d0
 bsr timing_engine_enqueue
 move.l (sp)+,d0
 move.w $454(a6),d0
 bra.w timing_engine_after_message_left
timing_engine_message_right
 move.l d0,-(sp)
 moveq #3,d0
 bsr timing_engine_enqueue
 move.l (sp)+,d0
 move.w $454(a6),d0
 bra.w timing_engine_after_message_right

timing_engine_enqueue
 move.w sr,-(sp)
 movem.l d0-d2/a0-a1,-(sp)
 lea timing_engine_state(pc),a0
 moveq #0,d1
 move.w timing_engine_count-timing_engine_state(a0),d1
 cmp.w #16,d1
 bhs.s .full
 mulu.w #12,d1
 lea timing_engine_events(pc),a1
 adda.l d1,a1
 move.w d0,(a1)
 clr.w 2(a1)
 move.l timing_input_clock(pc),4(a1)
 move.l a3,8(a1)
 addq.w #1,timing_engine_count-timing_engine_state(a0)
 addq.l #1,timing_engine_produced-timing_engine_state(a0)
 bra.s .done
.full
 addq.l #1,timing_engine_overflow-timing_engine_state(a0)
.done
 movem.l (sp)+,d0-d2/a0-a1
 move.w (sp)+,ccr
 rts

timing_engine_present
 move.w sr,-(sp)
 movem.l d0-d7/a0-a6,-(sp)
 lea timing_engine_state(pc),a0
 tst.w timing_engine_presenting-timing_engine_state(a0)
 bne.s .done
 move.w #1,timing_engine_presenting-timing_engine_state(a0)
.next
 lea timing_engine_state(pc),a0
 move.w timing_engine_read-timing_engine_state(a0),d0
 cmp.w timing_engine_count-timing_engine_state(a0),d0
 bhs.s .finished
 addq.w #1,timing_engine_read-timing_engine_state(a0)
 addq.l #1,timing_engine_consumed-timing_engine_state(a0)
 mulu.w #12,d0
 lea timing_engine_events(pc),a1
 adda.l d0,a1
 move.w (a1),d0
 move.w d0,timing_engine_presenting-timing_engine_state(a0)
 cmp.w #1,d0
 beq.s .flash
 cmp.w #2,d0
 beq.s .hud
 move.l 8(a1),a3
 bsr timing_engine_native_message
 bra.s .next
.flash
 bsr timing_engine_native_flash
 bra.s .next
.hud
 bsr timing_engine_native_hud
 bra.s .next
.finished
 clr.w timing_engine_count-timing_engine_state(a0)
 clr.w timing_engine_read-timing_engine_state(a0)
 clr.w timing_engine_presenting-timing_engine_state(a0)
.done
 movem.l (sp)+,d0-d7/a0-a6
 move.w (sp)+,ccr
 bra.w timing_engine_footer

timing_engine_native_entry dc.w $4ef9
 dc.l 0
timing_engine_native_cooling_branch dc.w $4ef9
 dc.l 0
timing_engine_native_footer dc.w $4ef9
 dc.l 0
timing_engine_after_flash_left dc.w $4ef9
 dc.l 0
timing_engine_after_flash_right dc.w $4ef9
 dc.l 0
timing_engine_after_hud_left dc.w $4ef9
 dc.l 0
timing_engine_after_hud_right dc.w $4ef9
 dc.l 0
timing_engine_after_message_left dc.w $4ef9
 dc.l 0
timing_engine_after_message_right dc.w $4ef9
 dc.l 0
timing_engine_native_flash dc.w $4ef9
 dc.l 0
timing_engine_native_hud dc.w $4ef9
 dc.l 0
timing_engine_native_message dc.w $4ef9
 dc.l 0

timing_engine_state dc.b 'PDENGN01'
timing_engine_active dc.w 0
timing_engine_presenting dc.w 0
timing_engine_count dc.w 0
timing_engine_read dc.w 0
timing_engine_ticks dc.l 0
timing_engine_coolings dc.l 0
timing_engine_produced dc.l 0
timing_engine_consumed dc.l 0
timing_engine_overflow dc.l 0
timing_engine_events ds.b 192
