; Fractional position integration for one car axis, 68020+.
; A0 -> {signed integer word, unsigned Q16 fraction, signed /5 remainder word}.
; D0.w = native 100 ms displacement. Returns D1.l = 0 or -1 on overflow.
; D0-D2/CCR scratch; D3-D7/A0-A6 preserved. On failure ALL state is unchanged.
; State must live in a MEMF_PUBLIC allocation. Each car/axis owns its own state.
; Caller must transform fractions at segment changes and explicitly reset them
; at teleports/clamps. This helper alone is not the converted car integrator.
FF1Position20:
        swap    d0
        clr.w   d0

; Same contract/state as above, but D0.l is fractional Q16 velocity in native
; displacement-per-100-ms units. Retain projected/response velocity fractions
; instead of truncating to a native word before position integration.
FF1Position20Q16:
        movem.l d3-d4/a1,-(sp)
        move.l  a0,a1
        move.w  4(a1),-(sp)
        move.l  sp,a0
        bsr.w   FF1Step20Delta
        tst.l   d1
        bne.b   FF1PositionDone
        move.l  (a1),d3
        add.l   d0,d3
        bvs.b   FF1PositionOverflow
        move.l  d3,(a1)
        move.w  (sp),4(a1)
        bra.b   FF1PositionDone
FF1PositionOverflow:
        moveq   #-1,d1
FF1PositionDone:
        addq.l  #2,sp
        move.l  a1,a0
        movem.l (sp)+,d3-d4/a1
        rts

; Rotate fractional tails after the native integer segment rotation.
; A0 -> two consecutive six-byte axis states (old fractions/remainders).
; D0.w = signed Q15 cosine, D1.w = signed Q15 sine from native tables.
; D2.w/D3.w = native rotated integer X/Z. Returns D1.l = 0 success/-1 overflow.
; Commits both axes together; failure leaves both unchanged. D0-D1/CCR scratch;
; D2-D7/A0-A6 preserved. Requires 68020. Zero tails give EXACT native integers.
; Tail unit is 1/(5*65536). Rotate fraction AND /5 remainder together using
; signed 64-bit products; floor once per output axis to this unit. Added error
; is less than one tail unit per axis per crossing (excluding native rounding).
FF1PositionRotate20:
        movem.l d2-d7/a1-a2,-(sp)
        moveq   #5,d6
        bra.b   FF1PositionRotateDenominator

; Same rotation with /25 position remainders, used after integration of
; velocity carrying /5 remainders. Never mix the /5 and /25 state formats.
FF1PositionRotate25:
        movem.l d2-d7/a1-a2,-(sp)
        moveq   #25,d6
FF1PositionRotateDenominator:
        move.l  d6,a1
        suba.w  #16,sp
        move.l  sp,a2
        move.w  d2,12(a2)
        move.w  d3,14(a2)
        move.w  d0,d2
        ext.l   d2
        move.w  d1,d3
        ext.l   d3
        moveq   #0,d0
        move.w  2(a0),d0
        mulu.w  d6,d0
        move.w  4(a0),d4
        ext.l   d4
        add.l   d4,d0
        moveq   #0,d1
        move.w  8(a0),d1
        mulu.w  d6,d1
        move.w  10(a0),d4
        ext.l   d4
        add.l   d4,d1
        move.l  d0,d4
        muls.l  d2,d5:d4
        move.l  d1,d6
        muls.l  d3,d7:d6
        sub.l   d6,d4
        subx.l  d7,d5
        bsr.w   FF1PositionShift15
        move.l  d4,(a2)
        move.l  d0,d4
        muls.l  d3,d5:d4
        move.l  d1,d6
        muls.l  d2,d7:d6
        add.l   d6,d4
        addx.l  d7,d5
        bsr.w   FF1PositionShift15
        move.l  d4,6(a2)
        move.l  a1,d6
        move.l  (a2),d4
        divsl.l d6,d5:d4
        move.w  d5,4(a2)
        move.w  12(a2),d5
        swap    d5
        clr.w   d5
        add.l   d4,d5
        bvs.b   FF1PositionRotateOverflow
        move.l  d5,(a2)
        move.l  6(a2),d4
        divsl.l d6,d5:d4
        move.w  d5,10(a2)
        move.w  14(a2),d5
        swap    d5
        clr.w   d5
        add.l   d4,d5
        bvs.b   FF1PositionRotateOverflow
        move.l  d5,6(a2)
        move.l  (a2),(a0)
        move.w  4(a2),4(a0)
        move.l  6(a2),6(a0)
        move.w  10(a2),10(a0)
        moveq   #0,d1
        bra.b   FF1PositionRotateDone
