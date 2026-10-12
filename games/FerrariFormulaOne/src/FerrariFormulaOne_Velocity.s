; Ferrari Formula One fractional velocity/history primitives, diagnostic-only.
; A vector is {signed Q16 X.l, signed Q16 Z.l}, allocated in MEMF_PUBLIC.
; Velocity units remain displacement per native 100 ms, NOT per selected tick.
; Frame changes must transform both current and previous velocity. Explicit
; impulses/reset writers require separate ownership; do not feed an impulse
; through the continuous derivative simply because the next tick is 20 ms.

; A0 old vector, A1 new vector, A2 output acceleration in native-reference units.
; Output = 5 * (new - old), componentwise, retaining Q16 precision.
; D1.l = 0 success, -1 if either result exceeds signed Q16 storage.
; All registers except D1/CCR preserved. All eight output bytes commit together;
; failure leaves output unchanged. Output may alias either input. 68000-safe.
FF1VelocityDerivative20:
        movem.l d0/d2-d4,-(sp)
        move.l  (a1),d2
        sub.l   (a0),d2
        bvs.b   .overflow
        move.l  d2,d0
        add.l   d2,d2
        bvs.b   .overflow
        add.l   d2,d2
        bvs.b   .overflow
        add.l   d0,d2
        bvs.b   .overflow
        move.l  4(a1),d3
        sub.l   4(a0),d3
        bvs.b   .overflow
        move.l  d3,d0
        add.l   d3,d3
        bvs.b   .overflow
        add.l   d3,d3
        bvs.b   .overflow
        add.l   d0,d3
        bvs.b   .overflow
        move.l  d2,(a2)
        move.l  d3,4(a2)
        moveq   #0,d1
        bra.b   .done
.overflow:
        moveq   #-1,d1
.done:
        movem.l (sp)+,d0/d2-d4
        rts

; A0 vector, D0.w signed Q15 cosine, D1.w signed Q15 sine from native tables.
; Rotate (X,Z) -> (X*C-Z*S, X*S+Z*C)/32768, floor once per output component.
; D1.l = 0 success, -1 overflow. Other registers preserved, CCR scratch.
; Both components commit together. Failure leaves the complete vector unchanged.
; Error from this operation is < 1/65536 native velocity unit per component,
; excluding native coefficient quantization. 68020+ (signed 64-bit products).
FF1VelocityRotate020:
        movem.l d0/d2-d7,-(sp)
        suba.w  #8,sp
        move.w  d0,d2
        ext.l   d2
        move.w  d1,d3
        ext.l   d3
        move.l  (a0),d4
        muls.l  d2,d5:d4
        move.l  4(a0),d6
        muls.l  d3,d7:d6
        sub.l   d6,d4
        subx.l  d7,d5
        bsr.w   FF1VelocityShift15
        tst.l   d1
        bne.b   .done
        move.l  d4,(sp)
        move.l  (a0),d4
        muls.l  d3,d5:d4
        move.l  4(a0),d6
        muls.l  d2,d7:d6
        add.l   d6,d4
        addx.l  d7,d5
        bsr.w   FF1VelocityShift15
        tst.l   d1
        bne.b   .done
        move.l  d4,4(sp)
        move.l  (sp),(a0)
        move.l  4(sp),4(a0)
.done:
        adda.w  #8,sp
        movem.l (sp)+,d0/d2-d7
        rts

; D5:D4 signed 64-bit input, D4 signed 32-bit floor(input / 32768).
; D1 status 0/-1. D5-D6 scratch. Internal helper checks discarded sign bits.
FF1VelocityShift15:
        move.l  d5,d6
        asr.l   #8,d6
        asr.l   #7,d6
        lsr.l   #8,d4
        lsr.l   #7,d4
        lsl.l   #8,d5
        lsl.l   #8,d5
        lsl.l   #1,d5
        or.l    d5,d4
        tst.l   d4
        bmi.b   .negative
        tst.l   d6
        bne.b   .overflow
        bra.b   .success
.negative:
        cmpi.l  #-1,d6
        bne.b   .overflow
