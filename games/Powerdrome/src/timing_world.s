; 20-ms world scheduler. No additional native call frame is
; held while the world body executes: native nonlocal stack exits remain valid.
 IFND TIMING_WORLD_SEED
TIMING_WORLD_SEED = -1
 ENDC
 IFGT TIMING_WORLD_SEED-65535
 FAIL "TIMING_WORLD_SEED must be -1 or an unsigned word"
 ENDC
 IFLT TIMING_WORLD_SEED+1
 FAIL "TIMING_WORLD_SEED must be -1 or an unsigned word"
 ENDC
timing_world_initialize
 movem.l d0/a0,-(sp)
 lea timing_session_state(pc),a0
 addq.l #1,8(a0)
 lea timing_world_state(pc),a0
 IFNE TIMING_MOUSE
 bsr timing_mouse_reset
 ENDC
 bsr timing_forces_initialize
 IFNE TIMING_WEATHER_EFFECTS
 bsr timing_weather_reset
 ENDC
 tst.w timing_pit_rebase-timing_world_state(a0)
 bne.s .keep_message_clock
 clr.w timing_message_clock+8-timing_world_state(a0)
.keep_message_clock
 clr.w timing_world20_initialized-timing_world_state(a0)
 clr.w timing_world20_scalar_remainder-timing_world_state(a0)
 clr.l timing_world20_vector_remainders-timing_world_state(a0)
 clr.l timing_world20_vector_remainders+4-timing_world_state(a0)
 clr.l timing_world20_vector_remainders+8-timing_world_state(a0)
 tst.w timing_pit_rebase-timing_world_state(a0)
 bne.s .seed_ready
 tst.w timing_pit_initial-timing_world_state(a0)
 bne.s .seed_ready
 move.l a0,-(sp)
 lea timing_pit_opponent_state(pc),a0
 clr.w 8(a0)
 movea.l (sp)+,a0
 IFEQ TIMING_WORLD_SEED+1
 move.w $62(a6),d0
 ELSE
 move.w #TIMING_WORLD_SEED,d0
 ENDC
 move.w d0,26(a0)
 move.w d0,28(a0)
.seed_ready
 clr.w timing_pit_initial-timing_world_state(a0)
 movem.l (sp)+,d0/a0
 rts

timing_world_begin
 move.w sr,-(sp)
 movem.l d0/a0,-(sp)
 IFNE VERIFY_PHASE
 bsr phase_record
 dc.w 16
 ENDC
 lea timing_world_state(pc),a0
 tst.w 8(a0)
 bne.s .next
 move.w #1,8(a0)
 move.l $5e(a6),12(a0)
 move.w $62(a6),24(a0)
 move.w 26(a0),$62(a6)
.next
 bsr timing_world20_begin
 bsr timing_opponent_flight_initialize
 moveq #0,d0
 move.w timing_control_phase(pc),d0
 bsr timing_world20_test_control
 bne.s .phase_ready
 subq.w #1,d0
.phase_ready
 move.l d0,$5e(a6)
 move.w d0,30(a0)
 bsr timing_message_phase_update
 move.l timing_world20_clock(pc),16(a0)
 addq.l #1,20(a0)
 movem.l (sp)+,d0/a0
 move.w (sp)+,ccr
 rts

timing_world_movement
 move.w #TIMING_WORLD_STEP,$21c(a6)
 move.w $194(a6),d4
 muls.w $21c(a6),d4
 bra.w timing_world_after_multiply

timing_world_opponents
 bsr timing_pit_is_retiring
 bne.w timing_world_native_end
 ; The native interval has exactly two gameplay readers: player and opponents.
 ; Incident presentation can change it after player movement but before this call.
 movem.l d0,-(sp)
 moveq #0,d0
 move.w timing_world_phase(pc),d0
 move.l d0,$5e(a6)
 movem.l (sp)+,d0
 move.w #TIMING_WORLD_STEP,$21c(a6)
 ; Practice has no opponent simulation; keep its previous end-of-step delta.
 tst.w $be(a6)
 beq.s .opponents_due_check
 bsr timing_world20_test_control
 beq.w timing_world_native_end
.opponents_due_check
 move.w #TIMING_PERIOD,$21c(a6)
 tst.w $be(a6)
 beq.w timing_world_opponent_call
 bra.w timing_world_native_end

