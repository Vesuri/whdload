 IFND TIMING_INPUT
TIMING_INPUT = 0
 ENDC
 IFND TIMING_BRAKE
TIMING_BRAKE = TIMING_INPUT
 ENDC
 IFNE TIMING_INPUT
 IFEQ TIMING_BRAKE
 FAIL "TIMING_INPUT requires TIMING_BRAKE"
 ENDC
 ENDC
 IFND TIMING_ORIENTATION
TIMING_ORIENTATION = 0
 ENDC
 IFNE TIMING_INPUT
 IFEQ TIMING_ORIENTATION
 FAIL "TIMING_INPUT requires TIMING_ORIENTATION"
 ENDC
 ENDC
; Development-only staged extraction. Not included unless TIMING_PERIODIC=1.
; An 18-unit (90 ms) cadence is 11.111 Hz on PAL, near the measured A500 routes.
TIMING_PERIOD = 18
install_periodic
 movem.l d0-d2/a0-a2,-(sp)
 move.l perf_game(pc),a1
 lea timing_targets(pc),a0
 moveq #(timing_targets_end-timing_targets)/6-1,d2
.fix
 move.l (a0)+,d0
 add.l a1,d0
 move.w (a0)+,d1
 lea timing_targets(pc),a2
 adda.w d1,a2
 move.l d0,(a2)
 dbra d2,.fix
 move.l (4).w,a0
 btst #AFB_68010,AttnFlags+1(a0)
 beq.s .flags
 lea timing_frame(pc),a0
 move.w #$42e7,(a0)
 IFNE TIMING_BRAKE
 lea timing_brake_vbl(pc),a0
 move.w #$42e7,(a0)
 ENDC
 IFNE TIMING_INPUT
 lea timing_brake_before_control(pc),a0
 move.w #$42e7,(a0)
 lea timing_brake_before_movement(pc),a0
 move.w #$42e7,(a0)
 lea timing_input_pause_begin(pc),a0
 move.w #$42e7,(a0)
 lea timing_input_pause_end(pc),a0
 move.w #$42e7,(a0)
 lea timing_input_joy_fire(pc),a0
 move.w #$42e7,(a0)
 lea timing_input_joy_down(pc),a0
 move.w #$42e7,(a0)
 ENDC
.flags
 lea pl_periodic(pc),a0
 move.l _resload(pc),a2
 jsr resload_Patch(a2)
 movem.l (sp)+,d0-d2/a0-a2
 rts
pl_periodic PL_START
 ; Six-byte BTST is replayed after accounting for the current interval.
 ; TIMING_RANGE h0:$ca44 6 bit=C3
 PL_P $ca44,timing_frame
 ; BSR control; TST animation. Continuation is the original conditional branch.
 ; TIMING_RANGE h0:$ca74 8 bit=C3
 PL_P $ca74,timing_control
 PL_NOP $ca7a,2
 ; TIMING_RANGE h0:$d922 8 bit=C3
 PL_P $d922,timing_resource
 PL_NOP $d928,2
 ; TIMING_RANGE h0:$d9a0 8 bit=C3
 PL_P $d9a0,timing_resource_end
 PL_NOP $d9a6,2
 IFNE TIMING_ORIENTATION
 ; TIMING_RANGE h0:$cce2 8 bit=C3
 ; TIMING_RANGE h0:$d028 6 bit=C3
 PL_P $d028,timing_brake_parity
 PL_P $cce2,timing_orientation_end
 PL_NOP $cce8,2
 ENDC
 IFNE TIMING_BRAKE
 ; Native decrements are serviced separately; their following clamps/jitter remain.
 ; TIMING_RANGE h0:$d00a 6 bit=C3
 PL_NOP $d00a,6
 ; TIMING_RANGE h0:$d01e 4 bit=C3
 PL_NOP $d01e,4
 IFNE TIMING_BRAKE
 ; Runs after native input sampling and the independent coverage-input hook.
 ; TIMING_RANGE h0:$5786 6 bit=C3
 PL_PS $5786,timing_brake_vbl
 ENDC
 ENDC
 IFNE TIMING_INPUT
 ; Historical buttons and modifiers; live input memory is never overwritten.
 ; TIMING_RANGE h0:$cf66 8 bit=C3
 PL_P $cf66,timing_input_buttons
 PL_NOP $cf6c,2
 ; TIMING_RANGE h0:$cf7a 6 bit=C3
 PL_P $cf7a,timing_input_modifiers
 ; TIMING_RANGE h0:$be12 6 bit=C3
 PL_PS $be12,timing_input_pause_begin
 ; TIMING_RANGE h0:$beec 6 bit=C3
 PL_PS $beec,timing_input_pause_end
 ; TIMING_RANGE h0:$d092 8 bit=C3
 PL_P $d092,timing_input_read_axes
 PL_NOP $d098,2
 ; TIMING_RANGE h0:$d082 8 bit=C3
 PL_P $d082,timing_input_write_axes
 PL_NOP $d088,2
 ; TIMING_RANGE h0:$d266 6 bit=C3
 PL_P $d266,timing_input_joystick
 ; TIMING_RANGE h0:$cf24 6 bit=C3
 PL_P $cf24,timing_input_poll_mode
 ; TIMING_RANGE h0:$cf40 6 bit=C3
 PL_P $cf40,timing_input_speed_mode
 ; TIMING_RANGE h0:$d0a2 6 bit=C3
 PL_P $d0a2,timing_input_axis_mode
 ; TIMING_RANGE h0:$cf46 6 bit=C3
 PL_PS $cf46,timing_input_joy_fire
 ; TIMING_RANGE h0:$cf4e 6 bit=C3
 PL_PS $cf4e,timing_input_joy_down
 ENDC
 PL_END

