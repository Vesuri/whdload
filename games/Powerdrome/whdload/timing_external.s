; External pit departure: retain all 17 native table positions and draw calls.
; PAL A500 calibration: 9 x 80 ms, 5 x 60 ms, 3 x 40 ms through return.
; Deadlines retain overruns; waiting never advances player simulation or RNG.
timing_external_step
 move.w sr,-(sp)
 movem.l d0-d1/a0-a1,-(sp)
 cmp.w #16,d7
 bne.s .ready
 bsr timing_clock
 move.l perf_game(pc),a0
 lea timing_external_deadline(pc),a1
 move.l $f96(a0),(a1)
.ready
 movem.l (sp)+,d0-d1/a0-a1
 move.w (sp)+,ccr
 ; Replay the two native moves, including their NZVC/X behavior.
 move.w #$a0,d0
 move.w (a0)+,d1
 bra.w timing_external_continue

timing_external_end
 ; Restore the native loop's saved registers before adding our own stack frame.
 movem.l (sp)+,d7/a0
timing_external_flags
 move.w sr,-(sp)
 movem.l d0-d1/a0-a1,-(sp)
 moveq #16,d0
 sub.w d7,d0
 add.w d0,d0
 lea timing_external_periods(pc),a0
 move.w (a0,d0.w),d1
 ext.l d1
 lea timing_external_deadline(pc),a1
 add.l d1,(a1)
 move.l perf_game(pc),a0
.wait
 bsr timing_clock
 move.l $f96(a0),d0
 sub.l (a1),d0
 bmi.s .wait
 movem.l (sp)+,d0-d1/a0-a1
 move.w (sp)+,ccr
 ; DBRA preserves flags; retain the native terminal low word of FFFF.
 dbra d7,.again
 bra.w timing_external_return
.again
 bra.w timing_external_loop

timing_external_loop dc.w $4ef9
 dc.l 0
timing_external_continue dc.w $4ef9
 dc.l 0
timing_external_return dc.w $4ef9
 dc.l 0
timing_external_deadline dc.l 0
timing_external_periods
 dc.w 16,16,16,16,16,16,16,16,16,12,12,12,12,12,8,8,8
