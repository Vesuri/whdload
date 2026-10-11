; Integrate each pickup motion interval before its native event at tick twelve.
; State: actor pointer, remaining ticks, Y increment, yaw increment, remainders.
s60_pickup_state: ds.b 16
s60_pickup_reset:
        lea (s60_pickup_state,pc),a0
        clr.l (a0)
        clr.l (4,a0)
        clr.l (8,a0)
        clr.l (12,a0)
        rts
s60_pickup_install:
        move.l (s60_code,pc),a0
        cmp.w #$5279,($3d2a,a0)
        bne s60_bad
        cmp.l #$d1a80010,($3da0,a0)
        bne s60_bad
        cmp.l #$d1680018,($3db0,a0)
        bne s60_bad
        rts
s60_pickup_update:
        movem.l d2/a3/a6,-(sp)
        lea (s60_pickup_state,pc),a6
        move.l ($46c0-S60_DATA,a4),d0
        beq .inactive
        move.l d0,a3
        cmp.l (a6),d0
        beq .phase
        bsr s60_pickup_reset
        move.l a3,(a6)
.phase: tst.w (4,a6)
        bne .advance
        move.w #S60_LEGACY_DIV,(4,a6)
        clr.w (6,a6)
        clr.w (8,a6)
        cmp.w #29,($0346-S60_DATA,a4)
        beq .advance ; native thirtieth call removes, without further motion
        move.w ($034a-S60_DATA,a4),(6,a6)
        move.w ($0348-S60_DATA,a4),(8,a6)
.advance:
        subq.w #1,(4,a6)
        beq .event
        move.w (6,a6),d0
        ext.l d0
        move.w (10,a6),d1
        ext.l d1
        add.l d1,d0
        divs #S60_LEGACY_DIV,d0
        move.w d0,d1
        ext.l d1
        add.l d1,($10,a3)
        swap d0
        move.w d0,(10,a6)
        move.w (8,a6),d0
        ext.l d0
        move.w (12,a6),d1
        ext.l d1
        add.l d1,d0
        divs #S60_LEGACY_DIV,d0
        add.w d0,($18,a3)
        swap d0
        move.w d0,(12,a6)
        bra .done
.event:
        ; Undo only our first eleven substeps. The untouched native routine
        ; applies the full increment, completing this interval exactly once.
        move.w (6,a6),d0
        muls #11,d0
        divs #S60_LEGACY_DIV,d0
        ext.l d0
        sub.l d0,($10,a3)
        move.w (8,a6),d0
        muls #11,d0
        divs #S60_LEGACY_DIV,d0
        sub.w d0,($18,a3)
        clr.w (10,a6)
        clr.w (12,a6)
        S60_CALL $3d2a
        tst.l ($46c0-S60_DATA,a4)
        bne .done
.inactive:
        bsr s60_pickup_reset
.done:  movem.l (sp)+,d2/a3/a6
        rts
