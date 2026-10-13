; 68000 200 ms adapters to the audited per-car bridge layouts.
; Included only by the experimental complete C4 integration.
 include "FerrariFormulaOne_Wide000.s"
 include "FerrariFormulaOne_Physics200.s"
 include "FerrariFormulaOne_Position200.s"
FF1VelocityProject020 equ FF1VelocityProject000
FF1VelocityRotate020 equ FF1VelocityRotate000
FF1VelocityDerivative20 equ FF1VelocityDerivative200
FF1Step20Delta:
 add.l d0,d0
 moveq #0,d1
 rts
FF1VelocityRotateCarry020:
 bsr.w FF1VelocityRotate000
 tst.l d1
 bne.b .done
 clr.l (a1)
.done: rts
FF1VelocityApply20:
 move.l a1,-(sp)
 move.l a2,a1
 bsr.w FF1VelocityApply200
 move.l (sp)+,a1
 tst.l d1
 bne.b .done
 clr.l (a1)
.done: rts
FF1SpeedFromVelocity020:
 bsr.w FF1SpeedFromVelocity000
 clr.w 4(a1)
 rts
FF1SpeedRate20:
 bsr.w FF1SpeedRate200
 tst.l d1
 bne.b .done
 clr.w 4(a0)
.done: rts
FF1Wear20Delta:
 bsr.w FF1Wear200Delta
 tst.l d1
 bne.b .done
 clr.w (a1)
.done: rts
FF1Position20Velocity:
 move.l d2,-(sp)
 move.l d0,d2
 add.l d2,d2
 bvs.b .bad
 add.l (a0),d2
 bvs.b .bad
 move.l d2,(a0)
 clr.w 4(a0)
 moveq #0,d1
 bra.b .done
.bad: moveq #-1,d1
.done:
 move.l (sp)+,d2
 rts
FF1PositionRotate25:
 movem.l a0-a1,-(sp)
 suba.w #8,sp
 move.l a0,a1
 move.l (a0),(sp)
 move.l 6(a0),4(sp)
 move.l sp,a0
 bsr.w FF1PositionRotate200
 tst.l d1
 bne.b .done
 move.l (sp),(a1)
 move.l 4(sp),6(a1)
 clr.w 4(a1)
 clr.w 10(a1)
.done:
 addq.l #8,sp
 movem.l (sp)+,a0-a1
 rts
FF1PositionCrossed25:
 move.l a0,-(sp)
 suba.w #8,sp
 move.l (a0),(sp)
 move.l 6(a0),4(sp)
 move.l sp,a0
 bsr.w FF1PositionCrossed000
 addq.l #8,sp
 move.l (sp)+,a0
 rts
FF1VelocityLimit020:
 movem.l d2-d3,-(sp)
 move.l d0,d3
 tst.w d1
 bmi.b .bad
 tst.l d2
 beq.b .bad
 cmpi.l #65535,d2
 bhi.b .bad
 muls.w d1,d0
 move.l d2,d1
 bsr.w FF1Divide000
 cmpi.l #-32768,d0
 blt.b .bad
 cmpi.l #32767,d0
 bgt.b .bad
 moveq #0,d1
 bra.b .done
.bad:
 move.l d3,d0
 moveq #-1,d1
.done:
 movem.l (sp)+,d2-d3
 rts
FF1SquareRootU32:
 movem.l d1-d4,-(sp)
 move.l d0,d1
 moveq #0,d2
 move.l #32768,d3
.loop:
 move.l d2,d4
 or.l d3,d4
 move.l d4,d0
 mulu.w d0,d0
 cmp.l d1,d0
 bhi.b .next
 move.l d4,d2
.next:
 lsr.l #1,d3
 bne.b .loop
 move.l d2,d0
 movem.l (sp)+,d1-d4
 rts
; Current raw request is held until the next 200 ms controller sample. The
; previous request was therefore also the held request at t-100 ms.
FF1SteeringSample20:
 move.w 16(a0),d2
 ext.l d2
 move.w d0,16(a0)
 move.l d3,12(a0)
 add.w d2,d0
 asr.w #1,d0
 ext.l d0
 moveq #0,d1
 rts
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

FF1Heading20:
        move.l  a1,-(sp)
        move.l  a0,a1
        move.w  4(a0),-(sp)
        move.l  sp,a0
        bsr.w   FF1Step20Delta
        tst.l   d1
        bne.b   .done
        add.l   d0,(a1)
        move.w  (sp),4(a1)
.done:
        addq.l  #2,sp
        move.l  a1,a0
        move.l  (sp)+,a1
        rts

; A0 -> {relative axis, world axis}. Equivalent to native world -= relative;
; relative = 0, but includes both remainders and normalizes their difference.
; D0-D1/CCR scratch; other registers preserved. 68000-safe, cannot overflow
; because the angular integer component intentionally wraps as native does.
FF1HeadingZeroRelative:
        move.l  (a0),d0
        sub.l   d0,6(a0)
        move.w  10(a0),d0
        sub.w   4(a0),d0
        cmpi.w  #5,d0
        blt.b   .negative
        subq.w  #5,d0
        addq.l  #1,6(a0)
        bra.b   .commit
.negative:
        cmpi.w  #-5,d0
        bgt.b   .commit
        addq.w  #5,d0
        subq.l  #1,6(a0)
.commit:
        move.w  d0,10(a0)
        clr.l   (a0)
        clr.w   4(a0)
        moveq   #0,d1
        rts

; D0.l new native Q12 angle, A0 destination axis. Explicit reset.
; Registers preserved, CCR scratch. 68000-safe.
FF1HeadingReset:
        move.l  d0,(a0)
        clr.w   4(a0)
        rts

; D0.l new native Q12 angle, A0 destination, A1 source axis. For assignments
; whose difference from source is an exact integer Q12 frame offset.
; Registers preserved, CCR scratch. 68000-safe; self-assignment is valid.
FF1HeadingAssign:
        move.l  d0,(a0)
        move.w  4(a1),4(a0)
        rts
FF1SteeringReset:
        move.w  d0,(a0)
        move.w  d0,2(a0)
        move.w  d0,4(a0)
        move.w  d0,6(a0)
        move.w  d0,8(a0)
        clr.w   10(a0)
        move.l  d3,12(a0)
        move.w  d0,16(a0)
        rts

