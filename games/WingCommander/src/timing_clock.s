; D's scheduler arithmetic, independent of game or platform callbacks.
; A0 -> 28-byte state; D0.l current wrapping field count; D1.l measured field Hz (50 or 60);
; D2.w active (zero rebases). Returns D0.l issued ticks at timing_world_rate per second.
; D0-D3 and CCR scratch; all address registers and D4-D7 preserved.
; State: last field, debt (field/rate units: Hz units make one tick), active fields, issued ticks,
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
        mulu.w  timing_world_rate+2(pc),d3
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
        mulu.l  timing_world_rate(pc),d3
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

; World ticks per second. Native flight is 10 Hz; the player's speed option
; selects 12, 15 or 20 for ordinary flight only. Scenes on the shared clock
; (title, fly-by, launch, ejection, rooms) save the current rate and run at 10.
; Change the rate only before a rebase: debt units are per-rate.
timing_rate_flight:
        move.l  a0,-(sp)
        lea     timing_world_rate(pc),a0
        move.l  timing_flight_rate(pc),(a0)
        move.l  (sp)+,a0
        rts
timing_rate_native:
        move.l  a0,-(sp)
        lea     timing_world_rate(pc),a0
        move.l  #10,(a0)
        move.l  (sp)+,a0
        rts
timing_rate_scene:
        move.l  a0,-(sp)
        lea     timing_saved_rate(pc),a0
        move.l  timing_world_rate(pc),(a0)
        lea     timing_world_rate(pc),a0
        move.l  #10,(a0)
        move.l  (sp)+,a0
        rts
timing_rate_restore:
        move.l  a0,-(sp)
        lea     timing_world_rate(pc),a0
        move.l  timing_saved_rate(pc),(a0)
        move.l  (sp)+,a0
        rts
        cnop    0,4
timing_flight_rate: dc.l 10     ; option: 10, 12, 15 or 20
timing_high_framerate: dc.w 1   ; option: 0 draws one picture per world tick
        dc.w    0
timing_saved_rate:  dc.l 10
timing_world_rate:  dc.l 10     ; last: the clock check finds it at the end
