        IFD VERIFY
        IFD BOSS_GATE_TEST
s60_gate_native: ds.b 16
        rts
s60_gate_results:
        dc.b 'BG60'
        dc.w 0,0,0 ; cases, errors, first failing case
        dc.b 0,0 ; expected, actual at first failure
s60_gate_actor: ds.b $6e
s60_gate_enemy: ds.b $6e
s60_gate_saved: ds.b 1024
s60_test_boss_gate:
        move.l (s60_ticks,pc),d0
        cmp.l #BOSS_GATE_TEST,d0
        bne .done
        move.w (s60_gate_results+4,pc),d0
        bne .done
        movem.l d0-d7/a0-a3,-(sp)
        move.w ($43b2-S60_DATA,a4),-(sp)
        moveq #0,d0
        move.b ($1efc-S60_DATA,a4),d0
        move.w d0,-(sp)
        lea ($3fb2-S60_DATA,a4),a0
        lea (s60_gate_saved,pc),a1
        move.w #255,d0
.save:  move.l (a0)+,(a1)+
        dbf d0,.save
        lea (s60_gate_actor,pc),a3
        move.l a3,($3fb2-S60_DATA,a4)
        move.w #1,($43b2-S60_DATA,a4)
        moveq #0,d7
.classes:
        move.b d7,($54,a3)
        bsr .compare
        addq.w #1,d7
        cmp.w #256,d7
        bne .classes
        clr.w ($43b2-S60_DATA,a4)
        bsr .compare
        move.w #-1,($43b2-S60_DATA,a4)
        bsr .compare
        lea (s60_gate_actor,pc),a3
        clr.b ($54,a3)
        lea (s60_gate_enemy,pc),a2
        move.b #$ff,($54,a2)
        lea ($3fb2-S60_DATA,a4),a0
        move.w #255,d0
.fill:  move.l a3,(a0)+
        dbf d0,.fill
        move.w #256,($43b2-S60_DATA,a4)
        bsr .compare
        move.l a2,($3fb2-S60_DATA,a4)
        bsr .compare
        lea (s60_gate_actor,pc),a3
        move.l a3,($3fb2-S60_DATA,a4)
        move.l a2,($3fb2+255*4-S60_DATA,a4)
        bsr .compare
        lea (s60_gate_actor,pc),a3
        move.l a3,($3fb2+255*4-S60_DATA,a4)
        move.l a2,($3fb2+127*4-S60_DATA,a4)
        bsr .compare
        lea (s60_gate_saved,pc),a0
        lea ($3fb2-S60_DATA,a4),a1
        move.w #255,d0
.restore:
        move.l (a0)+,(a1)+
        dbf d0,.restore
        move.w (sp)+,d0
        move.b d0,($1efc-S60_DATA,a4)
        move.w (sp)+,($43b2-S60_DATA,a4)
        movem.l (sp)+,d0-d7/a0-a3
.done:  rts
.compare:
        move.b #1,($1efc-S60_DATA,a4)
        move.w ($43b2-S60_DATA,a4),d2
        ble .expected
        lea ($3fb2-S60_DATA,a4),a0
        bra .test
.native:
        move.l (a0)+,a3
        bsr s60_gate_native ; original $c074..$c083, including relocated CLR
.test:  dbf d2,.native
.expected:
        moveq #0,d3
        move.b ($1efc-S60_DATA,a4),d3
        eori.b #1,($1efc-S60_DATA,a4) ; stale opposite value must be replaced
        bsr s60_boss_gate
        lea (s60_gate_results,pc),a1
        cmp.b ($1efc-S60_DATA,a4),d3
        beq .count
        addq.w #1,(6,a1)
        cmp.w #1,(6,a1)
        bne .count
        move.w (4,a1),(8,a1)
        move.b d3,(10,a1)
        move.b ($1efc-S60_DATA,a4),(11,a1)
.count: addq.w #1,(4,a1)
        rts
        ENDC
        ENDC
