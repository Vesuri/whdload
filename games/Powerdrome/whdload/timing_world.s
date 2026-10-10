; Development-only full-world cadence pilot. No additional native call frame is
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
 IFNE TIMING_WORLD20
 bsr timing_forces_initialize
 clr.w timing_world20_initialized-timing_world_state(a0)
 clr.w timing_world20_scalar_remainder-timing_world_state(a0)
 clr.l timing_world20_vector_remainders-timing_world_state(a0)
 clr.l timing_world20_vector_remainders+4-timing_world_state(a0)
 clr.l timing_world20_vector_remainders+8-timing_world_state(a0)
 ENDC
 IFNE TIMING_WORLD20
 tst.w timing_pit_rebase-timing_world_state(a0)
 bne.s .seed_ready
 tst.w timing_pit_initial-timing_world_state(a0)
 bne.s .seed_ready
 move.l a0,-(sp)
 lea timing_pit_opponent_state(pc),a0
 clr.w 8(a0)
 movea.l (sp)+,a0
 ENDC
 IFEQ TIMING_WORLD_SEED+1
 move.w $62(a6),d0
 ELSE
 move.w #TIMING_WORLD_SEED,d0
 ENDC
 move.w d0,26(a0)
 move.w d0,28(a0)
.seed_ready
 IFNE TIMING_WORLD20
 clr.w timing_pit_initial-timing_world_state(a0)
 ENDC
 movem.l (sp)+,d0/a0
 rts

timing_world_begin
 move.w sr,-(sp)
 movem.l d0/a0,-(sp)
 lea timing_world_state(pc),a0
 tst.w 8(a0)
 bne.s .next
 move.w #1,8(a0)
 move.l $5e(a6),12(a0)
 move.w $62(a6),24(a0)
 move.w 26(a0),$62(a6)
.next
 IFNE TIMING_WORLD20
 bsr timing_world20_begin
 bsr timing_opponent_flight_initialize
 ENDC
 moveq #0,d0
 move.w timing_control_phase(pc),d0
 IFNE TIMING_WORLD20
 bsr timing_world20_test_control
 bne.s .phase_ready
 subq.w #1,d0
.phase_ready
 ENDC
 move.l d0,$5e(a6)
 move.w d0,30(a0)
 IFNE TIMING_WORLD20
 move.l timing_world20_clock(pc),16(a0)
 ELSE
 move.l timing_input_clock(pc),16(a0)
 ENDC
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
 IFNE TIMING_WORLD20
 bsr timing_pit_is_retiring
 bne.w timing_world_native_end
 ENDC
 ; The native interval has exactly two gameplay readers: player and opponents.
 ; Incident presentation can change it after player movement but before this call.
 movem.l d0,-(sp)
 moveq #0,d0
 move.w timing_world_phase(pc),d0
 move.l d0,$5e(a6)
 movem.l (sp)+,d0
 IFNE TIMING_WORLD20
 move.w #TIMING_WORLD_STEP,$21c(a6)
 ; Practice has no opponent simulation; keep its previous end-of-step delta.
 tst.w $be(a6)
 beq.s .opponents_due_check
 bsr timing_world20_test_control
 beq.w timing_world_native_end
.opponents_due_check
 ENDC
 move.w #TIMING_PERIOD,$21c(a6)
 tst.w $be(a6)
 beq.w timing_world_opponent_call
 bra.w timing_world_native_end

timing_world_end
 move.w sr,-(sp)
 movem.l a0,-(sp)
 IFNE TIMING_WORLD20
 bsr timing_pit_is_retiring
 beq.s .ordinary_end
 lea timing_pit_state(pc),a0
 clr.w 10(a0)
 addq.l #1,56(a0)
 movem.l (sp)+,a0
 move.w (sp)+,ccr
 bra.w timing_world_render
.ordinary_end
 ENDC
 IFNE TIMING_WORLD20
 lea timing_world20_state(pc),a0
 addq.l #4,12(a0)
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
 IFNE TIMING_WORLD20
 bsr timing_center_present
 ENDC
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
 movem.l (sp)+,a0
 move.w (sp)+,ccr
 rts

timing_world_session_gate
 IFNE TIMING_WORLD20
 bsr timing_pit_abort
 ENDC
 bsr timing_world_restore
 move.w $43a(a6),d1
 cmp.w #4,d1
 bra.w timing_world_after_session_gate
timing_world_result_gate
 IFNE TIMING_WORLD20
 bsr timing_result_begin
 bsr timing_pit_abort
 ENDC
 IFNE TIMING_WORLD20
 bsr timing_world_input_disable
 ENDC
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

 IFNE TIMING_WORLD20
 INCLUDE timing_result.s
 INCLUDE timing_retune.s
 INCLUDE timing_pit.s
 INCLUDE timing_world20.s
 ENDC
