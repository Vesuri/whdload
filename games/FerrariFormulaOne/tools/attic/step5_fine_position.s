; VERIFY-only position conversion. Other physics still executes native ticks.
install_fine_position:
 movem.l d0-d7/a0-a6,-(sp)
 cmpi.w #8,d0
 bne.w .done
 cmpi.l #$30390003,$67a04
 bne.w .bad
 cmpi.w #$2fc2,$67a08
 bne.w .bad
 cmpi.l #$30390003,$67a36
 bne.w .bad
 cmpi.w #$2fca,$67a3a
 bne.w .bad
 cmpi.l #$30390003,$68292
 bne.w .bad
 cmpi.w #$2fbc,$68296
 bne.w .bad
 lea fine_advance(pc),a0
 move.w #$4ef9,$67a04
 move.l a0,$67a06
 lea fine_boundary(pc),a0
 move.w #$4ef9,$67a36
 move.l a0,$67a38
 lea fine_bounds(pc),a0
 move.w #$4ef9,$68292
 move.l a0,$68294
 lea fine_installed(pc),a0
 move.l #1,(a0)
 bra.b .done
.bad:
 lea error(pc),a0
 move.l #11,(a0)
.done:
 movem.l (sp)+,d0-d7/a0-a6
 rts

fine_advance:
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 bsr.w bridge_context
 tst.l d0
 bmi.w fine_fault
 move.w $32fc2,(a0)
 move.w $32fc4,6(a0)
 move.l a0,a3
 lea fine_trial(pc),a0
 move.l (a3),(a0)
 move.l 4(a3),4(a0)
 move.l 8(a3),8(a0)
 ; Record input before changing the independent axis states.
 move.l fine_steps(pc),d0
 cmpi.l #800,d0
 bhs.w fine_record_overflow
 lsl.l #5,d0
 lea fine_records(pc),a4
 adda.l d0,a4
 move.w $32fbc,(a4)
 clr.w 2(a4)
 move.w $32f94,4(a4)
 move.w $32f96,6(a4)
 move.l (a0),8(a4)
 move.l 4(a0),12(a4)
 move.l 8(a0),16(a4)
 move.w $32f94,d0
 bsr.w FF1Position20
 tst.l d1
 bne.w fine_fault
 addq.l #6,a0
 move.w $32f96,d0
 bsr.w FF1Position20
 tst.l d1
 bne.w fine_fault
 moveq #0,d0
 bsr.w FF1PositionClampLower
 move.w d1,2(a4)
 lea fine_trial(pc),a0
 move.l (a0),(a3)
 move.l 4(a0),4(a3)
 move.l 8(a0),8(a3)
 move.l (a0),20(a4)
 move.l 4(a0),24(a4)
 move.l 8(a0),28(a4)
 move.w (a0),$32fc2
 move.w 6(a0),$32fc4
 lea fine_steps(pc),a0
 addq.l #1,(a0)
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $67a36
fine_record_overflow:
 lea error(pc),a0
 move.l #12,(a0)
 bra.w fine_stop
fine_fault:
 lea error(pc),a0
 move.l #13,(a0)
fine_stop:
 bra.b fine_stop

fine_boundary:
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 bsr.w bridge_context
 tst.l d0
 bmi.w fine_fault
 move.w $32fc2,(a0)
 move.w $32fc4,6(a0)
 moveq #0,d4
 move.w $32fca,d4
 cmp.w $2268c,d4
 bhs.w fine_fault
 add.l d4,d4
 lea $1dc24,a1
 move.w (a1,d4.l),d4
 move.w d4,-16(a6)
 andi.l #1023,d4
 add.l d4,d4
 lea $2180c,a1
 move.w (a1,d4.l),d0
 muls.w #1000,d0
 asr.l #8,d0
 asr.l #7,d0
 lea $21a0c,a1
 move.w (a1,d4.l),d1
 muls.w #1000,d1
 asr.l #8,d1
 asr.l #7,d1
 bsr.w FF1PositionCrossed020
 tst.l d1
 bne.w fine_fault
 lea fine_cross_pending(pc),a1
 move.w d0,(a1)
 tst.l d0
 beq.b .inside
 lea fine_car_crosses(pc),a1
 addq.w #1,(a1)
 cmpi.w #64,(a1)
 bhi.w fine_fault
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $67aac
.inside:
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $68292

fine_bounds:
 move.w $32fbc,d0
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 lea fine_cross_pending(pc),a1
 tst.w (a1)
 beq.b .bounds
 clr.w (a1)
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $67a36
.bounds:
 moveq #0,d0
 move.w $32fbc,d0
 cmpi.w #7,d0
 bhi.w fine_fault
 add.l d0,d0
 lea $32f30,a1
 tst.w (a1,d0.l)
 ble.b .done
 bsr.w bridge_context
 tst.l d0
 bmi.w fine_fault
 move.w $32fc2,(a0)
 moveq #0,d4
 move.w $32fca,d4
 cmp.w $2268c,d4
 bhs.w fine_fault
 add.l d4,d4
 lea $1d29c,a1
 move.w (a1,d4.l),d0
 addi.w #100,d0
 bsr.w FF1PositionClampUpper
 lea $1c914,a1
 move.w (a1,d4.l),d0
 neg.w d0
 subi.w #100,d0
 bsr.w FF1PositionClampLower
 move.w (a0),$32fc2
.done:
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $68298
fine_installed: dc.l 0
fine_steps: dc.l 0
fine_cross_pending: dc.w 0
fine_car_crosses: dc.w 0
fine_trial: ds.b 12
fine_records: ds.b 25600
