; Experimental fade pacing in 20-ms movement ticks. Palette work stays in presentation.
; Candidate A500 calibration: first +960/-1180 ms, then +1400/-1160 ms.
; Native physical weather deadlines and forecast scheduling are still separate work.
timing_weather_fade_check
 move.l perf_game(pc),a0
 adda.l #$bd1a,a0
 cmp.l #$202e005e,(a0)
 bne.s .wrong
 cmp.l #$0240000f,4(a0)
 bne.s .wrong
 rts
.wrong
 pea TDREASON_WRONGVER
 move.l _resload(pc),a2
 jmp resload_Abort(a2)

timing_weather_fade_reset
 move.l a0,-(sp)
 lea timing_weather_fade_state(pc),a0
 clr.l 8(a0)
 clr.l 12(a0)
 clr.l 16(a0)
 movea.l (sp)+,a0
 rts

timing_weather_fade_tick
 movem.l d0-d7/a0-a6,-(sp)
 bsr timing_weather_enabled
 beq.w .reset
 IFNE TIMING_WEATHER_FADE_TEST
 bsr timing_weather_fade_test
 ENDC
 ; Other animations reuse the transition word; own only a published weather state.
 tst.w $4c0(a6)
 ble.w .reset
 lea timing_weather_fade_state(pc),a0
 addq.l #1,20(a0)
 move.w $4c6(a6),d0
 cmp.w 8(a0),d0
 beq.s .same
 move.w d0,8(a0)
 clr.w 10(a0)
 clr.w 18(a0)
 tst.w d0
 beq.w .done
 move.w #1,10(a0)
 move.l timing_world20_clock(pc),d1
 move.l d1,40(a0)
 tst.w d0
 bmi.s .new_negative
 add.l #192,d1
 bra.s .deadline
.new_negative
 add.l #236,d1
.deadline
 move.l d1,12(a0)
.same
 tst.w 10(a0)
 beq.w .done
 move.l timing_world20_clock(pc),d1
 sub.l 12(a0),d1
 bmi.w .done
 move.l timing_world20_clock(pc),44(a0)
 move.w $4c6(a6),16(a0) ; publish pre-mutation palette phase
 tst.w $4c6(a6)
 bmi.s .negative
 add.l #280,12(a0)
 addq.l #1,24(a0)
 move.w #1,18(a0)
 subq.w #1,$4c6(a6)
 bne.s .mutated
 move.w #3,18(a0)
 movem.l a0,-(sp)
 bsr timing_weather_fade_positive_gear
 movem.l (sp)+,a0
 bra.s .complete
.negative
 add.l #232,12(a0)
 addq.l #1,28(a0)
 move.w #2,18(a0)
 addq.w #1,$4c6(a6)
 bne.s .mutated
 move.w #4,18(a0)
 movem.l a0,-(sp)
 bsr timing_weather_fade_negative_gear
 movem.l (sp)+,a0
.complete
 addq.l #1,32(a0)
 clr.w 10(a0)
.mutated
 move.w $4c6(a6),8(a0)
 bra.s .done
.reset
 bsr timing_weather_fade_reset
.done
 movem.l (sp)+,d0-d7/a0-a6
 rts

; Draw the latest absolute palette phase once. Intermediate catch-up phases can be
; coalesced, but their transition mutations and gear commits all run in simulation.
timing_weather_fade_outer
 movem.l d0-d7/a0-a6,-(sp)
 bsr timing_weather_enabled
 beq.w .native
 tst.w $4c0(a6)
 ble.w .native
 lea timing_weather_fade_state(pc),a0
 move.w 18(a0),d0
 beq.s .done
 clr.w 18(a0)
 addq.l #1,36(a0)
 move.w $4c6(a6),-(sp)
 move.w 16(a0),$4c6(a6)
 move.w d0,-(sp)
 btst #0,d0
 beq.s .negative
 bsr timing_weather_fade_positive
 bra.s .finish
.negative
 bsr timing_weather_fade_negative
.finish
 move.w (sp)+,d0
 move.w (sp)+,$4c6(a6)
 cmp.w #3,d0
 bne.s .negative_finish
 bsr timing_weather_fade_palette
 bra.s .done
.negative_finish
 cmp.w #4,d0
 bne.s .done
 ; Native negative completion draws once more at transition zero.
 move.w $4c6(a6),-(sp)
 clr.w $4c6(a6)
 bsr timing_weather_fade_negative
 move.w (sp)+,$4c6(a6)
.done
 movem.l (sp)+,d0-d7/a0-a6
 bra.w timing_weather_fade_after
.native
 movem.l (sp)+,d0-d7/a0-a6
 move.l $5e(a6),d0
 and.w #15,d0
 bra.w timing_weather_fade_native

timing_weather_fade_native dc.w $4ef9
 dc.l 0
timing_weather_fade_after dc.w $4ef9
 dc.l 0
timing_weather_fade_positive dc.w $4ef9
 dc.l 0
timing_weather_fade_negative dc.w $4ef9
 dc.l 0
timing_weather_fade_positive_gear dc.w $4ef9
 dc.l 0
timing_weather_fade_negative_gear dc.w $4ef9
 dc.l 0
timing_weather_fade_palette dc.w $4ef9
 dc.l 0

timing_weather_fade_state dc.b 'PDWFAD01'
 dc.w 0 ; +8 expected native transition
 dc.w 0 ; +10 active deadline
 dc.l 0 ; +12 next logical deadline
 dc.w 0 ; +16 pre-step published palette phase
 dc.w 0 ; +18 pending palette kind: positive/negative/positive finish/negative finish
 dc.l 0 ; +20 eligible logical movement ticks
 dc.l 0 ; +24 positive steps
 dc.l 0 ; +28 negative steps
 dc.l 0 ; +32 gear commits
 dc.l 0 ; +36 palette publications drawn
 dc.l 0 ; +40 transition start clock
 dc.l 0 ; +44 latest step clock

 IFNE TIMING_WEATHER_FADE_TEST
; Both directed transitions, with a one-second stable interval between them.
; No clock, RNG or input rewrite; natural forecasts are suppressed for isolation.
timing_weather_fade_test
 lea timing_weather_fade_test_state(pc),a0
 move.l 8(a0),d0
 beq.s .start
 cmp.l #1,d0
 bne.s .done
 tst.w $4c6(a6)
 bne.s .done
 move.l timing_world20_clock(pc),d0
 sub.l timing_weather_fade_state+44(pc),d0
 cmp.l #200,d0
 blo.s .done
 move.l #2,8(a0)
 move.l timing_world20_clock(pc),16(a0)
 move.w #-15,$4c6(a6)
 bra.s .done
.start
 move.l timing_world20_state+16(pc),d0
 cmp.l #200,d0
 blo.s .done
 move.l #1,8(a0)
 move.l timing_world20_clock(pc),12(a0)
 move.w #1,$4c0(a6)
 move.l #-1,$4b8(a6)
 move.l #-1,$4bc(a6)
 clr.w $4cc(a6)
 move.w #15,$4c6(a6)
.done
 rts
timing_weather_fade_test_state dc.b 'PDWFTS01'
 dc.l 0 ; fixture phase
 dc.l 0 ; positive start
 dc.l 0 ; negative start
 ENDC
