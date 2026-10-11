; Experimental forecast/start/expiry ownership. Native duration arithmetic is reused.
; Main-context logical controls own RNG; no physical/global clock is overwritten.
timing_weather_cycle_check
 move.l perf_game(pc),a0
 adda.l #$dd0e,a0
 cmp.l #$4a6e00b6,(a0)
 bne.w .wrong
 cmp.w #$661c,4(a0)
 bne.w .wrong
 adda.w #$dde6-$dd0e,a0
 cmp.l #$4a6e00b6,(a0)
 bne.w .wrong
 cmp.w #$6b10,4(a0)
 bne.w .wrong
 adda.w #$e1c4-$dde6,a0
 cmp.w #$2e39,(a0)
 bne.w .wrong
 move.l perf_game(pc),d0
 add.l #$f96,d0
 cmp.l 2(a0),d0
 bne.w .wrong
 adda.w #$e1f0-$e1c4,a0
 cmp.l #$d7ce6100,(a0)
 bne.w .wrong
 cmp.w #$5320,4(a0)
 bne.w .wrong
 adda.w #$e23c-$e1f0,a0
 cmp.w #$d0b9,(a0)
 bne.s .wrong
 cmp.l 2(a0),d0
 bne.s .wrong
 rts
.wrong
 pea TDREASON_WRONGVER
 move.l _resload(pc),a2
 jmp resload_Abort(a2)

timing_weather_cycle_reset
 move.l a0,-(sp)
 lea timing_weather_cycle_state(pc),a0
 clr.l 8(a0)
 clr.l 12(a0)
 clr.l 16(a0)
 clr.l 20(a0)
 movea.l (sp)+,a0
 rts

timing_weather_cycle_tick
 movem.l d0-d7/a0-a6,-(sp)
 bsr timing_weather_enabled
 beq.w .done
 bsr timing_world20_test_control
 beq.w .done
 IFNE TIMING_WEATHER_TRANSFER_TEST
 bsr timing_weather_transfer_test
 ENDC
 lea timing_weather_cycle_state(pc),a0
 tst.w 10(a0)
 bne.s .owned
 ; Translate any pre-existing native deadlines at first ownership transfer.
 move.l perf_game(pc),a1
 move.l $f96(a1),d1
 move.l timing_world20_clock(pc),d2
 lea $4bc(a6),a1
 bsr timing_weather_cycle_transfer
 lea $4b8(a6),a1
 bsr timing_weather_cycle_transfer
 move.w #1,10(a0)
.owned
 move.w #1,8(a0)
 move.l timing_world20_clock(pc),24(a0)
 IFNE TIMING_WEATHER_CYCLE_TEST
 bsr timing_weather_cycle_test
 lea timing_weather_cycle_state(pc),a0
 ENDC
 tst.w $4c0(a6)
 bgt.s .onset
 addq.l #1,28(a0)
 moveq #2,d1
 bsr timing_weather_random
 tst.w d0
 bne.s .onset
 ; The native routine only forecasts when the flag is exactly zero.
 tst.w $4c0(a6)
 bne.s .onset
 bsr timing_weather_cycle_forecast
 lea timing_weather_cycle_state(pc),a0
 addq.l #1,32(a0)
 move.l 24(a0),52(a0)
.onset
 tst.w $4bc(a6) ; preserve the native high-word sentinel test
 bmi.s .expiry
 move.l 24(a0),d0
 cmp.l $4bc(a6),d0
 blt.s .expiry
 move.w $62(a6),68(a0)
 bsr timing_weather_cycle_start
 lea timing_weather_cycle_state(pc),a0
 move.w $62(a6),70(a0)
 addq.l #1,36(a0)
 move.l 24(a0),56(a0)
 move.l $4b8(a6),d0
 sub.l 24(a0),d0
 move.l d0,64(a0)
.expiry
 move.l $5e(a6),d0
 and.w #7,d0
 bne.s .release
 tst.l $4b8(a6)
 bmi.s .release
 move.l 24(a0),d0
 cmp.l $4b8(a6),d0
 blt.s .release
 ; Native E25E's positive-mode message branch cannot apply to human-flight owner.
 ; Defer its palette call, then perform its persistent mutations in native order.
 move.w #1,14(a0)
 move.w #-15,$4c6(a6)
 move.l #-1,$4b8(a6)
 move.l #-1,$4bc(a6)
 clr.w $4cc(a6)
 addq.l #1,40(a0)
 move.l 24(a0),60(a0)
