
; Private full-contact fallback: use the selected road plane's angle only
; where the native wheel-height arcsine is outside its defined domain.
_private_road_pitch:
 move.w _time_scalar_fields(pc),d1
 cmpi.w #8,d1
 beq.s .native
 move.w 4(a7),d0
 cmpi.w #180,d0
 bgt.s .plane
 cmpi.w #-180,d0
 bge.s .native
.plane:
 movea.l -$671c(a4),a0
 move.w -$66b4(a4),d0
 sub.w 14(a0),d0
 cmpi.w #720,d0
 ble.s .negative
 subi.w #1440,d0
.negative:
 cmpi.w #-720,d0
 bge.s .return
 addi.w #1440,d0
 bra.s .return
.native:
 move.w 6(a7),-(a7)
 move.w 6(a7),-(a7)
 jsr -$7f20(a4)
 addq.w #4,a7
.return:
 move.l (a7),4(a7)
 addq.w #4,a7
 rts
