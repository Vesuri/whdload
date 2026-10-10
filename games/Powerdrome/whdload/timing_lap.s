; Opponent lap timestamps use a stable setup epoch plus elapsed logical time.
; Physical/native epoch resampling remains separate for repair/result callers.
timing_lap_initialize
 move.l a0,-(sp)
 lea timing_lap_state(pc),a0
 move.l $206(a6),8(a0)
 clr.l 12(a0)
 clr.l 16(a0)
 movea.l (sp)+,a0
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
