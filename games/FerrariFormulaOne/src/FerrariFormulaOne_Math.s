; Ferrari Formula One: candidate exact-output signed long division helpers.
; Not yet installed by the slave. Runtime integration must qualify the game
; version, choose the CPU entry point and flush instruction caches after patching.
;
; Input D0 dividend, D1 divisor. Output D0 quotient, D1 remainder. D2-D5 and
; all other registers preserved. Preserve the original routine's zero-divisor,
; INT_MIN/-1 wrap and condition-code behavior, including its sign-restoration
; flags (which are not simply flags for the returned quotient).
;
; Default includes both CPU entries. Define FF1_MATH_000_ONLY for a pure
; 68000 build; FF1Divide000 and its shared suffix use only 68000 instructions.
FF1Divide000:
        movem.l d2-d5,-(sp)
        move.l  d1,d5
        beq.w   FF1DivZeroDivisor
        bpl.b   .positive_divisor
        neg.l   d1
.positive_divisor:
        move.l  d0,d4
        beq.w   FF1DivZeroNumerator
        bpl.b   .positive_numerator
        neg.l   d0
.positive_numerator:
        cmpi.l  #$ffff,d1
        bhi.b   .long_divisor
        move.l  d0,d2
        swap    d2
        andi.l  #$ffff,d2
        cmp.w   d1,d2
        bcc.b   .two_parts
        divu.w  d1,d0
        move.l  d0,d2
        andi.l  #$ffff,d0
        swap    d2
        andi.l  #$ffff,d2
        bra.b   FF1DivRestore
.two_parts:
        ; high16/divisor cannot overflow; remainder < divisor makes the
        ; following remainder:low16 division safe as well.
        divu.w  d1,d2
        move.w  d2,d3
        move.w  d0,d2
        divu.w  d1,d2
        move.w  d3,d0
        swap    d0
        move.w  d2,d0
        swap    d2
        andi.l  #$ffff,d2
        bra.b   FF1DivRestore
.long_divisor:
        ; General unsigned restoring division, retaining the native result.
        clr.l   d2
        moveq   #31,d3
.bit:   asl.l   #1,d0
        roxl.l  #1,d2
        cmp.l   d1,d2
        bcs.b   .next
        sub.l   d1,d2
        addq.l  #1,d0
.next:  dbra    d3,.bit
        bra.b   FF1DivRestore

        ifnd FF1_MATH_000_ONLY
FF1Divide020:
        movem.l d2-d5,-(sp)
        move.l  d1,d5
        beq.b   FF1DivZeroDivisor
        bpl.b   .positive_divisor
        neg.l   d1
.positive_divisor:
        move.l  d0,d4
        beq.b   FF1DivZeroNumerator
        bpl.b   .positive_numerator
        neg.l   d0
.positive_numerator:
        divul.l d1,d2:d0
        endc
FF1DivRestore:
        ; The native normalized 32-pass loop leaves X clear. DIVU does not
        ; define it, so restore it explicitly before the native sign suffix.
        andi    #$ef,ccr
        move.l  d2,d1
        eor.l   d4,d5
        bpl.b   .positive_quotient
        neg.l   d0
.positive_quotient:
        eor.l   d1,d4
        bpl.b   FF1DivDone
        neg.l   d1
        bra.b   FF1DivDone
FF1DivZeroNumerator:
        clr.l   d1
FF1DivZeroDivisor:
        clr.l   d0
FF1DivDone:
        movem.l (sp)+,d2-d5
        rts
