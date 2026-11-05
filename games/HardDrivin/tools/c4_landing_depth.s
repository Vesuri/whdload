; Retain native zero/eight-field penetration test. Other intervals use contact
; below the surface rather than frame-dependent overshoot to reach fall>50 test.
_private_landing_depth:
 move.l d0,-(a7)
 move.w _time_scalar_fields(pc),d0
 beq.s .native
 cmpi.w #8,d0
 beq.s .native
 move.l (a7)+,d0
 cmpi.w #0,-8(a5)
 rts
.native:
 move.l (a7)+,d0
 cmpi.w #-5,-8(a5)
 rts
