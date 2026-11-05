C4QEvents:
 movem.l d0-d7/a0-a6,-(sp)
 lea QOriginal(pc),a1
 bsr.w QSave
 move.l $6d684,-(sp)
 move.l $6d688,-(sp)
 move.l $6d68c,-(sp)
 move.w $6d690,-(sp)
 move.l $24eec,-(sp)
 move.l $24ef0,-(sp)
 move.w $24ef4,-(sp)
 move.w #$4ef9,$24eec
 lea QRng(pc),a0
 move.l a0,$24eee
 lea QCases(pc),a5
 move.w #420-1,d7
.next:
 lea QOriginal(pc),a1
 bsr.w QRestore
 move.w (a5),$32fbc
 lea $2268e,a0
 moveq #7,d0
.status: move.w 2(a5),(a0)+
 dbra d0,.status
 lea $66c3e,a0
 moveq #13,d0
.components: move.l #$3fffff,(a0)+
 dbra d0,.components
 clr.w $6ef52
 move.w #200,$66c76
 move.w #1,$1c1c4
 lea $1c5dc,a0
 moveq #7,d0
.threshold: move.w #32767,(a0)+
 dbra d0,.threshold
 lea $24f60,a0
 moveq #55,d0
.seed: move.w 6(a5),d1
 mulu.w d0,d1
 move.w d1,(a0)+
 dbra d0,.seed
 move.w 4(a5),d0
 tst.w (a5)
 bne.b .opponent
 cmpi.w #13,d0
 beq.b .ready
 cmpi.w #6,d0
 bhs.b .component
 lsl.w #2,d0
 lea QTyres(pc),a0
 move.l (a0,d0.w),a0
 clr.l (a0)
 bra.b .ready
.component:
 subi.w #6,d0
 lsl.w #2,d0
 lea QParts(pc),a0
 move.l (a0,d0.w),a0
 clr.l (a0)
 bra.b .ready
.opponent:
 lea $22356,a0
 moveq #7,d1
.tyre: move.l #70000,(a0)+
 dbra d1,.tyre
 move.w (a5),d1
 lsl.w #2,d1
 lea $22356,a0
 subq.w #1,d0
 ext.l d0
 add.l d0,(a0,d1.w)
.ready:
 lea QRngCount(pc),a0
 clr.l (a0)
 lea QInitial(pc),a1
 bsr.w QSave
 ; Independent oracle: execute original native event body once per pulse,
 ; re-entering its original eligibility guards each time.
 move.w #$4ef9,$6d684
 lea QNativeReturn(pc),a0
 move.l a0,$6d686
 bsr.w QNativePulse
 bsr.w QNativePulse
 lea QExpected(pc),a1
 bsr.w QSave
 lea QExpectedRng(pc),a0
 move.l QRngCount(pc),(a0)
 lea QInitial(pc),a1
 bsr.w QRestore
 lea QRngCount(pc),a0
 clr.l (a0)
 ; Restore installed C4 end hook and call its installed start hook.
 move.l 20(sp),$6d684
 move.l 16(sp),$6d688
 move.w #$4ef9,$6d68c
 lea QReturn(pc),a0
 move.l a0,$6d68e
 bsr.w QCandidatePulse
 lea QActual(pc),a1
 bsr.w QSave
 lea QExpected(pc),a0
 lea QActual(pc),a1
 move.w #154-1,d0
.compare:
 move.w (a0)+,d1
 cmp.w (a1)+,d1
 bne.w QBad
 dbra d0,.compare
 move.l QRngCount(pc),d0
 cmp.l QExpectedRng(pc),d0
 bne.w QBad
 move.w #420-1,d1
 sub.w d7,d1
 lsl.w #2,d1
 lea QRngResults(pc),a0
 move.l d0,(a0,d1.w)
 lea QChecked(pc),a0
 addq.l #1,(a0)
 addq.l #8,a5
 dbra d7,.next
 move.w (sp)+,$24ef4
 move.l (sp)+,$24ef0
 move.l (sp)+,$24eec
 move.w (sp)+,$6d690
 move.l (sp)+,$6d68c
 move.l (sp)+,$6d688
 move.l (sp)+,$6d684
 lea QOriginal(pc),a1
 bsr.w QRestore
 bsr.w C4QGuards
 movem.l (sp)+,d0-d7/a0-a6
 rts
