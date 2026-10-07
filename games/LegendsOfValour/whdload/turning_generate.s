; Runtime one-degree ray tables. 68000-only integer arithmetic, no FPU/library.
; Inputs D0=width, D1=focal length, A0=180-row destination, A1=36-row legacy.
; Preserve all registers. Keep original rows (including unused padding) every
; fifth angle; generate only new angles with Q22 trigonometry.
_turn_generate
        movem.l d0-a6,-(sp)
        lea (_turn_gen_state,pc),a3
        move.w d0,(a3)
        move.w d1,(2,a3)
        addq.w #8,d0
        lsl.w #2,d0
        move.w d0,(4,a3)
        clr.w (6,a3)
        move.l a0,a5
        move.l a1,a6
.row
        move.l a5,a1
        moveq #0,d0
        move.w (6,a3),d0
        divu.w #5,d0
        swap d0
        tst.w d0
        bne .new
        move.w (4,a3),d0
        lsr.w #2,d0
        subq.w #1,d0
.copy   move.l (a6)+,(a1)+
        dbf d0,.copy
        bra .next
.new
        ; Clear only the selected destination row (including padding).
        move.w (4,a3),d0
        lsr.w #2,d0
        subq.w #1,d0
.clear  clr.l (a1)+
        dbf d0,.clear
        move.l a5,a1
        move.w (6,a3),d0
        cmp.w #90,d0
        bls .sin_index
        neg.w d0
        add.w #180,d0
.sin_index
        lsl.w #2,d0
        lea (_turn_sine,pc),a0
        move.l (a0,d0.w),d6
        move.w (6,a3),d0
        sub.w #90,d0
        bpl .cos_index
        neg.w d0
.cos_index
        lsl.w #2,d0
        move.l (a0,d0.w),d7
        cmp.w #90,(6,a3)
        bls .cos_sign
        neg.l d7
.cos_sign
        move.l d7,d0
        move.w (2,a3),d1
        add.w d1,d1
        bsr _turn_multiply
        move.l d0,d4
        move.l d6,d0
        move.w (a3),d1
        subq.w #1,d1
        bsr _turn_multiply
        sub.l d0,d4
        move.l d6,d0
        move.w (2,a3),d1
        add.w d1,d1
        bsr _turn_multiply
        move.l d0,d5
        move.l d7,d0
        move.w (a3),d1
        subq.w #1,d1
        bsr _turn_multiply
        add.l d0,d5
        add.l d6,d6
        add.l d7,d7
        move.w #-1,(8,a3)
        move.w (a3),(10,a3)
.column
        move.l d4,d0
        move.l d5,d1
        moveq #0,d2
        tst.l d0
        bmi .left
        tst.l d1
        bmi .bottom_right
        cmp.l d1,d0
        bhi .region
        moveq #1,d2
        bra .region
.bottom_right
        neg.l d1
        moveq #7,d2
        cmp.l d1,d0
        bhi .region
        moveq #6,d2
        bra .region
.left
        neg.l d0
        tst.l d1
        bmi .bottom_left
        moveq #2,d2
        cmp.l d0,d1
        bhi .region
        moveq #3,d2
        bra .region
.bottom_left
        neg.l d1
        moveq #4,d2
        cmp.l d1,d0
        bhi .region
        moveq #5,d2
.region
        cmp.w (8,a3),d2
        beq .values
        tst.w (8,a3)
        bpl .marker
        move.w d2,(a1)+
        bra .remember
.marker clr.w (a1)+
.remember
        move.w d2,(8,a3)
.values
        cmp.l d1,d0
        bls .ordered
        exg d0,d1
.ordered
        ; D0=minor, D1=major. Q16 ratio by restoring division.
        moveq #0,d2
        moveq #15,d3
.ratio
        add.l d0,d0
        add.w d2,d2
        cmp.l d1,d0
        bcs .ratio_next
        sub.l d1,d0
        addq.w #1,d2
.ratio_next
        dbf d3,.ratio
        cmp.w #2,d2
        bcc .ratio_store
        moveq #2,d2                 ; 0=marker, 1=DIVU overflow in native rays
.ratio_store
        move.w d2,(a1)+
        ; round(2^39 / major): unsigned 40/32 restoring division.
        move.l d1,d2
        lsr.l #1,d2
        move.l #128,d0
        moveq #31,d3
.scale
        add.l d2,d2
        addx.l d0,d0
        cmp.l d1,d0
        bcs .scale_next
        sub.l d1,d0
        addq.l #1,d2
.scale_next
        dbf d3,.scale
        move.w d2,(a1)+
        add.l d6,d4
        sub.l d7,d5
        subq.w #1,(10,a3)
        bne .column
.next
        adda.w (4,a3),a5
        addq.w #1,(6,a3)
        cmp.w #180,(6,a3)
        bcs .row
        movem.l (sp)+,d0-a6
        rts

; Signed D0.l times unsigned small D1.w, bounded signed 32-bit result.
_turn_multiply
        move.l d0,d2
        mulu.w d1,d0
        swap d2
        muls.w d1,d2
        swap d2
        clr.w d2
        add.l d2,d0
        rts

_turn_gen_state ds.w 6
        INCLUDE turning_trig.s
