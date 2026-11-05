C4QGuards:
 movem.l d0-d7/a0-a6,-(sp)
 lea QGuardSaved(pc),a1
 lea $6717c,a0
 moveq #2,d0
.save0: move.w (a0)+,(a1)+
 dbra d0,.save0
 lea $6719e,a0
 moveq #2,d0
.save1: move.w (a0)+,(a1)+
 dbra d0,.save1
 lea $682c6,a0
 moveq #2,d0
.save2: move.w (a0)+,(a1)+
 dbra d0,.save2
 lea $683c2,a0
 moveq #2,d0
.save3: move.w (a0)+,(a1)+
 dbra d0,.save3
 lea $66840,a0
 moveq #2,d0
.save4: move.w (a0)+,(a1)+
 dbra d0,.save4
 lea $66f94,a0
 moveq #0,d0
.save5: move.w (a0)+,(a1)+
 dbra d0,.save5
 lea $66be0,a0
 moveq #0,d0
.save6: move.w (a0)+,(a1)+
 dbra d0,.save6
 lea $1c222,a0
 moveq #0,d0
.save7: move.w (a0)+,(a1)+
 dbra d0,.save7
 lea $32f30,a0
 moveq #7,d0
.save8: move.w (a0)+,(a1)+
 dbra d0,.save8
 move.w #$4ef9,$6717c
 lea QGuardReturn(pc),a0
 move.l a0,$6717e
 move.w #$4ef9,$6719e
 lea QGuardReturn(pc),a0
 move.l a0,$671a0
 move.w #$4ef9,$682c6
 lea QGuardReturn(pc),a0
 move.l a0,$682c8
 move.w #$4ef9,$683c2
 lea QGuardReturn(pc),a0
 move.l a0,$683c4
 move.w #$4ef9,$66840
 lea QGuardReturn(pc),a0
 move.l a0,$66842
 lea QGuardCases(pc),a5
 move.w #88-1,d7
.next:
 move.w 4(a5),$66f94
 move.w 4(a5),$66be0
 move.w 6(a5),$1c222
 lea $32f30,a0
 moveq #7,d0
.seed: move.w 4(a5),(a0)+
 dbra d0,.seed
 move.l #123,-(sp)
 bsr.w QGuardRun
 addq.l #4,sp
 tst.w (a5)
 beq.b .countdown
 cmpi.w #1,(a5)
 beq.b .contact
 move.w $66be0,d0
 bra.b .compare
.countdown: move.w $66f94,d0
 bra.b .compare
.contact:
 move.w 2(a5),d0
 add.w d0,d0
 lea $32f30,a0
 move.w (a0,d0.w),d0
.compare:
 cmp.w 8(a5),d0
 bne.w QGuardBad
 lea QGuardChecked(pc),a0
 addq.l #1,(a0)
 adda.w #10,a5
 dbra d7,.next
 lea QGuardSaved(pc),a1
 lea $6717c,a0
 moveq #2,d0
.restore0: move.w (a1)+,(a0)+
 dbra d0,.restore0
 lea $6719e,a0
 moveq #2,d0
.restore1: move.w (a1)+,(a0)+
 dbra d0,.restore1
 lea $682c6,a0
 moveq #2,d0
.restore2: move.w (a1)+,(a0)+
 dbra d0,.restore2
 lea $683c2,a0
 moveq #2,d0
.restore3: move.w (a1)+,(a0)+
 dbra d0,.restore3
 lea $66840,a0
 moveq #2,d0
.restore4: move.w (a1)+,(a0)+
 dbra d0,.restore4
 lea $66f94,a0
 moveq #0,d0
.restore5: move.w (a1)+,(a0)+
 dbra d0,.restore5
 lea $66be0,a0
 moveq #0,d0
.restore6: move.w (a1)+,(a0)+
 dbra d0,.restore6
 lea $1c222,a0
 moveq #0,d0
.restore7: move.w (a1)+,(a0)+
 dbra d0,.restore7
 lea $32f30,a0
 moveq #7,d0
.restore8: move.w (a1)+,(a0)+
 dbra d0,.restore8
 movem.l (sp)+,d0-d7/a0-a6
 rts
QGuardRun:
 link a6,#-24
 tst.w (a5)
 beq.b .countdown
 cmpi.w #1,(a5)
 beq.b .contact
 jmp $6681c
