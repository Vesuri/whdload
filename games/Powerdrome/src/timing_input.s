; VBL produces timestamped external input. Logical controls own corrected axis state.
; 256 sixteen-byte slots, with one empty slot. Overflow is explicit and invalidates a run.
TIMING_INPUT_MASK = 4080
; Every stick sum saturates here. Symmetric, so the native NEG.W of an axis cannot overflow.
TIMING_AXIS_LIMIT = 32767

; Player movement is the native per-VBL mouse count, taken where the VBL server adds it
; to the raw counters (ext.w + add.w at $56d2 and $56fc). Only these counts are queued, so
; a native write to the stick (contact damping, resets) is never mistaken for movement.
; X keeps d1, which already holds the Y counter byte.
timing_input_mouse_x
 ext.w d0
 movem.l d0-d1/a0-a1,-(sp)
 lea $42a(a6),a0
 lea timing_input_pending_x(pc),a1
 bsr.s timing_input_player
 movem.l (sp)+,d0-d1/a0-a1
 rts

timing_input_mouse_y
 ext.w d1
 movem.l d0-d1/a0-a1,-(sp)
 move.w d1,d0
 lea $42e(a6),a0
 lea timing_input_pending_y(pc),a1
 bsr.s timing_input_player
 movem.l (sp)+,d0-d1/a0-a1
 rts

; d0.w player delta, a0 raw native axis, a1 pending axis. Both sums saturate. Uses d0-d1.
timing_input_player
 move.w d0,d1
 ext.l d1
 move.w (a0),d0
 ext.l d0
 add.l d1,d0
 bsr.s timing_input_saturate
 move.w d0,(a0)
 move.w (a1),d0
 ext.l d0
 add.l d1,d0
 bsr.s timing_input_saturate
 move.w d0,(a1)
 rts

; d0.l -> d0 clamped to +-TIMING_AXIS_LIMIT.
timing_input_saturate
 cmp.l #TIMING_AXIS_LIMIT,d0
 ble.s .not_high
 move.l #TIMING_AXIS_LIMIT,d0
 rts
.not_high
 cmp.l #-TIMING_AXIS_LIMIT,d0
 bge.s .done
 move.l #-TIMING_AXIS_LIMIT,d0
.done
 rts

timing_input_initialize
 clr.l timing_input_read-timing_state(a1)
 clr.w timing_input_control_active-timing_state(a1)
 move.l timing_last-timing_state(a1),timing_input_clock-timing_state(a1)
 ; Start with the same normalized input representation as the VBL producer.
 ; A joystick can enter gameplay with stale native mouse-button state.
 clr.w timing_input_joy-timing_state(a1)
 clr.w timing_input_last_joy-timing_state(a1)
 move.w $432(a6),d0
 tst.w $422(a6)
 beq.s .buttons_ready
 move.l d3,-(sp)
 bsr timing_brake_joystick
 move.l (sp)+,d3
 moveq #0,d0
 move.b $427(a6),d0
 move.w d0,timing_input_joy-timing_state(a1)
 move.w d0,timing_input_last_joy-timing_state(a1)
 moveq #0,d0
 btst #7,$427(a6)
 beq.s .buttons_ready
 btst #0,$427(a6)
 beq.s .brake
 moveq #1,d0
 bra.s .buttons_ready
.brake
 btst #1,$427(a6)
 beq.s .buttons_ready
 moveq #2,d0
.buttons_ready
 move.l perf_game(pc),a0
 swap d0
 move.w $f9e(a0),d0
 move.l d0,timing_input_current-timing_state(a1)
 move.l d0,timing_input_last-timing_state(a1)
 move.w $42a(a6),timing_input_sample_x-timing_state(a1)
 move.w $42e(a6),timing_input_sample_y-timing_state(a1)
 move.w $42a(a6),timing_input_x-timing_state(a1)
 move.w $42e(a6),timing_input_y-timing_state(a1)
 ; Movement made before gameplay (menus) belongs to the pointer, not the stick.
 clr.w timing_input_pending_x-timing_state(a1)
 clr.w timing_input_pending_y-timing_state(a1)
 move.w $422(a6),timing_input_mode-timing_state(a1)
 move.w $422(a6),timing_input_last_mode-timing_state(a1)
 IFNE TIMING_WORLD20
 bsr timing_world_input_initialize
 ENDC
 rts

timing_input_sample
 movem.l d0-d6/a0,-(sp)
 move.l perf_game(pc),a0
 swap d0
 move.w $f9e(a0),d0
 move.w timing_input_pending_x-timing_state(a1),d4
 move.w timing_input_pending_y-timing_state(a1),d5
 moveq #0,d6
 tst.w $422(a6)
 beq.s .joy_ready
 move.b $427(a6),d6
.joy_ready
 cmp.l timing_input_last-timing_state(a1),d0
 bne.s .changed
 tst.w d4
 bne.s .changed
 tst.w d5
 bne.s .changed
 cmp.w timing_input_last_joy-timing_state(a1),d6
 bne.s .changed
 move.w $422(a6),d1
 cmp.w timing_input_last_mode-timing_state(a1),d1
 beq.w .done
