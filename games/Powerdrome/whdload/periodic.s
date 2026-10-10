 IFND TIMING_INPUT
TIMING_INPUT = 0
 ENDC
 IFND TIMING_BRAKE
TIMING_BRAKE = TIMING_INPUT
 ENDC
 IFNE TIMING_INPUT
 IFEQ TIMING_BRAKE
 FAIL "TIMING_INPUT requires TIMING_BRAKE"
 ENDC
 ENDC
 IFND TIMING_ORIENTATION
TIMING_ORIENTATION = 0
 ENDC
 IFNE TIMING_INPUT
 IFEQ TIMING_ORIENTATION
 FAIL "TIMING_INPUT requires TIMING_ORIENTATION"
 ENDC
 ENDC
 IFND TIMING_ENGINE
TIMING_ENGINE = 0
 ENDC
 IFNE TIMING_ENGINE
 IFEQ TIMING_INPUT
 FAIL "TIMING_ENGINE requires TIMING_INPUT"
 ENDC
 ENDC
 IFND TIMING_MOVE_CLOCK
TIMING_MOVE_CLOCK = 0
 ENDC
 IFNE TIMING_MOVE_CLOCK
 IFEQ TIMING_INPUT
 FAIL "TIMING_MOVE_CLOCK requires TIMING_INPUT"
 ENDC
 ENDC
 IFND TIMING_WORLD
TIMING_WORLD = 0
 ENDC
 IFNE TIMING_WORLD
 IFEQ TIMING_INPUT
 FAIL "TIMING_WORLD requires TIMING_INPUT"
 ENDC
 IFEQ TIMING_ENGINE
 FAIL "TIMING_WORLD requires TIMING_ENGINE"
 ENDC
 IFNE TIMING_MOVE_CLOCK
 FAIL "TIMING_WORLD owns movement time; disable TIMING_MOVE_CLOCK"
 ENDC
 ENDC
 IFND TIMING_WORLD20
TIMING_WORLD20 = 0
 ENDC
 IFNE TIMING_WORLD20
 IFEQ TIMING_WORLD
 FAIL "TIMING_WORLD20 requires TIMING_WORLD"
 ENDC
TIMING_WORLD_STEP = 4
 ELSE
TIMING_WORLD_STEP = 18
 ENDC
 IFND TIMING_RETUNE_RESULT_TEST
TIMING_RETUNE_RESULT_TEST = 0
 ENDC
 IFLT TIMING_RETUNE_RESULT_TEST
 FAIL "TIMING_RETUNE_RESULT_TEST must be 0, 1 (initial), or 2 (rescue)"
 ENDC
 IFGT TIMING_RETUNE_RESULT_TEST-2
 FAIL "TIMING_RETUNE_RESULT_TEST must be 0, 1 (initial), or 2 (rescue)"
 ENDC
 IFNE TIMING_RETUNE_RESULT_TEST
 IFND VERIFY
 FAIL "TIMING_RETUNE_RESULT_TEST requires VERIFY"
 ENDC
 IFEQ TIMING_WORLD20
 FAIL "TIMING_RETUNE_RESULT_TEST requires TIMING_WORLD20"
 ENDC
 ENDC
 IFND TIMING_SETUP_SEED
TIMING_SETUP_SEED = -1
 ENDC
 IFGT TIMING_SETUP_SEED-65535
 FAIL "TIMING_SETUP_SEED must be -1 or an unsigned word"
 ENDC
 IFLT TIMING_SETUP_SEED+1
 FAIL "TIMING_SETUP_SEED must be -1 or an unsigned word"
 ENDC
 IFNE TIMING_SETUP_SEED+1
 IFND VERIFY
 FAIL "TIMING_SETUP_SEED requires VERIFY"
 ENDC
 IFEQ TIMING_WORLD20
 FAIL "TIMING_SETUP_SEED requires TIMING_WORLD20"
 ENDC
 ENDC
; Development-only staged extraction. Not included unless TIMING_PERIODIC=1.
; An 18-unit (90 ms) cadence is 11.111 Hz on PAL, near the measured A500 routes.
TIMING_PERIOD = 18
install_periodic
 movem.l d0-d2/a0-a2,-(sp)
 move.l perf_game(pc),a1
 lea timing_targets(pc),a0
 moveq #(timing_targets_end-timing_targets)/6-1,d2