QNativePulse:
 movem.l d0-d7/a0-a6,-(sp)
 move.l #123,-(sp)
 bsr.w QNativeBody
 addq.l #4,sp
 movem.l (sp)+,d0-d7/a0-a6
 rts
QNativeBody:
 link a6,#-8
 tst.w $32fbc
 jmp $6d4fe
QCandidatePulse:
 movem.l d0-d7/a0-a6,-(sp)
 move.l #123,-(sp)
 bsr.w QCandidateBody
 addq.l #4,sp
 movem.l (sp)+,d0-d7/a0-a6
 rts
QCandidateBody:
 link a6,#-8
 jmp $6d4f8
QNativeReturn:
 moveq #0,d0
 move.w d0,$6f13a
QReturn:
 unlk a6
 rts
QRng:
 move.w sr,-(sp)
 move.l a0,-(sp)
 lea QRngCount(pc),a0
 addq.l #1,(a0)
 move.l (sp)+,a0
 move.w (sp)+,ccr
 link a6,#-2
 move.l $24fd4,a0
 jmp $24ef6
QBad:
 lea error(pc),a0
 move.l #4101,(a0)
 bra.w C1Fault
QSave:
 movem.l d0/a0-a1,-(sp)
 lea $2268e,a0
 move.w #15,d0
.copy0:
 move.w (a0)+,(a1)+
 dbra d0,.copy0
 lea $22356,a0
 move.w #15,d0
.copy1:
 move.w (a0)+,(a1)+
 dbra d0,.copy1
 lea $66c3e,a0
 move.w #31,d0
.copy2:
 move.w (a0)+,(a1)+
 dbra d0,.copy2
 lea $6ef52,a0
 move.w #0,d0
.copy3:
 move.w (a0)+,(a1)+
 dbra d0,.copy3
 lea $6f0f0,a0
 move.w #1,d0
.copy4:
 move.w (a0)+,(a1)+
 dbra d0,.copy4
 lea $6f10a,a0
 move.w #15,d0
.copy5:
 move.w (a0)+,(a1)+
 dbra d0,.copy5
 lea $6f13a,a0
 move.w #0,d0
.copy6:
 move.w (a0)+,(a1)+
 dbra d0,.copy6
 lea $24f60,a0
 move.w #59,d0
.copy7:
 move.w (a0)+,(a1)+
 dbra d0,.copy7
 lea $32fbc,a0
 move.w #0,d0
.copy8:
 move.w (a0)+,(a1)+
 dbra d0,.copy8
 lea $1c1c4,a0
 move.w #0,d0
.copy9:
 move.w (a0)+,(a1)+
 dbra d0,.copy9
 lea $1c5dc,a0
 move.w #7,d0
.copy10:
 move.w (a0)+,(a1)+
 dbra d0,.copy10
 movem.l (sp)+,d0/a0-a1
 rts
QRestore:
 movem.l d0/a0-a1,-(sp)
 lea $2268e,a0
 move.w #15,d0
.copy0:
 move.w (a1)+,(a0)+
 dbra d0,.copy0
 lea $22356,a0
 move.w #15,d0
.copy1:
 move.w (a1)+,(a0)+
 dbra d0,.copy1
 lea $66c3e,a0
 move.w #31,d0
.copy2:
 move.w (a1)+,(a0)+
 dbra d0,.copy2
 lea $6ef52,a0
 move.w #0,d0
.copy3:
 move.w (a1)+,(a0)+
 dbra d0,.copy3
 lea $6f0f0,a0
 move.w #1,d0
.copy4:
 move.w (a1)+,(a0)+
 dbra d0,.copy4
 lea $6f10a,a0
 move.w #15,d0
.copy5:
 move.w (a1)+,(a0)+
 dbra d0,.copy5
 lea $6f13a,a0
 move.w #0,d0
.copy6:
 move.w (a1)+,(a0)+
 dbra d0,.copy6
 lea $24f60,a0
 move.w #59,d0