FF1PositionRotateOverflow:
        moveq   #-1,d1
FF1PositionRotateDone:
        adda.w  #16,sp
        movem.l (sp)+,d2-d7/a1-a2
        rts

; Signed 64-bit D5:D4 >> 15, low 32-bit result. Caller guarantees it fits.
FF1PositionShift15:
        lsr.l   #8,d4
        lsr.l   #7,d4
        lsl.l   #8,d5
        lsl.l   #8,d5
        lsl.l   #1,d5
        or.l    d5,d4
        rts

; Explicit clamp/teleport of one axis. D0.w = new integer, A0 = six-byte axis.
; All registers preserved, CCR scratch; 68000-safe. Clear fractional carry even
; when the replacement integer equals the previous integer.
FF1PositionReset:
        move.w  d0,(a0)
        clr.l   2(a0)
        rts

; Contact placement at source position + an INTEGER separation/frame offset.
; D0.w = native destination integer, A0 = destination axis, A1 = source axis.
; Copy source fraction AND rational remainder, including self-assignment.
; All registers preserved, CCR scratch; 68000-safe. This is not a general
; coordinate-frame rotation or a velocity/impulse conversion.
FF1PositionAssign:
        move.w  d0,(a0)
        move.l  2(a1),2(a0)
        rts

; Continuous segment-boundary predicate for the converted 020 path.
; A0 -> X and Z six-byte axes. D0.w = native sin(angle,1000), D1.w =
; native cos(angle,1000). D0.l returns 0/1 for X*S/C + Z >= 512;
; D1.l returns 0, or -1 for undefined C=0 (D0=0). D2-D7/A0-A6 preserved.
; Includes signed /5 remainders. No state writes, division or early rounding.
; Signed 64-bit products cover the full stored coordinate/coefficient domain.
; For C<0 reverse the comparison. This is a continuous geometry predicate;
; the native-step control MUST retain the original rounded integer predicate.
; The original truncates X*S/C to an integer before adding Z, so decisions
; with zero tails, its rounding differs by less than one longitudinal unit.
; Nonzero tails add the intended fractional geometric displacement as well.
FF1PositionCrossed020:
        movem.l d2-d7,-(sp)
        move.w  d0,d2
        moveq   #5,d0
        bra.b   FF1PositionCrossDenominator

; Same continuous boundary predicate for /25 position remainders.
FF1PositionCrossed25:
        movem.l d2-d7,-(sp)
        move.w  d0,d2
        moveq   #25,d0
FF1PositionCrossDenominator:
        ext.l   d2
        move.w  d1,d3
        ext.l   d3
        beq.w   FF1PositionCrossUndefined
        move.l  (a0),d4
        muls.l  d2,d5:d4
        move.l  6(a0),d6
        muls.l  d3,d7:d6
        add.l   d6,d4
        addx.l  d7,d5
        move.l  #$02000000,d6
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
        cmpi.l  #25,d0
        bne.b   FF1PositionCrossAddRemainder
        move.l  d4,d6
        move.l  d5,d7
        add.l   d4,d4
        addx.l  d5,d5
        add.l   d4,d4
        addx.l  d5,d5
        add.l   d6,d4
        addx.l  d7,d5
