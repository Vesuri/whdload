; Private input controller: aim at the next road cross-section in car space.
_private_loop_input:
 movem.l d0-d7/a0-a6,-(a7)
 move.l -$671c(a4),d0
 sub.l -$66ae(a4),d0
 cmpi.l #35*20,d0
 blo .done
 cmpi.l #53*20,d0
 bhs .done
 movea.l -$671c(a4),a0
 adda.w #20,a0
 lea _private_aim_point(pc),a1
 move.w (a0),d0
 add.w 6(a0),d0
 ; Loop coordinates can overflow the signed sum: average the difference.
 move.w 6(a0),d0
 sub.w (a0),d0
 asr.w #1,d0
 add.w (a0),d0
 sub.w -$670a(a4),d0
 move.w d0,(a1)
 move.w 8(a0),d0
 sub.w 2(a0),d0
 asr.w #1,d0
 add.w 2(a0),d0
 sub.w -$6708(a4),d0
 move.w d0,2(a1)
 move.w 10(a0),d0
 sub.w 4(a0),d0
 asr.w #1,d0
 add.w 4(a0),d0
 sub.w -$6706(a4),d0
 move.w d0,4(a1)
 move.l a1,-(a7)
 move.l a1,-(a7)
 move.w -$6bb8(a4),-(a7)
 move.w -$6bb6(a4),-(a7)
 move.w #1,-(a7)
 jsr -$7f38(a4)
 lea 14(a7),a7
 lea _private_aim_point(pc),a1
 move.l a1,-(a7)
 move.l a1,-(a7)
 move.w -$6bb4(a4),-(a7)
 move.w -$6bb2(a4),-(a7)
 move.w #1,-(a7)
 jsr -$7f32(a4)
 lea 14(a7),a7
 lea _private_aim_point(pc),a1
 move.l a1,-(a7)
 move.l a1,-(a7)
 move.w -$6bb0(a4),-(a7)
 move.w -$6bae(a4),-(a7)
 move.w #1,-(a7)
 jsr -$7f3e(a4)
 lea 14(a7),a7
 move.w _private_aim_point(pc),d0
 asl.w #1,d0
 cmpi.w #60,d0
 ble.s .lower
 moveq #60,d0
.lower:
 cmpi.w #-60,d0
 bge.s .input
 moveq #-60,d0
.input:
 addi.w #320,d0
 move.w d0,-$6a06(a4)
.done:
 movem.l (a7)+,d0-d7/a0-a6
 rts
_private_aim_point: dcb.w 3,0
