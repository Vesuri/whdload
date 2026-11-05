; Ferrari Formula One: fractional scaling of continuous native-step increments.
; These helpers do not convert filters, derivatives, thresholds or impulses.
; The caller chooses units (including fixed-point units), owns one remainder
; per independent quantity/car, and must transform/reset it with that state.
; Never share a remainder between position axes, velocity, heading or wear.
;
; Fine: D0.l = signed increment for native 100 ms; A0 = signed-word remainder
; in -4..4, initially zero. D0.l returns the 20 ms increment. D1.l = 0 success,
; -1 on signed addition overflow. On error D0 and remainder are unchanged.
; D2/CCR scratch; D3-D7/A0-A6 preserved. Requires FF1Divide020 and a 68020+.
; With constant input, five successful calls sum exactly to one native increment;
; reversal carries through zero instead of throwing away sub-unit movement.
FF1Step20Delta:
        move.l  d0,d2
        move.w  (a0),d1
        ext.l   d1
        add.l   d1,d0
        bvs.b   FF1StepOverflow
        moveq   #5,d1
        bsr.w   FF1Divide020
        move.w  d1,(a0)
        moveq   #0,d1
        rts

; Provisional 200 ms coarse interval: double the integrated increment.
; D0.l input/output, D1.l status as above, D2/CCR scratch; others preserved.
; No fractional state is needed for this integer ratio. A caller must handle
; overflow explicitly; wrapping or silently dropping the increment is forbidden.
; This entry point is 68000-safe. It does not select an accepted 68000 interval.
FF1Step200Delta:
        move.l  d0,d2
        add.l   d0,d0
        bvs.b   FF1StepOverflow
        moveq   #0,d1
        rts

FF1StepOverflow:
        move.l  d2,d0
        moveq   #-1,d1
        rts