.release
 clr.w 8(a0)
.done
 movem.l (sp)+,d0-d7/a0-a6
 rts

; A1 points to a native deadline; D1 is physical now, D2 logical now.
; Preserve negative sentinels; due/overdue work becomes due at the logical cursor.
; Do not let a large overdue offset turn a live deadline into an inactive sentinel.
timing_weather_cycle_transfer
 move.l (a1),d0
 bmi.s .done
 sub.l d1,d0
 bpl.s .future
 moveq #0,d0
.future
 add.l d2,d0
 move.l d0,(a1)
.done
 rts

; Claimed logical deadlines must never be compared with the physical clock, even
; while a pit/mode transition temporarily suspends ordinary flight simulation.
timing_weather_cycle_outer
 move.l d0,-(sp)
 move.w timing_weather_cycle_state+10(pc),d0
 movem.l (sp)+,d0
 bne.w timing_weather_cycle_after_forecast
 tst.w $b6(a6)
 bne.w timing_weather_cycle_native_deadline
 bra.w timing_weather_cycle_native_trial

timing_weather_cycle_expiry_outer
 move.l d0,-(sp)
 move.w timing_weather_cycle_state+10(pc),d0
 movem.l (sp)+,d0
 bne.w timing_weather_cycle_after_expiry
 tst.w $b6(a6)
 bmi.w timing_weather_cycle_after_expiry
 bra.w timing_weather_cycle_native_expiry

timing_weather_cycle_clock
 move.l a0,-(sp)
 lea timing_weather_cycle_state(pc),a0
 tst.w 8(a0)
 beq.s .native
 move.l 24(a0),d7
 bra.s .done
.native
 move.l perf_game(pc),a0
 move.l $f96(a0),d7
.done
 movem.l (sp)+,a0
 rts

timing_weather_cycle_add_clock
 move.l a0,-(sp)
 lea timing_weather_cycle_state(pc),a0
 tst.w 8(a0)
 beq.s .native
 add.l 24(a0),d0
 bra.s .done
.native
 move.l perf_game(pc),a0
 add.l $f96(a0),d0
.done
 movem.l (sp)+,a0
 rts

timing_weather_cycle_message
 adda.l a6,a3
 move.l a0,-(sp)
 lea timing_weather_cycle_state(pc),a0
 tst.w 8(a0)
 beq.s .native
 move.w #1,12(a0)
 move.l a3,16(a0)
 move.l timing_message_clock+12(pc),20(a0)
 movem.l (sp)+,a0
 rts
.native
 movem.l (sp)+,a0
 bra.w timing_weather_cycle_native_message

timing_weather_cycle_present
 move.w sr,-(sp)
 movem.l d0-d7/a0-a6,-(sp)
 lea timing_weather_cycle_state(pc),a0
 cmp.w #1,12(a0)
 bne.s .palette
 move.w #2,12(a0)
 addq.l #1,44(a0)
 move.l 16(a0),a3
 bsr timing_weather_cycle_native_message
 lea timing_weather_cycle_state(pc),a0
 clr.w 12(a0)
.palette
 tst.w 14(a0)
 beq.s .done
 clr.w 14(a0)
 addq.l #1,48(a0)
 bsr timing_weather_cycle_native_palette
.done
 movem.l (sp)+,d0-d7/a0-a6
 move.w (sp)+,ccr
 rts

timing_weather_cycle_native_trial dc.w $4ef9
 dc.l 0
timing_weather_cycle_native_deadline dc.w $4ef9
 dc.l 0
timing_weather_cycle_after_forecast dc.w $4ef9
 dc.l 0
timing_weather_cycle_native_expiry dc.w $4ef9
 dc.l 0
timing_weather_cycle_after_expiry dc.w $4ef9
 dc.l 0
timing_weather_cycle_forecast dc.w $4ef9
 dc.l 0
timing_weather_cycle_start dc.w $4ef9
 dc.l 0