.fix
 move.l (a0)+,d0
 add.l a1,d0
 move.w (a0)+,d1
 lea timing_targets(pc),a2
 adda.w d1,a2
 move.l d0,(a2)
 dbra d2,.fix
 move.l (4).w,a0
 btst #AFB_68010,AttnFlags+1(a0)
 beq.w .flags
 lea timing_frame(pc),a0
 move.w #$42e7,(a0)
 IFNE TIMING_WORLD20
 IFNE TIMING_SETUP_SEED+1
 lea timing_setup_begin(pc),a0
 move.w #$42e7,(a0)
 lea timing_setup_reseed(pc),a0
 move.w #$42e7,(a0)
 ENDC
 lea timing_pit_opponent_save_return(pc),a0
 move.w #$42e7,(a0)
 lea timing_pit_opponent_allocate(pc),a0
 move.w #$42e7,(a0)
 lea timing_pit_opponent_begin(pc),a0
 move.w #$42e7,(a0)
 lea timing_pit_opponent_end(pc),a0
 move.w #$42e7,(a0)
 lea timing_pit_opponent_restore(pc),a0
 move.w #$42e7,(a0)
 IFD VERIFY
 lea timing_result_flags(pc),a0
 move.w #$42e7,(a0)
 lea timing_retune_flags(pc),a0
 move.w #$42e7,(a0)
 ENDC
 lea timing_external_step(pc),a0
 move.w #$42e7,(a0)
 lea timing_external_flags(pc),a0
 move.w #$42e7,(a0)
 lea timing_result_begin(pc),a0
 move.w #$42e7,(a0)
 lea timing_result_clock_d7(pc),a0
 move.w #$42e7,(a0)
 lea timing_pit_retune(pc),a0
 move.w #$42e7,(a0)
 lea timing_initial_pit_enter(pc),a0
 move.w #$42e7,(a0)
 lea timing_pit_enter(pc),a0
 move.w #$42e7,(a0)
 lea timing_pit_leave(pc),a0
 move.w #$42e7,(a0)
 lea timing_pit_abort(pc),a0
 move.w #$42e7,(a0)
 lea timing_world20_divide(pc),a0
 move.w #$42e7,(a0)
 lea timing_center_present(pc),a0
 move.w #$42e7,(a0)
 lea timing_key_publish(pc),a0
 move.w #$42e7,(a0)
 lea timing_world_shift_test(pc),a0
 move.w #$42e7,(a0)
 ENDC
 IFNE TIMING_WORLD
 lea timing_world_begin(pc),a0
 move.w #$42e7,(a0)
 lea timing_world_restore(pc),a0
 move.w #$42e7,(a0)
 lea timing_session_end(pc),a0
 move.w #$42e7,(a0)
 lea timing_world_end(pc),a0
 move.w #$42e7,(a0)
 ENDC
 IFNE TIMING_MOVE_CLOCK
 lea timing_movement_clock(pc),a0
 move.w #$42e7,(a0)
 lea timing_movement_read_flags(pc),a0
 move.w #$42d0,(a0)
 ENDC
 IFNE TIMING_BRAKE
 lea timing_brake_vbl(pc),a0
 move.w #$42e7,(a0)
 ENDC
 IFNE TIMING_INPUT
 IFNE TIMING_ENGINE
 lea timing_engine_tick(pc),a0
 move.w #$42e7,(a0)
 lea timing_engine_enqueue(pc),a0
 move.w #$42e7,(a0)
 lea timing_engine_present(pc),a0
 move.w #$42e7,(a0)
 ENDC
 lea timing_resource_tick(pc),a0
 move.w #$42e7,(a0)
 lea timing_brake_before_control(pc),a0
 move.w #$42e7,(a0)
 lea timing_brake_before_movement(pc),a0
 move.w #$42e7,(a0)
 lea timing_input_pause_begin(pc),a0
 move.w #$42e7,(a0)
 lea timing_input_pause_end(pc),a0
 move.w #$42e7,(a0)
 lea timing_input_joy_fire(pc),a0
 move.w #$42e7,(a0)
 lea timing_input_joy_down(pc),a0
 move.w #$42e7,(a0)
 ENDC
.flags
 lea pl_periodic(pc),a0
 move.l _resload(pc),a2
 jsr resload_Patch(a2)
 movem.l (sp)+,d0-d2/a0-a2
 rts
