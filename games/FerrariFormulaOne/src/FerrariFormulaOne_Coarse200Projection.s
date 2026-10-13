; Complete C4 only: skip integer projection replaced by velocity_project.
; Requires both existing response and return bypasses. Between this block
; and velocity_returned, the native projected globals and -4/-6 locals have
; no consumers; the conversion owns projection and overwrites velocity globals.
; Existing transaction restores the complete native hunk on exit/unload.
FF1Coarse200ProjectionSkip:
 move.w C4ResponseSkipEnabled(pc),-(sp)
 tst.w (sp)+
 beq.w .done
 move.w C4ReturnSkipEnabled(pc),-(sp)
 tst.w (sp)+
 beq.w .done
 cmpi.w #$322e,$6dc52
 bne.w C1Fault
 cmpi.w #$000a,$6dc54
 bne.w C1Fault
 cmpi.w #$48c1,$6dc56
 bne.w C1Fault
 cmpi.w #$342e,$6dc58
 bne.w C1Fault
 cmpi.w #$000e,$6dc5a
 bne.w C1Fault
 cmpi.w #$48c2,$6dc5c
 bne.w C1Fault
 cmpi.w #$2f02,$6dc5e
 bne.w C1Fault
 cmpi.w #$2f01,$6dc60
 bne.w C1Fault
 cmpi.w #$3d40,$6dc62
 bne.w C1Fault
 cmpi.w #$fffa,$6dc64
 bne.w C1Fault
 cmpi.w #$3d40,$6dc66
 bne.w C1Fault
 cmpi.w #$fffc,$6dc68
 bne.w C1Fault
 cmpi.w #$4eb9,$6dc6a
 bne.w C1Fault
 cmpi.w #$0002,$6dc6c
 bne.w C1Fault
 cmpi.w #$4fe0,$6dc6e
 bne.w C1Fault
 cmpi.w #$508f,$6dc70
 bne.w C1Fault
 cmpi.w #$33c0,$6dc72
 bne.w C1Fault
 cmpi.w #$0003,$6dc74
 bne.w C1Fault
 cmpi.w #$2f94,$6dc76
 bne.w C1Fault
 cmpi.w #$302e,$6dc78
 bne.w C1Fault
 cmpi.w #$000a,$6dc7a
 bne.w C1Fault
 cmpi.w #$48c0,$6dc7c
 bne.w C1Fault
 cmpi.w #$322e,$6dc7e
 bne.w C1Fault
 cmpi.w #$000e,$6dc80
 bne.w C1Fault
 cmpi.w #$48c1,$6dc82
 bne.w C1Fault
 cmpi.w #$2f01,$6dc84
 bne.w C1Fault
 cmpi.w #$2f00,$6dc86
 bne.w C1Fault
 cmpi.w #$4eb9,$6dc88
 bne.w C1Fault
 cmpi.w #$0002,$6dc8a
 bne.w C1Fault
 cmpi.w #$5000,$6dc8c
 bne.w C1Fault
 cmpi.w #$508f,$6dc8e
 bne.w C1Fault
 cmpi.w #$33c0,$6dc90
 bne.w C1Fault
 cmpi.w #$0003,$6dc92
 bne.w C1Fault
 cmpi.w #$2f96,$6dc94
 bne.w C1Fault
 move.w C4ProjectionSkipEnabled(pc),-(sp)
 tst.w (sp)+
 beq.b .done
 move.w #$6000,$6dc52
 move.w #$0042,$6dc54
.done:
 rts
C4ProjectionSkipEnabled: dc.w 1
