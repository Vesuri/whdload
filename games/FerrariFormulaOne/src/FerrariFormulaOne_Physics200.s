; Checked arithmetic for the 68000 200 ms candidate. Not installed by itself.
; Velocities remain Q16 displacement per native 100 ms. Integer interval ratio
; two needs no /5 carries. Keep independent current/history/position vectors.
; Caller owns clamps, impulses, frame changes, input/event cadence and lifetime.
; All storage is CPU-only/public. Requires FerrariFormulaOne_Wide000.s.
;
; A0 old and A1 new Q16 vectors; A2 output normalized native-reference change.
; Output=floor((new-old)/2), componentwise. Full signed difference before shift;
; error <1 Q16 unit per component. Output may alias either input.
; D1=0; all other registers preserved, CCR scratch.
FF1VelocityDerivative200:
 movem.l d0/d2-d5,-(sp)
 move.l (a1),d0
 move.l (a0),d2
 bsr.b FF1DifferenceHalf200
 move.l d0,d5
 move.l 4(a1),d0
 move.l 4(a0),d2
 bsr.b FF1DifferenceHalf200
 move.l d5,(a2)
 move.l d0,4(a2)
 moveq #0,d1
 movem.l (sp)+,d0/d2-d5
 rts
FF1DifferenceHalf200:
 move.l d0,d3
 move.l d2,d4
 moveq #31,d1
 asr.l d1,d3
 asr.l d1,d4
 sub.l d2,d0
 subx.l d4,d3
 asr.l #1,d3
 roxr.l #1,d0
 rts

; A0 current Q16 vector, A1 continuous native-reference response vector.
; current += 2*response, both axes atomically. May alias. D1=0/-1 success/error;
; other registers preserved, CCR scratch. Overflow leaves all state unchanged.
; Also suitable for position integration with a physical velocity at A1.
FF1VelocityApply200:
 movem.l d0/d2-d3,-(sp)
 move.l (a1),d0
 add.l d0,d0
 bvs.b .bad
 add.l (a0),d0
 bvs.b .bad
 move.l 4(a1),d2
 add.l d2,d2
 bvs.b .bad
 add.l 4(a0),d2
 bvs.b .bad
 move.l d0,(a0)
 move.l d2,4(a0)
 moveq #0,d1
 bra.b .done
.bad:
 moveq #-1,d1
.done:
 movem.l (sp)+,d0/d2-d3
 rts

; A0 vector, D0.w cosine and D1.w sine (signed Q15 table coefficients).
; (X,Z) -> floor((X*C-Z*S, X*S+Z*C)/32768). Atomic signed Q16 range check.
; D1=0/-1; every other register preserved, CCR scratch. Current AND history
; must be rotated by the caller at a segment change; no impulse scaling here.
FF1VelocityRotate000:
 movem.l d0/d2-d7,-(sp)
 suba.w #4,sp
 IFD FF1_C4_MUL_INLINE
 move.w FF1MulInlineControl(pc),d6
 beq.w .p2_rotate
 ENDC
 move.w d0,d2
 ext.l d2
 move.w d1,d3
 ext.l d3
 move.l (a0),d0
 move.l d2,d1
 bsr.w FF1MultiplyS32x16_000
 move.l d0,d4
 move.l d1,d5
 move.l 4(a0),d0
 move.l d3,d1
 bsr.w FF1MultiplyS32x16_000
 sub.l d0,d4
 subx.l d1,d5
 bsr.w FF1Q15Product000
 tst.l d1
 bne.b .done
 move.l d4,(sp)
 move.l (a0),d0
 move.l d3,d1
 bsr.w FF1MultiplyS32x16_000
 move.l d0,d4
 move.l d1,d5
 move.l 4(a0),d0
 move.l d2,d1
 bsr.w FF1MultiplyS32x16_000
 add.l d0,d4
 addx.l d1,d5
 bsr.w FF1Q15Product000
 tst.l d1
 bne.b .done
 move.l d4,4(a0)
 move.l (sp),(a0)
.done:
 addq.l #4,sp
 movem.l (sp)+,d0/d2-d7
 rts

 IFD FF1_C4_MUL_INLINE
 include "FerrariFormulaOne_Coarse200MulInline.s"
 ENDC

; Internal signed D5:D4 >>15 to D4. D1 status, D5/D6 scratch.
; After doubling, the upper long must fit a signed word. The low word of
; that upper long then supplies result bits 31..16 (all MC68000 instructions).
FF1Q15Product000:
 add.l d4,d4
 addx.l d5,d5
 bvs.b .bad
 move.w d5,d6
 ext.l d6
 cmp.l d5,d6
 bne.b .bad
 swap d4
 swap d5
 move.w d4,d5
 move.l d5,d4
 moveq #0,d1
 rts
.bad:
 moveq #-1,d1
 rts

