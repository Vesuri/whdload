; First press: one degree. Suppress repeats for eight PAL fields (160 ms),
; then retain the view's existing held-turn increment. A zero command releases.
; With the simulation patch use consumed simulation fields, not render time.
TURN_REPEAT_FIELDS = 8
_turn_input
        movem.l d0-a6,-(sp)
        move.l (_turn_active,pc),d0
        beq .done
        lea (_turn_press,pc),a0
        move.l (64,sp),d0
        cmp.l #17,d0
        beq .turn
        cmp.l #19,d0
        beq .turn
        clr.l (a0)
        bra .done
.turn
        move.l (_h11,pc),a1
        move.l ($602c,a1),d1
        IFD _sim_consumed
        move.l (_custom2,pc),d2
        btst #6,d2
        beq .clock_ready
        move.l (_sim_consumed,pc),d1
.clock_ready
        ENDC
        cmp.l (a0),d0
        beq .repeat
        move.l d0,(a0)
        move.l d1,(4,a0)
        move.w #1,($6012,a1)
        bra .done
.repeat
        sub.l (4,a0),d1
        cmp.l #TURN_REPEAT_FIELDS,d1
        bcc .held
        clr.w ($6012,a1)
        bra .done
.held   move.w (_turn_hold_step,pc),($6012,a1)
.done   movem.l (sp)+,d0-a6
        move.l (_turn_input_original,pc),-(sp)
        rts

; Run after native mouse addition/wrapping. Complete signed modulo handles
; large deltas too, and leaves the original DIVS/MULS quantizer in place.
_turn_mouse_finish
        movem.l d1/a0,-(sp)
        move.l (_turn_active,pc),d1
        beq .original
        move.w ($c28,a4),d0
        ext.l d0
        divs.w #360,d0
        swap d0
        tst.w d0
        bpl .store
        add.w #360,d0
.store  move.w d0,($c28,a4)
        lea (_turn_press,pc),a0
        clr.l (a0)
.original
        movem.l (sp)+,d1/a0
        clr.w (-30510,a4)
        move.w ($c28,a4),d0
        rts

        CNOP 0,4
_turn_press dc.l 0,0
_turn_input_original dc.l 0
_turn_hold_step dc.w 5
