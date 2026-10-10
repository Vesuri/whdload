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
.original
        movem.l (sp)+,d1/a0
        clr.w (-30510,a4)
        move.w ($c28,a4),d0
        rts
