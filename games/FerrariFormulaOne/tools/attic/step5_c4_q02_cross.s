QCross:
 movem.l d0-d7/a0-a6,-(sp)
 lea QSaved(pc),a1
 lea $68298,a0
 move.w #2,d0
.save0: move.w (a0)+,(a1)+
 dbra d0,.save0
 lea $1dc24,a0
 move.w #31,d0
.save1: move.w (a0)+,(a1)+
 dbra d0,.save1
 lea $1c21e,a0
 move.w #0,d0
.save2: move.w (a0)+,(a1)+
 dbra d0,.save2
 lea $32f30,a0
 move.w #7,d0
.save3: move.w (a0)+,(a1)+
 dbra d0,.save3
 lea $32f94,a0
 move.w #1,d0
.save4: move.w (a0)+,(a1)+
 dbra d0,.save4
 lea $32fb4,a0
 move.w #1,d0
.save5: move.w (a0)+,(a1)+
 dbra d0,.save5
 lea $32fbc,a0
 move.w #7,d0
.save6: move.w (a0)+,(a1)+
 dbra d0,.save6
 lea position_shadow(pc),a0
 move.w #47,d0
.save7: move.w (a0)+,(a1)+
 dbra d0,.save7
 lea velocity_shadow(pc),a0
 move.w #47,d0
.save8: move.w (a0)+,(a1)+
 dbra d0,.save8
 lea fine_cross_pending(pc),a0
 move.w #1,d0
.save9: move.w (a0)+,(a1)+
 dbra d0,.save9
 move.w #$4ef9,$68298
 lea QReturn(pc),a0
 move.l a0,$6829a
 lea writer_results(pc),a4
 moveq #0,d7
.car:
 moveq #0,d5
.pattern:
 moveq #0,d6
.velocity:
 move.w d7,$32fbc
 clr.w $1c21e
 lea $32f30,a0
 moveq #7,d0
.timers: clr.w (a0)+
 dbra d0,.timers
 lea $1dc24,a0
 moveq #0,d0
.angles:
 move.w d5,d1
 beq.b .straight
 move.w #16,d1
 cmpi.w #2,d5
 bne.b .save_angle
 btst #0,d0
 beq.b .save_angle
 neg.w d1
 bra.b .save_angle
.straight: moveq #0,d1
.save_angle: move.w d1,(a0)+
 addq.w #1,d0
 cmpi.w #32,d0
 blo.b .angles
 move.w #10,$32fca
 move.w #10,$32fc2
 move.w #500,$32fc4
 clr.w $32fc6
 clr.l $32fb4
 lea fine_cross_pending(pc),a0
 clr.l (a0)
 move.w d7,d0
 mulu.w #12,d0
 lea position_shadow(pc),a0
 adda.w d0,a0
 move.l #$000a1234,(a0)
 move.w #-3,4(a0)
 move.l #$01f45678,6(a0)
 move.w #2,10(a0)
 lea velocity_shadow(pc),a0
 adda.w d0,a0
 move.w d6,d1
 add.w d1,d1
 lea QVx(pc),a1
 move.w (a1,d1.w),d1
 move.w d1,$32f94
 move.w d1,(a0)
 move.w #$4321,2(a0)
 move.l #$01f42345,4(a0)
 move.w #500,$32f96
 move.l #$fffc0004,8(a0)
 movem.l d0-d7/a0-a6,-(sp)
 bsr.w QEnter
 movem.l (sp)+,d0-d7/a0-a6
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
 move.w $32fc2,(a4)+
 move.w $32fc4,(a4)+
 move.w $32f94,(a4)+
 move.w $32f96,(a4)+
 move.w $32fca,(a4)+
 move.w fine_car_crosses(pc),(a4)+
 move.w $32fc6,(a4)+
 move.w fine_cross_pending(pc),(a4)+
 addq.w #1,d6
 cmpi.w #3,d6
 blo.w .velocity
 addq.w #1,d5
 cmpi.w #3,d5
 blo.w .pattern
 addq.w #1,d7
 cmpi.w #8,d7
 blo.w .car
 lea QSaved(pc),a1
 lea $68298,a0
 move.w #2,d0
.restore0: move.w (a1)+,(a0)+
 dbra d0,.restore0
 lea $1dc24,a0
 move.w #31,d0
.restore1: move.w (a1)+,(a0)+
 dbra d0,.restore1
 lea $1c21e,a0
 move.w #0,d0
.restore2: move.w (a1)+,(a0)+
 dbra d0,.restore2
 lea $32f30,a0
 move.w #7,d0
.restore3: move.w (a1)+,(a0)+
 dbra d0,.restore3
 lea $32f94,a0
 move.w #1,d0
.restore4: move.w (a1)+,(a0)+
 dbra d0,.restore4
 lea $32fb4,a0
 move.w #1,d0
.restore5: move.w (a1)+,(a0)+
 dbra d0,.restore5
 lea $32fbc,a0
 move.w #7,d0
.restore6: move.w (a1)+,(a0)+
 dbra d0,.restore6
 lea position_shadow(pc),a0
 move.w #47,d0
.restore7: move.w (a1)+,(a0)+
 dbra d0,.restore7
 lea velocity_shadow(pc),a0
 move.w #47,d0
.restore8: move.w (a1)+,(a0)+
 dbra d0,.restore8
 lea fine_cross_pending(pc),a0
 move.w #1,d0
.restore9: move.w (a1)+,(a0)+
 dbra d0,.restore9
 movem.l (sp)+,d0-d7/a0-a6
 rts
QEnter:
 link a6,#-64
 jmp $67a04
QReturn:
 unlk a6
 rts
QVx:
 dc.w -80,0,80
QSaved:
 ds.b 308
writer_results:
 ds.b 2880
