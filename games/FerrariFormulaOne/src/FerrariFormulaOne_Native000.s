; SPS 0481 opt-in native 68000 arithmetic. The coarse host owns binding,
; interrupt exclusion, patch rollback and cache flush. Physics remains 100 ms.
; Validate the complete original helper before replacing its entry point.
 IFD FF1_COARSE_020
 fail "FF1_COARSE_NATIVE_000 requires the 68000 coarse build"
 ENDC
 IFND FF1_NATIVE_000_STAGE
FF1_NATIVE_000_STAGE equ 1
 ENDC
FF1InstallNative000:
 movem.l d0-d2/a0-a1,-(sp)
 lea FF1Divide000Signature(pc),a0
 lea $293d0,a1
 moveq #32,d1
.check:
 move.w (a0)+,d2
 cmp.w (a1)+,d2
 bne.w .bad
 dbra d1,.check
 IFGT FF1_NATIVE_000_STAGE-1
 move.w C3Enabled(pc),d0
 cmpi.w #2,d0
 blo.b .track_checked
 lea FF1Track000Signature(pc),a0
 lea $6977a,a1
 move.w #136,d1
.track_check:
 move.w (a0)+,d2
 cmp.w (a1)+,d2
 bne.w .bad
 dbra d1,.track_check
 lea $67514,a1
 moveq #10,d1
.caller_check:
 move.w (a0)+,d2
 cmp.w (a1)+,d2
 bne.w .bad
 dbra d1,.caller_check
.track_checked:
 ENDC
 lea FF1Divide000(pc),a0
 move.w #$4ef9,$293d0
 move.l a0,$293d2
 IFGT FF1_NATIVE_000_STAGE-1
 move.w C3Enabled(pc),d0
 cmpi.w #2,d0
 blo.b .done
 lea FF1Lookahead000(pc),a0
 move.w #$4ef9,$6977a
 move.l a0,$6977c
 move.w #$4e71,$69780
 ENDC
 bra.b .done
.bad:
 lea error(pc),a0
 move.l #40,(a0)
.done:
 movem.l (sp)+,d0-d2/a0-a1
 rts
FF1_MATH_000_ONLY equ 1
 include "FerrariFormulaOne_Math.s"
FF1Divide000Signature:
 dc.b $48,$e7,$3c,$00,$2a,$01,$67,$32,$6a,$02,$44,$81,$28,$00,$67,$28,$6a,$02,$44,$80,$42,$82,$76,$1f,$e3,$80,$e3,$92,$b4,$81,$65,$04,$94,$81,$52,$80,$51,$cb,$ff,$f2,$22,$02,$b9,$85,$6a,$02,$44,$80,$b3,$84,$6a,$08,$44,$81,$60,$04,$42,$81,$42,$80,$4c,$df,$00,$3c,$4e,$75

 IFGT FF1_NATIVE_000_STAGE-1
; Sole native caller $67514 consumes D0 and overwrites D1/A0 and XNZVC
; before use, as audited for B6. Argument-slot mutation is dead there.
FF1Lookahead000:
 tst.w $1ed8a
 bne.b .native
 moveq #0,d1
 move.w $2268c,d1
 cmpi.w #12,d1
 blo.b .native
 ; At count 32767 the last segment +2 wraps the native signed word.
 ; Keep native behavior for that whole boundary domain.
 cmpi.w #32766,d1
 bhi.b .native
 move.w 6(sp),d0
 ext.l d0
 bmi.b .native
 cmp.l d1,d0
 bhs.b .native
 lea $1dc24,a0
 bra.w FF1TrackLookaheadNormal
.native:
 link a6,#-8
 clr.l -6(a6)
 jmp $69782
 include "FerrariFormulaOne_Track.s"
FF1Track000Signature:
 dc.w $4e56,$fff8,$42ae,$fffa,$4a79,$0001,$ed8a,$665c,$3d7c,$000a,$fffe,$546e,$000a,$302e,$fffe,$536e,$fffe,$4a40,$6730,$3039,$0002,$268c,$322e,$000a,$b240,$6d04,$916e,$000a,$302e,$000a,$526e,$000a,$48c0,$e380,$2040,$d1fc,$0001,$dc24,$3010,$48c0,$d1ae,$fffa,$60c4,$4aae,$fffa,$6a08,$202e,$fffa,$4480,$6004,$202e,$fffa,$4e5e,$4e75,$3d7c,$0008,$fffe,$3039,$0003,$2fbc,$48c0,$e380,$2040,$d1fc,$0002,$275a,$3010,$0c40,$015e,$6f04,$586e,$000a,$302e,$fffe,$536e,$fffe,$4a40,$676c,$3039,$0002,$268c,$322e,$000a,$b240,$6d04,$916e,$000a,$302e,$000a,$3f40,$0000,$5240,$322f,$0000,$48c1,$e381,$2041,$d1fc,$0001,$dc24,$3210,$3d40,$000a,$4a41,$6a18,$526e,$000a,$48c0,$e380,$2040,$d1fc,$0001,$dc24,$3010,$48c0,$4480,$6018,$302e,$000a,$526e,$000a,$48c0,$e380,$2040,$d1fc,$0001,$dc24,$3010,$48c0,$d1ae,$fffa,$6088,$202e,$fffa,$e380,$4e5e,$4e75
 dc.w $6100,$2264,$588f,$23c0,$0003,$2f8a,$3039,$0003,$2fbc,$48c0,$e380

 ENDC