pl_periodic PL_START
 IFNE TIMING_WORLD20
 ; Timestamp centering at native keyboard publication, before drawing consumes it.
 ; TIMING_RANGE h0:$5816 6 bit=C3
 PL_PS $5816,timing_key_publish
 ; Native post-render C/X/Z handlers no longer mutate simulation state.
 ; TIMING_RANGE h0:$c88e 8 bit=C3
 PL_P $c88e,timing_center_skip
 PL_NOP $c894,2
 ; TIMING_RANGE h0:$c89a 6 bit=C3
 PL_P $c89a,timing_center_skip
 ; TIMING_RANGE h0:$c8b0 6 bit=C3
 PL_P $c8b0,timing_center_skip
 ; Both centering/orientation and displacement use movement-time Shift history.
 ; TIMING_RANGE h0:$ca5a 8 bit=C3
 PL_PSS $ca5a,timing_world_shift_test,2
 ; TIMING_RANGE h0:$cd20 8 bit=C3
 PL_PSS $cd20,timing_world_shift_test,2
 ; TIMING_RANGE h0:$cd5c 8 bit=C3
 PL_P $cd5c,timing_fall_step
 PL_NOP $cd62,2
 ; Replace the bounded impulse body: no interior native branch remains live.
 ; TIMING_RANGE h0:$cd96 46 bit=C3
 PL_P $cd96,timing_impulse_step
 PL_NOP $cd9c,40
 ; Native initialization/repair writes reset the matching local fractions.
 ; TIMING_RANGE h0:$b390 8 bit=C3
 PL_PSS $b390,timing_fall_reset,2
 ; TIMING_RANGE h0:$c59e 8 bit=C3
 PL_PSS $c59e,timing_fall_reset,2
 ; TIMING_RANGE h0:$9c8c 6 bit=C3
 PL_PS $9c8c,timing_impulse_random_start
 ; TIMING_RANGE h0:$adba 6 bit=C3
 PL_PS $adba,timing_impulse_field_start
 ; Preserve sub-step fractions in scalar and direction-vector integration.
 ; TIMING_RANGE h0:$ccf6 8 bit=C3
 PL_P $ccf6,timing_world20_divide
 PL_NOP $ccfc,2
 ; TIMING_RANGE h0:$cd32 8 bit=C3
 PL_P $cd32,timing_world20_vectors
 PL_NOP $cd38,2
 ENDC
 IFNE TIMING_WORLD20
 ; TIMING_RANGE h0:$cde2 8 bit=C3
 PL_P $cde2,timing_world20_age
 PL_NOP $cde8,2
 ; Gate repeated contact feedback/damage at the slow cadence, after geometry.
 ; TIMING_RANGE h0:$fb64 6 bit=C3
 PL_P $fb64,timing_world20_contact
 IFNE TIMING_SETUP_SEED+1
 ; Fixed test seed before native initialization random draws.
 ; TIMING_RANGE h0:$b9a0 6 bit=C3
 PL_P $b9a0,timing_setup_begin
 ; Whole native MOVE.W clock-low-word to RNG seed.
 ; TIMING_RANGE h0:$bad6 8 bit=C3
 PL_P $bad6,timing_setup_reseed
 PL_NOP $badc,2
 ENDC
 ; Native entry MOVE.W plus BMI.W; original return depth is preserved.
 ; TIMING_RANGE h0:$d3d6 8 bit=C3
 PL_P $d3d6,timing_pit_opponents
 PL_NOP $d3dc,2
 ; Opponent-only direct clock reads. Outside modal updates these stay native.
 ; TIMING_RANGE h0:$d4b6 6 bit=C3
 PL_PS $d4b6,timing_pit_clock_d7
 ; TIMING_RANGE h0:$d4fe 6 bit=C3
 PL_PS $d4fe,timing_pit_clock_d0
 ; TIMING_RANGE h0:$d7f8 6 bit=C3
 PL_PS $d7f8,timing_pit_clock_d7
 ; TIMING_RANGE h0:$d836 6 bit=C3
 PL_PS $d836,timing_pit_clock_d7
 ; TIMING_RANGE h0:$d866 6 bit=C3
 PL_PS $d866,timing_pit_clock_d7
 IFNE TIMING_RETUNE_RESULT_TEST
 ; Native MOVE/TST/BPL; inject only the selected pit-boundary result outcome.
 ; TIMING_RANGE h0:$d560 10 bit=C3
 PL_P $d560,timing_retune_test_finish
 PL_NOP $d566,4
 ENDC
 ; External pit sequence: native moves, then native MOVEM/DBRA loop tail.
 ; TIMING_RANGE h0:$14764 6 bit=C3
 PL_P $14764,timing_external_step
 ; TIMING_RANGE h0:$1479e 8 bit=C3
 PL_P $1479e,timing_external_end
 PL_NOP $147a4,2
 ; Only ordinary result-duration accounting reads the logical winning instant.
 ; TIMING_RANGE h0:$c094 6 bit=C3
 PL_PS $c094,timing_result_clock_d7
 ; Departure retune BSR plus following MOVE.W; preserve native continuation.
 ; TIMING_RANGE h0:$14090 10 bit=C3
 PL_P $14090,timing_pit_retune
 PL_NOP $14096,4
 ; Native pit-result decision; only boundary catch-up defers its nonlocal exit.
 ; TIMING_RANGE h0:$d606 6 bit=C3
 PL_P $d606,timing_retune_result_gate
 ; Initial BSR plus MOVE.W; no world frame exists on this path.
 ; TIMING_RANGE h0:$bc3a 10 bit=C3
 PL_P $bc3a,timing_initial_pit_call
 PL_NOP $bc40,4
 ; Rescue BSR plus the complete following MOVE.W. Preserve native call depth.
 ; TIMING_RANGE h0:$ce1e 10 bit=C3
 PL_P $ce1e,timing_pit_call
 PL_NOP $ce24,4
 ; TIMING_RANGE h0:$fb84 8 bit=C3
 PL_P $fb84,timing_world20_damage
 PL_NOP $fb8a,2
 ENDC
 IFNE TIMING_WORLD
 ; TIMING_RANGE h0:$ccee 8 bit=C3
 PL_P $ccee,timing_world_movement
 PL_NOP $ccf4,2
 ; Recovery draws must not advance opponents outside scheduled world updates.
 ; Both call sites immediately test $e8 and do not consume returned registers/CCR.
 ; TIMING_RANGE h0:$fe40 4 bit=C3
 PL_NOP $fe40,4
 ; TIMING_RANGE h0:$ffc2 4 bit=C3
 PL_NOP $ffc2,4
 ; Restore world delta after incident helpers may have presented intermediate images.
 ; TIMING_RANGE h0:$ced2 6 bit=C3
 PL_P $ced2,timing_world_opponents
 ; TST pre-render flag and its two-byte conditional branch.
 ; TIMING_RANGE h0:$cedc 6 bit=C3
 PL_P $cedc,timing_world_end
 ; Restore temporary ownership at common mode destinations. Native callers keep
 ; their own stack unwinding, including incident, opponent and lap-end exits.
 ; TIMING_RANGE h0:$bf32 8 bit=C3
 PL_P $bf32,timing_world_session_gate
 PL_NOP $bf38,2
 ; TIMING_RANGE h0:$bfb0 6 bit=C3
 PL_P $bfb0,timing_world_result_gate
 ; Native cleanup call after the result animation and all its world updates.
 ; TIMING_RANGE h0:$c2aa 6 bit=C3
 PL_PS $c2aa,timing_session_finish
 ENDC
 IFNE TIMING_MOVE_CLOCK
 ; TIMING_RANGE h0:$ccee 8 bit=C3
 PL_P $ccee,timing_movement_clock
 PL_NOP $ccf4,2
 ENDC
 ; Six-byte BTST is replayed after accounting for the current interval.
 ; TIMING_RANGE h0:$ca44 6 bit=C3
 PL_P $ca44,timing_frame
 ; BSR control; TST animation. Continuation is the original conditional branch.
 ; TIMING_RANGE h0:$ca74 8 bit=C3
 PL_P $ca74,timing_control
 PL_NOP $ca7a,2
 ; TIMING_RANGE h0:$d922 8 bit=C3
 PL_P $d922,timing_resource
 PL_NOP $d928,2
 ; TIMING_RANGE h0:$d9a0 8 bit=C3
 PL_P $d9a0,timing_resource_end
 PL_NOP $d9a6,2
 IFNE TIMING_ORIENTATION
 ; TIMING_RANGE h0:$cce2 8 bit=C3
 ; TIMING_RANGE h0:$d028 6 bit=C3
 PL_P $d028,timing_brake_parity
 PL_P $cce2,timing_orientation_end
 PL_NOP $cce8,2
 ENDC
 IFNE TIMING_BRAKE
 ; Native decrements are serviced separately; their following clamps/jitter remain.
 ; TIMING_RANGE h0:$d00a 6 bit=C3
 PL_NOP $d00a,6
 ; TIMING_RANGE h0:$d01e 4 bit=C3
 PL_NOP $d01e,4
 IFNE TIMING_BRAKE
 ; Runs after native input sampling and the independent coverage-input hook.
 ; TIMING_RANGE h0:$5786 6 bit=C3
 PL_PS $5786,timing_brake_vbl
 ENDC
 ENDC
 IFNE TIMING_INPUT
 ; Historical buttons and modifiers; live input memory is never overwritten.
 ; TIMING_RANGE h0:$cf66 8 bit=C3
 PL_P $cf66,timing_input_buttons
 PL_NOP $cf6c,2
 ; TIMING_RANGE h0:$cf7a 6 bit=C3
 PL_P $cf7a,timing_input_modifiers
 ; TIMING_RANGE h0:$be12 6 bit=C3
 PL_PS $be12,timing_input_pause_begin
 ; TIMING_RANGE h0:$beec 6 bit=C3
 PL_PS $beec,timing_input_pause_end
 ; TIMING_RANGE h0:$d092 8 bit=C3
 PL_P $d092,timing_input_read_axes
 PL_NOP $d098,2
 ; TIMING_RANGE h0:$d082 8 bit=C3
 PL_P $d082,timing_input_write_axes
 PL_NOP $d088,2
 ; TIMING_RANGE h0:$d266 6 bit=C3
 PL_P $d266,timing_input_joystick
 ; TIMING_RANGE h0:$cf24 6 bit=C3
 PL_P $cf24,timing_input_poll_mode
 ; TIMING_RANGE h0:$cf40 6 bit=C3
 PL_P $cf40,timing_input_speed_mode
 ; TIMING_RANGE h0:$d0a2 6 bit=C3
 PL_P $d0a2,timing_input_axis_mode
 ; TIMING_RANGE h0:$cf46 6 bit=C3
 PL_PS $cf46,timing_input_joy_fire
 ; TIMING_RANGE h0:$cf4e 6 bit=C3
 PL_PS $cf4e,timing_input_joy_down
 ENDC
 IFNE TIMING_ENGINE
 ; TIMING_RANGE h0:$cfe4 8 bit=C3
 PL_P $cfe4,timing_heat_left
 PL_NOP $cfea,2
 ; TIMING_RANGE h0:$cff0 8 bit=C3
 PL_P $cff0,timing_heat_right
 PL_NOP $cff6,2
 ; TIMING_RANGE h0:$de04 6 bit=C3
 PL_P $de04,timing_engine_present
 ; TIMING_RANGE h0:$dfae 8 bit=C3
 PL_P $dfae,timing_engine_cooling
 PL_NOP $dfb4,2
 ; TIMING_RANGE h0:$dffc 8 bit=C3
 PL_P $dffc,timing_engine_footer
 PL_NOP $e002,2
 ; TIMING_RANGE h0:$de7e 10 bit=C3
 PL_P $de7e,timing_engine_flash_left
 PL_NOP $de84,4
 ; TIMING_RANGE h0:$df46 10 bit=C3
 PL_P $df46,timing_engine_flash_right
 PL_NOP $df4c,4
 ; TIMING_RANGE h0:$de88 10 bit=C3
 PL_P $de88,timing_engine_hud_left
 PL_NOP $de8e,4
 ; TIMING_RANGE h0:$df50 10 bit=C3
 PL_P $df50,timing_engine_hud_right
 PL_NOP $df56,4
 ; TIMING_RANGE h0:$de92 8 bit=C3
 PL_P $de92,timing_engine_message_left
 PL_NOP $de98,2
 ; TIMING_RANGE h0:$df5a 8 bit=C3
 PL_P $df5a,timing_engine_message_right
 PL_NOP $df60,2
 ENDC
 PL_END

