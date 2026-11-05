; Test-only fixed render poses. Full simulation still executes.
HeavyInit:
 lea HeavyAnchor(pc),a0
 move.w $6a60a,(a0)
 move.w $6a66a,d0
 sub.w $6a67a,d0
 move.w d0,2(a0)
 cmpi.l #$4e56ffea,$69e44
 bne.w C1Fault
 cmpi.l #$48e73c00,$69e48
 bne.w C1Fault
 lea HeavyCar(pc),a0
 move.w #$4ef9,$69e44
 move.l a0,$69e46
 move.w #$4e71,$69e4a
 move.w C1Control(pc),d0
 cmpi.w #2,d0
 bne.w .done
 lea HeavyNativeBegin(pc),a0
 move.w #$4ef9,$65606
 move.l a0,$65608
 lea HeavyNativeEnd(pc),a0
 move.w #$4ef9,$65d6e
 move.l a0,$65d70
 lea C1Vbl(pc),a0
 move.w #$4eb9,$24946
 move.l a0,$24948
.done:
 rts
HeavyNativeBegin:
 bsr.w HeavyBegin
 move.w $1c6a2,d0
 jmp $6560c
HeavyNativeEnd:
 bsr.w HeavyEnd
 tst.w $66f94
 jmp $65d74
HeavyBegin:
 movem.l d0-d3/a0-a3,-(sp)
 move.w sr,-(sp)
 lea HeavySaved(pc),a1
 lea $6a60a,a0
 moveq #3,d0
.save0:
 move.l (a0)+,(a1)+
 dbra d0,.save0
 lea $6a61a,a0
 moveq #3,d0
.save1:
 move.l (a0)+,(a1)+
 dbra d0,.save1
 lea $6a62a,a0
 moveq #3,d0
.save2:
 move.l (a0)+,(a1)+
 dbra d0,.save2
 lea $6a66a,a0
 moveq #3,d0
.save3:
 move.l (a0)+,(a1)+
 dbra d0,.save3
 lea $6a67a,a0
 moveq #3,d0
.save4:
 move.l (a0)+,(a1)+
 dbra d0,.save4
 lea $2268e,a0
 moveq #3,d0
.save5:
 move.l (a0)+,(a1)+
 dbra d0,.save5
 move.w $1c6a2,(a1)+
 move.w $66f96,(a1)+
 move.w $66c7c,(a1)
 lea HeavyFixed(pc),a1
 lea $6a60a,a0
 moveq #3,d0
.fixed0:
 move.l (a1)+,(a0)+
 dbra d0,.fixed0
 lea $6a61a,a0
 moveq #3,d0
.fixed1:
 move.l (a1)+,(a0)+
 dbra d0,.fixed1
 lea $6a62a,a0
 moveq #3,d0
.fixed2:
 move.l (a1)+,(a0)+
 dbra d0,.fixed2
 lea $6a66a,a0
 moveq #3,d0
.fixed3:
 move.l (a1)+,(a0)+
 dbra d0,.fixed3
 lea $6a67a,a0
 moveq #3,d0
.fixed4:
 move.l (a1)+,(a0)+
 dbra d0,.fixed4
 lea $2268e,a0
 moveq #3,d0
.fixed5:
 move.l (a1)+,(a0)+
 dbra d0,.fixed5
 move.w (a1)+,$1c6a2
 move.w (a1)+,$66f96
 move.w (a1),$66c7c
 lea HeavyCarCount(pc),a0
 clr.l (a0)
 clr.l 4(a0)
HeavyStartDone:
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d3/a0-a3
 rts
HeavyCar:
 move.l d0,-(sp)
 move.l a0,-(sp)
 move.w sr,-(sp)
 lea HeavyCarCount(pc),a0
 addq.l #1,(a0)
 moveq #0,d0
 move.l 30(sp),d0
 cmpi.w #7,d0
 bhi.w C1Fault
 bset d0,7(a0)
 move.w (sp)+,ccr
 move.l (sp)+,a0
 move.l (sp)+,d0
 link a6,#-22
 movem.l d2-d5,-(sp)
 jmp $69e4c
HeavyEnd:
 movem.l d0-d3/a0-a3,-(sp)
 move.w sr,-(sp)
 lea HeavyFrames(pc),a0
 addq.l #1,(a0)
 move.l HeavyCarCount(pc),d0
 cmpi.l #7,d0
 bne.b .incomplete
 move.l HeavyCarMask(pc),d0
 cmpi.l #254,d0
 beq.b .restore
.incomplete:
 lea HeavyIncomplete(pc),a0
 addq.l #1,(a0)
.restore:
 lea HeavySaved(pc),a0
 lea $6a60a,a1
 moveq #3,d0
.restore0:
 move.l (a0)+,(a1)+
 dbra d0,.restore0
 lea $6a61a,a1
 moveq #3,d0
.restore1:
 move.l (a0)+,(a1)+
 dbra d0,.restore1
 lea $6a62a,a1
 moveq #3,d0
.restore2:
 move.l (a0)+,(a1)+
 dbra d0,.restore2
 lea $6a66a,a1
 moveq #3,d0
.restore3:
 move.l (a0)+,(a1)+
 dbra d0,.restore3
 lea $6a67a,a1
 moveq #3,d0
.restore4:
 move.l (a0)+,(a1)+
 dbra d0,.restore4
 lea $2268e,a1
 moveq #3,d0
.restore5:
 move.l (a0)+,(a1)+
 dbra d0,.restore5
 move.w (a0)+,$1c6a2
 move.w (a0)+,$66f96
 move.w (a0),$66c7c
HeavyRestored:
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d3/a0-a3
 rts
HeavyFrames: dc.l 0
HeavyIncomplete: dc.l 0
HeavyCarCount: dc.l 0
HeavyCarMask: dc.l 0
HeavyAnchor: dc.w 0,0
HeavyX: dc.w 0,-60,-40,-20,0,20,40,60
HeavyZ: dc.w 32,130,190,250,310,250,190,130
HeavySaved: ds.b 102

HeavyFixed:
 dc.b 3,52,3,53,3,55,3,56,3,58,3,59,3,61,3,62
 dc.b 1,94,254,162,1,94,254,162,1,94,254,162,1,94,254,162
 dc.b 0,251,1,251,0,251,1,251,0,251,1,251,0,251,1,251
 dc.b 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
 dc.b 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
 dc.b 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
 dc.b 0,0,0,0,0,0