.success:
        moveq   #0,d1
        rts
.overflow:
        moveq   #-1,d1
        rts

; A0 vector, D0.w/D1.w native integer X/Z. Reset both fractional components,
; including when the integer value is unchanged. Registers preserved;
; CCR scratch. 68000-safe. This does not choose whether a writer is an impulse.
FF1VelocityReset:
        move.l  d2,-(sp)
        move.w  d0,d2
        swap    d2
        clr.w   d2
        move.l  d2,(a0)
        move.w  d1,d2
        swap    d2
        clr.w   d2
        move.l  d2,4(a0)
        move.l  (sp)+,d2
        rts

; Project fractional speed using native quantized heading coefficients.
; D0.l Q16 speed, D1.w Q15 sine, D2.w Q15 cosine, A0 output Q16 vector.
; X=floor(speed*S/32768), Z=floor(speed*C/32768). D1 status 0/-1;
; other registers preserved, CCR scratch. Both outputs commit together;
; overflow leaves the output unchanged. 68020+. This deliberately retains
; the supplied native coefficient quantization; no angle interpolation implied.
FF1VelocityProject020:
        movem.l d0/d2-d7,-(sp)
        suba.w  #8,sp
        move.w  d1,d3
        ext.l   d3
        ext.l   d2
        move.l  d0,d4
        muls.l  d3,d5:d4
        bsr.w   FF1VelocityShift15
        tst.l   d1
        bne.b   .done
        move.l  d4,(sp)
        move.l  d0,d4
        muls.l  d2,d5:d4
        bsr.w   FF1VelocityShift15
        tst.l   d1
        bne.b   .done
        move.l  d4,4(sp)
        move.l  (sp),(a0)
        move.l  4(sp),4(a0)
.done:
        adda.w  #8,sp
        movem.l (sp)+,d0/d2-d7
        rts

; Integrate a continuous native-reference Q16 response over 20 ms.
; A0 current Q16 vector (8 bytes), A1 independent signed /5 remainders (4 bytes),
; A2 response vector (8 bytes). A2 may alias A0; remainders must be disjoint.
; D1 status 0/-1. All other registers preserved, CCR scratch; 68020+.
; Commit both components AND both remainders together. On any overflow, all
; state is unchanged. Requires FF1Step20Delta/FF1Divide020. Callers must rotate,
; transfer or reset remainders with the associated velocity state. This applies
; only to continuous response; collision impulses are not divided by five.
FF1VelocityApply20:
        movem.l d0/d2-d7/a0-a3,-(sp)
        suba.w  #12,sp
        move.l  sp,a3
        move.l  (a0),(a3)
        move.l  4(a0),4(a3)
        move.l  (a1),8(a3)
        move.l  a0,-(sp)
        lea     8(a3),a0
        move.l  (a2),d0
        bsr.w   FF1Step20Delta
        tst.l   d1
        bne.b   .done
        add.l   d0,(a3)
        bvs.b   .overflow
        lea     10(a3),a0
        move.l  4(a2),d0
        bsr.w   FF1Step20Delta
        tst.l   d1
        bne.b   .done
        add.l   d0,4(a3)
        bvs.b   .overflow
        move.l  (sp),a0
        move.l  (a3),(a0)
        move.l  4(a3),4(a0)
        move.l  8(a3),(a1)
        bra.b   .done
.overflow:
        moveq   #-1,d1
.done:
        adda.w  #16,sp
        movem.l (sp)+,d0/d2-d7/a0-a3
        rts