timing_frame
 move.w sr,-(sp)
 movem.l d0-d2/a0-a1,-(sp)
 bsr timing_clock
 lea timing_state(pc),a1
 move.l perf_game(pc),a0
 IFNE TIMING_INPUT
 ; One clock domain for VBL input timestamps and periodic work (PAL).
 move.l $48fe(a0),d0
 sub.l timing_input_paused_fields-timing_state(a1),d0
 lsl.l #2,d0
 ELSE
 move.l $f96(a0),d0
 ENDC
 move.l d0,d1
 sub.l timing_last-timing_state(a1),d1
 move.l d0,timing_last-timing_state(a1)
 tst.w timing_started-timing_state(a1)
 beq.s .initial
 move.l $5e(a6),d0
 cmp.l timing_loop-timing_state(a1),d0
 blo.s .initial
 tst.l d1
 bmi.s .initial
 add.l d1,timing_phase-timing_state(a1)
 clr.w timing_due-timing_state(a1)
.again
 cmp.l #TIMING_WORLD_STEP,timing_phase-timing_state(a1)
 blo.s .accounted
 cmp.w #32,timing_due-timing_state(a1)
 bhs.s .accounted
 sub.l #TIMING_WORLD_STEP,timing_phase-timing_state(a1)
 addq.w #1,timing_due-timing_state(a1)
 addq.l #1,timing_ticks-timing_state(a1)
 bra.s .again
