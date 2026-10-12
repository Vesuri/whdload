; Ferrari Formula One angular state. One axis is {Q12 angle.l, /5 remainder.w}.
; Native angle extraction uses (angle >> 12) & 1023; preserve native 32-bit
; modular addition. 2^32 is an integer multiple of the 2^22-unit revolution.
; Allocate independent per-car state with MEMF_PUBLIC.
;
; A0 -> axis, D0.l native 100 ms integrated increment. D1.l = 0 success,
; -1 if increment+remainder overflows. Error leaves state unchanged.
; D0-D2/CCR scratch; D3-D7/A0-A6 preserved. 68020+, FF1Step20Delta required.
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
