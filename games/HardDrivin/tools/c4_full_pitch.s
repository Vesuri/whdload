
_private_full_contact_reset:
 bsr _contact_reset
 move.l a0,-(a7)
 lea _motion_state(pc),a0
 clr.l MS_ROLL(a0)
 movea.l (a7)+,a0
 clr.w -$66ea(a4)
 clr.w -$66ec(a4)
 rts
_private_full_contact_pitch:
 movem.l d1-d4/a0-a2,-(a7)
 move.w _time_scalar_fields(pc),d1
 cmpi.w #8,d1
 bne.s .scaled
 neg.w d0
 asr.w #1,d0
 move.w d0,-(a7)
 movea.l _motion_pitch_function(pc),a0
 jsr (a0)
 addq.w #2,a7
 bra.s .done
.scaled:
 neg.w d0
 move.w d0,d4
 cmpi.w #136,d1
 bhs.s .full
 add.w d1,d1
 lea _private_half_gain(pc),a0
 move.w (a0,d1.w),d1
 tst.w d0
 bpl.s .positive
 neg.w d0
.positive:
 mulu.w d1,d0
 tst.w d4
 bpl.s .project
 neg.l d0
 bra.s .project
.full:
 swap d0
 clr.w d0
.project:
 bsr _contact_pitch_projection
 lea _motion_state+MS_PITCH(pc),a0
 lea -$66b4(a4),a1
 bsr _contact_add_angle
.done:
 movem.l (a7)+,d1-d4/a0-a2
 rts