; D0 Q16 speed, D1.w sine, D2.w cosine; A0 output Q16 vector.
; Projection keeps native coefficient quantization. Atomic on overflow.
; D1=0/-1, all other registers preserved, CCR scratch.
FF1VelocityProject000:
 movem.l d0/d2-d7,-(sp)
 suba.w #4,sp
 move.l d0,d7
 ext.l d1
 move.w d2,d3
 ext.l d3
 bsr.w FF1MultiplyS32x16_000
 move.l d0,d4
 move.l d1,d5
 bsr.b FF1Q15Product000
 tst.l d1
 bne.b .done
 move.l d4,(sp)
 move.l d7,d0
 move.l d3,d1
 bsr.w FF1MultiplyS32x16_000
 move.l d0,d4
 move.l d1,d5
 bsr.w FF1Q15Product000
 tst.l d1
 bne.b .done
 move.l (sp),(a0)
 move.l d4,4(a0)
.done:
 addq.l #4,sp
 movem.l (sp)+,d0/d2-d7
 rts

; A0 Q16 velocity vector, A1 output Q16 scalar (four bytes).
; Exact floor magnitude in Q16 units; below 4 ->0, above 500 ->500.
; Caller clears the physical vector when zero is returned. No /5 remainder.
; D1=0; other registers preserved, CCR scratch. Full signed input domain.
FF1SpeedFromVelocity000:
 movem.l d0/d2-d5,-(sp)
 move.l (a0),d0
 move.l d0,d1
 bsr.w FF1MultiplyS64_000
 move.l d0,d2
 move.l d1,d3
 move.l 4(a0),d0
 move.l d0,d1
 bsr.w FF1MultiplyS64_000
 add.l d2,d0
 addx.l d3,d1
 bsr.w FF1SquareRootU64_000
 cmpi.l #4*65536,d0
 blo.b .stop
 cmpi.l #500*65536,d0
 bls.b .store
 move.l #500*65536,d0
 bra.b .store
.stop:
 moveq #0,d0
.store:
 move.l d0,(a1)
 moveq #0,d1
 movem.l (sp)+,d0/d2-d5
 rts

; A0 Q16 scalar in [0,500], D0.l native integer proposal in signed-word range.
; Apply twice (proposal-floor(current)); clamp [0,500]. Do the bounded integer
; calculation first, retaining the old fractional word until a bound is hit.
; D1=0/-1, D0 scratch, other registers preserved. Error leaves state unchanged.
FF1SpeedRate200:
 moveq #2,d1
; Same operation with D1.w eligible native pulses (0..2). Used only for rates
; suppressed by the native modulo-four engine phase. Other rates use two.
FF1SpeedRatePulses200:
 movem.l d2-d3,-(sp)
 cmpi.w #2,d1
 bhi.b .bad
 cmpi.l #500*65536,(a0)
 bhi.b .bad
 cmpi.l #-32768,d0
 blt.b .bad
 cmpi.l #32767,d0
 bgt.b .bad
 moveq #0,d2
 move.w (a0),d2
 sub.l d2,d0
 tst.w d1
 beq.b .keep
 subq.w #1,d1
 beq.b .once
 add.l d0,d0
.once:
 add.l d2,d0
 bmi.b .zero
 cmpi.l #500,d0
 bge.b .cap
 swap d0
 move.w 2(a0),d0
 bra.b .store
.cap:
 move.l #500*65536,d0
 bra.b .store
.zero:
 moveq #0,d0
 bra.b .store
.keep:
 move.l (a0),d0
.store:
 move.l d0,(a0)
 moveq #0,d1
 bra.b .done
.bad:
 moveq #-1,d1
.done:
 movem.l (sp)+,d2-d3
 rts

; D0.w last phase of this 200 ms window (0..3), D1.w native engine setting.
; Return D0.l number of eligible phases among (last-1 mod4,last), or -1 for
; invalid phase. Setting 4 suppresses phase 0, setting 5 suppresses 0 and 1.
; Other settings allow both. D1-D7/A0-A6 preserved, CCR scratch. This avoids
; duty-cycle aliasing when the outer modulo-four phase advances by two.
FF1PhasePulses200:
 movem.l d2-d4,-(sp)
 cmpi.w #3,d0
 bhi.b .bad
 moveq #15,d2
 cmpi.w #4,d1
 bne.b .five
 moveq #14,d2
 bra.b .count
.five:
 cmpi.w #5,d1
 bne.b .count
 moveq #12,d2
.count:
 moveq #0,d3
 btst d0,d2
 beq.b .previous
 addq.l #1,d3
.previous:
 move.w d0,d4
 subq.w #1,d4
 andi.w #3,d4
 btst d4,d2
 beq.b .answer
 addq.l #1,d3
.answer:
 move.l d3,d0
 bra.b .done
.bad:
 moveq #-1,d0
.done:
 movem.l (sp)+,d2-d4
 rts

; D0.l nonnegative native continuous loss, A0 -> nonnegative condition.l.
; Return min(2*loss,condition) in D0 without overflowing; condition read-only.
; D1=0/-1; other registers preserved. Error preserves D0. The native caller
; subtracts this final loss. Do not use for once-only damage/RNG trials.
FF1Wear200Delta:
 tst.l d0
 bmi.b .bad
 tst.l (a0)
 bmi.b .bad
 cmp.l (a0),d0
 bhs.b .cap
 add.l d0,d0
 cmp.l (a0),d0
 bls.b .okay
.cap:
 move.l (a0),d0
.okay:
 moveq #0,d1
 rts
.bad:
 moveq #-1,d1
 rts
