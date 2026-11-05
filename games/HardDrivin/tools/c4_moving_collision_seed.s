; Private fixture: initialize the player once after the real target starts moving.
 dc.b 'HDC4COL1'
_private_c4_moving_done: dc.w 0
_private_c4_moving_seed:
 movem.l d0-d7/a0-a6,-(a7)
 lea _verify_drive_state(pc),a0
 cmpi.w #2,(a0)
 bne .done
 move.w _private_c4_moving_done(pc),d0
 bne .done
 tst.b -$5221(a4)
 beq .done
 movea.l -$669e(a4),a1
 adda.w #96*56,a1
 move.w 12(a1),d0
 subi.w #17345,d0
 bpl.s .positive
 neg.w d0
.positive:
 cmpi.w #20,d0
 blo .done
 bsr _private_c4_seed
 move.w 8(a1),d0
 move.w d0,-$6716(a4)
 move.w d0,-$670a(a4)
 ext.l d0
 lsl.l #3,d0
 move.l d0,-$6704(a4)
 move.w 10(a1),d0
 move.w d0,-$6714(a4)
 move.w d0,-$6708(a4)
 ext.l d0
 lsl.l #3,d0
 move.l d0,-$6700(a4)
 move.w 12(a1),d0
 addi.w #PRIVATE_APPROACH_OFFSET,d0
 move.w d0,-$6712(a4)
 move.w d0,-$6706(a4)
 ext.l d0
 lsl.l #3,d0
 move.l d0,-$66fc(a4)
 lea _private_c4_moving_seed(pc),a0
 adda.l #_motion_reset-_private_c4_moving_seed,a0
 jsr (a0)
 lea _private_c4_moving_done(pc),a0
 move.w #1,(a0)
.done:
 movem.l (a7)+,d0-d7/a0-a6
 rts