timing_frame
 move.w sr,-(sp)
 movem.l d0-d2/a0-a1,-(sp)
 bsr timing_clock
 lea timing_state(pc),a1
 move.l perf_game(pc),a0
 IFNE TIMING_INPUT
 ; One clock domain for VBL input timestamps and periodic work (PAL).
 move.l $48fe(a0),d0
 sub.l timing_input_paused_fields-timing_state(a1),d0
 lsl.l #2,d0
 ELSE
 move.l $f96(a0),d0
 ENDC
 move.l d0,d1
 sub.l timing_last-timing_state(a1),d1
 move.l d0,timing_last-timing_state(a1)
 tst.w timing_started-timing_state(a1)
 beq.s .initial
 move.l $5e(a6),d0
 cmp.l timing_loop-timing_state(a1),d0
 blo.s .initial
 tst.l d1
 bmi.s .initial
 add.l d1,timing_phase-timing_state(a1)
 clr.w timing_due-timing_state(a1)
.again
 cmp.l #TIMING_PERIOD,timing_phase-timing_state(a1)
 blo.s .accounted
 cmp.w #32,timing_due-timing_state(a1)
 bhs.s .accounted
 sub.l #TIMING_PERIOD,timing_phase-timing_state(a1)
 addq.w #1,timing_due-timing_state(a1)
 addq.l #1,timing_ticks-timing_state(a1)
 bra.s .again
.initial
 IFNE TIMING_INPUT
 bsr timing_input_initialize
 ENDC
 IFNE TIMING_BRAKE
 clr.w timing_brake_active-timing_state(a1)
 clr.l timing_brake_phase-timing_state(a1)
 IFNE TIMING_BRAKE
 clr.l timing_brake_pending-timing_state(a1)
 IFNE TIMING_INPUT
 clr.l timing_brake_read-timing_state(a1)
 ENDC
 ENDC
 ENDC
 move.w #1,timing_control_phase-timing_state(a1)
 move.w #1,timing_started-timing_state(a1)
 clr.l timing_phase-timing_state(a1)
 move.w #1,timing_due-timing_state(a1)
 addq.l #1,timing_ticks-timing_state(a1)
.accounted
 move.l $5e(a6),timing_loop-timing_state(a1)
 addq.l #1,timing_frames-timing_state(a1)
 IFNE TIMING_BRAKE
 IFEQ TIMING_INPUT
 bsr timing_service_brake
 ENDC
 ENDC
 IFNE TIMING_ORIENTATION
 move.w timing_due-timing_state(a1),timing_orientation_left-timing_state(a1)
 ENDC
 movem.l (sp)+,d0-d2/a0-a1
 move.w (sp)+,ccr
 IFNE TIMING_ORIENTATION
 ; No angle integration on draws between periodic updates. Movement still uses elapsed time.
 move.l d0,-(sp)
 move.w timing_due(pc),d0
 movem.l (sp)+,d0
 beq.w timing_orientation_move
 ENDC
timing_orientation_again
 IFNE TIMING_ORIENTATION
 ; The original first driving loop has odd parity. Advance by control updates, not draws.
 move.l d0,-(sp)
 move.w timing_control_phase(pc),d0
 btst #0,d0
 movem.l (sp)+,d0
 ELSE
 btst #0,$61(a6)
 ENDC
 bra.w timing_after_frame

timing_control
 movem.l d0/a0,-(sp)
 lea timing_state(pc),a0
 IFNE TIMING_ORIENTATION
 moveq #1,d0
 ELSE
 move.w timing_due(pc),d0
 ENDC
 move.w d0,timing_control_left-timing_state(a0)
 movem.l (sp)+,d0/a0
 beq.s .done
.next
 move.l a0,-(sp)
 lea timing_state(pc),a0
 addq.l #1,timing_controls-timing_state(a0)
 move.l (sp)+,a0
 IFNE TIMING_INPUT
 bsr timing_input_for_control
 bsr timing_brake_before_control
 ENDC
 pea .returned(pc)
 bra.w timing_native_control
.returned
 move.l a0,-(sp)
 lea timing_state(pc),a0
 IFNE TIMING_INPUT
 clr.w timing_input_control_active-timing_state(a0)
 add.l #TIMING_PERIOD,timing_input_clock-timing_state(a0)
 ENDC
 addq.w #1,timing_control_phase-timing_state(a0)
 subq.w #1,timing_control_left-timing_state(a0)
 movea.l (sp)+,a0
 bne.s .next
