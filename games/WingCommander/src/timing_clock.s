; D's scheduler arithmetic, independent of game or platform callbacks.
; A0 -> 28-byte state; D0.l current wrapping field count; D1.l measured field Hz (50 or 60);
; D2.w active (zero rebases). Returns D0.l issued ticks.
; D0-D3 and CCR scratch; all address registers and D4-D7 preserved.
; State: last field, debt (tenths of a field), active fields, issued ticks,
; dropped debt units, rebase count (all long), ready word, padding word.
; Four ticks per batch. Debt above that budget is dropped and counted, never
; silently interpreted as completed world time. Modal time is excluded.
timing_advance:
        move.l  d0,d3
        sub.l   (a0),d3
        move.l  d0,(a0)
        tst.w   d2
        beq.s   .inactive
        tst.w   24(a0)
        beq.s   .initial
        add.l   d3,8(a0)
        cmp.l   d1,d3
        bhi.s   .stall
        mulu.w  #10,d3
        add.l   4(a0),d3
        move.l  d3,d0
        divu.w  d1,d0
        move.l  d0,d2
        swap    d2
        andi.l  #$ffff,d2
        move.l  d2,4(a0)
        andi.l  #$ffff,d0
        cmpi.w  #4,d0
        bls.s   .count
        move.l  d0,d2
        subq.l  #4,d2
        mulu.w  d1,d2
        add.l   d2,16(a0)
        moveq   #4,d0
.count:
        add.l   d0,12(a0)
        rts
.stall:
        ; Long loading/stall interval: discard all debt, record recovery.
        mulu.l  #10,d3
        add.l   4(a0),d3
        add.l   d3,16(a0)
        clr.l   4(a0)
        addq.l  #1,20(a0)
        moveq   #0,d0
        moveq   #0,d1
        rts
.inactive:
        clr.w   24(a0)
.initial:
        tst.w   d2
        beq.s   .clear
        move.w  #1,24(a0)
.clear:
        move.l  4(a0),d3
        add.l   d3,16(a0)
        clr.l   4(a0)
        addq.l  #1,20(a0)
        moveq   #0,d0
        moveq   #0,d1
        rts
        cnop    0,4
