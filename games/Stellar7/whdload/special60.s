; Continuous motion for the native $f328 enemy callback. Decisions retain one
; update per N calls; vertical and charge motion are integrated each tick.
; These non-projectile records reuse word 4 for phase (bit 15 = extra charge),
; word 6 for the signed native vertical increment, and word 62 for its remainder.
s60_special_install:
        move.l (s60_code,pc),a0
        adda.l #$f328,a0
        cmp.l #$48e72010,(a0)
        bne s60_bad
        cmp.l #$266f000c,(4,a0)
        bne s60_bad
        rts
s60_special_ai:
        movem.l d2-d4/a2-a3/a6,-(sp)
        bsr s60_motion_record
        move.w (4,a6),d0
        and.w #$7fff,d0
        bne .integrate
        move.w #S60_LEGACY_DIV,(4,a6)
        clr.w (6,a6)
        bsr s60_special_prepare
        cmp.l (a6),a3 ; native type-13 collision can delete this actor
        bne s60_special_done
.integrate:
        move.w (6,a6),d0
        ext.l d0
        move.w (62,a6),d1
        ext.l d1
        add.l d1,d0
        divs #S60_LEGACY_DIV,d0
        move.w d0,d1
        ext.l d1
        add.l d1,($10,a3)
        swap d0
        move.w d0,(62,a6)
        btst #7,(4,a6)
        beq s60_special_count
        move.l a3,-(sp)
        S60_CALL $8682
s60_special_charge_return:
        addq.l #4,sp
        bra s60_special_count
s60_special_count:
        subq.w #1,(4,a6)
s60_special_done:
        movem.l (sp)+,d2-d4/a2-a3/a6
        rts

s60_special_prepare:
        move.w (2,a3),d0
        cmp.w #13,d0
        beq .type13
        cmp.w #47,d0
        beq .type47
        cmp.w #48,d0
        beq .type48
        rts
.type13:
        move.l ($66,a3),d1
        beq .fall13
        move.l d1,a0
        cmp.w #13,(2,a0)
        beq .native13
        cmp.l ($43c0-S60_DATA,a4),d1
        beq .done
        clr.l ($66,a3)
        move.w ($1218-S60_DATA,a4),d1 ; native table $11fe + 2*13
        ext.l d1
        move.l ($10,a3),d0
        add.l d1,d0
        cmp.l #1000,d0
        ble .climb13
        move.l #1000,d0
        sub.l ($10,a3),d0
        move.w d0,(6,a6)
        rts
.climb13:
        move.w d1,(6,a6)
        bra .steer
.fall13:
        move.l ($10,a3),d0
        ble .steer
        move.w ($1218-S60_DATA,a4),d1
        ext.l d1
        cmp.l d1,d0
        bge .fall_amount
        move.l d0,d1
.fall_amount:
        neg.w d1
        move.w d1,(6,a6)
        bra .steer
.native13:
        move.l a3,-(sp)
        S60_CALL $f328 ; preserve removal, count and explosion behavior
        addq.l #4,sp
        rts
.type47:
        bsr .descent
        tst.b ($5b,a3)
        beq .steer47
        subq.b #1,($5b,a3)
        bset #7,(4,a6)
        rts
.steer47:
        move.w ($5e,a3),($18,a3)
        move.b ($56,a3),d0
        addq.b #1,d0
        and.b #3,d0
        move.b d0,($56,a3)
        bra .steer
.type48:
        bsr .descent
        move.b ($5b,a3),d0
        beq .transform
        subq.b #1,d0
        move.b d0,($5b,a3)
        cmp.b #13,d0
        bge .done
        moveq #13,d1
        sub.b d0,d1
        move.b d1,($56,a3)
        rts
.transform:
        move.w #47,(2,a3)
        move.b #60,($5b,a3)
        move.w #100,($40,a3)
        S60_CALL $116ec
        move.w d0,($18,a3)
.done:  rts
.descent:
        tst.l ($10,a3)
        ble .done
        move.w #-50,(6,a6)
        rts
.steer:
        move.l a3,-(sp)
        S60_CALL $f748
        addq.l #4,sp
        rts
