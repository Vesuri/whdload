; Separate experimental braking cadence, calibrated to the native A500 response route.
; VBL owns owed events; with historical input they are merged by timestamp.
; Callers preserve d0-d2/a0-a1 and flags. No additional native control call.
TIMING_BRAKE_PERIOD = 14

timing_service_brake
 moveq #0,d2
.pending
 tst.l timing_brake_pending-timing_state(a1)
 beq.s .finished
 cmp.w #32,d2
 bhs.s .finished
 IFNE TIMING_INPUT
 ; d1 is the latest logical instant eligible for service, not the render clock.
 move.w timing_brake_read-timing_state(a1),d0
 lea timing_brake_queue(pc),a0
 adda.w d0,a0
 move.l d1,d0
 sub.l (a0),d0
 bmi.s .finished
 addq.w #4,timing_brake_read-timing_state(a1)
 and.w #1020,timing_brake_read-timing_state(a1)
 ENDC
 subq.l #1,timing_brake_pending-timing_state(a1)
 addq.w #1,d2
 addq.l #1,timing_brakes-timing_state(a1)
 tst.w $1ba(a6)
 ble.s .pending
 tst.w $e4(a6)
 beq.s .pending
 move.w $1f0(a6),d0
 btst #5,$139(a6)
 beq.s .decrement
 moveq #3,d0
.decrement
 sub.w d0,$194(a6)
 bpl.s .pending
 clr.w $194(a6)
 bra.s .pending
.finished
 rts

timing_brake_tag dc.b 'PDBRAK02'
timing_brake_active dc.w 0
timing_brake_phase dc.l 0
timing_brakes dc.l 0

timing_brake_pending dc.l 0

 IFNE TIMING_INPUT
; Separate read/write words make publication atomic with respect to VBL interruption.
timing_brake_queue_tag dc.b 'PDBQUE01'
timing_brake_read dc.w 0
timing_brake_write dc.w 0
timing_brake_overflow dc.l 0
timing_brake_queue ds.b 1024

timing_brake_before_control
 move.w sr,-(sp)
 movem.l d0-d2/a0-a1,-(sp)
 lea timing_state(pc),a1
 move.l timing_input_clock(pc),d1
 bsr timing_service_brake
 movem.l (sp)+,d0-d2/a0-a1
 move.w (sp)+,ccr
 rts

timing_brake_before_movement
 move.w sr,-(sp)
 movem.l d0-d2/a0-a1,-(sp)
 lea timing_state(pc),a1
 ; Service intervening brake events, but never overtake an older deferred control.
 move.l timing_input_clock(pc),d1
 subq.l #1,d1
 move.l timing_last(pc),d0
 sub.l d1,d0
 bpl.s .cutoff
 move.l timing_last(pc),d1
.cutoff
 bsr timing_service_brake
 movem.l (sp)+,d0-d2/a0-a1
 move.w (sp)+,ccr
 rts

timing_brake_enqueue
 move.w timing_brake_write-timing_state(a1),d2
 move.w d2,d3
 addq.w #4,d3
 and.w #1020,d3
 cmp.w timing_brake_read-timing_state(a1),d3
 beq.s .full
 move.l perf_game(pc),a0
 move.l $48fe(a0),d1
 sub.l timing_input_paused_fields-timing_state(a1),d1
 lsl.l #2,d1
 lea timing_brake_queue(pc),a0
 adda.w d2,a0
 move.l d1,(a0)
 move.w d3,timing_brake_write-timing_state(a1)
 addq.l #1,timing_brake_pending-timing_state(a1)
 rts
.full
 addq.l #1,timing_brake_overflow-timing_state(a1)
 rts
 ENDC

; Account only input time here. Physics stays in the ordinary movement context.
; Each PAL callback contributes four native clock units. 14 units alternates 3/4 fields.
timing_brake_vbl
 move.w sr,-(sp)
 movem.l d0-d3/a0-a1,-(sp)
 lea timing_state(pc),a1
 tst.w timing_started-timing_state(a1)
 beq.w .done
 IFNE TIMING_INPUT
 tst.w timing_input_paused-timing_state(a1)
 beq.s .running
 addq.l #1,timing_input_paused_fields-timing_state(a1)
 bra.w .done
.running
 ENDC
 move.w $432(a6),d0
 tst.w $422(a6)
 beq.s .buttons
 bsr timing_brake_joystick
 moveq #0,d0
 btst #7,$427(a6)
 beq.s .buttons
 btst #0,$427(a6)
 beq.s .joy_brake
 moveq #1,d0
 bra.s .buttons
.joy_brake
 btst #1,$427(a6)
 beq.s .buttons
 moveq #2,d0
.buttons
 IFNE TIMING_INPUT
 bsr timing_input_sample
 ENDC
 and.w #3,d0
 cmp.w #2,d0
 bne.s .released
 tst.w timing_brake_active-timing_state(a1)
 bne.s .held
 move.w #1,timing_brake_active-timing_state(a1)
 clr.l timing_brake_phase-timing_state(a1)
 IFNE TIMING_INPUT
 bsr timing_brake_enqueue
 ELSE
 addq.l #1,timing_brake_pending-timing_state(a1)
 ENDC
 bra.s .done
.held
 addq.l #4,timing_brake_phase-timing_state(a1)
 cmp.l #TIMING_BRAKE_PERIOD,timing_brake_phase-timing_state(a1)
 blo.s .done
 sub.l #TIMING_BRAKE_PERIOD,timing_brake_phase-timing_state(a1)
 IFNE TIMING_INPUT
 bsr timing_brake_enqueue
 ELSE
 addq.l #1,timing_brake_pending-timing_state(a1)
 ENDC
 bra.s .done
.released
 clr.w timing_brake_active-timing_state(a1)
 clr.l timing_brake_phase-timing_state(a1)
 ; Do not clear already owed steps on release.
.done
 movem.l (sp)+,d0-d3/a0-a1
 move.w (sp)+,ccr
 move.w #-1,$494(a6)
 rts

timing_brake_joystick dc.w $4ef9
 dc.l 0