.initial
 IFNE TIMING_WORLD
 bsr timing_world_initialize
 ENDC
 IFNE TIMING_MOVE_CLOCK
 clr.w timing_movement_started-timing_state(a1)
 ENDC
 IFNE TIMING_INPUT
 bsr timing_input_initialize
 ENDC
 IFNE TIMING_BRAKE
 clr.w timing_brake_active-timing_state(a1)
 clr.l timing_brake_phase-timing_state(a1)
 IFNE TIMING_BRAKE
 clr.l timing_brake_pending-timing_state(a1)
 IFNE TIMING_INPUT
 clr.l timing_brake_read-timing_state(a1)
 ENDC
 ENDC
 ENDC
 IFNE TIMING_ENGINE
 IFNE TIMING_WORLD20
 tst.w timing_pit_rebase-timing_state(a1)
 bne.s .keep_engine_phase
 ENDC
 bsr timing_heat_initialize
 ; Preserve all low counter bits, not only the original first-loop odd parity.
 move.w $60(a6),timing_control_phase-timing_state(a1)
.keep_engine_phase
 ELSE
 move.w #1,timing_control_phase-timing_state(a1)
 ENDC
 IFNE TIMING_WORLD20
 clr.w timing_pit_rebase-timing_state(a1)
 ENDC
 move.w #1,timing_started-timing_state(a1)
 clr.l timing_phase-timing_state(a1)
 move.w #1,timing_due-timing_state(a1)
 addq.l #1,timing_ticks-timing_state(a1)
