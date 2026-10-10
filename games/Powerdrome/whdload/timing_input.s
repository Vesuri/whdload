; Timestamped button/modifier changes. Producer: PAL VBL. Consumer: logical controls.
; 256 slots, one empty slot. A full queue preserves unread events and records overflow;
; an overflow invalidates validation and requires a mode/capacity policy before release.
TIMING_INPUT_MASK = 2040

timing_input_initialize
 ; timing_frame has saved d0-d2/a0-a1. Initially VBL capture is still inactive.
 clr.l timing_input_read-timing_state(a1)
 move.l timing_last-timing_state(a1),timing_input_clock-timing_state(a1)
 move.l perf_game(pc),a0
 move.w $432(a6),d0
 swap d0
 move.w $f9e(a0),d0
 move.l d0,timing_input_current-timing_state(a1)
 move.l d0,timing_input_last-timing_state(a1)
 rts

timing_input_sample
 ; d0 contains sampled buttons; preserve it for the separate brake accountant.
 movem.l d0-d3/a0,-(sp)
 move.l perf_game(pc),a0
 swap d0
 move.w $f9e(a0),d0
 cmp.l timing_input_last-timing_state(a1),d0
 beq.s .done
 move.l $48fe(a0),d1
 sub.l timing_input_paused_fields-timing_state(a1),d1
 lsl.l #2,d1
 move.w timing_input_write-timing_state(a1),d2
 move.w d2,d3
 addq.w #8,d3
 and.w #TIMING_INPUT_MASK,d3
 cmp.w timing_input_read-timing_state(a1),d3
 beq.s .full
 lea timing_input_queue(pc),a0
 adda.w d2,a0
 move.l d1,(a0)
 move.l d0,4(a0)
 move.l d0,timing_input_last-timing_state(a1)
 addq.l #1,timing_input_produced-timing_state(a1)
 ; Publish only after the complete event is stored.
 move.w d3,timing_input_write-timing_state(a1)
 bra.s .done
.full
 addq.l #1,timing_input_overflow-timing_state(a1)
.done
 movem.l (sp)+,d0-d3/a0
 rts

timing_input_for_control
 movem.l d0-d2/a0-a1,-(sp)
 lea timing_state(pc),a1
.next
 move.w timing_input_read-timing_state(a1),d0
 cmp.w timing_input_write-timing_state(a1),d0
 beq.s .done
 lea timing_input_queue(pc),a0
 adda.w d0,a0
 move.l timing_input_clock-timing_state(a1),d1
 sub.l (a0),d1
 bmi.s .done
 move.l 4(a0),timing_input_current-timing_state(a1)
 addq.l #1,timing_input_consumed-timing_state(a1)
 addq.w #8,d0
 and.w #TIMING_INPUT_MASK,d0
 move.w d0,timing_input_read-timing_state(a1)
 bra.s .next
.done
 movem.l (sp)+,d0-d2/a0-a1
 rts

timing_input_buttons
 move.w timing_input_current(pc),d7
 btst #0,d7
 bra.w timing_input_after_buttons
timing_input_modifiers
 move.w timing_input_current+2(pc),d0
 bra.w timing_input_after_modifiers

timing_input_after_buttons dc.w $4ef9
 dc.l 0
timing_input_after_modifiers dc.w $4ef9
 dc.l 0

timing_input_tag dc.b 'PDINPT01'
timing_input_read dc.w 0
timing_input_write dc.w 0
timing_input_clock dc.l 0
timing_input_current dc.l 0
timing_input_last dc.l 0
timing_input_produced dc.l 0
timing_input_consumed dc.l 0
timing_input_overflow dc.l 0
timing_input_queue ds.b 2048


; Paused callbacks advance only this exclusion counter. All logical deadlines and queued
; timestamps share field_count-paused_fields, so no queue rewrite or fractional reset is needed.
timing_pause_tag dc.b 'PDPAUS01'
timing_input_paused dc.w 0
timing_input_paused_fields dc.l 0
timing_input_pauses dc.l 0
timing_input_resumes dc.l 0

timing_input_pause_begin
 move.w sr,-(sp)
 move.l a0,-(sp)
 lea timing_state(pc),a0
 move.w #1,timing_input_paused-timing_state(a0)
 addq.l #1,timing_input_pauses-timing_state(a0)
 movea.l (sp)+,a0
 move.w (sp)+,ccr
 bra.w timing_input_native_pause

timing_input_pause_end
 move.w sr,-(sp)
 move.l a0,-(sp)
 lea timing_state(pc),a0
 clr.w timing_input_paused-timing_state(a0)
 addq.l #1,timing_input_resumes-timing_state(a0)
 ; Restore X before replaying the original MOVE.L, which determines the other flags.
 move.w 4(sp),ccr
 move.l perf_game(pc),a0
 move.l d7,$f96(a0)
 movea.l (sp)+,a0
 addq.l #2,sp
 rts

timing_input_native_pause dc.w $4ef9
 dc.l 0
