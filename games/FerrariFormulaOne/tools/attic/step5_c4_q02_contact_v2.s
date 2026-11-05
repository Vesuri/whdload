
contact_fixture:
 movem.l d0-d7/a0-a6,-(sp)
 lea QContactSaved(pc),a1
 lea speed_shadow(pc),a0
 move.w #23,d0
.save0: move.w (a0)+,(a1)+
 dbra d0,.save0
 lea $24f60,a0
 move.w #59,d0
.save1: move.w (a0)+,(a1)+
 dbra d0,.save1
 lea $6f10a,a0
 move.w #15,d0
.save2: move.w (a0)+,(a1)+
 dbra d0,.save2
 lea $32f30,a0
 move.w #7,d0
.save3: move.w (a0)+,(a1)+
 dbra d0,.save3
 lea $1c21e,a0
 move.w #0,d0
.save4: move.w (a0)+,(a1)+
 dbra d0,.save4
 lea $2268e,a0
 move.w #7,d0
.save5: move.w (a0)+,(a1)+
 dbra d0,.save5
 lea $6a60a,a0
 move.w #23,d0
.save6: move.w (a0)+,(a1)+
 dbra d0,.save6
 lea $2275a,a0
 move.w #7,d0
.save7: move.w (a0)+,(a1)+
 dbra d0,.save7
 lea $6f13c,a0
 move.w #15,d0
.save8: move.w (a0)+,(a1)+
 dbra d0,.save8
 lea velocity_shadow(pc),a0
 move.w #47,d0
.save9: move.w (a0)+,(a1)+
 dbra d0,.save9
 lea position_shadow(pc),a0
 move.w #47,d0
.save10: move.w (a0)+,(a1)+
 dbra d0,.save10
 lea contact_vectors(pc),a3
 lea contact_results(pc),a4
 move.w #55,d7
case_loop:
 clr.w $1c21e
 lea velocity_shadow(pc),a0
 moveq #0,d6
seed_loop:
 move.l d6,d0
 add.l d0,d0
 lea $2268e,a1
 move.w #1,(a1,d0.w)
 lea $6a60a,a1
 move.w #10,(a1,d0.w)
 lea $6a61a,a1
 clr.w (a1,d0.w)
 lea $6a62a,a1
 move.w #100,(a1,d0.w)
 lea $2275a,a1
 move.w #100,(a1,d0.w)
 lea $6f14c,a1
 move.w #100,(a1,d0.w)
 lea $6f13c,a1
 clr.w (a1,d0.w)
 clr.w (a0)+
 move.w d6,d0
 mulu.w #257,d0
 addi.w #256,d0
 move.w d0,(a0)+
 move.w #100,(a0)+
 move.w d6,d0
 mulu.w #513,d0
 addi.w #512,d0
 move.w d0,(a0)+
 move.w d6,d0
 subq.w #4,d0
 move.w d0,(a0)+
 moveq #4,d0
 sub.w d6,d0
 move.w d0,(a0)+
 addq.w #1,d6
 cmpi.w #8,d6
 blo.w seed_loop
 moveq #0,d0
 move.w (a3)+,d0
 moveq #0,d1
 move.w (a3)+,d1
 move.w (a3)+,d2
 add.l d0,d0
 add.l d1,d1
 lea $2268e,a1
 clr.w (a1,d0.w)
 clr.w (a1,d1.w)
 tst.w d2
 bne.b second_front
 lea $6a62a,a1
 move.w #101,(a1,d0.w)
 lea $2275a,a1
 move.w #120,(a1,d1.w)
 lea $6f14c,a1
 move.w #120,(a1,d1.w)
 bra.b run_contact
second_front:
 lea $6a62a,a1
 move.w #101,(a1,d1.w)
 lea $2275a,a1
 move.w #120,(a1,d0.w)
 lea $6f14c,a1
 move.w #120,(a1,d0.w)
run_contact:
 ; Match shadow integers to the fixture input, keeping distinct tails.
 lea velocity_shadow+4(pc),a0
 lea $6f14c,a1
 moveq #7,d6
sync_seed:
 move.w (a1)+,(a0)
 adda.w #12,a0
 dbra d6,sync_seed
 lea speed_shadow(pc),a0
 lea $2275a,a1
 moveq #0,d0
.speed_seed:
 move.w (a1)+,(a0)+
 move.w d0,d1
 mulu.w #111,d1
 addi.w #$2345,d1
 move.w d1,(a0)+
 move.w d0,d1
 subq.w #3,d1
 move.w d1,(a0)+
 addq.w #1,d0
 cmpi.w #8,d0
 blo.b .speed_seed
 lea position_shadow(pc),a0
 moveq #0,d6
