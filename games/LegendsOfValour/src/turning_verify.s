; VERIFY-only table oracle. Expected hashes derive solely from the independent
; mathematical Q22 host model, excluding every copied legacy row.
_turn_verify_table
        movem.l d0-a6,-(sp)
        move.l a0,a2
        move.l a1,a4
        move.w d0,d7
        addq.w #8,d7
        lsl.w #2,d7
        move.l #$4f82abc5,d6
        cmp.w #192,d0
        beq .begin
        move.l #$d1d979c5,d6
        cmp.w #112,d0
        beq .begin
        move.l #$abf40145,d6
.begin  move.l #5381,d5
        moveq #0,d4
.row    move.l a2,a0
        moveq #0,d0
        move.w d4,d0
        divu.w #5,d0
        swap d0
        tst.w d0
        bne .generated
        move.w d7,d3
        lsr.w #1,d3
        subq.w #1,d3
.legacy move.w (a0)+,d0
        cmp.w (a4)+,d0
        bne .bad
        dbf d3,.legacy
        bra .next
.generated
        move.w d7,d3
        lsr.w #1,d3
        subq.w #1,d3
.hash   move.l d5,d0
        lsl.l #5,d5
        add.l d0,d5
        move.w (a0)+,d0
        eor.w d0,d5
        dbf d3,.hash
.next   adda.w d7,a2
        addq.w #1,d4
        cmp.w #180,d4
        bcs .row
        cmp.l d6,d5
        bne .bad
        lea (_turn_verified,pc),a0
        addq.l #1,(a0)
        lea (_turn_verified_views,pc),a0
        cmp.w #80,(2,sp)
        beq .count_view
        addq.l #4,a0
        cmp.w #112,(2,sp)
        beq .count_view
        addq.l #4,a0
.count_view
        addq.l #1,(a0)
        movem.l (sp)+,d0-a6
        rts
.bad    lea (_turn_verify_bad,pc),a0
        bra _c2p_abort
_turn_generation_fields dc.l 0,0,0
_turn_lifecycle_cycles dc.l 0
_turn_verified dc.l 0
_turn_verified_views dc.l 0,0,0
_turn_verify_bad dc.b "1 degree turning: generated ray-table mismatch",0
        EVEN
