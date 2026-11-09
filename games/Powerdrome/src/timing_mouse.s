 machine 68020
; Enhanced mouse steering: Q12 angular rates per 90 ms, applied every 20 ms.
; Rebuild within an epoch from its saved matrix, rather than rounding the matrix
; repeatedly for each small step. Native candidate acceptance is retained.
; All entries are reached only by the 68020+/Fast-RAM timing installation.
timing_mouse_reset
 movem.l d0/a1,-(sp)
 lea timing_mouse_state(pc),a1
 moveq #(timing_mouse_state_end-timing_mouse_state)/2-1,d0
.clear
 clr.w (a1)+
 dbra d0,.clear
 movem.l (sp)+,d0/a1
 rts

; Native gain 136/256, with the discarded fractions kept for the angle division.
timing_mouse_gain
 move.l a0,-(sp)
 lea timing_mouse_gain_x(pc),a0
 muls.w #136,d2
 move.w d2,(a0)
 and.w #255,(a0)+
 asr.l #8,d2
 muls.w #136,d3
 move.w d3,(a0)
 and.w #255,(a0)
 asr.l #8,d3
 movea.l (sp)+,a0
 rts

timing_mouse_divide
 ; Replay the native division first; retain its full register results.
 move.w d3,d0
 move.w d2,d1
 ext.l d0
 divs.w $1ee(a6),d0
 ext.l d1
 divs.w $1ec(a6),d1
 move.w ccr,-(sp)
 movem.l d0-d3/a0,-(sp)
 ; A control update that took native contact damping keeps the native whole-degree
 ; rates. A damped stick stays at -1 under ASR; natively that divides to 0, the next
 ; candidate is the current orientation and is accepted, ending the damping. A retained
 ; fraction would keep pushing into the floor, so the stick would never read the mouse.
 lea timing_input_damped(pc),a0
 move.w (a0),d2
 clr.w (a0)
 lea timing_mouse_fraction_pitch(pc),a0
 clr.l (a0)
 tst.w d2
 bne.s .done
 move.w timing_input_mode(pc),d2
 bne.s .done
 ; DIVS's signed remainder retains the sub-degree part. The horizontal
 ; gain remainder is negated because native D2 was negated at $d0b4.
 swap d0
 ext.l d0
 asl.l #8,d0
 asl.l #4,d0
 moveq #0,d2
 move.w timing_mouse_gain_y(pc),d2
 lsl.l #4,d2
 add.l d2,d0
 divs.w $1ee(a6),d0
 move.w d0,(a0)+
 swap d1
 ext.l d1
 asl.l #8,d1
 asl.l #4,d1
 moveq #0,d2
 move.w timing_mouse_gain_x(pc),d2
 lsl.l #4,d2
 sub.l d2,d1
 divs.w $1ec(a6),d1
 move.w d1,(a0)
.done
 movem.l (sp)+,d0-d3/a0
 move.w (sp)+,ccr
 rts

; A step without a control epoch still integrates the held mouse angular rate.
timing_mouse_between
 move.w timing_input_mode(pc),d0
 bne.w timing_orientation_move
 move.w timing_mouse_ready(pc),d0
 beq.w timing_orientation_move
 tst.w $258(a6)
 bne.w timing_orientation_move
 bra.w timing_mouse_candidate

timing_mouse_rotate
 movem.l d0-d7/a0-a2,-(sp)
 lea timing_mouse_state(pc),a0
 move.w timing_input_mode(pc),d0
 bne.w .native
 tst.w $258(a6)
 bne.w .native
 bsr timing_world20_test_control
 beq.s .continue
 ; Rates remain in native units in game state; only this private copy is Q12.
 move.w $3a6(a6),d0
 ext.l d0
 asl.l #8,d0
 asl.l #4,d0
 move.w timing_mouse_fraction_pitch(pc),d1
 ext.l d1
 add.l d1,d0
 move.l d0,timing_mouse_rates-timing_mouse_state(a0)
 move.w $3a8(a6),d0
 ext.l d0
 asl.l #8,d0
 asl.l #4,d0
 move.w timing_mouse_fraction_yaw(pc),d1
 ext.l d1
 add.l d1,d0
 move.l d0,timing_mouse_rates+4-timing_mouse_state(a0)
 move.w $3aa(a6),d0
 ext.l d0
 asl.l #8,d0
 asl.l #4,d0
 move.l d0,timing_mouse_rates+8-timing_mouse_state(a0)
 ; Carry angle conversion fractions from the completed previous epoch.
 move.l timing_mouse_pending(pc),timing_mouse_carry-timing_mouse_state(a0)
 move.w timing_mouse_pending+4(pc),timing_mouse_carry+4-timing_mouse_state(a0)
 tst.w (a0)
 beq.s .rebase
 lea $3e8(a6),a1
 lea timing_mouse_expected(pc),a2
 moveq #8,d0