.changed
 move.l $48fe(a0),d1
 sub.l timing_input_paused_fields-timing_state(a1),d1
 lsl.l #2,d1
 move.w timing_input_write-timing_state(a1),d2
 move.w d2,d3
 add.w #16,d3
 and.w #TIMING_INPUT_MASK,d3
 cmp.w timing_input_read-timing_state(a1),d3
 beq.s .full
 lea timing_input_queue(pc),a0
 adda.w d2,a0
 move.l d1,(a0)
 move.l d0,4(a0)
 move.w d4,8(a0)
 move.w d5,10(a0)
 move.w d6,12(a0)
 move.w $422(a6),14(a0)
 move.l d0,timing_input_last-timing_state(a1)
 move.w $42a(a6),timing_input_sample_x-timing_state(a1)
 move.w $42e(a6),timing_input_sample_y-timing_state(a1)
 clr.w timing_input_pending_x-timing_state(a1)
 clr.w timing_input_pending_y-timing_state(a1)
 move.w d6,timing_input_last_joy-timing_state(a1)
 move.w $422(a6),timing_input_last_mode-timing_state(a1)
 addq.l #1,timing_input_produced-timing_state(a1)
 move.w d3,timing_input_write-timing_state(a1)
 bra.s .done
.full
 addq.l #1,timing_input_overflow-timing_state(a1)
.done
 movem.l (sp)+,d0-d6/a0
 rts

timing_input_for_control
 movem.l d0-d2/a0-a2,-(sp)
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
 move.w 8(a0),d1
 lea timing_input_x(pc),a2
 bsr.s .axis
 move.w 10(a0),d1
 lea timing_input_y(pc),a2
 bsr.s .axis
 move.w 12(a0),timing_input_joy-timing_state(a1)
 move.w 14(a0),timing_input_mode-timing_state(a1)
 addq.l #1,timing_input_consumed-timing_state(a1)
 add.w #16,d0
 and.w #TIMING_INPUT_MASK,d0
 move.w d0,timing_input_read-timing_state(a1)
 bra.s .next
.done
 move.w #1,timing_input_control_active-timing_state(a1)
 movem.l (sp)+,d0-d2/a0-a2
 rts
; d1.w queued delta added to the private axis (a2), saturating. Keeps d0.
.axis
 move.l d0,-(sp)
 move.w (a2),d0
 ext.l d0
 ext.l d1
 add.l d1,d0
 bsr timing_input_saturate
 move.w d0,(a2)
 move.l (sp)+,d0
 rts

timing_input_buttons
 bsr timing_input_is_active
 beq.s .live
 move.w timing_input_current(pc),d7
 bra.s .test
.live
 move.w $432(a6),d7
.test
 btst #0,d7
 bra.w timing_input_after_buttons

timing_input_modifiers
 bsr timing_input_is_active
 beq.s .live
 move.w timing_input_current+2(pc),d0
 bra.w timing_input_after_modifiers
.live
 move.l a0,-(sp)
 move.l perf_game(pc),a0
 move.w $f9e(a0),d0
 movea.l (sp)+,a0
 bra.w timing_input_after_modifiers

timing_input_read_axes
 bsr timing_input_is_active
 beq.s .live
 move.w timing_input_x(pc),d2
 move.w timing_input_y(pc),d3
 bra.w timing_input_after_read_axes
.live
 move.w $42a(a6),d2
 move.w $42e(a6),d3
 bra.w timing_input_after_read_axes

 ; Native contact damping. It sets the stick, so it sets both the private axes that
; controls read and the raw counters, as the single native variable would.
timing_input_write_axes
 move.l a0,-(sp)
 lea timing_state(pc),a0
 move.w d2,timing_input_x-timing_state(a0)
 move.w d3,timing_input_y-timing_state(a0)
 move.w #1,timing_input_damped-timing_state(a0)
 movea.l (sp)+,a0
 move.w d2,$42a(a6)
 move.w d3,$42e(a6)
 bra.w timing_input_after_write_axes

