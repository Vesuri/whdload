C4TestRecovery:
 movem.l d0-d7/a0-a6,-(sp)
 lea C4RecoverySaved(pc),a1
 lea $2268e,a0
 moveq #7,d0
.save0:
 move.w (a0)+,(a1)+
 dbra d0,.save0
 lea $22356,a0
 moveq #15,d0
.save1:
 move.w (a0)+,(a1)+
 dbra d0,.save1
 lea $22376,a0
 moveq #15,d0
.save2:
 move.w (a0)+,(a1)+
 dbra d0,.save2
 lea $22604,a0
 moveq #3,d0
.save3:
 move.w (a0)+,(a1)+
 dbra d0,.save3
 lea $2260c,a0
 moveq #3,d0
.save4:
 move.w (a0)+,(a1)+
 dbra d0,.save4
 lea $1c21e,a0
 moveq #0,d0
.save5:
 move.w (a0)+,(a1)+
 dbra d0,.save5
 lea $66c7c,a0
 moveq #0,d0
.save6:
 move.w (a0)+,(a1)+
 dbra d0,.save6
 lea $66f94,a0
 moveq #0,d0
.save7:
 move.w (a0)+,(a1)+
 dbra d0,.save7
 lea $1c222,a0
 moveq #0,d0
.save8:
 move.w (a0)+,(a1)+
 dbra d0,.save8
 lea $1c1e0,a0
 moveq #0,d0
.save9:
 move.w (a0)+,(a1)+
 dbra d0,.save9
 lea $1c8ae,a0
 moveq #0,d0
.save10:
 move.w (a0)+,(a1)+
 dbra d0,.save10
 lea $6a694,a0
 moveq #0,d0
.save11:
 move.w (a0)+,(a1)+
 dbra d0,.save11
 lea $6a60a,a0
 moveq #7,d0
.save12:
 move.w (a0)+,(a1)+
 dbra d0,.save12
 lea fuel_remainders(pc),a0
 moveq #7,d0
.save13:
 move.w (a0)+,(a1)+
 dbra d0,.save13
 lea wear_remainders+8(pc),a0
 moveq #7,d0
.save14:
 move.w (a0)+,(a1)+
 dbra d0,.save14
 lea public_bindings(pc),a5
 dc.w $dbfc
 dc.l C4RecoveryCases-public_bindings
 moveq #83,d7
.next:
 clr.w $1c21e
 clr.w $66c7c
 clr.w $66f94
 clr.w $1c222
 move.w 4(a5),$1c1e0
 move.w #17,$1c8ae
 move.w 2(a5),d0
 cmpi.w #1,d0
 bne.b .gate2
 move.w #1,$1c21e
.gate2:
 cmpi.w #2,d0
 bne.b .gate3
 move.w #1,$66c7c
.gate3:
 cmpi.w #3,d0
 bne.b .gate4
 move.w #1,$66f94
.gate4:
 cmpi.w #4,d0
 bne.b .states
 move.w #1,$1c222
.states:
 moveq #0,d6
.car:
 move.w d6,d0
 add.w d0,d0
 lea $2268e,a0
 move.w (a5),(a0,d0.w)
 lea fuel_remainders(pc),a0
 move.w #4,(a0,d0.w)
 lea wear_remainders+8(pc),a0
 move.w #4,(a0,d0.w)
 add.w d0,d0
 lea $22356,a0
 move.l #1000,(a0,d0.w)
 lea $22376,a0
 move.l #12345,(a0,d0.w)
 lea $22604,a0
 clr.b (a0,d6.w)
 lea $2260c,a0
 clr.b (a0,d6.w)
 cmpi.w #5,2(a5)
 bne.b .nextcar
 btst #0,d6
 beq.b .nextcar
 move.b #1,(a0,d6.w)
.nextcar:
 addq.w #1,d6
 cmpi.w #8,d6
 blo.b .car
 move.w #$1234,$6a694
 move.w #1000,$6a60a
 lea $6a60c,a0
 moveq #6,d0