.check_control
 cmpm.w (a1)+,(a2)+
 bne.s .external
 dbra d0,.check_control
 clr.w timing_mouse_elapsed-timing_mouse_state(a0)
 lea timing_mouse_matrix_state(pc),a1
 lea timing_mouse_base(pc),a2
 moveq #8,d0
.save_precise
 move.l (a1)+,(a2)+
 dbra d0,.save_precise
 bra.s .integrate
.continue
 ; A native reset/collision writer invalidates the saved epoch matrix.
 lea $3e8(a6),a1
 lea timing_mouse_expected(pc),a2
 moveq #8,d0
.compare
 cmpm.w (a1)+,(a2)+
 bne.s .external
 dbra d0,.compare
 bra.s .integrate
.external
 clr.l timing_mouse_carry-timing_mouse_state(a0)
 clr.w timing_mouse_carry+4-timing_mouse_state(a0)
.rebase
 clr.w timing_mouse_elapsed-timing_mouse_state(a0)
 lea $3e8(a6),a1
 lea timing_mouse_base(pc),a2
 moveq #8,d0
.copy
 move.w (a1)+,d1
 ext.l d1
 moveq #14,d2
 asl.l d2,d1
 move.l d1,(a2)+
 dbra d0,.copy
.integrate
 move.w #1,(a0)
 addq.w #4,timing_mouse_elapsed-timing_mouse_state(a0)
 lea timing_mouse_rates(pc),a1
 lea timing_mouse_angles(pc),a2
 moveq #0,d2
 moveq #2,d0
.scale
 move.l (a1)+,d1
 moveq #0,d4
 move.w timing_mouse_elapsed(pc),d4
 muls.l d4,d1
 lea timing_mouse_carry(pc),a0
 move.w (a0,d2.w),d3
 ext.l d3
 add.l d3,d1
 move.l d1,d4
 divs.l #18,d1
 move.l d1,(a2)+
 muls.l #18,d1
 sub.l d1,d4
 move.l d4,d1
 lea timing_mouse_pending(pc),a0
 move.w d1,(a0,d2.w)
 addq.w #2,d2
 dbra d0,.scale
 lea timing_mouse_base(pc),a1
 lea timing_mouse_matrix_state(pc),a2
 moveq #8,d0
.base
 move.l (a1)+,(a2)+
 dbra d0,.base
 lea timing_mouse_state(pc),a0
 move.w #1,timing_mouse_active-timing_mouse_state(a0)
 bsr timing_mouse_matrix
 lea timing_mouse_matrix_state(pc),a1
 lea $3fa(a6),a2
 moveq #8,d0
.publish
 move.l (a1)+,d1
 add.l #8192,d1
 moveq #14,d2
 asr.l d2,d1
 move.w d1,(a2)+
 dbra d0,.publish
 lea timing_mouse_state(pc),a0
 clr.w timing_mouse_active-timing_mouse_state(a0)
 addq.l #1,timing_mouse_steps-timing_mouse_state(a0)
 bra.s .done
.native
 clr.w (a0)
 clr.w timing_mouse_elapsed-timing_mouse_state(a0)
 clr.l timing_mouse_carry-timing_mouse_state(a0)
 clr.w timing_mouse_carry+4-timing_mouse_state(a0)
 clr.l timing_mouse_pending-timing_mouse_state(a0)
 clr.w timing_mouse_pending+4-timing_mouse_state(a0)
 clr.w timing_mouse_active-timing_mouse_state(a0)
 bsr timing_mouse_native_roll
 bsr timing_mouse_native_yaw
 bsr timing_mouse_native_pitch
.done
 movem.l (sp)+,d0-d7/a0-a2
 bra.w timing_mouse_after_rotate

; Called after native candidate acceptance/rejection. Rejected candidates must
; not build a hidden angular backlog against a wall or pitch constraint.
timing_mouse_finish
 move.w ccr,-(sp)
 movem.l d0-d2/a0-a2,-(sp)
 lea timing_mouse_state(pc),a0
 tst.w (a0)
 beq.s .done
 lea $3e8(a6),a1
 lea $3fa(a6),a2
 moveq #8,d0
.compare
 cmpm.w (a1)+,(a2)+
 bne.s .rejected
 dbra d0,.compare
 bra.s .remember
.rejected
 clr.l timing_mouse_carry-timing_mouse_state(a0)
 clr.w timing_mouse_carry+4-timing_mouse_state(a0)
 clr.l timing_mouse_pending-timing_mouse_state(a0)
 clr.w timing_mouse_pending+4-timing_mouse_state(a0)
 clr.w timing_mouse_elapsed-timing_mouse_state(a0)
 lea $3e8(a6),a1
 lea timing_mouse_base(pc),a2
 moveq #8,d0
.copy
 move.w (a1)+,d1
 ext.l d1
 moveq #14,d2
 asl.l d2,d1
 move.l d1,(a2)+
 dbra d0,.copy
 lea timing_mouse_base(pc),a1
 lea timing_mouse_matrix_state(pc),a2
 moveq #8,d0
