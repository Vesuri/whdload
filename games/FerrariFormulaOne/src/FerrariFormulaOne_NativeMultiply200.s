; Exact low-32 native product for the experimental complete 200 ms build.
; Preserve the original $29500 ABI, including D1-D4 and its unusual XNZVC.
; Host transaction owns resident-hunk restoration and cache flushing.
FF1InstallMultiplyNative200:
 lea FF1MultiplyNative200Signature(pc),a0
 lea $29500,a1
 moveq #32,d0
.check:
 move.w (a0)+,d1
 cmp.w (a1)+,d1
 bne.w C1Fault
 dbra d0,.check
 IFD FF1_NATIVEMUL200_AB
 move.w FF1NativeMul200Control(pc),-(sp)
 tst.w (sp)+
 bne.b .done
 ENDC
 lea FF1MultiplyNative200(pc),a0
 move.w #$4ef9,$29500
 move.l a0,$29502
.done:
 rts

FF1MultiplyNative200:
 movem.l d1-d4,-(sp)
 move.l d0,d4
 eor.l d1,d4
 tst.l d0
 beq.b .done
 bpl.b .a_positive
 neg.l d0
.a_positive:
 move.l d0,d2
 tst.l d1
 bne.b .b_nonzero
 clr.l d0
 bra.b .done
.b_nonzero:
 bpl.b .b_positive
 neg.l d1
.b_positive:
 ; Always form the low-word product. Omit a cross product only when its
 ; high-word operand is zero; the native final addition still owns X.
 move.l d0,d3
 mulu.w d1,d3
 swap d2
 tst.w d2
 beq.b .a_high_zero
 mulu.w d1,d2
 swap d2
 clr.w d2
 add.l d2,d3
.a_high_zero:
 swap d1
 tst.w d1
 beq.b .b_high_zero
 mulu.w d1,d0
 swap d0
 clr.w d0
 add.l d3,d0
 bra.b .sign
.b_high_zero:
 ; Native B.high product is zero. ADD, rather than MOVE, must clear X.
 moveq #0,d0
 add.l d3,d0
.sign:
 tst.l d4
 bpl.b .done
 neg.l d0
.done:
 movem.l (sp)+,d1-d4
 rts
 IFD FF1_NATIVEMUL200_AB
FF1NativeMul200Control: dc.w 0
 ENDC
FF1MultiplyNative200Signature:
 dc.b $48,$e7,$78,$00,$28,$00,$b3,$84,$4a,$80,$67,$30,$6a,$02,$44,$80,$24,$00,$4a,$81,$66,$04,$42,$80,$60,$22,$6a,$02,$44,$81,$26,$00,$c6,$c1,$48,$42,$c4,$c1,$48,$42,$42,$42,$d6,$82,$48,$41,$c0,$c1,$48,$40,$42,$40,$d0,$83,$4a,$84,$6a,$02,$44,$80,$4c,$df,$00,$1e,$4e,$75