timing_world_end
 move.w sr,-(sp)
 movem.l a0,-(sp)
 bsr timing_pit_is_retiring
 beq.s .ordinary_end
 lea timing_pit_state(pc),a0
 clr.w 10(a0)
 addq.l #1,56(a0)
 movem.l (sp)+,a0
 move.w (sp)+,ccr
 bra.w timing_world_render
.ordinary_end
 bsr timing_opponent_effects_tick
 IFNE TIMING_WEATHER_CYCLE
 bsr timing_weather_cycle_tick
 ENDC
 IFNE TIMING_WEATHER_EFFECTS
 bsr timing_weather_tick
 ENDC
 IFNE TIMING_WEATHER_FADE
 ; Native outer-loop generation precedes the fade mutation at the same boundary.
 bsr timing_weather_fade_tick
 ENDC
 lea timing_world20_state(pc),a0
 addq.l #4,12(a0)
 IFNE VERIFY_PHASE
 bsr phase_record
 dc.w 15
 ENDC
 lea timing_state(pc),a0
 subq.w #1,timing_orientation_left-timing_state(a0)
 movem.l (sp)+,a0
 beq.s .finished
 move.w (sp)+,ccr
 bra.w timing_orientation_again
.finished
 move.w (sp)+,ccr
 bsr timing_world_restore
timing_world_render
 IFNE VERIFY_PHASE
 bsr phase_record
 dc.w 2
 ENDC
 IFNE TIMING_WEATHER_CYCLE
 bsr timing_weather_cycle_present
 ENDC
 bsr timing_center_present
 ; Replay the entire displaced TST/BEQ, preserving its condition flags.
 tst.w $2be(a6)
 beq.w timing_world_native_render
 bra.w timing_world_pre_render

timing_world_restore
 move.w sr,-(sp)
 movem.l a0,-(sp)
 lea timing_world_state(pc),a0
 tst.w 8(a0)
 beq.s .done
 move.l 12(a0),$5e(a6)
 move.w $62(a6),26(a0)
 move.w 24(a0),$62(a6)
 clr.w 8(a0)
.done
 IFNE VERIFY_PHASE
 ; Close an abandoned step without incrementing its completed-tick count.
 ; Normal completion already emitted 15; these closes then become no-ops.
 bsr phase_record
 dc.w 17
 bsr phase_record
 dc.w 2
 ENDC
 movem.l (sp)+,a0
 move.w (sp)+,ccr
 rts

timing_world_session_gate
 bsr timing_pit_abort
 bsr timing_world_restore
 move.w $43a(a6),d1
 cmp.w #4,d1
 bra.w timing_world_after_session_gate
timing_world_result_gate
 bsr timing_result_begin
 bsr timing_pit_abort
 bsr timing_world_input_disable
 bsr timing_world_restore
 move.w #0,$b0(a6)
 bra.w timing_world_after_result_gate

timing_world_after_multiply dc.w $4ef9
 dc.l 0
timing_world_native_end dc.w $4ef9
 dc.l 0
timing_world_opponent_call dc.w $4ef9
 dc.l 0
timing_world_pre_render dc.w $4ef9
 dc.l 0
timing_world_native_render dc.w $4ef9
 dc.l 0
timing_world_after_session_gate dc.w $4ef9
 dc.l 0
timing_world_after_result_gate dc.w $4ef9
 dc.l 0

timing_world_state dc.b 'PDWORLD1'
 dc.w 0 ; active while the native counter belongs to this logical world update
 dc.w 0
 dc.l 0 ; outer/render counter restored before normal scene drawing or known exits
 dc.l 0 ; current logical world time (same units as input timestamps)
 dc.l 0 ; complete-world updates started
 dc.w 0 ; saved outer/render RNG seed
 dc.w 0 ; persistent world RNG seed
 dc.w 0 ; initial world seed (test diagnostics)
timing_world_phase dc.w 0

 INCLUDE timing_session.s

 INCLUDE timing_sync_test.s
 INCLUDE timing_opponent_effects.s
 INCLUDE timing_lap.s
 INCLUDE timing_player_lap.s
 INCLUDE timing_external.s
 IFNE TIMING_REPAIR
 INCLUDE timing_repair.s
 ENDC
 INCLUDE timing_result.s
 INCLUDE timing_retune.s
 INCLUDE timing_pit.s
 INCLUDE timing_world20.s