FF1PositionCrossAddRemainder:
        move.w  4(a0),d6
        muls.w  d2,d6
        move.w  10(a0),d7
        muls.w  d3,d7
        add.l   d7,d6
        move.l  d6,d7
        moveq   #31,d0
        asr.l   d0,d7
        add.l   d6,d4
        addx.l  d7,d5
        moveq   #0,d0
        tst.l   d3
        bmi.b   FF1PositionCrossNegativeCos
        tst.l   d5
        bmi.b   FF1PositionCrossDone
        moveq   #1,d0
        bra.b   FF1PositionCrossDone
FF1PositionCrossNegativeCos:
        tst.l   d5
        bmi.b   FF1PositionCrossYes
        bne.b   FF1PositionCrossDone
        tst.l   d4
        bne.b   FF1PositionCrossDone
FF1PositionCrossYes:
        moveq   #1,d0
FF1PositionCrossDone:
        moveq   #0,d1
        movem.l (sp)+,d2-d7
        rts
FF1PositionCrossUndefined:
        moveq   #0,d0
        moveq   #-1,d1
        movem.l (sp)+,d2-d7
        rts

; Clamp a full axis (including its signed /5 remainder) to an INTEGER bound.
; A0 -> axis, D0.w = bound. D1.l returns 1 if clamped, 0 if unchanged.
; D0/D2-D7/A0-A6 preserved; CCR scratch; both entries are 68000-safe.
; Valid tails: unsigned fraction word, signed remainder in -4..4.
FF1PositionClampLower:
        move.w  (a0),d1
        cmp.w   d0,d1
        blt.b   FF1PositionClampApply
        bgt.b   FF1PositionClampKeep
        tst.w   2(a0)
        bne.b   FF1PositionClampKeep
        tst.w   4(a0)
        bmi.b   FF1PositionClampApply
        bra.b   FF1PositionClampKeep
FF1PositionClampUpper:
        move.w  (a0),d1
        cmp.w   d0,d1
        bgt.b   FF1PositionClampApply
        blt.b   FF1PositionClampKeep
        tst.w   2(a0)
        bne.b   FF1PositionClampApply
        tst.w   4(a0)
        bgt.b   FF1PositionClampApply
FF1PositionClampKeep:
        moveq   #0,d1
        rts
FF1PositionClampApply:
        bsr.w   FF1PositionReset
        moveq   #1,d1
        rts

; Integrate physical velocity Q16 + signed remainder/5 over 20 ms.
; D0.l velocity Q16, D1.w velocity remainder (-4..4), A0 -> position
; Q16.l plus signed /25 remainder.w (-24..24). Exact rational increment:
; (5*velocity + velocity remainder + old position remainder)/25.
; D1 status 0/-1. Atomic on invalid carry or position overflow.
; D0/CCR scratch; D2-D7/A0-A6 preserved. 68020+.
FF1Position20Velocity:
        movem.l d2-d5,-(sp)
        ext.l   d1
        cmpi.l  #-4,d1
        blt.b   .bad
        cmpi.l  #4,d1
        bgt.b   .bad
        move.w  4(a0),d4
        ext.l   d4
        cmpi.l  #-24,d4
        blt.b   .bad
        cmpi.l  #24,d4
        bgt.b   .bad
        add.l   d1,d4
        move.l  d4,d5
        moveq   #31,d1
        asr.l   d1,d5
        move.l  d0,d2
        muls.l  #5,d3:d2
        add.l   d4,d2
        addx.l  d5,d3
        divs.l  #25,d3:d2
        bvs.b   .bad
        add.l   (a0),d2
        bvs.b   .bad
        move.l  d2,(a0)
        move.w  d3,4(a0)
        moveq   #0,d1
        bra.b   .done
.bad:
        moveq   #-1,d1
.done:
        movem.l (sp)+,d2-d5
        rts
