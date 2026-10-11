; Pointer-walking equivalent of native $3ab8's active-list loop.
; Keep the original stack frame and resume its secondary-object/reset tail.
; Player coordinates are constant during the list walk, even with duplicates:
; the player pointer itself is excluded before any subtraction.
s60_recenter:
        link a5,#-16
        movem.l d4-d7/a3,-(sp)
        movem.l d2-d3/a1-a2,-(sp)
        move.w ($43b2-S60_DATA,a4),d7
        ble .tail
        subq.w #1,d7
        lea ($3fb2-S60_DATA,a4),a1
        move.l ($43c0-S60_DATA,a4),a2
        move.l (8,a2),d2
        move.l (12,a2),d3
        moveq #15,d4
        and.w ($1e96-S60_DATA,a4),d4
        move.l #32768,d6
        moveq #1,d5
        swap d5
.loop:  move.l (a1)+,a3
        cmpa.l a2,a3
        beq .next
        cmp.w #7,(2,a3)
        beq .next
        sub.l d2,(8,a3)
        sub.l d3,(12,a3)
        tst.w d4
        bne .next
        ; Preserve native D1's last scratch value as well as wrapped positions.
        move.l (8,a3),d0
        cmp.l d6,d0
        ble .x_low
        sub.l d5,(8,a3)
        bra .z
.x_low: move.l d6,d0
        neg.l d0
        move.l (8,a3),d1
        cmp.l d0,d1
        bge .z
        add.l d5,(8,a3)
.z:     move.l (12,a3),d0
        cmp.l d6,d0
        ble .z_low
        sub.l d5,(12,a3)
        bra .next
.z_low: move.l d6,d0
        neg.l d0
        move.l (12,a3),d1
        cmp.l d0,d1
        bge .next
        add.l d5,(12,a3)
.next:  dbf d7,.loop
        moveq #0,d7
        add.w d7,d7 ; native final positive loop-index increment clears X
.tail:  movem.l (sp)+,d2-d3/a1-a2
        move.l (s60_code,pc),a0
        adda.l #$3b5e,a0
        jmp (a0)
