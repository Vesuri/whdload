; FF1_PLAYER_HOOKS stores the unsigned 0..4 carry in a byte; no adjacent
; byte may be read or written. The default word ABI is unchanged.
; Continuous condition loss at the 20 ms quantum (68020+).
; D0.l nonnegative native 100 ms decrement, A0 -> nonnegative condition.l,
; A1 -> unsigned remainder.w (0..4), owned by this condition in MEMF_PUBLIC.
; Return D0.l decrement to subtract, D1.l status 0/-1. Condition is not written.
; Scale the requested loss BEFORE saturation. Clear carry on depletion,
; including an already-zero condition. Invalid input leaves D0/carry unchanged.
; D2-D4/A0-A6 preserved, CCR scratch. Explicit part replacement must reset carry.
        ifd FF1_HELPERS_020
FF1Wear20Delta:
        move.l  d2,-(sp)
        tst.l   d0
        bmi.b   .bad
        move.l  (a0),d2
        bmi.b   .bad
        moveq   #0,d1
        ifd FF1_PLAYER_HOOKS
        move.b  (a1),d1
        else
        move.w  (a1),d1
        endc
        cmpi.w  #4,d1
        bhi.b   .bad
        add.l   d1,d0
        cmpi.l  #255,d0
        bhi.b   .divide
        move.w  FF1WearFifths(pc,d0.w*2),d1
        moveq   #0,d0
        move.b  d1,d0
        lsr.w   #8,d1
        bra.b   .clamp
.divide:
        divul.l #5,d1:d0
.clamp:
        cmp.l   d2,d0
        blo.b   .store
        move.l  d2,d0
        moveq   #0,d1
.store:
        ifd FF1_PLAYER_HOOKS
        move.b  d1,(a1)
        else
        move.w  d1,(a1)
        endc
        moveq   #0,d1
        bra.b   .done
.bad:
        moveq   #-1,d1
.done:
        move.l  (sp)+,d2
        rts
        else
FF1Wear20Delta:
        movem.l d2-d4,-(sp)
        move.l  d0,d4
        tst.l   d0
        bmi.b   .bad
        move.l  (a0),d3
        bmi.b   .bad
        moveq   #0,d2
 IFD FF1_PLAYER_HOOKS
        move.b  (a1),d2
 ELSE
        move.w  (a1),d2
 ENDC
        cmpi.w  #4,d2
        bhi.b   .bad
        add.l   d2,d0
        moveq   #0,d2
        divu.l  #5,d2:d0
        cmp.l   d3,d0
        blo.b   .store
        move.l  d3,d0
        moveq   #0,d2
.store:
 IFD FF1_PLAYER_HOOKS
        move.b  d2,(a1)
 ELSE
        move.w  d2,(a1)
 ENDC
        moveq   #0,d1
        bra.b   .done
.bad:
        move.l  d4,d0
        moveq   #-1,d1
.done:
        movem.l (sp)+,d2-d4
        rts
        endc
        ifd FF1_HELPERS_020
; Packed unsigned remainder:quotient for every numerator 0..255.
FF1WearFifths:
FF1WearNumerator set 0
        rept 256
        dc.w ((FF1WearNumerator-(FF1WearNumerator/5)*5)<<8)|(FF1WearNumerator/5)
FF1WearNumerator set FF1WearNumerator+1
        endr
        endc
