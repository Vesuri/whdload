; Experimental normal-flight effect ownership. Forecast/fade scheduling is separate.
; Logical 90-ms updates own lifetime and both generation/visual RNG advances.
; Presentation replays the latest pre-draw seed without changing simulation RNG.
timing_weather_check
 move.l perf_game(pc),a0
 adda.l #$bc8a,a0
 cmp.l #$4a6e04cc,(a0)
 bne.s .wrong
 cmp.l #$6700008a,4(a0)
 bne.s .wrong
 adda.l #$112e6-$bc8a,a0
 cmp.l #$4a6e04ce,(a0)
 bne.s .wrong
 cmp.w #$6714,4(a0)
 bne.s .wrong
 cmp.l #$3d7cffff,14(a0)
 bne.s .wrong
 cmp.w #$04d0,18(a0)
 bne.s .wrong
 rts
.wrong
 pea TDREASON_WRONGVER
 move.l _resload(pc),a2
 jmp resload_Abort(a2)

timing_weather_enabled
 move.l d0,-(sp)
 move.w timing_started(pc),d0
 beq.s .done
 move.w timing_pit_state+8(pc),d0
 bne.s .no
 tst.w $b6(a6)
 bne.s .no
 tst.w $43a(a6)
 bpl.s .no
 moveq #1,d0
 bra.s .done
.no
 moveq #0,d0
.done
 tst.w d0
 movem.l (sp)+,d0
 rts

timing_weather_reset
 move.l a0,-(sp)
 lea timing_weather_state(pc),a0
 clr.l 8(a0)
 clr.l 12(a0)
 clr.l 16(a0)
 movea.l (sp)+,a0
 rts

timing_weather_tick
 movem.l d0-d7/a0-a6,-(sp)
 bsr timing_weather_enabled
 bne.s .enabled
 bsr timing_weather_reset
 bra.w .done
.enabled
 bsr timing_world20_test_control
 beq.w .done
 IFNE TIMING_WEATHER_EFFECT_TEST
 bsr timing_weather_effect_test
 ENDC
 lea timing_weather_state(pc),a0
 addq.l #1,20(a0)
 move.l timing_world20_clock(pc),40(a0)
 clr.w 8(a0)
 tst.w $4ce(a6)
 beq.s .generation
 move.w $4ce(a6),8(a0)
 move.w $62(a6),10(a0)
 subq.w #1,$4ce(a6)
 addq.l #1,24(a0)
 moveq #0,d1
 moveq #3,d7
.visual_rng
 bsr timing_weather_random
 dbra d7,.visual_rng
.generation
 tst.w $4cc(a6)
 beq.w .done
 tst.w $4c6(a6)
 bne.w .done
 tst.w $104(a6)
 bne.w .done
 tst.w $4d2(a6)
 beq.s .attempt
 subq.w #1,$4d2(a6)
 bne.w .done
 move.w #1,16(a0) ; native rectangle cleanup belongs to presentation
.attempt
 addq.l #1,28(a0)
 moveq #7,d1
 bsr timing_weather_random
 cmp.w #6,d0
 bgt.s .done
 and.w #5,d0
 move.w d0,$4ce(a6)
 addq.l #1,32(a0)
 moveq #14,d1
 bsr timing_weather_random
 addq.w #4,d0
 move.w d0,$4d2(a6)
.done
 movem.l (sp)+,d0-d7/a0-a6
 rts

; The outer loop still performs native rectangle cleanup, but no owned RNG work.
timing_weather_outer
 movem.l d0-d7/a0-a6,-(sp)
 bsr timing_weather_enabled
 beq.s .native
 lea timing_weather_state(pc),a0
 tst.w 16(a0)
 beq.s .owned_done
 clr.w 16(a0)
 move.l perf_game(pc),a0
 tst.l $4f74(a0)
 beq.s .owned_done
 lea timing_weather_state(pc),a1
 addq.l #1,44(a1)
 movea.l $5ae(a0),a0
 adda.l #$30,a0
 move.l 4(a0),d0
 moveq #$3f,d1
 move.l 8(a0),d2
 moveq #3,d3
 movea.l (a0),a0
 bsr timing_weather_cleanup