.copy_rejected
 move.l (a1)+,(a2)+
 dbra d0,.copy_rejected
.remember
 lea $3e8(a6),a1
 lea timing_mouse_expected(pc),a2
 moveq #8,d0
.copy_expected
 move.w (a1)+,(a2)+
 dbra d0,.copy_expected
.done
 movem.l (sp)+,d0-d2/a0-a2
 move.w (sp)+,ccr
 rts

; Rotate Q28 matrix rows using Q30 trigonometry. Signed 64-bit products
; retain precision before publishing rounded Q14 native state. Only the private
; mouse matrix uses these units; the renderer/game retain their native format.
timing_mouse_matrix
 move.l timing_mouse_angles+8(pc),d0
 beq.s .yaw
 bsr timing_mouse_trig
 lea timing_mouse_matrix_state(pc),a1
 lea 12(a1),a2
 bsr timing_mouse_pair
.yaw
 move.l timing_mouse_angles+4(pc),d0
 beq.s .pitch
 bsr timing_mouse_trig
 neg.l d1
 lea timing_mouse_matrix_state(pc),a1
 lea 24(a1),a2
 bsr timing_mouse_pair
.pitch
 move.l timing_mouse_angles(pc),d0
 beq.s .done
 bsr timing_mouse_trig
 lea timing_mouse_matrix_state+12(pc),a1
 lea 12(a1),a2
 bra.s timing_mouse_pair
.done
 rts

timing_mouse_pair
 moveq #2,d0
.column
 move.l d0,-(sp)
 move.l (a1),d4
 muls.l d2,d5:d4
 move.l (a2),d6
 muls.l d1,d7:d6
 sub.l d6,d4
 subx.l d7,d5
 moveq #30,d0
 lsr.l d0,d4
 asl.l #2,d5
 or.l d5,d4
 move.l d4,d3
 move.l (a1),d4
 muls.l d1,d5:d4
 move.l (a2),d6
 muls.l d2,d7:d6
 add.l d6,d4
 addx.l d7,d5
 lsr.l d0,d4
 asl.l #2,d5
 or.l d5,d4
 move.l d3,(a1)+
 move.l d4,(a2)+
 move.l (sp)+,d0
 dbra d0,.column
 rts

; Signed Q12 degrees -> Q30 sine/cosine. The mathematical quarter-wave table
; has 1/64-degree spacing; interpolate its remaining six fractional bits.
timing_mouse_trig
 movem.l d3-d5/a0,-(sp)
 move.l d0,d5
 bsr .lookup
 move.l d1,d4
 move.l d5,d0
 add.l #90*4096,d0
 bsr .lookup
 move.l d1,d2
 move.l d4,d1
 movem.l (sp)+,d3-d5/a0
 rts
.lookup
 ; Remainder is bounded even for extreme accumulated mouse coordinates.
 divsl.l #360*4096,d3:d0
 move.l d3,d0
 bpl.s .positive
 add.l #360*4096,d0
.positive
 moveq #1,d3
 cmp.l #180*4096,d0
 blo.s .half
 sub.l #180*4096,d0
 moveq #-1,d3
.half
 cmp.l #90*4096,d0
 bls.s .quarter
 neg.l d0
 add.l #180*4096,d0
.quarter
 move.l d3,-(sp)
 move.l d0,d3
 and.l #63,d3
 lsr.l #6,d0
 lsl.l #2,d0
 lea timing_mouse_sine(pc),a0
 move.l (a0,d0.l),d1
 tst.w d3
 beq.s .sign
 move.l 4(a0,d0.l),d0
 sub.l d1,d0
 muls.l d3,d0
 add.l #32,d0
 asr.l #6,d0
 add.l d0,d1
.sign
 move.l (sp)+,d3
 muls.l d3,d1
 rts

timing_mouse_native_trig dc.w $4ef9
 dc.l 0
timing_mouse_native_pitch dc.w $4ef9
 dc.l 0
timing_mouse_native_yaw dc.w $4ef9
 dc.l 0
timing_mouse_native_roll dc.w $4ef9
 dc.l 0
timing_mouse_after_rotate dc.w $4ef9
 dc.l 0
timing_mouse_candidate dc.w $4ef9
 dc.l 0

timing_mouse_tag dc.b 'PDMOUSE1'
timing_mouse_state
timing_mouse_ready dc.w 0
timing_mouse_active dc.w 0
timing_mouse_elapsed dc.w 0
timing_mouse_gain_x dc.w 0
timing_mouse_gain_y dc.w 0
timing_mouse_fraction_pitch dc.w 0
timing_mouse_fraction_yaw dc.w 0
timing_mouse_rates ds.l 3
timing_mouse_angles ds.l 3
timing_mouse_base ds.l 9
timing_mouse_expected ds.w 9
timing_mouse_matrix_state ds.l 9
timing_mouse_steps dc.l 0
timing_mouse_carry ds.w 3
timing_mouse_pending ds.w 3
timing_mouse_state_end

 machine 68000
