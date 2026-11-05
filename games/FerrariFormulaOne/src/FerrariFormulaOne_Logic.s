; Ferrari Formula One: simulation work extracted from presentation.
; Not yet installed by the normal slave. Call only after version/hunk validation.
;
; Native player recovery status advances toward -1 once per native update.
; That update represents 100 ms. Use FF1TimeConsume's tenth-second pulse count,
; independently of calendar/session clock eligibility or whether a frame is drawn.
; A0 points to the status word; D0.w is 0..2 elapsed tenth-second pulses.
; Return D0.w = status after advancement. D1/CCR scratch; other registers preserved.
; Never pass negative pulses, or use this for unrelated status values/deadlines.
FF1AdvanceRecovery:
        move.w  (a0),d1
        cmpi.w  #-1,d1
        bge.b   .done
        add.w   d0,d1
        cmpi.w  #-1,d1
        ble.b   .store
        moveq   #-1,d1
.store: move.w  d1,(a0)
.done:  move.w  d1,d0
        rts