.accounted
 move.l $5e(a6),timing_loop-timing_state(a1)
 addq.l #1,timing_frames-timing_state(a1)
 IFNE TIMING_BRAKE
 IFEQ TIMING_INPUT
 bsr timing_service_brake
 ENDC
 ENDC
 IFNE TIMING_ORIENTATION
 move.w timing_due-timing_state(a1),timing_orientation_left-timing_state(a1)
 ENDC
 movem.l (sp)+,d0-d2/a0-a1
 move.w (sp)+,ccr
 IFNE TIMING_ORIENTATION
 ; No angle integration on draws between periodic updates. Movement still uses elapsed time.
 move.l d0,-(sp)
 move.w timing_due(pc),d0
 movem.l (sp)+,d0
 IFNE TIMING_WORLD
 beq.w timing_world_render
 ELSE
 beq.w timing_orientation_move
 ENDC
 ENDC
timing_orientation_again
 IFNE TIMING_WORLD
 bsr timing_world_begin
 IFNE TIMING_WORLD20
 bsr timing_world20_test_control
 beq.w timing_orientation_move
 ENDC
 ENDC
 IFNE TIMING_ORIENTATION
 ; The original first driving loop has odd parity. Advance by control updates, not draws.
 move.l d0,-(sp)
 move.w timing_control_phase(pc),d0
 btst #0,d0
 movem.l (sp)+,d0
 ELSE
 btst #0,$61(a6)
 ENDC
 bra.w timing_after_frame

timing_control
 movem.l d0/a0,-(sp)
 lea timing_state(pc),a0
 IFNE TIMING_ORIENTATION
 moveq #1,d0
 ELSE
 move.w timing_due(pc),d0
 ENDC
 move.w d0,timing_control_left-timing_state(a0)
 movem.l (sp)+,d0/a0
 beq.s .done
.next
 move.l a0,-(sp)
 lea timing_state(pc),a0
 addq.l #1,timing_controls-timing_state(a0)
 move.l (sp)+,a0
 IFNE TIMING_INPUT
 bsr timing_input_for_control
 bsr timing_brake_before_control
 ENDC
 pea .returned(pc)
 bra.w timing_native_control
.returned
 IFNE TIMING_INPUT
 bsr timing_resource_tick
 IFNE TIMING_ENGINE
 bsr timing_engine_tick
 ENDC
 ENDC
 move.l a0,-(sp)
 lea timing_state(pc),a0
 IFNE TIMING_INPUT
 clr.w timing_input_control_active-timing_state(a0)
 add.l #TIMING_PERIOD,timing_input_clock-timing_state(a0)
 ENDC
 addq.w #1,timing_control_phase-timing_state(a0)
 subq.w #1,timing_control_left-timing_state(a0)
 movea.l (sp)+,a0
 bne.s .next
.done
 tst.w $258(a6)
 bra.w timing_after_control

timing_resource
 IFNE TIMING_INPUT
 ; Resource mutation belongs to each logical control update; HUD drawing stays here.
 bra.w timing_resource_draw_due
 ELSE
 movem.l d0/a0,-(sp)
 lea timing_state(pc),a0
 move.w timing_due(pc),d0
 move.w d0,timing_resource_left-timing_state(a0)
 movem.l (sp)+,d0/a0
 beq.s timing_resource_draw_due
 tst.w $240(a6)
 bne.s timing_resource_draw_due
timing_resource_next
 move.l a0,-(sp)
 lea timing_state(pc),a0
 addq.l #1,timing_resources-timing_state(a0)
 movea.l (sp)+,a0
 bra.w timing_native_resource
 ENDC
timing_resource_draw_due
 pea timing_resource_continuation(pc)
 bra.w timing_resource_draw

timing_resource_end
 move.w d1,$1ba(a6)
 IFNE TIMING_INPUT
 rts
 ELSE
 move.l a0,-(sp)
 lea timing_state(pc),a0
 subq.w #1,timing_resource_left-timing_state(a0)
 movea.l (sp)+,a0
 bne.s timing_resource_next
 bra.s timing_resource_draw_due
 ENDC

 IFNE TIMING_INPUT
; Preserve the control caller's full machine state, including X. Native depletion
; sound calls remain in the main context and return through timing_resource_end.
timing_resource_tick
 move.w sr,-(sp)
 movem.l d0-d7/a0-a6,-(sp)
 tst.w $240(a6)
 bne.s .done
 lea timing_state(pc),a0
 addq.l #1,timing_resources-timing_state(a0)
 pea .done(pc)
 bra.w timing_native_resource
