; Player lap duration and HUD elapsed time share a private logical start.
; Native state+$206 retains its physical-clock value for other game callers.
timing_player_lap_invalidate
 move.l a0,-(sp)
 lea timing_player_lap_state(pc),a0
 clr.w 8(a0)
 movea.l (sp)+,a0
 rts

; Called inside the shared countdown reset, whose caller preserves CCR/regs.
timing_player_lap_reset
 movem.l d0/a0,-(sp)
 move.w timing_started(pc),d0
 beq.s .done
 move.w timing_world20_initialized(pc),d0
 beq.s .done
 tst.w $b6(a6)
 bne.s .done
 lea timing_player_lap_state(pc),a0
 move.w #1,8(a0)
 move.l timing_world20_clock(pc),12(a0)
 move.l $206(a6),16(a0)
 addq.l #1,20(a0)
.done
 movem.l (sp)+,d0/a0
 rts

; Two native instructions, preserving the physical subtraction's X flag.
timing_player_lap_commit
 sub.l $206(a6),d0
 bsr timing_player_lap_prepare
 move.l d7,$206(a6)
 rts

timing_player_lap_prepare
 move.w sr,-(sp)
 movem.l d1/a0,-(sp)
 lea timing_player_lap_state(pc),a0
 move.w timing_started(pc),d1
 beq.s .invalidate
 move.w timing_world_state+8(pc),d1
 beq.s .invalidate
 tst.w $b6(a6)
 bne.s .invalidate
 tst.w $43a(a6)
 bpl.s .invalidate
 move.l timing_world20_clock(pc),d1
 tst.w 8(a0)
 beq.s .start
 move.l $206(a6),d1
 cmp.l 16(a0),d1
 bne.s .resync
 move.l timing_world20_clock(pc),d1
 move.l d1,d0
 sub.l 12(a0),d0
 addq.l #1,24(a0)
 move.l d0,32(a0)
 bra.s .start
.resync
 ; An unaudited native reset keeps this lap's original physical duration.
 addq.l #1,36(a0)
 move.l timing_world20_clock(pc),d1
.start
 move.w #1,8(a0)
 move.l d1,12(a0)
 move.l d7,16(a0)
 bra.s .done
.invalidate
 clr.w 8(a0)
.done
 movem.l (sp)+,d1/a0
 move.w (sp)+,ccr
 rts

; Native SUB followed by MOVE.W #$12,D1. Keep native D7 and state+$206.
timing_player_lap_hud
 sub.l $206(a6),d0
 bsr timing_player_lap_display
 move.w #$12,d1
 rts

timing_player_lap_display
 move.w sr,-(sp)
 movem.l d1/a0,-(sp)
 lea timing_player_lap_state(pc),a0
 tst.w 8(a0)
 beq.s .done
 move.w timing_started(pc),d1
 beq.s .done
 tst.w $b6(a6)
 bne.s .done
 tst.w $43a(a6)
 bpl.s .done
 move.l $206(a6),d1
 cmp.l 16(a0),d1
 bne.s .invalidate
 move.l timing_world20_clock(pc),d0
 ; At presentation the cursor names the next step. Display the last step's time.
 move.w timing_world_state+8(pc),d1
 bne.s .elapsed
 subq.l #4,d0
.elapsed
 sub.l 12(a0),d0
 bpl.s .nonnegative
 moveq #0,d0
.nonnegative
 addq.l #1,28(a0)
 move.l d0,40(a0)
 bra.s .done
.invalidate
 clr.w 8(a0)
 addq.l #1,36(a0)
.done
 movem.l (sp)+,d1/a0
 move.w (sp)+,ccr
 rts

timing_player_lap_state dc.b 'PDPLAP01'
 dc.w 0,0 ; private lap valid, padding
 dc.l 0 ; logical lap start
 dc.l 0 ; native physical lap start, for external-reset detection
 dc.l 0 ; shared countdown resets
 dc.l 0 ; logical lap durations selected
 dc.l 0 ; logical HUD durations selected
 dc.l 0 ; most recent logical lap duration
 dc.l 0 ; external-reset detections
 dc.l 0 ; most recent logical HUD duration