timing_weather_cycle_native_message dc.w $4ef9
 dc.l 0
timing_weather_cycle_native_palette dc.w $4ef9
 dc.l 0

timing_weather_cycle_state dc.b 'PDWCYC01'
 dc.w 0 ; +8 active logical call
 dc.w 0 ; +10 claimed deadline domain
 dc.w 0 ; +12 message pending=1 / presenting=2
 dc.w 0 ; +14 expiry palette pending
 dc.l 0 ; +16 message pointer
 dc.l 0 ; +20 message publication phase
 dc.l 0 ; +24 logical control clock
 dc.l 0 ; +28 forecast RNG trials
 dc.l 0 ; +32 forecasts
 dc.l 0 ; +36 onsets
 dc.l 0 ; +40 expiries
 dc.l 0 ; +44 message deliveries
 dc.l 0 ; +48 expiry palette deliveries
 dc.l 0 ; +52 forecast clock
 dc.l 0 ; +56 onset clock
 dc.l 0 ; +60 expiry clock
 dc.l 0 ; +64 native randomized duration
 dc.w 0 ; +68 onset RNG before
 dc.w 0 ; +70 onset RNG after

 IFNE TIMING_WEATHER_CYCLE_TEST
; Seed one forecast trial at a repeatable control tick; no clock/deadline shortening.
timing_weather_cycle_test
 lea timing_weather_cycle_test_state(pc),a0
 tst.l 8(a0)
 bne.s .done
 move.l timing_world20_state+16(pc),d0
 cmp.l #200,d0
 blo.s .done
 move.l #1,8(a0)
 move.l d0,12(a0)
 move.l timing_world20_clock(pc),16(a0)
 clr.w $62(a6) ; native shift-2 trial: 0 -> 1 -> result 0
 clr.w $4c0(a6)
 move.l #-1,$4b8(a6)
 move.l #-1,$4bc(a6)
 clr.w $4c6(a6)
 clr.w $4cc(a6)
.done
 rts
timing_weather_cycle_test_state dc.b 'PDWCTS01'
 dc.l 0,0,0
 ENDC


 IFNE TIMING_WEATHER_TRANSFER_TEST
; Exercise the actual assembled transfer helper on private cells, once per process.
; No native deadline, clock, seed or input field is changed by these vectors.
timing_weather_transfer_test
 lea timing_weather_transfer_test_state(pc),a2
 tst.l 8(a2)
 bne.s .done
 move.l #1,8(a2)
 lea 20(a2),a0
 moveq #10,d3
.next
 move.l (a0),16(a0)
 lea 16(a0),a1
 move.l 4(a0),d1
 move.l 8(a0),d2
 bsr timing_weather_cycle_transfer
 move.l d1,20(a0)
 move.l d2,24(a0)
 move.l a1,28(a0)
 addq.l #1,12(a2)
 move.l 16(a0),d0
 cmp.l 12(a0),d0
 beq.s .matched
 addq.l #1,16(a2)
.matched
 lea 32(a0),a0
 dbra d3,.next
.done
 rts

timing_weather_transfer_test_state dc.b 'PDWTFR01'
 dc.l 0 ; invocation count
 dc.l 0 ; case count
 dc.l 0 ; result mismatches
 ; Each row: deadline, physical now, logical now, expected result;
 ; then result, preserved physical/logical registers and destination pointer.
 dc.l -1,1000,200,-1
 dc.l 0,0,0,0
 dc.l $80000000,1000,200,$80000000
 dc.l 0,0,0,0
 dc.l 1500,1000,200,700
 dc.l 0,0,0,0
 dc.l 1000,1000,200,200
 dc.l 0,0,0,0
 dc.l 999,1000,200,200
 dc.l 0,0,0,0
 dc.l 1,10000,200,200
 dc.l 0,0,0,0
 dc.l 0,10,0,0
 dc.l 0,0,0,0
 dc.l 1,0,0,1
 dc.l 0,0,0,0
 dc.l $7fffffff,$7ffffffe,100,101
 dc.l 0,0,0,0
 dc.l $7fffffff,$7fffffff,100,100
 dc.l 0,0,0,0
 dc.l $7ffffffe,$7fffffff,100,100
 dc.l 0,0,0,0
 ENDC
