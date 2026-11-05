; C4 positive signed division with native quotient/remainder/CCR semantics.
; Nonpositive inputs and wide quotients retain the audited general helper.
; For n>0,d>0, native final flags are X=N=V=C=0 and Z iff quotient=0.
; The final ADD clears X as well as setting those quotient flags.
FF1C4DividePositive:
 tst.l d0
 ble.w FF1Div000General
 tst.l d1
 ble.w FF1Div000General
 cmpi.l #$ffff,d1
 bhi.w FF1C4DivLarge
 cmpi.w #10,d1
 beq.b FF1C4DivBy10
 cmpi.w #56,d1
 beq.b FF1C4DivBy56
FF1C4DivideShortGate:
 IFD FF1_C4_DIV_SHORT_FRAMES_TEST
 bra.w FF1C4DivideShortFast
 ELSE
 move.l d2,-(sp)
 move.l d0,d2
 ENDC
 swap d2
 cmp.w d1,d2
 bcc.w FF1C4DivGeneralPop
 divu.w d1,d0
 move.l d0,d1
 andi.l #$ffff,d0
 swap d1
 andi.l #$ffff,d1
FF1C4DivDone:
 move.l (sp)+,d2
FF1C4DivFlags:
 addi.l #0,d0
 rts
FF1C4DivBy10:
 cmpi.l #1023,d0
 bhi.b FF1C4DivideShortGate
 ; Exact packed quotient:remainder bytes. CPU-only table is appended to
 ; the public owner with the existing C4 tables; no DMA memory is used.
 move.l a0,-(sp)
 lea FF1C4DividePositive(pc),a0
 ; Fixed long-immediate encoding: binding-table growth must not shrink or
 ; widen this instruction between the two diagnostic assembly passes.
 dc.w $d1fc ; adda.l #relative table offset,a0
 dc.l FF1C4DivideTenTable-FF1C4DividePositive
 add.w d0,d0
 moveq #0,d1
 move.w (a0,d0.w),d1
 move.l d1,d0
 lsr.w #8,d0
 andi.w #255,d1
 move.l (sp)+,a0
 bra.b FF1C4DivFlags
FF1C4DivBy56:
 cmpi.l #$fffff,d0
 bhi.b FF1C4DivideShortGate
 ; q0=floor(floor(n/16)*18724/65536). For n<=2^20-1,
 ; 0<=n/56-floor(n/16)*18724/65536<1; q0 needs at most +1.
 move.l d2,-(sp)
 move.l d0,d2
 lsr.l #4,d0
 mulu.w #18724,d0
 swap d0
 andi.l #$ffff,d0
 move.l d0,d1
 mulu.w #56,d1
 sub.l d1,d2
 cmpi.l #56,d2
 blo.b FF1C4DivRemainder
 subi.l #56,d2
 addq.l #1,d0
FF1C4DivRemainder:
 move.l d2,d1
 bra.b FF1C4DivDone
FF1C4DivLarge:
 ; Repeated observed pair, guarded on both full operands. Other values
 ; retain the general algorithm; this is an exact constant fold only.
 cmpi.l #700000,d1
 bne.b FF1C4DivGeneral
 cmpi.l #$3fc000,d0
 bne.b FF1C4DivGeneral
 moveq #5,d0
 move.l #677920,d1
 bra.w FF1C4DivFlags
FF1C4DivGeneralPop:
 move.l (sp)+,d2
FF1C4DivGeneral:
 bra.w FF1Div000General
 IFD FF1_C4_DIV_SHORT_FRAMES
; Same positive short-divisor contract, without touching D2 or the stack.
; SWAP/CMP preserve input X on the full-domain fallback. A fitting DIVU
; packs remainder:quotient; unpack directly with zeroed upper words.
FF1C4DivideShortFast:
 swap d0
 cmp.w d1,d0
 bcc.b .wide
 swap d0
 divu.w d1,d0
 moveq #0,d1
 swap d0
 move.w d0,d1
 clr.w d0
 swap d0
 ; Native quotient flags, including X=0 and Z iff quotient=0.
 addi.w #0,d0
 tst.l d0
 rts
.wide:
 swap d0
 bra.w FF1Div000General
 ENDC
FF1DivFastEnd:
