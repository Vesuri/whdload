; Latch an opponent's logical winning instant before result cleanup restores
; its clock ownership. Only the ordinary race-duration read uses this instant;
; display/input waits and unclassified result sources retain the native clock.
timing_result_begin
 move.w sr,-(sp)
 movem.l d0/a0,-(sp)
 lea timing_result_state(pc),a0
 clr.l 8(a0)
 addq.l #1,16(a0)
 move.w timing_pit_opponent_state+10(pc),d0
 bne.s .opponent
 move.w timing_retune_state+10(pc),d0
 beq.s .done
 moveq #2,d0
 bra.s .latch
.opponent
 moveq #1,d0
.latch
 move.w #1,8(a0)
 move.w d0,10(a0)
 move.l timing_pit_opponent_state+36(pc),12(a0)
.done
 movem.l (sp)+,d0/a0
 move.w (sp)+,ccr
 rts

timing_result_clock_d7
 move.w sr,-(sp)
 movem.l a0-a1,-(sp)
 lea timing_result_state(pc),a0
 IFD VERIFY
 move.w 8(sp),28(a0)
 ENDC
 addq.l #1,20(a0)
 move.l perf_game(pc),a1
 move.l $f96(a1),d7
 move.l d7,24(a0)
 tst.w 8(a0)
 beq.s .selected
 move.l 12(a0),d7
.selected
 move.l d7,32(a0)
 movem.l (sp)+,a0-a1
 move.w (sp)+,ccr
 ; Native MOVE.L sets NZVC and preserves X. Restore X before reproducing it.
 tst.l d7
 IFD VERIFY
 bsr timing_result_flags
 ENDC
 rts

 IFD VERIFY
timing_result_flags
 move.w sr,-(sp)
 move.l a0,-(sp)
 lea timing_result_state(pc),a0
 move.w 4(sp),30(a0)
 movea.l (sp)+,a0
 move.w (sp)+,ccr
 rts
 ENDC

timing_result_state dc.b 'PDRSLT01'
 dc.w 0 ; logical winning instant valid until session cleanup
 dc.w 0 ; source: 0 native, 1 active opponent, 2 deferred pit opponent
 dc.l 0 ; logical winning instant in the native clock epoch
 dc.l 0 ; result entries
 dc.l 0 ; ordinary race-duration clock reads
 dc.l 0 ; native physical clock observed at the duration read
 dc.w 0 ; VERIFY guest input CCR
 dc.w 0 ; VERIFY guest output CCR
 dc.l 0 ; clock returned to the native duration calculation