.done
 movem.l (sp)+,d0-d7/a0-a6
 move.w (sp)+,ccr
 rts
 ENDC

 IFNE TIMING_ORIENTATION
timing_brake_parity
 move.l d0,-(sp)
 move.w timing_control_phase(pc),d0
 btst #0,d0
 movem.l (sp)+,d0
 bra.w timing_after_brake_parity
timing_after_brake_parity dc.w $4ef9
 dc.l 0
timing_orientation_end
 IFNE TIMING_WORLD
 ; Finish this whole world update before starting the next owed control update.
 bra.w timing_orientation_move
 ELSE
 move.l a0,-(sp)
 lea timing_state(pc),a0
 subq.w #1,timing_orientation_left-timing_state(a0)
 movea.l (sp)+,a0
 bne.w timing_orientation_again
 ENDC
timing_orientation_move
 IFNE TIMING_INPUT
 IFEQ TIMING_WORLD
 bsr timing_brake_before_movement
 ENDC
 ENDC
 move.w $3f4(a6),d5
 move.w $3f6(a6),d6
 bra.w timing_after_orientation
timing_after_orientation dc.w $4ef9
 dc.l 0
 ENDC

timing_clock dc.w $4ef9
 dc.l 0
timing_after_frame dc.w $4ef9
 dc.l 0
timing_native_control dc.w $4ef9
 dc.l 0
timing_after_control dc.w $4ef9
 dc.l 0
timing_native_resource dc.w $4ef9
 dc.l 0
timing_resource_draw dc.w $4ef9
 dc.l 0
timing_resource_continuation dc.w $4ef9
 dc.l 0

