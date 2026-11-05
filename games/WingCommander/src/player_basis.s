; Field steering keeps a Q14 orientation; only its rounded Q8 projection is
; exposed to the game. Never feed that projection back into successive turns.
; Native/script pose changes and scene boundaries revoke the private history.
; All arithmetic is 68000-safe (signed word products, bounded long sums).
player_basis_reset:
        movem.l a0,-(sp)
        lea     player_basis_valid(pc),a0
        clr.w   (a0)
        movem.l (sp)+,a0
        rts

player_basis_sync:
        movem.l d0-d3/a0-a3,-(sp)
        lea     player_basis_native(pc),a1
        lea     player_basis_offsets(pc),a2
        moveq   #2,d2
.compare_vector:
        movea.l a4,a0
        adda.w  (a2)+,a0
        moveq   #2,d3
.compare:
        move.l  (a0)+,d0
        cmp.l   (a1)+,d0
        bne.s   .seed
        dbra    d3,.compare
        dbra    d2,.compare_vector
        tst.w   player_basis_valid(pc)
        bne.s   .done
.seed:
        lea     player_basis_values(pc),a1
        lea     player_basis_offsets(pc),a2
        lea     player_basis_native(pc),a3
        moveq   #2,d2
.seed_vector:
        movea.l a4,a0
        adda.w  (a2)+,a0
        moveq   #2,d3
.seed_axis:
        move.l  (a0)+,d0
        move.l  d0,(a3)+
        lsl.l   #6,d0
        move.w  d0,(a1)+
        dbra    d3,.seed_axis
        dbra    d2,.seed_vector
        lea     player_basis_valid(pc),a0
        move.w  #1,(a0)
.done:
        movem.l (sp)+,d0-d3/a0-a3
        rts

; D0 angle in native degrees, D4 pitch/yaw/roll. Preserve caller's axis state.
player_basis_rotate:
        movem.l d0-d7/a0-a2,-(sp)
        move.w  d0,d6
        bsr.w   player_basis_sine
        move.w  d0,d5
        move.w  d6,d0
        addi.w  #90,d0
        bsr.w   player_basis_sine
        move.w  d0,d6
        lea     player_basis_values+6(pc),a0
        lea     player_basis_values(pc),a1
        tst.w   d4
        beq.s   .pair
        cmpi.w  #1,d4
        bne.s   .roll
        lea     player_basis_values+12(pc),a0
        neg.w   d5
        bra.s   .pair
.roll:
        lea     player_basis_values+12(pc),a1
.pair:
        moveq   #2,d7
.axis:
        move.w  (a0),d2
        move.w  (a1),d3
        move.w  d2,d0
        muls.w  d6,d0
        move.w  d3,d1
        muls.w  d5,d1
        sub.l   d1,d0
        bsr.w   player_basis_round
        move.w  d0,(a0)+
        move.w  d3,d0
        muls.w  d6,d0
        move.w  d2,d1
        muls.w  d5,d1
        add.l   d1,d0
        bsr.w   player_basis_round
        move.w  d0,(a1)+
        dbra    d7,.axis
        movem.l (sp)+,d0-d7/a0-a2
        rts

; Round Q28 to Q14 symmetrically, including negative values. D1 scratch.
player_basis_round:
        move.l  d0,d1
        bpl.s   .positive
        neg.l   d0
.positive:
        addi.l  #8192,d0
        asr.l   #7,d0
        asr.l   #7,d0
        tst.l   d1
        bpl.s   .done
        neg.l   d0
.done:  rts

; Sine for a signed integer degree, quarter-wave Q14 table, not native Q8.
player_basis_sine:
        ext.l   d0
        divs.w  #360,d0
        swap    d0
        tst.w   d0
        bpl.s   .positive
        addi.w  #360,d0
.positive:
        moveq   #1,d1
        cmpi.w  #180,d0
        blt.s   .half
        subi.w  #180,d0
        neg.w   d1
.half:
        cmpi.w  #90,d0
        ble.s   .lookup
        neg.w   d0
        addi.w  #180,d0
