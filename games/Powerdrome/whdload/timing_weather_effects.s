; Experimental normal-flight effect ownership. Forecast scheduling remains separate.
; TIMING_WEATHER_FADE optionally schedules the transition alongside these effects.
; Separate weather-loop and visual deadlines own generation/lifetime RNG advances.
; A500 candidate: 80/140-ms loops without/with an effect, visual phase +20 ms.
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
 IFNE TIMING_WEATHER_FADE
 bsr timing_weather_fade_reset
 ENDC
 move.l a0,-(sp)
 lea timing_weather_state(pc),a0
 clr.l 8(a0)
 clr.l 12(a0)
 clr.l 16(a0)
 lea timing_weather_clock(pc),a0
 clr.l 8(a0)
 clr.l 12(a0)
 clr.l 16(a0)
 clr.l 20(a0)
 clr.l 24(a0)
 clr.l 36(a0)
 clr.l 40(a0)
 movea.l (sp)+,a0
 rts

timing_weather_tick
 movem.l d0-d7/a0-a6,-(sp)
 bsr timing_weather_enabled
 bne.s .enabled
 bsr timing_weather_reset
 bra.w .done
.enabled
 lea timing_weather_state(pc),a0
 lea timing_weather_clock(pc),a1
 tst.w 8(a1)
 bne.s .visual_check
 move.w #1,8(a1)
 move.l timing_world20_clock(pc),12(a1)
.visual_check
 tst.w 10(a1)
 beq.s .generation_check
 move.l timing_world20_clock(pc),d0
 sub.l 16(a1),d0
 bmi.s .generation_check
 clr.w 10(a1)
 addq.l #1,32(a1)
 move.l 16(a1),24(a1)
 move.l 16(a1),40(a0)
 clr.w 8(a0)
 tst.w $4ce(a6)
 beq.s .visual_seed_done
 move.w $4ce(a6),8(a0)
 move.w $62(a6),10(a0)
 subq.w #1,$4ce(a6)
 addq.l #1,24(a0)
 moveq #0,d1
 moveq #3,d7
.visual_rng
 bsr timing_weather_random
 dbra d7,.visual_rng
.visual_seed_done
 move.w $62(a6),40(a1)
.generation_check
 move.l timing_world20_clock(pc),d0
 sub.l 12(a1),d0
 bmi.w .done
 IFNE TIMING_WEATHER_EFFECT_TEST
 bsr timing_weather_effect_test
 lea timing_weather_state(pc),a0
 lea timing_weather_clock(pc),a1
 ENDC
 addq.l #1,20(a0)
 addq.l #1,28(a1)
 move.l 12(a1),20(a1)
.generation
 tst.w $4cc(a6)
 beq.w .scheduled
 tst.w $4c6(a6)
 bne.w .scheduled
 tst.w $104(a6)
 bne.w .scheduled
 tst.w $4d2(a6)
 beq.s .attempt
 subq.w #1,$4d2(a6)
 bne.w .scheduled
 move.w #1,16(a0)
.attempt
 addq.l #1,28(a0)
 moveq #7,d1
 bsr timing_weather_random
 cmp.w #6,d0
 bgt.s .scheduled
 and.w #5,d0
 move.w d0,$4ce(a6)
 addq.l #1,32(a0)
 moveq #14,d1
 bsr timing_weather_random
 addq.w #4,d0
 move.w d0,$4d2(a6)
.scheduled
 move.w $62(a6),38(a1)
 move.w #1,10(a1)
 move.l 20(a1),d0
 addq.l #4,d0
 move.l d0,16(a1)
 moveq #16,d0
 tst.w $4ce(a6)
 beq.s .period_ready
 moveq #28,d0
.period_ready
 move.w d0,36(a1)
 add.l d0,12(a1)
.done
 movem.l (sp)+,d0-d7/a0-a6
 rts

; The outer loop still performs native sound trigger, but no owned RNG work.
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

timing_weather_state dc.b 'PDWEFX02'
 dc.w 0 ; +8 latest logical pre-decrement lifetime (visible state)
 dc.w 0 ; +10 visual pre-draw seed
 dc.w 0 ; +12 temporary render seed ownership
 dc.w 0 ; +14 saved outer seed
 dc.w 0 ; +16 pending sound trigger
 dc.w 0 ; +18 reserved
 dc.l 0 ; +20 logical weather-loop generations
 dc.l 0 ; +24 logical visual RNG events
 dc.l 0 ; +28 generation attempts
 dc.l 0 ; +32 successful selections (including zero lifetime)
 dc.l 0 ; +36 actual effect draws
 dc.l 0 ; +40 most recent visual publication timestamp
 dc.l 0 ; +44 actual sound-trigger calls

timing_weather_clock dc.b 'PDWECLK1'
 dc.w 0 ; +8 initialized
 dc.w 0 ; +10 visual publication pending
 dc.l 0 ; +12 next generation deadline
 dc.l 0 ; +16 visual deadline
 dc.l 0 ; +20 last generation clock
 dc.l 0 ; +24 last visual clock
 dc.l 0 ; +28 generation boundaries
 dc.l 0 ; +32 visual publications, including blank scenes
 dc.w 0 ; +36 upcoming scene period, native clock units
 dc.w 0 ; +38 RNG immediately after generation
 dc.w 0 ; +40 RNG immediately after visual publication
 dc.w 0 ; +42 reserved

 IFNE TIMING_WEATHER_EFFECT_TEST
; Directed effect-only fixtures. No clock/input rewrite or cache changes.
; Mode 1 publishes an existing effect; mode 2 seeds a successful native selection.
; Mode 3 seeds an immediate sound plus a four-cycle delay for a second request.
; Suppress native forecasts so this isolates generation, drawing and RNG ownership,
; not forecast/fade/steering calibration. Trigger once per process on a weather-loop boundary.
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
 IFEQ TIMING_WEATHER_EFFECT_TEST-2
 ; LCG: 3705 -> 640 (>>7 = 5), then 51585 (>>14 + 4 = 7).
 move.w #3705,$62(a6)
 clr.w $4ce(a6)
 clr.w $4d2(a6)
 ELSE
 IFEQ TIMING_WEATHER_EFFECT_TEST-3
 ; 557 -> 44 (lifetime 0), then 6005 (delay 4). Native generation owns both calls.
 move.w #557,$62(a6)
 clr.w $4ce(a6)
 move.w #1,$4d2(a6)
 ELSE
 move.w #5,$4ce(a6)
 move.w #4,$4d2(a6)
 ENDC
 ENDC
.done
 rts
timing_weather_effect_test_state
 IFEQ TIMING_WEATHER_EFFECT_TEST-3
 dc.b 'PDWEFT03'
 ELSE
 dc.b 'PDWEFT01'
 ENDC
 dc.l 0 ; activation count
 dc.l 0 ; world-step count at activation
 dc.l 0 ; logical timestamp at activation
 ENDC