.owned_done
 movem.l (sp)+,d0-d7/a0-a6
 bra.w timing_weather_fade
.native
 movem.l (sp)+,d0-d7/a0-a6
 tst.w $4cc(a6)
 beq.w timing_weather_fade
 bra.w timing_weather_generation

timing_weather_draw
 movem.l d0/a0,-(sp)
 bsr timing_weather_enabled
 beq.s .native
 lea timing_weather_state(pc),a0
 tst.w 8(a0)
 beq.s .skip
 move.w #1,12(a0)
 move.w $62(a6),14(a0)
 move.w 10(a0),$62(a6)
 addq.l #1,36(a0)
 ; Reproduce the native positive-lifetime decrement flags, not its mutation.
 move.w 8(a0),d0
 subq.w #1,d0
 movem.l (sp)+,d0/a0
 bra.w timing_weather_draw_body
.skip
 movem.l (sp)+,d0/a0
 bra.w timing_weather_after_draw
.native
 movem.l (sp)+,d0/a0
 tst.w $4ce(a6)
 beq.w timing_weather_after_draw
 subq.w #1,$4ce(a6)
 bra.w timing_weather_draw_body

timing_weather_draw_end
 movem.l d0/a0,-(sp)
 lea timing_weather_state(pc),a0
 tst.w 12(a0)
 beq.s .done
 move.w 14(a0),$62(a6)
 clr.w 12(a0)
.done
 movem.l (sp)+,d0/a0
 move.w #$ffff,$4d0(a6)
 bra.w timing_weather_present

timing_weather_random dc.w $4ef9
 dc.l 0
timing_weather_cleanup dc.w $4ef9
 dc.l 0
timing_weather_fade dc.w $4ef9
 dc.l 0
timing_weather_generation dc.w $4ef9
 dc.l 0
timing_weather_draw_body dc.w $4ef9
 dc.l 0
timing_weather_after_draw dc.w $4ef9
 dc.l 0
timing_weather_present dc.w $4ef9
 dc.l 0

timing_weather_state dc.b 'PDWEFX01'
 dc.w 0 ; +8 latest logical pre-decrement lifetime (visible state)
 dc.w 0 ; +10 visual pre-draw seed
 dc.w 0 ; +12 temporary render seed ownership
 dc.w 0 ; +14 saved outer seed
 dc.w 0 ; +16 pending rectangle cleanup
 dc.w 0 ; +18 reserved
 dc.l 0 ; +20 logical control updates
 dc.l 0 ; +24 logical visual RNG events
 dc.l 0 ; +28 generation attempts
 dc.l 0 ; +32 successful selections (including zero lifetime)
 dc.l 0 ; +36 actual effect draws
 dc.l 0 ; +40 most recent logical update timestamp
 dc.l 0 ; +44 actual rectangle cleanups

 IFNE TIMING_WEATHER_EFFECT_TEST
; Directed effect-only fixture. No clock/input/seed rewrite and no cache changes.
; Suppress native forecasts so this isolates generation, drawing and RNG ownership,
; not forecast/fade/steering calibration. Trigger once per process on a control tick.
timing_weather_effect_test
 lea timing_weather_effect_test_state(pc),a0
 tst.l 8(a0)
 bne.s .done
 move.l timing_world20_state+16(pc),d0
 cmp.l #200,d0
 blo.s .done
 move.l #1,8(a0)
 move.l d0,12(a0)
 move.l timing_world20_clock(pc),16(a0)
 move.w #1,$4c0(a6)
 move.l #-1,$4b8(a6)
 move.l #-1,$4bc(a6)
 clr.w $4c6(a6)
 move.w #$ffff,$4cc(a6)
 move.w #5,$4ce(a6)
 move.w #4,$4d2(a6)
.done
 rts
timing_weather_effect_test_state dc.b 'PDWEFT01'
 dc.l 0 ; activation count
 dc.l 0 ; world-step count at activation
 dc.l 0 ; logical timestamp at activation
 ENDC