; Rotate Q16 velocity AND signed /5 response remainders as one quantity.
; A0 vector (8 bytes), A1 remainders (4 bytes, each -4..4), disjoint.
; D0.w Q15 cosine, D1.w Q15 sine. D1 status 0/-1; other registers preserved.
; Floor once in units of 1/(5*65536), then split by signed division by five.
; Both axes and remainders commit atomically. Overflow leaves all state intact.
; Error per component <1/(5*65536) native velocity unit per rotation, excluding
; native coefficient quantization. 68020+, MEMF_PUBLIC state.
FF1VelocityRotateCarry020:
        movem.l d0/d2-d7,-(sp)
        suba.w  #12,sp
        move.w  d0,d2
        ext.l   d2
        move.w  d1,d3
        ext.l   d3
        move.l  (a0),d4
        muls.l  d2,d5:d4
        move.l  4(a0),d6
        muls.l  d3,d7:d6
        sub.l   d6,d4
        subx.l  d7,d5
        move.l  d4,d6
        move.l  d5,d7
        add.l   d4,d4
        addx.l  d5,d5
        add.l   d4,d4
        addx.l  d5,d5
        add.l   d6,d4
        addx.l  d7,d5
        move.w  (a1),d6
        muls.w  d2,d6
        move.w  2(a1),d7
        muls.w  d3,d7
        sub.l   d7,d6
        move.l  d6,d7
        moveq   #31,d1
        asr.l   d1,d7
        add.l   d6,d4
        addx.l  d7,d5
        bsr.w   FF1VelocityTailDivide
        tst.l   d1
        bne.w   .done
        move.l  d4,0(sp)
        move.w  d5,8(sp)
        move.l  (a0),d4
        muls.l  d3,d5:d4
        move.l  4(a0),d6
        muls.l  d2,d7:d6
        add.l   d6,d4
        addx.l  d7,d5
        move.l  d4,d6
        move.l  d5,d7
        add.l   d4,d4
        addx.l  d5,d5
        add.l   d4,d4
        addx.l  d5,d5
        add.l   d6,d4
        addx.l  d7,d5
        move.w  (a1),d6
        muls.w  d3,d6
        move.w  2(a1),d7
        muls.w  d2,d7
        add.l   d7,d6
        move.l  d6,d7
        moveq   #31,d1
        asr.l   d1,d7
        add.l   d6,d4
        addx.l  d7,d5
        bsr.w   FF1VelocityTailDivide
        tst.l   d1
        bne.w   .done
        move.l  d4,4(sp)
        move.w  d5,10(sp)
        move.l  (sp),(a0)
        move.l  4(sp),4(a0)
        move.l  8(sp),(a1)
.done:
        adda.w  #12,sp
        movem.l (sp)+,d0/d2-d7
        rts

; Signed D5:D4 / 32768 floored, then signed 64/32 division by five.
; D4 quotient (Q16), D5 remainder; D1 status. D6 scratch.
FF1VelocityTailDivide:
        move.l  d5,d6
        lsl.l   #8,d6
        lsl.l   #8,d6
        lsl.l   #1,d6
        lsr.l   #8,d4
        lsr.l   #7,d4
        or.l    d6,d4
        asr.l   #8,d5
        asr.l   #7,d5
        divs.l  #5,d5:d4
        bvs.b   .overflow
        moveq   #0,d1
        rts
.overflow:
        moveq   #-1,d1
        rts

; Rescale a signed body component by nonnegative tyre limit / magnitude.
; D0.w component, D1.w limit (0..32767), D2.l magnitude (1..65535).
; D0.l signed result, truncated toward zero; D1.l status 0/-1.
; Preserve full signed 32-bit product, unlike the legacy EXT.L after MULS.W.
; Reject invalid inputs or a result outside a native signed word; on failure
; D0 is unchanged. D2-D7/A0-A6 preserved, CCR scratch. 68020+.
FF1VelocityLimit020:
        movem.l d2-d3,-(sp)
        move.l  d0,d3
        tst.w   d1
        bmi.b   .bad
        tst.l   d2
        beq.b   .bad
        cmpi.l  #65535,d2
        bhi.b   .bad
        muls.w  d1,d0
        divs.l  d2,d0
        cmpi.l  #-32768,d0
        blt.b   .bad
        cmpi.l  #32767,d0
        bgt.b   .bad
        moveq   #0,d1
        bra.b   .done
.bad:
        move.l  d3,d0
        moveq   #-1,d1
.done:
        movem.l (sp)+,d2-d3
        rts
