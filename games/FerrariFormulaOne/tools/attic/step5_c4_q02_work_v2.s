QWork:
 movem.l d0-d7/a0-a6,-(sp)
 lea QSaved(pc),a1
 lea $2aaa6,a0
 move.w #0,d0
.save0: move.w (a0)+,(a1)+
 dbra d0,.save0
 lea $32f94,a0
 move.w #1,d0
.save1: move.w (a0)+,(a1)+
 dbra d0,.save1
 lea $32fbc,a0
 move.w #4,d0
.save2: move.w (a0)+,(a1)+
 dbra d0,.save2
 lea position_shadow(pc),a0
 move.w #47,d0
.save3: move.w (a0)+,(a1)+
 dbra d0,.save3
 lea velocity_shadow(pc),a0
 move.w #47,d0
.save4: move.w (a0)+,(a1)+
 dbra d0,.save4
 lea speed_work(pc),a0
 move.w #2,d0
.save5: move.w (a0)+,(a1)+
 dbra d0,.save5
 lea writer_results(pc),a4
 moveq #0,d7
.car:
 moveq #0,d5
.value:
 bsr.w QSeed
 move.w $69940,-(sp)
 move.w #$4e75,$69940
 move.w d5,d0
 add.w d0,d0
 lea QValues(pc),a0
 move.w (a0,d0.w),d0
 ext.l d0
 move.w #999,d1
 movem.l d0-d7/a0-a6,-(sp)
 jsr $6993a
 movem.l (sp)+,d0-d7/a0-a6
 move.w (sp)+,$69940
 bsr.w QRecord
 bsr.w QSeed
 move.w $69a10,-(sp)
 move.w #$4e75,$69a10
 move.w d5,d0
 add.w d0,d0
 lea QValues(pc),a0
 move.w (a0,d0.w),d0
 ext.l d0
 move.w #999,d1
 movem.l d0-d7/a0-a6,-(sp)
 jsr $69a0a
 movem.l (sp)+,d0-d7/a0-a6
 move.w (sp)+,$69a10
 bsr.w QRecord
 bsr.w QSeed
 move.w $69994,-(sp)
 move.w #$4e75,$69994
 move.w d5,d0
 add.w d0,d0
 lea QValues(pc),a0
 move.w (a0,d0.w),d0
 ext.l d0
 move.w #999,d1
 movem.l d0-d7/a0-a6,-(sp)
 jsr $6998e
 movem.l (sp)+,d0-d7/a0-a6
 move.w (sp)+,$69994
 bsr.w QRecord
 bsr.w QSeed
 move.w $69a64,-(sp)
 move.w #$4e75,$69a64
 move.w d5,d0
 add.w d0,d0
 lea QValues(pc),a0
 move.w (a0,d0.w),d0
 ext.l d0
 move.w #999,d1
 movem.l d0-d7/a0-a6,-(sp)
 jsr $69a5e
 movem.l (sp)+,d0-d7/a0-a6
 move.w (sp)+,$69a64
 bsr.w QRecord
 addq.w #1,d5
 cmpi.w #3,d5
 blo.w .value
 addq.w #1,d7
 cmpi.w #8,d7
 blo.w .car
 lea QSaved(pc),a1
 lea $2aaa6,a0
 move.w #0,d0
.restore0: move.w (a1)+,(a0)+
 dbra d0,.restore0
 lea $32f94,a0
 move.w #1,d0
.restore1: move.w (a1)+,(a0)+
 dbra d0,.restore1
 lea $32fbc,a0
 move.w #4,d0
.restore2: move.w (a1)+,(a0)+
 dbra d0,.restore2
 lea position_shadow(pc),a0
 move.w #47,d0
.restore3: move.w (a1)+,(a0)+
 dbra d0,.restore3
 lea velocity_shadow(pc),a0
 move.w #47,d0
.restore4: move.w (a1)+,(a0)+
 dbra d0,.restore4
 lea speed_work(pc),a0
 move.w #2,d0
.restore5: move.w (a1)+,(a0)+
 dbra d0,.restore5
 movem.l (sp)+,d0-d7/a0-a6
 rts
QSeed:
 move.w #30,$2aaa6
 move.w d7,$32fbc
 move.w #10,$32fc2
 move.w #100,$32fc4
 move.w #7,$32f94
 move.w #200,$32f96
 move.w #50,$32fbe
 lea QSeedPosition(pc),a0
 lea position_shadow(pc),a1
 bsr.w QSeedEight
 lea QSeedVelocity(pc),a0
 lea velocity_shadow(pc),a1
 bsr.w QSeedEight
 lea speed_work(pc),a0
 move.l #$00321111,(a0)
 move.w #3,4(a0)
 rts
QSeedEight:
 moveq #7,d2
.loop:
 move.l (a0),(a1)+
 move.l 4(a0),(a1)+
 move.l 8(a0),(a1)+
 dbra d2,.loop
 rts
QRecord:
 ; Check every non-target owner remains unchanged, not only the target result.
 lea position_shadow(pc),a0
 lea QSeedPosition(pc),a1
 bsr.w QUntouched
 lea velocity_shadow(pc),a0
 lea QSeedVelocity(pc),a1
 bsr.w QUntouched
 move.w d7,d0
 mulu.w #12,d0
 lea position_shadow(pc),a0
 adda.w d0,a0
 move.l (a0),(a4)+
 move.l 4(a0),(a4)+
 move.l 8(a0),(a4)+
 lea velocity_shadow(pc),a0
 adda.w d0,a0
 move.l (a0),(a4)+
 move.l 4(a0),(a4)+
 move.l 8(a0),(a4)+
 lea speed_work(pc),a0
 move.l (a0),(a4)+
 move.w 4(a0),(a4)+
 move.w $32fc2,(a4)+
 move.w $32fc4,(a4)+
 move.w $32f94,(a4)+
 move.w $32f96,(a4)+
 move.w $32fbe,(a4)+
 rts
QUntouched:
 moveq #0,d2
.loop:
 cmp.w d7,d2
 beq.b .next
 move.l (a0),d0
 cmp.l (a1),d0
 bne.w QWorkBad
 move.l 4(a0),d0
 cmp.l 4(a1),d0
 bne.w QWorkBad
 move.l 8(a0),d0
 cmp.l 8(a1),d0
 bne.w QWorkBad
.next:
 adda.w #12,a0
 addq.w #1,d2
 cmpi.w #8,d2
 blo.b .loop
 rts
QWorkBad:
 lea error(pc),a0
 move.l #4201,(a0)
 bra.w C1Fault
QValues:
 dc.w -123,0,321
QSeedPosition:
 dc.w 10,$1234,-3,100,$5678,2
QSeedVelocity:
 dc.w 7,$789a,200,$bcde,-4,4
QSaved:
 ds.b 214
writer_results:
 ds.b 3840