.copy7:
 move.w (a1)+,(a0)+
 dbra d0,.copy7
 lea $32fbc,a0
 move.w #0,d0
.copy8:
 move.w (a1)+,(a0)+
 dbra d0,.copy8
 lea $1c1c4,a0
 move.w #0,d0
.copy9:
 move.w (a1)+,(a0)+
 dbra d0,.copy9
 lea $1c5dc,a0
 move.w #7,d0
.copy10:
 move.w (a1)+,(a0)+
 dbra d0,.copy10
 movem.l (sp)+,d0/a0-a1
 rts
QChecked: dc.l 0
QRngCount: dc.l 0
QExpectedRng: dc.l 0
QTyres: dc.l $66c52,$66c56,$66c5a,$66c5e,$66c6a,$66c6e
QParts: dc.l $66c62,$66c66,$66c4a,$66c4e,$66c72,$66c3e,$66c42
QOriginal: ds.b 308
QInitial: ds.b 308
QExpected: ds.b 308
QActual: ds.b 308
QRngResults: ds.l 420
QCases:
 dc.w 0,-25,0,0
 dc.w 0,-25,0,65535
 dc.w 0,-25,0,137
 dc.w 0,-25,1,0
 dc.w 0,-25,1,65535
 dc.w 0,-25,1,137
 dc.w 0,-25,2,0
 dc.w 0,-25,2,65535
 dc.w 0,-25,2,137
 dc.w 0,-25,3,0
 dc.w 0,-25,3,65535
 dc.w 0,-25,3,137
 dc.w 0,-25,4,0
 dc.w 0,-25,4,65535
 dc.w 0,-25,4,137
 dc.w 0,-25,5,0
 dc.w 0,-25,5,65535
 dc.w 0,-25,5,137
 dc.w 0,-25,6,0
 dc.w 0,-25,6,65535
 dc.w 0,-25,6,137
 dc.w 0,-25,7,0
 dc.w 0,-25,7,65535
 dc.w 0,-25,7,137
 dc.w 0,-25,8,0
 dc.w 0,-25,8,65535
 dc.w 0,-25,8,137
 dc.w 0,-25,9,0
 dc.w 0,-25,9,65535
 dc.w 0,-25,9,137
 dc.w 0,-25,10,0
 dc.w 0,-25,10,65535
 dc.w 0,-25,10,137
 dc.w 0,-25,11,0
 dc.w 0,-25,11,65535
 dc.w 0,-25,11,137
 dc.w 0,-25,12,0
 dc.w 0,-25,12,65535
 dc.w 0,-25,12,137
 dc.w 0,-25,13,0
 dc.w 0,-25,13,65535
 dc.w 0,-25,13,137
 dc.w 0,-1,0,0
 dc.w 0,-1,0,65535
 dc.w 0,-1,0,137
 dc.w 0,-1,1,0
 dc.w 0,-1,1,65535
 dc.w 0,-1,1,137
 dc.w 0,-1,2,0
 dc.w 0,-1,2,65535
 dc.w 0,-1,2,137
 dc.w 0,-1,3,0
 dc.w 0,-1,3,65535
 dc.w 0,-1,3,137
 dc.w 0,-1,4,0
 dc.w 0,-1,4,65535
 dc.w 0,-1,4,137
 dc.w 0,-1,5,0
 dc.w 0,-1,5,65535
 dc.w 0,-1,5,137
 dc.w 0,-1,6,0
 dc.w 0,-1,6,65535
 dc.w 0,-1,6,137
 dc.w 0,-1,7,0
 dc.w 0,-1,7,65535
 dc.w 0,-1,7,137
 dc.w 0,-1,8,0
 dc.w 0,-1,8,65535
 dc.w 0,-1,8,137
 dc.w 0,-1,9,0
 dc.w 0,-1,9,65535
 dc.w 0,-1,9,137
 dc.w 0,-1,10,0
 dc.w 0,-1,10,65535
 dc.w 0,-1,10,137
 dc.w 0,-1,11,0
 dc.w 0,-1,11,65535
 dc.w 0,-1,11,137
 dc.w 0,-1,12,0
 dc.w 0,-1,12,65535
 dc.w 0,-1,12,137
 dc.w 0,-1,13,0
 dc.w 0,-1,13,65535
 dc.w 0,-1,13,137
 dc.w 0,0,0,0
 dc.w 0,0,0,65535
 dc.w 0,0,0,137
 dc.w 0,0,1,0
 dc.w 0,0,1,65535
 dc.w 0,0,1,137
 dc.w 0,0,2,0
 dc.w 0,0,2,65535
 dc.w 0,0,2,137
 dc.w 0,0,3,0
 dc.w 0,0,3,65535
 dc.w 0,0,3,137
 dc.w 0,0,4,0
 dc.w 0,0,4,65535
 dc.w 0,0,4,137
 dc.w 0,0,5,0
 dc.w 0,0,5,65535
 dc.w 0,0,5,137
 dc.w 0,0,6,0
 dc.w 0,0,6,65535
 dc.w 0,0,6,137
 dc.w 0,0,7,0
 dc.w 0,0,7,65535
 dc.w 0,0,7,137
 dc.w 0,0,8,0
 dc.w 0,0,8,65535
 dc.w 0,0,8,137
 dc.w 0,0,9,0
 dc.w 0,0,9,65535
 dc.w 0,0,9,137
 dc.w 0,0,10,0
 dc.w 0,0,10,65535
 dc.w 0,0,10,137
 dc.w 0,0,11,0
 dc.w 0,0,11,65535
 dc.w 0,0,11,137
 dc.w 0,0,12,0
 dc.w 0,0,12,65535
 dc.w 0,0,12,137
 dc.w 0,0,13,0
 dc.w 0,0,13,65535
 dc.w 0,0,13,137
 dc.w 0,1,0,0
 dc.w 0,1,0,65535
 dc.w 0,1,0,137
 dc.w 0,1,1,0
 dc.w 0,1,1,65535
 dc.w 0,1,1,137
 dc.w 0,1,2,0
 dc.w 0,1,2,65535
 dc.w 0,1,2,137
 dc.w 0,1,3,0
 dc.w 0,1,3,65535
 dc.w 0,1,3,137
 dc.w 0,1,4,0
 dc.w 0,1,4,65535
 dc.w 0,1,4,137
 dc.w 0,1,5,0
 dc.w 0,1,5,65535
 dc.w 0,1,5,137
 dc.w 0,1,6,0
 dc.w 0,1,6,65535
 dc.w 0,1,6,137
 dc.w 0,1,7,0
 dc.w 0,1,7,65535
 dc.w 0,1,7,137
 dc.w 0,1,8,0
 dc.w 0,1,8,65535
 dc.w 0,1,8,137
 dc.w 0,1,9,0
 dc.w 0,1,9,65535
 dc.w 0,1,9,137
 dc.w 0,1,10,0
 dc.w 0,1,10,65535
 dc.w 0,1,10,137
 dc.w 0,1,11,0
 dc.w 0,1,11,65535
 dc.w 0,1,11,137
 dc.w 0,1,12,0
 dc.w 0,1,12,65535
 dc.w 0,1,12,137
 dc.w 0,1,13,0
 dc.w 0,1,13,65535
 dc.w 0,1,13,137
 dc.w 1,-25,0,0
 dc.w 1,-25,0,65535
 dc.w 1,-25,0,137
 dc.w 1,-25,1,0
 dc.w 1,-25,1,65535
 dc.w 1,-25,1,137
 dc.w 1,-25,2,0
 dc.w 1,-25,2,65535
 dc.w 1,-25,2,137
 dc.w 1,-1,0,0
 dc.w 1,-1,0,65535
 dc.w 1,-1,0,137
 dc.w 1,-1,1,0
 dc.w 1,-1,1,65535
 dc.w 1,-1,1,137
 dc.w 1,-1,2,0
 dc.w 1,-1,2,65535
 dc.w 1,-1,2,137
 dc.w 1,0,0,0
 dc.w 1,0,0,65535
 dc.w 1,0,0,137
 dc.w 1,0,1,0
 dc.w 1,0,1,65535
 dc.w 1,0,1,137
 dc.w 1,0,2,0
 dc.w 1,0,2,65535
 dc.w 1,0,2,137
 dc.w 1,1,0,0
 dc.w 1,1,0,65535
 dc.w 1,1,0,137
 dc.w 1,1,1,0
 dc.w 1,1,1,65535
 dc.w 1,1,1,137
 dc.w 1,1,2,0
 dc.w 1,1,2,65535
 dc.w 1,1,2,137
 dc.w 2,-25,0,0
 dc.w 2,-25,0,65535
 dc.w 2,-25,0,137
 dc.w 2,-25,1,0
 dc.w 2,-25,1,65535
 dc.w 2,-25,1,137
 dc.w 2,-25,2,0
 dc.w 2,-25,2,65535
 dc.w 2,-25,2,137
 dc.w 2,-1,0,0
 dc.w 2,-1,0,65535
 dc.w 2,-1,0,137
 dc.w 2,-1,1,0
 dc.w 2,-1,1,65535
 dc.w 2,-1,1,137
 dc.w 2,-1,2,0
 dc.w 2,-1,2,65535
 dc.w 2,-1,2,137
 dc.w 2,0,0,0
 dc.w 2,0,0,65535
 dc.w 2,0,0,137
 dc.w 2,0,1,0
 dc.w 2,0,1,65535
 dc.w 2,0,1,137
 dc.w 2,0,2,0
 dc.w 2,0,2,65535
 dc.w 2,0,2,137
 dc.w 2,1,0,0
 dc.w 2,1,0,65535
 dc.w 2,1,0,137
 dc.w 2,1,1,0
 dc.w 2,1,1,65535
 dc.w 2,1,1,137
 dc.w 2,1,2,0
 dc.w 2,1,2,65535
 dc.w 2,1,2,137
 dc.w 3,-25,0,0
 dc.w 3,-25,0,65535
 dc.w 3,-25,0,137
 dc.w 3,-25,1,0
 dc.w 3,-25,1,65535
 dc.w 3,-25,1,137
 dc.w 3,-25,2,0
 dc.w 3,-25,2,65535
 dc.w 3,-25,2,137
 dc.w 3,-1,0,0
 dc.w 3,-1,0,65535
 dc.w 3,-1,0,137
 dc.w 3,-1,1,0
 dc.w 3,-1,1,65535
 dc.w 3,-1,1,137
 dc.w 3,-1,2,0
 dc.w 3,-1,2,65535
 dc.w 3,-1,2,137
 dc.w 3,0,0,0
 dc.w 3,0,0,65535
 dc.w 3,0,0,137
 dc.w 3,0,1,0
 dc.w 3,0,1,65535
 dc.w 3,0,1,137
 dc.w 3,0,2,0
 dc.w 3,0,2,65535
 dc.w 3,0,2,137
 dc.w 3,1,0,0
 dc.w 3,1,0,65535
 dc.w 3,1,0,137
 dc.w 3,1,1,0
 dc.w 3,1,1,65535
 dc.w 3,1,1,137
 dc.w 3,1,2,0
 dc.w 3,1,2,65535
 dc.w 3,1,2,137
 dc.w 4,-25,0,0
 dc.w 4,-25,0,65535
 dc.w 4,-25,0,137
 dc.w 4,-25,1,0
 dc.w 4,-25,1,65535
 dc.w 4,-25,1,137
 dc.w 4,-25,2,0
 dc.w 4,-25,2,65535
 dc.w 4,-25,2,137
 dc.w 4,-1,0,0
 dc.w 4,-1,0,65535
 dc.w 4,-1,0,137
 dc.w 4,-1,1,0
 dc.w 4,-1,1,65535
 dc.w 4,-1,1,137
 dc.w 4,-1,2,0
 dc.w 4,-1,2,65535
 dc.w 4,-1,2,137
 dc.w 4,0,0,0
 dc.w 4,0,0,65535
 dc.w 4,0,0,137
 dc.w 4,0,1,0
 dc.w 4,0,1,65535
 dc.w 4,0,1,137
 dc.w 4,0,2,0
 dc.w 4,0,2,65535
 dc.w 4,0,2,137
 dc.w 4,1,0,0
 dc.w 4,1,0,65535
 dc.w 4,1,0,137
 dc.w 4,1,1,0
 dc.w 4,1,1,65535
 dc.w 4,1,1,137
 dc.w 4,1,2,0
 dc.w 4,1,2,65535
 dc.w 4,1,2,137
 dc.w 5,-25,0,0
 dc.w 5,-25,0,65535
 dc.w 5,-25,0,137
 dc.w 5,-25,1,0
 dc.w 5,-25,1,65535
 dc.w 5,-25,1,137
 dc.w 5,-25,2,0
 dc.w 5,-25,2,65535
 dc.w 5,-25,2,137
 dc.w 5,-1,0,0
 dc.w 5,-1,0,65535
 dc.w 5,-1,0,137
 dc.w 5,-1,1,0
 dc.w 5,-1,1,65535
 dc.w 5,-1,1,137
 dc.w 5,-1,2,0
 dc.w 5,-1,2,65535
 dc.w 5,-1,2,137
 dc.w 5,0,0,0
 dc.w 5,0,0,65535
 dc.w 5,0,0,137
 dc.w 5,0,1,0
 dc.w 5,0,1,65535
 dc.w 5,0,1,137
 dc.w 5,0,2,0
 dc.w 5,0,2,65535
 dc.w 5,0,2,137
 dc.w 5,1,0,0
 dc.w 5,1,0,65535
 dc.w 5,1,0,137
 dc.w 5,1,1,0
 dc.w 5,1,1,65535
 dc.w 5,1,1,137
 dc.w 5,1,2,0
 dc.w 5,1,2,65535
 dc.w 5,1,2,137
 dc.w 6,-25,0,0
 dc.w 6,-25,0,65535
 dc.w 6,-25,0,137
 dc.w 6,-25,1,0
 dc.w 6,-25,1,65535
 dc.w 6,-25,1,137
 dc.w 6,-25,2,0
 dc.w 6,-25,2,65535
 dc.w 6,-25,2,137
 dc.w 6,-1,0,0
 dc.w 6,-1,0,65535
 dc.w 6,-1,0,137
 dc.w 6,-1,1,0
 dc.w 6,-1,1,65535
 dc.w 6,-1,1,137
 dc.w 6,-1,2,0
 dc.w 6,-1,2,65535
 dc.w 6,-1,2,137
 dc.w 6,0,0,0
 dc.w 6,0,0,65535
 dc.w 6,0,0,137
 dc.w 6,0,1,0
 dc.w 6,0,1,65535
 dc.w 6,0,1,137
 dc.w 6,0,2,0
 dc.w 6,0,2,65535
 dc.w 6,0,2,137
 dc.w 6,1,0,0
 dc.w 6,1,0,65535
 dc.w 6,1,0,137
 dc.w 6,1,1,0
 dc.w 6,1,1,65535
 dc.w 6,1,1,137
 dc.w 6,1,2,0
 dc.w 6,1,2,65535
 dc.w 6,1,2,137
 dc.w 7,-25,0,0
 dc.w 7,-25,0,65535
 dc.w 7,-25,0,137
 dc.w 7,-25,1,0
 dc.w 7,-25,1,65535
 dc.w 7,-25,1,137
 dc.w 7,-25,2,0
 dc.w 7,-25,2,65535
 dc.w 7,-25,2,137
 dc.w 7,-1,0,0
 dc.w 7,-1,0,65535
 dc.w 7,-1,0,137
 dc.w 7,-1,1,0
 dc.w 7,-1,1,65535
 dc.w 7,-1,1,137
 dc.w 7,-1,2,0
 dc.w 7,-1,2,65535
 dc.w 7,-1,2,137
 dc.w 7,0,0,0
 dc.w 7,0,0,65535
 dc.w 7,0,0,137
 dc.w 7,0,1,0
 dc.w 7,0,1,65535
 dc.w 7,0,1,137
 dc.w 7,0,2,0
 dc.w 7,0,2,65535
 dc.w 7,0,2,137
 dc.w 7,1,0,0
 dc.w 7,1,0,65535
 dc.w 7,1,0,137
 dc.w 7,1,1,0
 dc.w 7,1,1,65535
 dc.w 7,1,1,137
 dc.w 7,1,2,0
 dc.w 7,1,2,65535
 dc.w 7,1,2,137

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