.lookup:
        add.w   d0,d0
        lea     player_basis_sines(pc),a2
        move.w  (a2,d0.w),d0
        muls.w  d1,d0
        rts

; Preserve orthogonality in Q14 before projecting to native Q8. Each vector is
; near unit length; one Newton inverse-length step bounds accumulated scale.
player_basis_publish:
        movem.l d0-d7/a0-a3,-(sp)
        lea     player_basis_values+6(pc),a0
        lea     player_basis_values(pc),a1
        lea     player_basis_values+12(pc),a2
        bsr.w   player_basis_cross
        lea     player_basis_values(pc),a0
        lea     player_basis_values+12(pc),a1
        lea     player_basis_values+6(pc),a2
        bsr.w   player_basis_cross
        lea     player_basis_values(pc),a0
        moveq   #2,d7
.vector:
        move.w  (a0),d0
        muls.w  d0,d0
        move.w  2(a0),d1
        muls.w  d1,d1
        add.l   d1,d0
        move.w  4(a0),d1
        muls.w  d1,d1
        add.l   d1,d0
        bsr.w   player_basis_round
        move.w  #49152,d6
        sub.w   d0,d6
        lsr.w   #1,d6
        moveq   #2,d3
.normalize:
        move.w  (a0),d0
        muls.w  d6,d0
        bsr.w   player_basis_round
        move.w  d0,(a0)+
        dbra    d3,.normalize
        dbra    d7,.vector
        lea     player_basis_values(pc),a1
        lea     player_basis_offsets(pc),a2
        lea     player_basis_native(pc),a3
        moveq   #2,d2
.export_vector:
        movea.l a4,a0
        adda.w  (a2)+,a0
        moveq   #2,d3
.export:
        move.w  (a1)+,d0
        ext.l   d0
        move.l  d0,d1
        bpl.s   .export_positive
        neg.l   d0
.export_positive:
        addi.l  #32,d0
        asr.l   #6,d0
        tst.l   d1
        bpl.s   .store
        neg.l   d0
.store:
        move.l  d0,(a0)+
        move.l  d0,(a3)+
        dbra    d3,.export
        dbra    d2,.export_vector
        movem.l (sp)+,d0-d7/a0-a3
        rts

; A2 = A0 cross A1; distinct vectors, D0/D1 scratch.
player_basis_cross:
        move.w  2(a0),d0
        muls.w  4(a1),d0
        move.w  4(a0),d1
        muls.w  2(a1),d1
        sub.l   d1,d0
        bsr.w   player_basis_round
        move.w  d0,(a2)
        move.w  4(a0),d0
        muls.w  (a1),d0
        move.w  (a0),d1
        muls.w  4(a1),d1
        sub.l   d1,d0
        bsr.w   player_basis_round
        move.w  d0,2(a2)
        move.w  (a0),d0
        muls.w  2(a1),d0
        move.w  2(a0),d1
        muls.w  (a1),d1
        sub.l   d1,d0
        bsr.w   player_basis_round
        move.w  d0,4(a2)
        rts

player_basis_offsets: dc.w $214a,$3452,$3752
player_basis_valid: dc.w 0
player_basis_values: dcb.w 9,0
player_basis_native: dcb.l 9,0
; round(16384 * sin(degrees * pi / 180)), degrees 0..90.
player_basis_sines:
        dc.w 0,286,572,857,1143,1428,1713,1997,2280,2563
        dc.w 2845,3126,3406,3686,3964,4240,4516,4790,5063,5334
        dc.w 5604,5872,6138,6402,6664,6924,7182,7438,7692,7943
        dc.w 8192,8438,8682,8923,9162,9397,9630,9860,10087,10311
        dc.w 10531,10749,10963,11174,11381,11585,11786,11982,12176,12365
        dc.w 12551,12733,12911,13085,13255,13421,13583,13741,13894,14044
        dc.w 14189,14330,14466,14598,14726,14849,14968,15082,15191,15296
        dc.w 15396,15491,15582,15668,15749,15826,15897,15964,16026,16083
        dc.w 16135,16182,16225,16262,16294,16322,16344,16362,16374,16382
        dc.w 16384
