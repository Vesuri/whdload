; Measured A500 drawing time, distributed over each native 33-step stage.
; The sound/display pause is added to the epoch, preserving existing lateness.
; Only supported human pit sequences are paced. No player simulation is run here.
timing_repair_enter_first
 move.w sr,-(sp)
 movem.l d0-d2/a0-a1,-(sp)
 cmp.w #32,d7
 bne.s .done
 moveq #0,d0
 bsr timing_repair_initialize
.done
 movem.l (sp)+,d0-d2/a0-a1
 move.w (sp)+,ccr
 movem.l d4-d7/a1-a2,-(sp)
 move.w $2a6(a6),d0
 bra.w timing_repair_first_continue

timing_repair_enter_second
 move.w sr,-(sp)
 movem.l d0-d2/a0-a1,-(sp)
 cmp.w #32,d7
 bne.s .pause
 moveq #1,d0
 bsr timing_repair_initialize
 bra.s .done
.pause
 cmp.w #31,d7
 bne.s .done
 lea timing_repair_state(pc),a1
 tst.w 8(a1)
 beq.s .done
 move.l perf_game(pc),a0
 ; Native clock sampling overwrites D0/D1; keep the deadline in saved D2.
 moveq #0,d2
 move.w 18(a1),d2
 add.l 24(a1),d2
.pause_wait
 bsr timing_clock
 move.l $f96(a0),d0
 sub.l d2,d0
 bmi.s .pause_wait
 move.l $f96(a0),d0
 sub.l 24(a1),d0
 add.l d0,12(a1)
 add.l d0,36(a1)
.done
 movem.l (sp)+,d0-d2/a0-a1
 move.w (sp)+,ccr
 movem.l d4-d7/a1-a2,-(sp)
 move.w $2a6(a6),d0
 bra.w timing_repair_second_continue

; Caller saves D0-D2/A0-A1/CCR. D0 is stage 0 or 1.
timing_repair_initialize
 lea timing_repair_state(pc),a1
 clr.w 8(a1)
 move.w d0,10(a1)
 tst.w $b6(a6)
 bne.s .done
 move.w timing_pit_state+8(pc),d1
 beq.s .done
 cmp.w #1,$47c(a6)
 bhi.s .done
 cmp.w #1,d4
 bhi.s .done
 ; Table order: item, direction, stage. Each entry is total 5-ms units.
 move.w $47c(a6),d1
 lsl.w #2,d1
 move.w d4,d2
 add.w d2,d2
 add.w d2,d1
 add.w d0,d1
 add.w d1,d1
 lea timing_repair_periods(pc),a0
 move.w (a0,d1.w),16(a1)
 lea timing_repair_pauses(pc),a0
 move.w (a0,d1.w),18(a1)
 bsr timing_clock
 move.l perf_game(pc),a0
 move.l $f96(a0),12(a1)
 move.l 12(a1),24(a1)
 move.w #1,8(a1)
 addq.l #1,28(a1)
.done
 rts

; Replay the native save/BSR/restore with exactly its original stack depth while
; E296 runs. It can update opponents and leave the pit nonlocally.
timing_repair_present_first
 movem.l d4-d7/a1-a2,-(sp)
 bsr timing_repair_native_present
 movem.l (sp)+,d4-d7/a1-a2
 bsr timing_repair_wait
 bra.w timing_repair_first_post

timing_repair_present_second
 movem.l d4-d7/a1-a2,-(sp)
 bsr timing_repair_native_present
 movem.l (sp)+,d4-d7/a1-a2
 bsr timing_repair_wait
 bra.w timing_repair_second_post

timing_repair_wait
 move.w sr,-(sp)
 movem.l d0-d1/a0-a1,-(sp)
 lea timing_repair_state(pc),a1
 tst.w 8(a1)
 beq.s .done
 cmp.w #32,d7
 bhi.s .done
 moveq #33,d0
 sub.w d7,d0
 mulu.w 16(a1),d0
 divu.w #33,d0
 and.l #$ffff,d0
 add.l 12(a1),d0
 move.l d0,20(a1)
 move.l perf_game(pc),a0
.wait
 bsr timing_clock
 move.l $f96(a0),d0
 move.l d0,24(a1)
 sub.l 20(a1),d0
 bmi.s .wait
 move.l d0,40(a1)
 cmp.l 44(a1),d0
 bls.s .count
 move.l d0,44(a1)
.count
 addq.l #1,32(a1)
 tst.w d7
 bne.s .done
 clr.w 8(a1)
.done
 movem.l (sp)+,d0-d1/a0-a1
 move.w (sp)+,ccr
 rts

timing_repair_first_continue dc.w $4ef9
 dc.l 0
timing_repair_second_continue dc.w $4ef9
 dc.l 0
timing_repair_native_present dc.w $4ef9
 dc.l 0
timing_repair_first_post dc.w $4ef9
 dc.l 0
timing_repair_second_post dc.w $4ef9
 dc.l 0

timing_repair_periods
 dc.w 680,680 ; item 0, direction 0: 3400 / 3400 ms
 dc.w 700,660 ; item 0, direction 1: 3500 / 3300 ms
 dc.w 752,672 ; item 1, direction 0: 3760 / 3360 ms
 dc.w 764,776 ; item 1, direction 1: 3820 / 3880 ms

timing_repair_pauses
 dc.w 0,220 ; item 0, direction 0: 1100 ms
 dc.w 0,232 ; item 0, direction 1: 1160 ms
 dc.w 0,228 ; item 1, direction 0: 1140 ms
 dc.w 0,228 ; item 1, direction 1: 1140 ms

timing_repair_state dc.b 'PDREPR01'
 dc.w 0,0 ; paced stage active, stage index
 dc.l 0 ; stage epoch, adjusted by the deliberate pause
 dc.w 0,0 ; total drawing clock units over 33 steps, minimum sound/display pause units
 dc.l 0 ; latest cumulative deadline
 dc.l 0 ; actual completion clock of the latest paced step
 dc.l 0 ; supported stages initialized
 dc.l 0 ; completed paced steps
 dc.l 0 ; cumulative excluded sound/display pause units
 dc.l 0 ; latest lateness
 dc.l 0 ; maximum lateness