.countdown: jmp $67164
.contact:
 move.w 2(a5),16(sp)
 move.w 2(a5),d0
 add.w d0,d0
 lea $32f30,a0
 adda.w d0,a0
 jmp $682a8
QGuardReturn:
 unlk a6
 rts
QGuardBad:
 lea error(pc),a0
 move.l #4102,(a0)
 bra.w C1Fault
QGuardChecked: dc.l 0
QGuardSaved: ds.b 52
QGuardCases:
 dc.w 0,0,-32768,1,32766
 dc.w 0,0,-2,1,-4
 dc.w 0,0,-1,1,-3
 dc.w 0,0,0,1,0
 dc.w 0,0,1,1,0
 dc.w 0,0,2,1,0
 dc.w 0,0,3,1,1
 dc.w 0,0,32767,1,32765
 dc.w 1,0,-32768,1,-32768
 dc.w 1,0,-2,1,-2
 dc.w 1,0,-1,1,-1
 dc.w 1,0,0,1,0
 dc.w 1,0,1,1,0
 dc.w 1,0,2,1,0
 dc.w 1,0,3,1,1
 dc.w 1,0,32767,1,32765
 dc.w 1,1,-32768,1,-32768
 dc.w 1,1,-2,1,-2
 dc.w 1,1,-1,1,-1
 dc.w 1,1,0,1,0
 dc.w 1,1,1,1,0
 dc.w 1,1,2,1,0
 dc.w 1,1,3,1,1
 dc.w 1,1,32767,1,32765
 dc.w 1,2,-32768,1,-32768
 dc.w 1,2,-2,1,-2
 dc.w 1,2,-1,1,-1
 dc.w 1,2,0,1,0
 dc.w 1,2,1,1,0
 dc.w 1,2,2,1,0
 dc.w 1,2,3,1,1
 dc.w 1,2,32767,1,32765
 dc.w 1,3,-32768,1,-32768
 dc.w 1,3,-2,1,-2
 dc.w 1,3,-1,1,-1
 dc.w 1,3,0,1,0
 dc.w 1,3,1,1,0
 dc.w 1,3,2,1,0
 dc.w 1,3,3,1,1
 dc.w 1,3,32767,1,32765
 dc.w 1,4,-32768,1,-32768
 dc.w 1,4,-2,1,-2
 dc.w 1,4,-1,1,-1
 dc.w 1,4,0,1,0
 dc.w 1,4,1,1,0
 dc.w 1,4,2,1,0
 dc.w 1,4,3,1,1
 dc.w 1,4,32767,1,32765
 dc.w 1,5,-32768,1,-32768
 dc.w 1,5,-2,1,-2
 dc.w 1,5,-1,1,-1
 dc.w 1,5,0,1,0
 dc.w 1,5,1,1,0
 dc.w 1,5,2,1,0
 dc.w 1,5,3,1,1
 dc.w 1,5,32767,1,32765
 dc.w 1,6,-32768,1,-32768
 dc.w 1,6,-2,1,-2
 dc.w 1,6,-1,1,-1
 dc.w 1,6,0,1,0
 dc.w 1,6,1,1,0
 dc.w 1,6,2,1,0
 dc.w 1,6,3,1,1
 dc.w 1,6,32767,1,32765
 dc.w 1,7,-32768,1,-32768
 dc.w 1,7,-2,1,-2
 dc.w 1,7,-1,1,-1
 dc.w 1,7,0,1,0
 dc.w 1,7,1,1,0
 dc.w 1,7,2,1,0
 dc.w 1,7,3,1,1
 dc.w 1,7,32767,1,32765
 dc.w 2,0,-32768,0,-32768
 dc.w 2,0,-32768,1,32766
 dc.w 2,0,-2,0,-2
 dc.w 2,0,-2,1,-4
 dc.w 2,0,-1,0,-1
 dc.w 2,0,-1,1,-3
 dc.w 2,0,0,0,0
 dc.w 2,0,0,1,0
 dc.w 2,0,1,0,1
 dc.w 2,0,1,1,0
 dc.w 2,0,2,0,2
 dc.w 2,0,2,1,0
 dc.w 2,0,3,0,3
 dc.w 2,0,3,1,1
 dc.w 2,0,32767,0,32767
 dc.w 2,0,32767,1,32765