timing_targets
 dc.l $59b6
 dc.w timing_clock+2-timing_targets
 dc.l $ca4a
 dc.w timing_after_frame+2-timing_targets
 dc.l $cef6
 dc.w timing_native_control+2-timing_targets
 dc.l $ca7c
 dc.w timing_after_control+2-timing_targets
 dc.l $d92a
 dc.w timing_native_resource+2-timing_targets
 dc.l $8b02
 dc.w timing_resource_draw+2-timing_targets
 dc.l $d9a8
 dc.w timing_resource_continuation+2-timing_targets
 IFNE TIMING_ORIENTATION
 dc.l $d02e
 dc.w timing_after_brake_parity+2-timing_targets
 dc.l $ccea
 dc.w timing_after_orientation+2-timing_targets
 ENDC
 IFNE TIMING_BRAKE
 dc.l $d382
 dc.w timing_brake_joystick+2-timing_targets
 ENDC
 IFNE TIMING_INPUT
 dc.l $d09a
 dc.w timing_input_after_read_axes+2-timing_targets
 dc.l $d08a
 dc.w timing_input_after_write_axes+2-timing_targets
 dc.l $d26c
 dc.w timing_input_joystick_body+2-timing_targets
 dc.l $cf2e
 dc.w timing_input_skip_poll+2-timing_targets
 dc.l $cf2a
 dc.w timing_input_do_poll+2-timing_targets
 dc.l $cf66
 dc.w timing_input_speed_mouse+2-timing_targets
 dc.l $cf46
 dc.w timing_input_speed_joy+2-timing_targets
 dc.l $d0a8
 dc.w timing_input_axis_mouse+2-timing_targets
 dc.l $d0b4
 dc.w timing_input_axis_joy+2-timing_targets
 dc.l $82b6
 dc.w timing_input_native_pause+2-timing_targets
 dc.l $cf6e
 dc.w timing_input_after_buttons+2-timing_targets
 dc.l $cf80
 dc.w timing_input_after_modifiers+2-timing_targets
 ENDC
 IFNE TIMING_ENGINE
 dc.l $8ae6
 dc.w timing_heat_native_random+2-timing_targets
 dc.l $cfec
 dc.w timing_heat_after_left+2-timing_targets
 dc.l $cff8
 dc.w timing_heat_after_right+2-timing_targets
 dc.l $de0a
 dc.w timing_engine_native_entry+2-timing_targets
 dc.l $dfb6
 dc.w timing_engine_native_cooling_branch+2-timing_targets
 dc.l $e004
 dc.w timing_engine_native_footer+2-timing_targets
 dc.l $de88
 dc.w timing_engine_after_flash_left+2-timing_targets
 dc.l $df50
 dc.w timing_engine_after_flash_right+2-timing_targets
 dc.l $de92
 dc.w timing_engine_after_hud_left+2-timing_targets
 dc.l $df5a
 dc.w timing_engine_after_hud_right+2-timing_targets
 dc.l $de9a
 dc.w timing_engine_after_message_left+2-timing_targets
 dc.l $df62
 dc.w timing_engine_after_message_right+2-timing_targets
 dc.l $e0c0
 dc.w timing_engine_native_flash+2-timing_targets
 dc.l $10d0c
 dc.w timing_engine_native_hud+2-timing_targets
 dc.l $13514
 dc.w timing_engine_native_message+2-timing_targets
 ENDC
 IFNE TIMING_MOVE_CLOCK
 dc.l $ccf6
 dc.w timing_movement_continue+2-timing_targets
 ENDC
 IFNE TIMING_WORLD
 dc.l $ccf6
 dc.w timing_world_after_multiply+2-timing_targets
 dc.l $cedc
 dc.w timing_world_native_end+2-timing_targets
 dc.l $ced8
 dc.w timing_world_opponent_call+2-timing_targets
 dc.l $cee2
 dc.w timing_world_pre_render+2-timing_targets
 dc.l $cee8
 dc.w timing_world_native_render+2-timing_targets
 dc.l $bf3a
 dc.w timing_world_after_session_gate+2-timing_targets
 dc.l $bfb6
 dc.w timing_world_after_result_gate+2-timing_targets
 dc.l $17148
 dc.w timing_session_native_cleanup+2-timing_targets
 ENDC
 IFNE TIMING_WORLD20
 IFNE TIMING_SETUP_SEED+1
 dc.l $b9a6
 dc.w timing_setup_after_begin+2-timing_targets
 dc.l $bade
 dc.w timing_setup_after_reseed+2-timing_targets
 ENDC
 IFNE TIMING_RETUNE_RESULT_TEST
 dc.l $d600
 dc.w timing_retune_test_result+2-timing_targets
 dc.l $d56c
 dc.w timing_retune_test_move+2-timing_targets
 ENDC
 dc.l $14764
 dc.w timing_external_loop+2-timing_targets
 dc.l $1476a
 dc.w timing_external_continue+2-timing_targets
 dc.l $147a6
 dc.w timing_external_return+2-timing_targets
 dc.l $e8d4
 dc.w timing_retune_native+2-timing_targets
 dc.l $1409a
 dc.w timing_retune_continue+2-timing_targets
 dc.l $d60c
 dc.w timing_retune_modal_result+2-timing_targets
 dc.l $d616
 dc.w timing_retune_native_result+2-timing_targets
 dc.l $bfb0
 dc.w timing_retune_result+2-timing_targets
 dc.l $d3d6
 dc.w timing_pit_opponent_direct+2-timing_targets
 dc.l $d3de
 dc.w timing_pit_opponent_body+2-timing_targets
 dc.l $d7f0
 dc.w timing_pit_opponent_empty+2-timing_targets
 dc.l $103a2
 dc.w timing_pit_native+2-timing_targets
 dc.l $ce28
 dc.w timing_pit_continue+2-timing_targets
 dc.l $bc44
 dc.w timing_initial_pit_continue+2-timing_targets
 dc.l $13514
 dc.w timing_center_message+2-timing_targets
 dc.l $bc4a
 dc.w timing_center_skip+2-timing_targets
 dc.l $cd64
 dc.w timing_fall_continue+2-timing_targets
 dc.l $cdc4
 dc.w timing_impulse_continue+2-timing_targets
 dc.l $ccfe
 dc.w timing_world20_after_divide+2-timing_targets
 dc.l $cd3a
 dc.w timing_world20_after_vectors+2-timing_targets
 dc.l $cdea
 dc.w timing_world20_after_age+2-timing_targets
 dc.l $cdf4
 dc.w timing_world20_skip_age+2-timing_targets
 dc.l $16f38
 dc.w timing_world20_contact_sound+2-timing_targets
 dc.l $fb6a
 dc.w timing_world20_contact_continue+2-timing_targets
 dc.l $fb8c
 dc.w timing_world20_damage_continue+2-timing_targets
 ENDC
timing_targets_end

timing_state dc.b 'PDTIME01'
timing_started dc.w 0
timing_due dc.w 0
timing_last dc.l 0
timing_phase dc.l 0
timing_loop dc.l 0
timing_ticks dc.l 0
timing_frames dc.l 0
timing_controls dc.l 0
timing_resources dc.l 0
timing_control_left dc.w 0
timing_resource_left dc.w 0
timing_orientation_left dc.w 0
timing_control_phase dc.w 1

 IFNE TIMING_BRAKE
 INCLUDE timing_brake.s
 ENDC

 IFNE TIMING_INPUT
 INCLUDE timing_input.s
 ENDC

 IFNE TIMING_ENGINE
 INCLUDE timing_engine.s
 ENDC

 IFNE TIMING_MOVE_CLOCK
 INCLUDE timing_movement.s
 ENDC

 IFNE TIMING_WORLD
 INCLUDE timing_world.s
 ENDC
