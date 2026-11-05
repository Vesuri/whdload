; Private impact gate after full/diagonal contact response. Native zero/eight
; and forced-native modes preserve original CC8A TST/BNE exactly.
_private_landing_impact:
 movem.l d0/a0,-(a7)
 IFND VERIFY_DISPATCH_NATIVE
 move.w _time_scalar_fields(pc),d0
 beq.s .native
 cmpi.w #8,d0
 beq.s .native
 tst.b -$69fa(a4)
 bne.s .native
 cmpi.w #50,-$66f2(a4)
 ble.s .native
 ; Return into the existing native hard-impact action. Its return path reaches
 ; this hook again with crash=25, then continues to the original fall reset.
 movea.l 8(a7),a0
 lea -$46(a0),a0
 move.l a0,8(a7)
 movem.l (a7)+,d0/a0
 rts
 ENDC
.native:
 movem.l (a7)+,d0/a0
 bra _motion_fall_ground
