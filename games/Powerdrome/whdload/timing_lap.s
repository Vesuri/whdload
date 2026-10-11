; Opponent lap timestamps use a stable setup epoch plus elapsed logical time.
; Physical/native epoch resampling remains separate for repair/result callers.
timing_lap_initialize
 move.l a0,-(sp)
 lea timing_lap_state(pc),a0
 move.l $206(a6),8(a0)
 clr.l 12(a0)
 clr.l 16(a0)
 clr.l 24(a0)
 clr.l 28(a0)
 clr.l 32(a0)
 clr.l 36(a0)
 clr.l 40(a0)
 movea.l (sp)+,a0
 rts

; Native countdown completion resets every linked pilot and the race start to
; state+$206. Rebase the logical lap domain once, before that shared reset.
; The mode update can execute after world ownership has been restored, so use
; the retained next-world timestamp, not the active-world flag.
timing_lap_reset
 move.w sr,-(sp)
 movem.l d0/a0,-(sp)
 bsr timing_player_lap_reset
 move.w timing_started(pc),d0
 beq.s .done
 move.w timing_world20_initialized(pc),d0
 beq.s .done
 move.w timing_pit_opponent_state+8(pc),d0
 beq.s .done
 lea timing_lap_state(pc),a0
 move.l 8(a0),36(a0)
 move.l timing_world20_clock(pc),d0
 move.l d0,28(a0)
 sub.l timing_pit_opponent_state+52(pc),d0
 add.l #TIMING_PERIOD,d0
 neg.l d0
 add.l $206(a6),d0
 move.l d0,8(a0)
 move.l $206(a6),32(a0)
 addq.l #1,24(a0)
.done
 movem.l (sp)+,d0/a0
 move.w (sp)+,ccr
 ; Native MOVE.L reproduces NZVC while retaining caller X.
 move.l $206(a6),$22e(a6)
 rts

timing_lap_clock_d7
 move.w sr,-(sp)
 move.l a0,-(sp)
 lea timing_pit_opponent_state(pc),a0
 tst.w 10(a0)
 beq.s .native
 move.l 20(a0),d7
 sub.l 52(a0),d7
 add.l #TIMING_PERIOD,d7
 add.l timing_lap_state+8(pc),d7
 bra.s .selected
.native
 move.l perf_game(pc),a0
 move.l $f96(a0),d7
.selected
 lea timing_lap_state(pc),a0
 addq.l #1,12(a0)
 move.l d7,16(a0)
 IFD VERIFY
 move.w 4(sp),20(a0)
 ENDC
 movea.l (sp)+,a0
 move.w (sp)+,ccr
 ; Restore X before reproducing native MOVE.L NZVC.
 tst.l d7
 IFD VERIFY
 bsr timing_lap_flags
 ENDC
 rts

 IFD VERIFY
timing_lap_flags
 move.w sr,-(sp)
 move.l a0,-(sp)
 lea timing_lap_state(pc),a0
 move.w 4(sp),22(a0)
 movea.l (sp)+,a0
 move.w (sp)+,ccr
 rts
 ENDC

timing_lap_state dc.b 'PDLAP001'
 dc.l 0 ; stable native setup epoch; not a sampled physical/VBL offset
 dc.l 0 ; native lap-clock reads
 dc.l 0 ; last returned clock
 dc.w 0,0 ; VERIFY guest input/output condition codes
 dc.l 0 ; shared native lap/race resets rebased
 dc.l 0 ; logical world timestamp at last reset
 dc.l 0 ; native shared timestamp at last reset
 dc.l 0 ; previous stable lap epoch
timing_lap_current dc.l 0 ; stable lap-domain instant of the current opponent update