; Native stick reset (two MOVE.W #0 to $42a/$42e): reposition (A), pit and session
; starts. Native code resets one variable; here the raw counters, the private axes and
; the movement not yet consumed (pending and queued) all belong to that stick, so they
; are cleared together. Masked against the VBL producer.
timing_input_zero_axes
 movem.l d0-d1/a0-a1,-(sp)
 move.w $dff01c,d1
 move.w #$4000,$dff09a
 clr.w $42a(a6)
 clr.w $42e(a6)
 lea timing_state(pc),a1
 clr.w timing_input_sample_x-timing_state(a1)
 clr.w timing_input_sample_y-timing_state(a1)
 clr.w timing_input_x-timing_state(a1)
 clr.w timing_input_y-timing_state(a1)
 clr.w timing_input_pending_x-timing_state(a1)
 clr.w timing_input_pending_y-timing_state(a1)
 lea timing_input_queue(pc),a0
 move.w timing_input_read-timing_state(a1),d0
.pending
 cmp.w timing_input_write-timing_state(a1),d0
 beq.s .done
 clr.l 8(a0,d0.w)
 add.w #16,d0
 and.w #TIMING_INPUT_MASK,d0
 bra.s .pending
.done
 addq.l #1,timing_input_resets-timing_state(a1)
 and.w #$4000,d1
 beq.s .masked
 move.w #$c000,$dff09a
.masked
 movem.l (sp)+,d0-d1/a0-a1
 rts

; The original joystick body at d26c..d380 has no calls or stack-relative data.
; Run it against only its own input fields; IRQs retain the native VBL state pointer.
timing_input_joystick
 bsr timing_input_is_active
 beq.s .live
 move.l a6,-(sp)
 lea timing_input_joy-$426(pc),a6
 pea .returned(pc)
 bra.w timing_input_joystick_body
.returned
 movea.l (sp)+,a6
 move.w timing_input_roll(pc),$428(a6)
 move.l a0,-(sp)
 lea timing_input_current(pc),a0
 move.w timing_input_joy_buttons(pc),(a0)
 movea.l (sp)+,a0
 rts
.live
 bsr timing_brake_joystick
 bra.w timing_input_joystick_body

timing_input_is_active
 move.l d0,-(sp)
 move.w timing_input_control_active(pc),d0
 movem.l (sp)+,d0
 rts

timing_input_test_mode
 move.l d0,-(sp)
 bsr timing_input_is_active
 beq.s .live
 move.w timing_input_mode(pc),d0
 bra.s .done
.live
 tst.w $422(a6)
.done
 movem.l (sp)+,d0
 rts

timing_input_poll_mode
 bsr timing_input_test_mode
 beq.w timing_input_skip_poll
 bra.w timing_input_do_poll

timing_input_speed_mode
 bsr timing_input_test_mode
 beq.w timing_input_speed_mouse
 bra.w timing_input_speed_joy

timing_input_axis_mode
 bsr timing_input_test_mode
 bne.w timing_input_axis_joy
 bra.w timing_input_axis_mouse

timing_input_joy_fire
 move.w sr,-(sp)
 bsr timing_input_is_active
 beq.s .live
 move.w (sp)+,ccr
 btst #7,timing_input_joy+1(pc)
 rts
.live
 move.w (sp)+,ccr
 btst #7,$427(a6)
 rts

timing_input_joy_down
 move.w sr,-(sp)
 bsr timing_input_is_active
 beq.s .live
 move.w (sp)+,ccr
 btst #1,timing_input_joy+1(pc)
 rts
.live
 move.w (sp)+,ccr
 btst #1,$427(a6)
 rts

timing_input_after_buttons dc.w $4ef9
 dc.l 0
timing_input_after_modifiers dc.w $4ef9
 dc.l 0
timing_input_after_read_axes dc.w $4ef9
 dc.l 0
timing_input_after_write_axes dc.w $4ef9
 dc.l 0
timing_input_joystick_body dc.w $4ef9
 dc.l 0
timing_input_skip_poll dc.w $4ef9
 dc.l 0
timing_input_do_poll dc.w $4ef9
 dc.l 0
timing_input_speed_mouse dc.w $4ef9
 dc.l 0
timing_input_speed_joy dc.w $4ef9
 dc.l 0
timing_input_axis_mouse dc.w $4ef9
 dc.l 0
timing_input_axis_joy dc.w $4ef9
 dc.l 0

timing_input_tag dc.b 'PDINPT02'
timing_input_read dc.w 0
timing_input_write dc.w 0
timing_input_clock dc.l 0
timing_input_current dc.l 0
timing_input_last dc.l 0
timing_input_produced dc.l 0
timing_input_consumed dc.l 0
timing_input_overflow dc.l 0
timing_input_sample_x dc.w 0
timing_input_sample_y dc.w 0
timing_input_last_joy dc.w 0
timing_input_last_mode dc.w 0
timing_input_mode dc.w 0
timing_input_control_active dc.w 0
; Match the native joystick body's d16(a6) offsets exactly, including unused gaps.
timing_input_joy dc.w 0                 ; $426 (low byte at $427)
timing_input_roll dc.w 0                ; $428
timing_input_x dc.w 0                   ; $42a
 dc.w 0                                ; $42c
timing_input_y dc.w 0                   ; $42e
 dc.w 0                                ; $430
timing_input_joy_buttons dc.w 0          ; $432
 dc.w 0
timing_input_queue ds.b 4096
; Paused callbacks advance only this exclusion counter. All logical deadlines and queued
; timestamps share field_count-paused_fields, so no queue rewrite or fractional reset is needed.
timing_pause_tag dc.b 'PDPAUS01'
timing_input_paused dc.w 0
timing_input_paused_fields dc.l 0
timing_input_pauses dc.l 0
timing_input_resumes dc.l 0
; Native stick resets taken through timing_input_zero_axes.
timing_input_resets dc.l 0
; Player mouse counts since the producer last queued them.
timing_input_pending_x dc.w 0
timing_input_pending_y dc.w 0
; Set by contact damping for the same control update's angle division (timing_mouse.s).
timing_input_damped dc.w 0

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