.done
 tst.w $258(a6)
 bra.w timing_after_control

timing_resource
 movem.l d0/a0,-(sp)
 lea timing_state(pc),a0
 move.w timing_due(pc),d0
 move.w d0,timing_resource_left-timing_state(a0)
 movem.l (sp)+,d0/a0
 beq.s timing_resource_draw_due
 tst.w $240(a6)
 bne.s timing_resource_draw_due
timing_resource_next
 move.l a0,-(sp)
 lea timing_state(pc),a0
 addq.l #1,timing_resources-timing_state(a0)
 movea.l (sp)+,a0
 bra.w timing_native_resource
timing_resource_draw_due
 pea timing_resource_continuation(pc)
 bra.w timing_resource_draw

timing_resource_end
 move.w d1,$1ba(a6)
 move.l a0,-(sp)
 lea timing_state(pc),a0
 subq.w #1,timing_resource_left-timing_state(a0)
 movea.l (sp)+,a0
 bne.s timing_resource_next
 bra.s timing_resource_draw_due

 IFNE TIMING_ORIENTATION
timing_brake_parity
 move.l d0,-(sp)
 move.w timing_control_phase(pc),d0
 btst #0,d0
 movem.l (sp)+,d0
 bra.w timing_after_brake_parity
timing_after_brake_parity dc.w $4ef9
 dc.l 0
timing_orientation_end
 move.l a0,-(sp)
 lea timing_state(pc),a0
 subq.w #1,timing_orientation_left-timing_state(a0)
 movea.l (sp)+,a0
 bne.w timing_orientation_again
timing_orientation_move
 IFNE TIMING_INPUT
 bsr timing_brake_before_movement
 ENDC
 move.w $3f4(a6),d5
 move.w $3f6(a6),d6
 bra.w timing_after_orientation
timing_after_orientation dc.w $4ef9
 dc.l 0
 ENDC

timing_clock dc.w $4ef9
 dc.l 0
timing_after_frame dc.w $4ef9
 dc.l 0
timing_native_control dc.w $4ef9
 dc.l 0
timing_after_control dc.w $4ef9
 dc.l 0
timing_native_resource dc.w $4ef9
 dc.l 0
timing_resource_draw dc.w $4ef9
 dc.l 0
timing_resource_continuation dc.w $4ef9
 dc.l 0

timing_targets
 dc.l $59b6
 dc.w timing_clock+2-timing_targets
 dc.l $ca4a
 dc.w timing_after_frame+2-timing_targets
 dc.l $cef6
 dc.w timing_native_control+2-timing_targets
 dc.l $ca7c
 dc.w timing_after_control+2-timing_targets
 dc.l $d92a
 dc.w timing_native_resource+2-timing_targets
 dc.l $8b02
 dc.w timing_resource_draw+2-timing_targets
 dc.l $d9a8
 dc.w timing_resource_continuation+2-timing_targets
 IFNE TIMING_ORIENTATION
 dc.l $d02e
 dc.w timing_after_brake_parity+2-timing_targets
 dc.l $ccea
 dc.w timing_after_orientation+2-timing_targets
 ENDC
 IFNE TIMING_BRAKE
 dc.l $d382
 dc.w timing_brake_joystick+2-timing_targets
 ENDC
 IFNE TIMING_INPUT
 dc.l $d09a
 dc.w timing_input_after_read_axes+2-timing_targets
 dc.l $d08a
 dc.w timing_input_after_write_axes+2-timing_targets
 dc.l $d26c
 dc.w timing_input_joystick_body+2-timing_targets
 dc.l $cf2e
 dc.w timing_input_skip_poll+2-timing_targets
 dc.l $cf2a
 dc.w timing_input_do_poll+2-timing_targets
 dc.l $cf66
 dc.w timing_input_speed_mouse+2-timing_targets
 dc.l $cf46
 dc.w timing_input_speed_joy+2-timing_targets
 dc.l $d0a8
 dc.w timing_input_axis_mouse+2-timing_targets
 dc.l $d0b4
 dc.w timing_input_axis_joy+2-timing_targets
 dc.l $82b6
 dc.w timing_input_native_pause+2-timing_targets
 dc.l $cf6e
 dc.w timing_input_after_buttons+2-timing_targets
 dc.l $cf80
 dc.w timing_input_after_modifiers+2-timing_targets
 ENDC
timing_targets_end

timing_state dc.b 'PDTIME01'
timing_started dc.w 0
timing_due dc.w 0
timing_last dc.l 0
timing_phase dc.l 0
timing_loop dc.l 0
timing_ticks dc.l 0
timing_frames dc.l 0
timing_controls dc.l 0
timing_resources dc.l 0
timing_control_left dc.w 0
timing_resource_left dc.w 0
timing_orientation_left dc.w 0
timing_control_phase dc.w 1

 IFNE TIMING_BRAKE
 INCLUDE timing_brake.s
 ENDC

 IFNE TIMING_INPUT
 INCLUDE timing_input.s
 ENDC
