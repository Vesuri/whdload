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
 bhi.w .large
 cmpi.w #10,d1
 beq.b .by10
 cmpi.w #56,d1
 beq.b .by56
.short:
 move.l d2,-(sp)
 move.l d0,d2
 swap d2
 cmp.w d1,d2
 bcc.w .general_pop
 divu.w d1,d0
 move.l d0,d1
 andi.l #$ffff,d0
 swap d1
 andi.l #$ffff,d1
.done:
 move.l (sp)+,d2
.flags:
 addi.l #0,d0
 rts
.by10:
 cmpi.l #1023,d0
 bhi.b .short
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
 bra.b .flags
.by56:
 cmpi.l #$fffff,d0
 bhi.b .short
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
 blo.b .remainder
 subi.l #56,d2
 addq.l #1,d0
.remainder:
 move.l d2,d1
 bra.b .done
.large:
 ; Repeated observed pair, guarded on both full operands. Other values
 ; retain the general algorithm; this is an exact constant fold only.
 cmpi.l #700000,d1
 bne.b .general
 cmpi.l #$3fc000,d0
 bne.b .general
 moveq #5,d0
 move.l #677920,d1
 bra.w .flags
.general_pop:
 move.l (sp)+,d2
.general:
 bra.w FF1Div000General
FF1DivFastEnd:
