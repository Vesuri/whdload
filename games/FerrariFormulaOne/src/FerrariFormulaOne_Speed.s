; Ferrari Formula One: continuous scalar speed rate, 68020+ candidate.
; A0 -> Q16 speed.l and signed fifth-of-Q16 remainder.w (-4..4).
; D0.l = proposed native 100 ms result evaluated from integer speed.
; Apply (proposal - floor(current Q16))/5 to the fractional current state.
; Clamp physical speed to 0..500 and clear the remainder at either bound.
; D1.l status 0/-1; invalid state/overflow leaves all six bytes unchanged.
; D0/CCR scratch; D2-D7/A0-A6 preserved. This helper does not schedule
; engine side effects or decide which native writers are continuous rates.
FF1SpeedRate20:
        movem.l d2-d5,-(sp)
        move.l  (a0),d4
        tst.l   d4
        bmi.b   .bad
        cmpi.l  #500*65536,d4
        bhi.b   .bad
        move.w  4(a0),d5
        ext.l   d5
        cmpi.l  #-4,d5
        blt.b   .bad
        cmpi.l  #4,d5
        bgt.b   .bad
        moveq   #0,d2
        move.w  (a0),d2
        sub.l   d2,d0
        bvs.b   .bad
        move.l  d0,d2
        moveq   #16,d3
        asr.l   d3,d2
        lsl.l   d3,d0
        move.l  d5,d3
        asr.l   #8,d3
        asr.l   #8,d3
        asr.l   #8,d3
        asr.l   #7,d3
        add.l   d5,d0
        addx.l  d3,d2
        divs.l  #5,d2:d0
        bvs.b   .bad
        add.l   d4,d0
        bvs.b   .bad
        tst.l   d0
        bmi.b   .zero
        cmpi.l  #500*65536,d0
        bhi.b   .maximum
        ; At an exact bound, discard outward fractional remainder too.
        bne.b   .lower
        tst.l   d2
        bpl.b   .maximum
.lower:
        tst.l   d0
        bne.b   .store
        tst.l   d2
        bmi.b   .zero
        bra.b   .store
.maximum:
        move.l  #500*65536,d0
        moveq   #0,d2
        bra.b   .store
.zero:
        moveq   #0,d0
        moveq   #0,d2
.store:
        move.l  d0,(a0)
        move.w  d2,4(a0)
        moveq   #0,d1
        bra.b   .done
.bad:
        moveq   #-1,d1
.done:
        movem.l (sp)+,d2-d5
        rts

; Derive scalar speed from the physical fractional velocity, 68020+.
; A0 -> X Q16.l, Z Q16.l, signed X/Z remainder.w (fifths of Q16).
; A1 -> scalar Q16.l, remainder.w. Floor magnitude at one fifth of Q16.
; Each 5*component+remainder must fit signed 32 bits; reject otherwise.
; Speed below 4 becomes zero (caller must stop the vector too), above 500
; is capped. Input untouched; output unchanged on error. D1 status 0/-1;
; D0/D2-D7/A0-A6 preserved, CCR scratch. Requires FF1SquareRootU64.
FF1SpeedFromVelocity020:
        movem.l d0/d2-d7,-(sp)
        move.w  8(a0),d5
        ext.l   d5
        cmpi.l  #-4,d5
        blt.w   .bad
        cmpi.l  #4,d5
        bgt.w   .bad
        move.l  (a0),d0
        muls.l  #5,d0
        bvs.w   .bad
        add.l   d5,d0
        bvs.w   .bad
        muls.l  d0,d1:d0
        move.l  d0,d3
        move.l  d1,d4
        move.w  10(a0),d5
        ext.l   d5
        cmpi.l  #-4,d5
        blt.w   .bad
        cmpi.l  #4,d5
        bgt.w   .bad
        move.l  4(a0),d0
        muls.l  #5,d0
        bvs.w   .bad
        add.l   d5,d0
        bvs.w   .bad
        muls.l  d0,d1:d0
        add.l   d3,d0
        addx.l  d4,d1
        bsr.w   FF1SquareRootU64
        cmpi.l  #4*65536*5,d0
        blo.b   .stop
        cmpi.l  #500*65536*5,d0
        bhs.b   .cap
        moveq   #0,d1
        divu.l  #5,d1:d0
        move.l  d0,(a1)
        move.w  d1,4(a1)
        bra.b   .okay
.stop:
        clr.l   (a1)
        clr.w   4(a1)
        bra.b   .okay
.cap:
        move.l  #500*65536,(a1)
        clr.w   4(a1)
.okay:
        moveq   #0,d1
        bra.b   .done
.bad:
        moveq   #-1,d1
.done:
        movem.l (sp)+,d0/d2-d7
        rts
