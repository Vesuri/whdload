; Optional C4 native low-32 multiply, preserving D1-D7/A0-A6
; and original XNZVC, with no saved-register frame on guarded word inputs.
; All guards preserve incoming X for native zero-input semantics.
FF1NativeFrameFast:
 cmpi.l #$ffff,d0
 bhi.b .a_not_unsigned
 cmpi.l #$ffff,d1
 bhi.b .b_not_unsigned
 ; Both operands are unsigned words. Native reports input-XOR flags, not
 ; product flags; equal operands therefore report Z even for a nonzero square.
 tst.l d0
 beq.b .done
 tst.l d1
 beq.b .unsigned_zero
 cmp.l d1,d0
 beq.b .unsigned_equal
 mulu.w d1,d0
 addi.l #0,d0
 tst.l d1
.done:
 rts
.unsigned_equal:
 mulu.w d1,d0
 addi.l #0,d0
 cmp.l d1,d1
 rts
.unsigned_zero:
 clr.l d0
 rts
.b_not_unsigned:
 ; The measured wide case is exactly eight times a positive long. The last
 ; native cross-product addition cannot carry: its high-word terms are a
 ; multiple of eight plus a value <=7. Preserve native X=0 and XOR N=Z=0.
 cmpi.l #8,d0
 bne.b .try_signed_b
 tst.l d1
 bmi.b .try_signed_b
 move.l d1,d0
 lsl.l #3,d0
 addi.l #0,d0
 tst.l d1
 rts
.try_signed_b:
 tst.w d0
 bmi.b .fallback
 cmpi.l #$ffff8000,d1
 bcc.b .signed
 bra.b .fallback
.a_not_unsigned:
 cmpi.l #$ffff8000,d0
 blo.b .fallback
 cmpi.l #32767,d1
 bls.b .signed
 cmpi.l #$ffff8000,d1
 blo.b .fallback
.signed:
 ; Both full operands have been guarded as signed words.
 tst.l d0
 beq.b .done
 tst.l d1
 beq.b .signed_zero
 cmp.l d1,d0
 beq.b .signed_equal
 muls.w d1,d0
 bmi.b .negative
 addi.l #0,d0
 rts
.signed_equal:
 muls.w d1,d0
 addi.l #0,d0
 cmp.l d1,d1
 rts
.negative:
 ; Exact nonzero negative product, strictly inside signed-32 range. Two
 ; negations retain the product while reproducing native NEG's X=N=C=1.
 neg.l d0
 neg.l d0
 rts
.signed_zero:
 ; Here B=0 implies A is negative: nonnegative A used the unsigned path.
 neg.l d0
 clr.l d0
 rts
.fallback:
 bra.w FF1NativeFrameControl