.position_seed:
 move.w d6,d0
 add.w d0,d0
 lea $6a61a,a1
 move.w (a1,d0.w),(a0)+
 move.w d6,d1
 mulu.w #257,d1
 addi.w #256,d1
 move.w d1,(a0)+
 move.w d6,d1
 subq.w #4,d1
 move.w d1,(a0)+
 lea $6a62a,a1
 move.w (a1,d0.w),(a0)+
 move.w d6,d1
 mulu.w #513,d1
 addi.w #512,d1
 move.w d1,(a0)+
 move.w d6,d1
 subq.w #4,d1
 move.w d1,(a0)+
 addq.w #1,d6
 cmpi.w #8,d6
 blo.b .position_seed
 movem.l d0-d7/a0-a6,-(sp)
 jsr $68d4e
 movem.l (sp)+,d0-d7/a0-a6
 lea velocity_shadow(pc),a0
 moveq #23,d6
save_shadow:
 move.l (a0)+,(a4)+
 dbra d6,save_shadow
 lea $6a62a,a0
 moveq #3,d6
save_positions:
 move.l (a0)+,(a4)+
 dbra d6,save_positions
 lea $2275a,a0
 moveq #3,d6
save_speeds:
 move.l (a0)+,(a4)+
 dbra d6,save_speeds
 lea $6f14c,a0
 moveq #3,d6
save_velocities:
 move.l (a0)+,(a4)+
 dbra d6,save_velocities
 move.l velocity_swaps(pc),(a4)+
 lea position_shadow(pc),a0
 moveq #23,d6
save_position_shadow:
 move.l (a0)+,(a4)+
 dbra d6,save_position_shadow
 lea $6f13c,a0
 moveq #3,d6
save_native_x:
 move.l (a0)+,(a4)+
 dbra d6,save_native_x
 lea speed_shadow(pc),a0
 moveq #11,d6
save_speed_shadow:
 move.l (a0)+,(a4)+
 dbra d6,save_speed_shadow
 dbra d7,case_loop
contact_complete:
 lea QContactSaved(pc),a1
 lea speed_shadow(pc),a0
 move.w #23,d0
.restore0: move.w (a1)+,(a0)+
 dbra d0,.restore0
 lea $24f60,a0
 move.w #59,d0
.restore1: move.w (a1)+,(a0)+
 dbra d0,.restore1
 lea $6f10a,a0
 move.w #15,d0
.restore2: move.w (a1)+,(a0)+
 dbra d0,.restore2
 lea $32f30,a0
 move.w #7,d0
.restore3: move.w (a1)+,(a0)+
 dbra d0,.restore3
 lea $1c21e,a0
 move.w #0,d0
.restore4: move.w (a1)+,(a0)+
 dbra d0,.restore4
 lea $2268e,a0
 move.w #7,d0
.restore5: move.w (a1)+,(a0)+
 dbra d0,.restore5
 lea $6a60a,a0
 move.w #23,d0
.restore6: move.w (a1)+,(a0)+
 dbra d0,.restore6
 lea $2275a,a0
 move.w #7,d0
.restore7: move.w (a1)+,(a0)+
 dbra d0,.restore7
 lea $6f13c,a0
 move.w #15,d0
.restore8: move.w (a1)+,(a0)+
 dbra d0,.restore8
 lea velocity_shadow(pc),a0
 move.w #47,d0
.restore9: move.w (a1)+,(a0)+
 dbra d0,.restore9
 lea position_shadow(pc),a0
 move.w #47,d0
.restore10: move.w (a1)+,(a0)+
 dbra d0,.restore10
 movem.l (sp)+,d0-d7/a0-a6
 rts
contact_first_count: dc.l 0
contact_second_count: dc.l 0
contact_vectors:
 dc.w 0,1,0
 dc.w 0,1,1
 dc.w 0,2,0
 dc.w 0,2,1
 dc.w 0,3,0
 dc.w 0,3,1
 dc.w 0,4,0
 dc.w 0,4,1
 dc.w 0,5,0
 dc.w 0,5,1
 dc.w 0,6,0
 dc.w 0,6,1
 dc.w 0,7,0
 dc.w 0,7,1
 dc.w 1,2,0
 dc.w 1,2,1
 dc.w 1,3,0
 dc.w 1,3,1
 dc.w 1,4,0
 dc.w 1,4,1
 dc.w 1,5,0
 dc.w 1,5,1
 dc.w 1,6,0
 dc.w 1,6,1
 dc.w 1,7,0
 dc.w 1,7,1
 dc.w 2,3,0
 dc.w 2,3,1
 dc.w 2,4,0
 dc.w 2,4,1
 dc.w 2,5,0
 dc.w 2,5,1
 dc.w 2,6,0
 dc.w 2,6,1
 dc.w 2,7,0
 dc.w 2,7,1
 dc.w 3,4,0
 dc.w 3,4,1
 dc.w 3,5,0
 dc.w 3,5,1
 dc.w 3,6,0
 dc.w 3,6,1
 dc.w 3,7,0
 dc.w 3,7,1
 dc.w 4,5,0
 dc.w 4,5,1
 dc.w 4,6,0
 dc.w 4,6,1
 dc.w 4,7,0
 dc.w 4,7,1
 dc.w 5,6,0
 dc.w 5,6,1
 dc.w 5,7,0
 dc.w 5,7,1
 dc.w 6,7,0
 dc.w 6,7,1
contact_results: ds.b 17248
QContactSaved: ds.b 522
