; Separate experimental braking cadence, calibrated to the native A500 response route.
; Called at the movement boundary with timing_state in a1. VBL owns the owed count.
; d0-d2/a0-a1 are already saved by timing_frame. No additional native control call.
TIMING_BRAKE_PERIOD = 14

timing_service_brake
 moveq #0,d2
.pending
 tst.l timing_brake_pending-timing_state(a1)
 beq.s .finished
 cmp.w #32,d2
 bhs.s .finished
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

; Account only input time here. Physics stays in the ordinary movement context.
; Each PAL callback contributes four native clock units. 14 units alternates 3/4 fields.
timing_brake_vbl
 move.w sr,-(sp)
 movem.l d0-d3/a0-a1,-(sp)
 lea timing_state(pc),a1
 tst.w timing_started-timing_state(a1)
 beq.s .done
 move.w $432(a6),d0
 tst.w $422(a6)
 beq.s .buttons
 bsr timing_brake_joystick
 moveq #0,d0
 btst #7,$427(a6)
 beq.s .buttons
 btst #0,$427(a6)
 bne.s .released
 btst #1,$427(a6)
 beq.s .buttons
 moveq #2,d0
.buttons
 and.w #3,d0
 cmp.w #2,d0
 bne.s .released
 tst.w timing_brake_active-timing_state(a1)
 bne.s .held
 move.w #1,timing_brake_active-timing_state(a1)
 clr.l timing_brake_phase-timing_state(a1)
 addq.l #1,timing_brake_pending-timing_state(a1)
 bra.s .done
.held
 addq.l #4,timing_brake_phase-timing_state(a1)
 cmp.l #TIMING_BRAKE_PERIOD,timing_brake_phase-timing_state(a1)
 blo.s .done
 sub.l #TIMING_BRAKE_PERIOD,timing_brake_phase-timing_state(a1)
 addq.l #1,timing_brake_pending-timing_state(a1)
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