.projections:
 clr.w (a0)+
 dbra d0,.projections
 movem.l d0-d7/a0-a6,-(sp)
 bsr.w recovery_tick
 movem.l (sp)+,d0-d7/a0-a6
 cmpi.w #$1234,$6a694
 bne.w C4RecoveryBad
 lea 6(a5),a1
 lea $2268e,a0
 moveq #7,d0
.check0:
 move.w (a0)+,d1
 cmp.w (a1)+,d1
 bne.w C4RecoveryBad
 dbra d0,.check0
 lea $22356,a0
 moveq #15,d0
.check1:
 move.w (a0)+,d1
 cmp.w (a1)+,d1
 bne.w C4RecoveryBad
 dbra d0,.check1
 lea $22376,a0
 moveq #15,d0
.check2:
 move.w (a0)+,d1
 cmp.w (a1)+,d1
 bne.w C4RecoveryBad
 dbra d0,.check2
 lea $22604,a0
 moveq #3,d0
.check3:
 move.w (a0)+,d1
 cmp.w (a1)+,d1
 bne.w C4RecoveryBad
 dbra d0,.check3
 lea fuel_remainders(pc),a0
 moveq #7,d0
.check4:
 move.w (a0)+,d1
 cmp.w (a1)+,d1
 bne.w C4RecoveryBad
 dbra d0,.check4
 lea wear_remainders+8(pc),a0
 moveq #7,d0
.check5:
 move.w (a0)+,d1
 cmp.w (a1)+,d1
 bne.w C4RecoveryBad
 dbra d0,.check5
 lea C4RecoveryChecked(pc),a0
 addq.l #1,(a0)
 adda.w #126,a5
 dbra d7,.next
 lea C4RecoverySaved(pc),a1
 lea $2268e,a0
 moveq #7,d0
.restore0:
 move.w (a1)+,(a0)+
 dbra d0,.restore0
 lea $22356,a0
 moveq #15,d0
.restore1:
 move.w (a1)+,(a0)+
 dbra d0,.restore1
 lea $22376,a0
 moveq #15,d0
.restore2:
 move.w (a1)+,(a0)+
 dbra d0,.restore2
 lea $22604,a0
 moveq #3,d0
.restore3:
 move.w (a1)+,(a0)+
 dbra d0,.restore3
 lea $2260c,a0
 moveq #3,d0
.restore4:
 move.w (a1)+,(a0)+
 dbra d0,.restore4
 lea $1c21e,a0
 moveq #0,d0
.restore5:
 move.w (a1)+,(a0)+
 dbra d0,.restore5
 lea $66c7c,a0
 moveq #0,d0
.restore6:
 move.w (a1)+,(a0)+
 dbra d0,.restore6
 lea $66f94,a0
 moveq #0,d0
.restore7:
 move.w (a1)+,(a0)+
 dbra d0,.restore7
 lea $1c222,a0
 moveq #0,d0
.restore8:
 move.w (a1)+,(a0)+
 dbra d0,.restore8
 lea $1c1e0,a0
 moveq #0,d0
.restore9:
 move.w (a1)+,(a0)+
 dbra d0,.restore9
 lea $1c8ae,a0
 moveq #0,d0
.restore10:
 move.w (a1)+,(a0)+
 dbra d0,.restore10
 lea $6a694,a0
 moveq #0,d0
.restore11:
 move.w (a1)+,(a0)+
 dbra d0,.restore11
 lea $6a60a,a0
 moveq #7,d0
.restore12:
 move.w (a1)+,(a0)+
 dbra d0,.restore12
 lea fuel_remainders(pc),a0
 moveq #7,d0
.restore13:
 move.w (a1)+,(a0)+
 dbra d0,.restore13
 lea wear_remainders+8(pc),a0
 moveq #7,d0
.restore14:
 move.w (a1)+,(a0)+
 dbra d0,.restore14
 movem.l (sp)+,d0-d7/a0-a6
 rts
C4RecoveryBad:
 lea error(pc),a0
 move.l #4001,(a0)
 bra.w C1Fault
C4RecoveryChecked: dc.l 0
C4RecoverySaved: ds.b 158
