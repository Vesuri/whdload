; SPS 0481 opt-in native 68000 arithmetic. The coarse host owns binding,
; interrupt exclusion, patch rollback and cache flush. Physics remains 100 ms.
; Validate the complete original helper before replacing its entry point.
 IFD FF1_COARSE_020
 fail "FF1_COARSE_NATIVE_000 requires the 68000 coarse build"
 ENDC
FF1InstallNative000:
 movem.l d0-d2/a0-a1,-(sp)
 lea FF1Divide000Signature(pc),a0
 lea $293d0,a1
 moveq #32,d1
.check:
 move.w (a0)+,d2
 cmp.w (a1)+,d2
 bne.b .bad
 dbra d1,.check
 lea FF1Divide000(pc),a0
 move.w #$4ef9,$293d0
 move.l a0,$293d2
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
