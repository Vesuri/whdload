; 68000 200 ms position/frame primitives. A0 -> {X Q16.l,Z Q16.l}.
; No rational carry: the selected/native interval ratio is exactly two.
; FF1VelocityApply200 performs checked displacement integration on this layout.
; Host owns per-car loads/stores, clamping/contact/save/reset and segment loops.
; These helpers do not install hooks. All state must use public memory.
;
; After native integer frame rotation, rotate only the old fractional tails
; and add them to the native integer answers D2.w/D3.w. D0.w cosine, D1.w sine
; are signed Q15 coefficients. This preserves native integer product rounding
; exactly when tails are zero, including native signed-word wrap semantics.
; D1=0/-1, all other registers preserved; failure leaves both axes unchanged.
FF1PositionRotate200:
 movem.l d0/d2-d5/a1,-(sp)
 suba.w #8,sp
 move.l a0,a1
 moveq #0,d4
 move.w 2(a0),d4
 move.l d4,(sp)
 move.w 6(a0),d4
 move.l d4,4(sp)
 move.l sp,a0
 bsr.w FF1VelocityRotate000
 tst.l d1
 bne.b .done
 swap d2
 clr.w d2
 add.l (sp),d2
 bvs.b .bad
 swap d3
 clr.w d3
 add.l 4(sp),d3
 bvs.b .bad
 move.l d2,(a1)
 move.l d3,4(a1)
 bra.b .done
.bad:
 moveq #-1,d1
.done:
 move.l a1,a0
 addq.l #8,sp
 movem.l (sp)+,d0/d2-d5/a1
 rts

; Continuous segment-plane predicate: X*S/C + Z >= 512.
; D0.w native sin(angle,1000), D1.w native cos(angle,1000).
; D0=0/1, D1=0 or -1 for undefined C=0. No state changes; other regs preserved.
; Full signed Q16 coordinates and signed-word coefficients. Compare in signed
; 64 bits and reverse inequality for C<0, without rounded intermediate division.
FF1PositionCrossed000:
 IFD FF1_CROSS200_AB
 move.w FF1Cross200Control(pc),-(sp)
 tst.w (sp)+
 bne.b .general
 ENDC
 ; For S=0 and C!=0, X*S/C+Z>=512 is exactly Z>=512, even
 ; when C is negative. Compare signed Q16 directly without any products.
 tst.w d1
 beq.b .general
 tst.w d0
 bne.b .general
 moveq #0,d0
 cmpi.l #512*65536,4(a0)
 sge d0
 andi.w #1,d0
 moveq #0,d1
 rts
.general:
 movem.l d2-d7,-(sp)
 move.w d1,d2
 ext.l d2
 beq.w .undefined
 move.w d0,d1
 ext.l d1
 move.l (a0),d0
 bsr.w FF1MultiplyS32x16_000
 move.l d0,d3
 move.l d1,d4
 move.l 4(a0),d0
 move.l d2,d1
 bsr.w FF1MultiplyS32x16_000
 add.l d0,d3
 addx.l d1,d4
 move.l #512*65536,d0
 move.l d2,d1
 bsr.w FF1MultiplyS32x16_000
 sub.l d0,d3
 subx.l d1,d4
 moveq #0,d0
 tst.l d2
 bmi.b .negative_cos
 tst.l d4
 bmi.b .okay
 bra.b .yes
.negative_cos:
 tst.l d4
 bmi.b .yes
 bne.b .okay
 tst.l d3
 bne.b .okay
.yes:
 moveq #1,d0
.okay:
 moveq #0,d1
 bra.b .done
.undefined:
 moveq #0,d0
 moveq #-1,d1
.done:
 movem.l (sp)+,d2-d7
 rts

; Native Q12 heading at A0, continuous native 100 ms delta in D0.l.
; Two modular additions preserve the original angular storage/wrap semantics;
; coordinate-frame adjustments and collision impulses must not use this entry.
; Registers preserved, CCR scratch.
FF1Heading200:
 add.l d0,(a0)
 add.l d0,(a0)
 rts

 IFD FF1_CROSS200_AB
FF1Cross200Control: dc.w 0
 ENDC
