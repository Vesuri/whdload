; Private input controller: while the loop holds the car, steer as a player
; might: aim the heading relative to the road at the drift (asin(230/(12*165)),
; about 26 units) less a share of the sideways offset; otherwise X320.
_private_loop_input:
 movem.l d0-d1/a0,-(a7)
 move.w #320,-$6a06(a4)
 lea _private_loop_input(pc),a0
 adda.l #_loop_state-_private_loop_input,a0
 tst.w LP_ACTIVE(a0)
 beq.s .done
 move.l LP_L(a0),d0
 asr.l #6,d0
 moveq #PRIVATE_LOOP_AIM,d1
 sub.w d0,d1
 sub.w LP_PSI(a0),d1
 asl.w #1,d1
 cmpi.w #60,d1
 ble.s .lower
 moveq #60,d1
.lower:
 cmpi.w #-60,d1
 bge.s .input
 moveq #-60,d1
.input:
 addi.w #320,d1
 move.w d1,-$6a06(a4)
.done:
 movem.l (a7)+,d0-d1/a0
 rts
 cnop 0,4
