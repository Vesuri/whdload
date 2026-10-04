; duel v1: three-field simulation. All entry hooks are gated by CUSTOM2.
; Continuous dynamics use dt = 1/2 of the original six-field step. Spatial
; road-unit loops, event impulses and field-based input/audio timers stay intact.
; Private fractional state belongs to the slave, never the read-only debugger.

sim_start:
    movem.l d0/a0,-(sp)
    move.l -17216(a4),d0
    move.l d0,-17212(a4)       ; displaced initial deadline
    lea sim_epoch(pc),a0
    move.l d0,(a0)
    lea sim_gear_field(pc),a0
    move.l d0,(a0)
    lea sim_gear_value(pc),a0
    move.w -24720(a4),(a0)
    lea sim_recovery_until(pc),a0
    clr.l (a0)
    lea sim_phase(pc),a0
    move.w #1,(a0)
    lea sim_fractions(pc),a0
    clr.l (a0)+               ; player time / opponent time
    clr.l (a0)                ; player sum / opponent sum
    lea sim_code(pc),a0
    move.l -32266(a4),d0      ; absolute target of RNG jump-table entry
    sub.l #$e9e2,d0
    move.l d0,(a0)
    lea sim_visual_seed(pc),a0
    move.w -18632(a4),d0
    eor.w #$a53c,d0
    move.w d0,(a0)
    movem.l (sp)+,d0/a0
    rts

sim_begin:
    movem.l d0-d2/a0,-(sp)
    lea sim_phase(pc),a0
    eori.w #1,(a0)            ; zero at original six-field boundaries
    bsr sim_visual_step
    bsr sim_recovery_step
    IFD VERIFY
    bsr verify_drive_mode
    ENDC
    lea sim_recovery_until(pc),a0
    tst.l (a0)
    beq.b .normal
    movem.l (sp)+,d0-d2/a0
    add.l #$92,(sp)           ; recovering player does not borrow demo AI state
    rts
.normal
    movem.l (sp)+,d0-d2/a0
    tst.w -17282(a4)          ; displaced demo check and branch
    bne.b .demo
    add.l #$92,(sp)           ; return to duel:05af2, bypass demo borrow
.demo
    rts

; Round odd signed word rates alternately. Constant inputs preserve their
; original six-field total, including negative rates and the 41-unit police rate.
sim_half_word:
    asr.w #1,d0             ; floor first: avoids overflow at +32767
    bcc.b .done
    bsr sim_test_phase
    bne.b .done
    addq.w #1,d0
.done
    rts

sim_speed_add:
    asr.l #1,d0
    add.l d0,-13282(a4)
    tst.w -13188(a4)          ; displaced following test
    rts

sim_yaw_add:
    move.w -4(a5),d0
    bsr sim_half_word
    add.w d0,-9862(a4)
    rts

sim_heat_add:
    move.l d0,-(sp)
    move.w d1,d0
    bsr sim_half_word
    move.w d0,d1
    movem.l (sp)+,d0
    add.w -24718(a4),d1
    move.w d1,-24718(a4)
    rts

sim_dashboard:
    move.l d0,-(sp)
    lsr.w #7,d1
    move.w d1,d0
    bsr sim_half_word
    move.w d0,d1
    movem.l (sp)+,d0
    move.w -3008(a4),d0
    rts

sim_ai_accel:
    mulu.w 22(a5),d0
    clr.w d0
    swap d0
    lsr.l #1,d0
    rts

sim_ai_lane:
    move.l d1,-(sp)
    move.w d0,d1
    move.w d2,d0
    bsr sim_half_word
    move.w d0,d2
    move.w d1,d0
    movem.l (sp)+,d1
    add.w d2,d0
    move.w d0,6(a5)
    rts

sim_ai_motion:
    move.l 10(a5),d0          ; AI speed retains original units for lookahead
    lsr.l #1,d0
    add.l 2(a5),d0
    rts

sim_traffic_forward:
    lsr.l #1,d0
    add.l -13470(a4),d0
    move.l d0,-13470(a4)
    rts
sim_traffic_oncoming:
    move.l -7652(a4),d0
    lsr.l #1,d0
    sub.l d0,-13466(a4)       ; CCR preserved for original wrap branch
    rts

; These counters retain their six-field time units. Thresholds and one-off
; crash/arrest penalties are therefore unchanged, including police scripts.
sim_crash_timer:
    bsr sim_test_phase
    bne.b .test
    addq.w #1,16(a5)
.test
    cmp.w #40,16(a5)
    rts
sim_police_timer:
    bsr sim_test_phase
    bne.b .test
    addq.w #1,-12980(a4)
.test
    cmp.w #30,-12980(a4)
    rts
sim_police_time_motion:
    bsr sim_test_phase
    bne.b .read
    addq.w #1,-7642(a4)
.read
    move.l 10(a5),d0
    lsr.l #1,d0
    add.l 2(a5),d0
    rts
sim_police_time_read:
    bsr sim_test_phase
    bne.b .read
    addq.w #1,-7642(a4)
.read
    move.w -7642(a4),d0
    rts
sim_police_limit_branch:
    bsr sim_test_phase
    bne.b .jump
    subq.w #1,-7642(a4)
.jump
    add.l #12,(sp)           ; return to original counter test at duel:0e074
    rts
sim_police_limit:
    move.w d1,d2            ; displaced negative-limit clamp
    bsr sim_test_phase
    bne.b .test
    subq.w #1,-7642(a4)
.test
    rts
sim_police_return_lane:
    movem.l d0,-(sp)
    moveq #41,d0
    bsr sim_half_word
    sub.w d0,6(a5)
    movem.l (sp)+,d0
    rts

; Gear audio can be called in the VBL as well as by physics. Elapsed fields,
; rather than call count or the step's phase, govern this envelope counter.
sim_gear_timer:
    movem.l d0-d1/a0,-(sp)
    bsr sim_test_active
    beq.b .advance          ; retain pre-race behaviour
    move.l -17216(a4),d0
    lea sim_gear_value(pc),a0
    move.w -24720(a4),d1
    cmp.w (a0),d1
    beq.b .elapsed
    move.w d1,(a0)          ; a new gear event resets the envelope epoch
    lea sim_gear_field(pc),a0
    move.l d0,(a0)
    bra.b .test
.elapsed
    lea sim_gear_field(pc),a0
    sub.l (a0),d0
    cmp.l #6,d0
    bcs.b .test
    add.l #6,(a0)
.advance
    addq.w #1,-24720(a4)
    lea sim_gear_value(pc),a0
    move.w -24720(a4),(a0)
.test
    movem.l (sp)+,d0-d1/a0
    cmp.w #25,-24720(a4)
    rts

; Continuous verge drag is called once per step with f3c0 set. The same
; routine also serves spatial collision checks, where the impulse stays whole.
sim_verge_low:
    move.l #12800,d0
    bra.b sim_verge_rate
sim_verge_high:
    move.l #29184,d0
sim_verge_rate:
    tst.w -3136(a4)
    beq.b .impulse
    lsr.l #1,d0
.impulse
    rts

; Crash recovery is simulation state, not a blocking drawing/acknowledgement
; loop. Forty original six-field crash ticks = 240 fields. Opponents, traffic,
; clock and input continue. Terminal crashes retain the original race-end path.
; Engine damage used the same CPU-paced life-loss path as a crash.
sim_overheat_check:
    tst.w -12938(a4)
    beq.b .done
    movem.l d0/a0,-(sp)
    move.l sim_trainer(pc),d0
    btst #0,d0
    bne.b .pending
    cmp.w #17,-14916(a4)      ; fatal crashes override an existing recovery
    beq.b .terminal
.pending
    lea sim_recovery_until(pc),a0
    tst.l (a0)
    bne.b .restore
    btst #0,d0
    bne.b .recover
    cmp.w #1,-17228(a4)
    ble.b .terminal
    subq.w #1,-17228(a4)
.recover
    addq.w #1,-10870(a4)
    lea sim_recovery_kind(pc),a0
    move.w #1,(a0)
    move.w #1,-14916(a4)      ; inhibit player physics during cooling
    bsr sim_begin_recovery
    bra.b .restore
.terminal
    lea sim_recovery_until(pc),a0
    clr.l (a0)
    movem.l (sp)+,d0/a0
    add.l #44,(sp)           ; original damage/race-end path at duel:05ca6
    rts
.restore
    movem.l (sp)+,d0/a0
.done
    rts

sim_crash_check:
    tst.w -14916(a4)
    beq .done
    movem.l d0/a0,-(sp)
    move.l sim_trainer(pc),d0
    btst #0,d0
    bne.b .pending
    cmp.w #17,-14916(a4)      ; fatal crashes override an existing recovery
    beq.b .terminal
.pending
    lea sim_recovery_until(pc),a0
    tst.l (a0)
    bne.b .restore
    btst #0,d0
    bne.b .recover
    cmp.w #1,-17228(a4)
    ble.b .terminal
    subq.w #1,-17228(a4)
.recover
    addq.w #1,-10872(a4)
    lea sim_recovery_kind(pc),a0
    clr.w (a0)
    bsr sim_begin_recovery
    bra.b .restore
.terminal
    lea sim_recovery_until(pc),a0
    clr.l (a0)
    movem.l (sp)+,d0/a0
    add.l #32,(sp)           ; original race-end handler at duel:05ca6
    rts
.restore
    movem.l (sp)+,d0/a0
.done
    rts

sim_begin_recovery:
    lea sim_recovery_until(pc),a0
    add.l #200,-10146(a4)
    add.l #200,-10864(a4)
    move.l -17216(a4),d0
    add.l #240,d0
    move.l d0,(a0)
    clr.l -13282(a4)
    clr.l -13188(a4)
    clr.w -13036(a4)
    clr.w -13038(a4)
    clr.w -9862(a4)
    clr.w -13390(a4)
    move.w #-1,-24720(a4)
    clr.w -2988(a4)
    bsr sim_idle_sound
    rts

sim_idle_sound:
    movem.l d0-a6,-(sp)
    move.w #1800,-2792(a4)    ; original engine period at zero RPM
    move.w #-1,-(sp)         ; retain channel volume
    move.w #1800,-(sp)
    move.w #3,-(sp)           ; engine channel
    jsr -32544(a4)
    addq.l #6,sp
    movem.l (sp)+,d0-a6
    rts

sim_recovery_step:
    lea sim_recovery_until(pc),a0
    move.l (a0),d0
    beq .done
    sub.l -17216(a4),d0
    bgt.b .animate
    clr.l (a0)
    clr.w -14916(a4)
    clr.w -7694(a4)
    clr.w -7692(a4)
    clr.w -10462(a4)          ; demo driver's crash timer
    clr.w -10460(a4)
    clr.l -10468(a4)          ; demo driver's speed
    move.l -17238(a4),-10476(a4)
    move.l #$700000,-13386(a4)
    move.l -13386(a4),-10472(a4)
    clr.w -12938(a4)
    clr.w -12936(a4)
    clr.w -24718(a4)
    clr.w -10150(a4)
    move.w #-1,-24648(a4)
    move.w #-1,-24652(a4)
    bra.b .done
.animate
    neg.w d0
    add.w #240,d0            ; elapsed fields: derived, never render-call count
    cmp.w #120,d0
    bcs.b .height
    move.w #120,d0
.height
    move.w d0,-7692(a4)
.done
    rts

; The ordinary renderer owns the crash message. No game state is advanced here.
sim_dashboard_draw:
    bsr sim_original_dashboard
    movem.l d0-d3/a0-a2,-(sp)
    lea sim_recovery_until(pc),a0
    tst.l (a0)
    beq.b .done
    lea sim_crash_message(pc),a0
    move.w sim_recovery_kind(pc),d0
    beq.b .message
    lea sim_heat_message(pc),a0
.message
    move.l a0,-(sp)
    move.w #20,-(sp)
    bsr sim_original_text
    addq.l #6,sp
.done
    movem.l (sp)+,d0-d3/a0-a2
    unlk a5                  ; displaced original renderer epilogue
    rts
sim_original_dashboard:
    move.l -32266(a4),-(sp)  ; renderer also runs before the race anchor
    sub.l #$e9e2-$b45e,(sp)
    rts
sim_original_text:
    ; A tail jump preserves the original stack-based font arguments.
    move.l -32266(a4),-(sp)
    sub.l #$e9e2-$686e,(sp)
    rts
sim_crash_message: dc.b "CRASH - 20 SECOND PENALTY",0
    even
sim_heat_message: dc.b "ENGINE DAMAGE - 20 SECOND PENALTY",0
    even
sim_recovery_kind: dc.w 0
sim_recovery_until: dc.l 0

; Three PAL fields = 3/5 of a nominal tenth. Carry fractions instead of
; truncating each step. Speed sums use the same weighting as race time.
sim_player_time:
    movem.l d0-d1/a0,-(sp)
    mulu.w #3,d0
    lea sim_player_sum_frac(pc),a0
    add.w (a0),d0
    divu.w #5,d0
    moveq #0,d1
    move.w d0,d1
    add.l d1,-7674(a4)
    swap d0
    move.w d0,(a0)
    lea sim_player_time_frac(pc),a0
    addq.w #3,(a0)
    cmp.w #5,(a0)
    bcs.b .done
    subq.w #5,(a0)
    addq.l #1,-10146(a4)
.done
    movem.l (sp)+,d0-d1/a0
    rts
sim_opponent_sum:
    asr.l d1,d0             ; displaced speed conversion
    movem.l d0-d1/a0,-(sp)
    mulu.w #3,d0
    lea sim_opponent_sum_frac(pc),a0
    add.w (a0),d0
    divu.w #5,d0
    moveq #0,d1
    move.w d0,d1
    add.l d1,-10836(a4)
    swap d0
    move.w d0,(a0)
    movem.l (sp)+,d0-d1/a0
    rts
sim_opponent_time:
    movem.l d0/a0,-(sp)
    tst.w -7670(a4)         ; original running/finish conditions
    beq.b .done
    move.w -13356(a4),d0
    cmp.w -10076(a4),d0
    bge.b .done
    lea sim_opponent_time_frac(pc),a0
    addq.w #3,(a0)
    cmp.w #5,(a0)
    bcs.b .done
    subq.w #5,(a0)
    addq.l #1,-10844(a4)
.done
    movem.l (sp)+,d0/a0
    jsr -32238(a4)          ; displaced input/exit check
    tst.w d0               ; displaced result test
    rts

; Pure state updates on simulation ticks; no drawing or gameplay RNG calls.
; The rare visual event's probability/countdown keep six-field quanta.
sim_visual_step:
    move.l -14920(a4),a0
    tst.w 2(a0)
    beq.b .event
    add.l #2000,-3120(a4)
    add.l #2500,-3116(a4)
    add.l #3000,-3112(a4)
    add.l #3500,-3108(a4)
.event
    bsr sim_test_phase
    bne .done
    tst.w -7640(a4)
    bne.b .animate
    cmp.w #95,-13282(a4)
    bcs .done
    tst.b -13378(a4)
    bmi .done
    bsr sim_visual_random
    and.w #$fff,d0
    bne .done
    st -7640(a4)
    bsr sim_visual_random
    and.w #$ff,d0
    add.w #32,d0
    move.w d0,-7638(a4)
    bsr sim_visual_random
    and.w #$7f,d0
    move.w d0,-7636(a4)
    move.l -14786(a4),-7634(a4)
    clr.l -7630(a4)
    move.w #5,-7626(a4)
.animate
    move.w -7626(a4),d2
    beq.b .done
    subq.w #2,-7636(a4)
    subq.w #1,-7626(a4)
    cmp.w #3,d2
    bge.b .done
    cmp.w #1,d2
    beq.b .final_shape
    move.l -14782(a4),-7634(a4)
    bra.b .done
.final_shape
    bsr sim_visual_random
    and.w #3,d0
    lsl.w #2,d0
    lea -14778(a4),a0
    move.l (a0,d0.w),-7634(a4)
.done
    rts
sim_visual_random:
    lea sim_visual_seed(pc),a0
    moveq #0,d0
    move.w (a0),d0
    mulu.w #6907,d0
    add.l #130253,d0
    move.w d0,(a0)
    rts

sim_draw_event:
    tst.w -7640(a4)
    beq.b .done
    movem.l d0-d3/a0-a2,-(sp)
    move.w #117,-18556(a4)
    lea -7638(a4),a2
    move.w (a2)+,d0
    move.w (a2)+,d1
    move.l (a2)+,a0
    suba.l a1,a1
    jsr -32148(a4)
    movem.l (sp)+,d0-d3/a0-a2
.done
    rts

sim_test_phase:
    move.l a0,-(sp)
    lea sim_phase(pc),a0
    tst.w (a0)
    movem.l (sp)+,a0
    rts
sim_test_active:
    move.l a0,-(sp)
    lea sim_code(pc),a0
    tst.l (a0)
    movem.l (sp)+,a0
    rts

sim_phase: dc.w 1
sim_visual_seed: dc.w 0
sim_fractions:
sim_player_time_frac: dc.w 0
sim_opponent_time_frac: dc.w 0
sim_player_sum_frac: dc.w 0
sim_opponent_sum_frac: dc.w 0
sim_gear_value: dc.w 0
sim_gear_field: dc.l 0
sim_code: dc.l 0

; Read only v1 options. Control fills tag values; all game patches remain C2-gated.
sim_tags:
    dc.l WHDLTAG_CUSTOM2_GET
render_options: dc.l 0
    dc.l WHDLTAG_CUSTOM1_GET
sim_trainer: dc.l 0
    IFD VERIFY
    dc.l WHDLTAG_CUSTOM5_GET
sim_drive_enabled: dc.l 0
    ENDC
    dc.l 0
sim_epoch: dc.l 0

    IFD VERIFY
; Actual joystick decoding and normal player physics consume this field-based
; tape. It starts after the race anchor; no debugger writes are involved.
verify_drive_mode:
    move.l sim_drive_enabled(pc),d0
    btst #0,d0
    beq.b .done
    clr.w -17282(a4)           ; play the first race, rather than borrow demo AI
    clr.w -12(a5)              ; also clear the race frame's cached attract flag
    move.l d0,d1
    move.l -17216(a4),d0
    sub.l sim_epoch(pc),d0
    btst #2,d1
    beq.b .heat
    cmp.l #900,d0
    bne.b .heat
    move.w #17,-14916(a4)      ; exercise original fatal-race path once
.heat
    btst #1,d1
    beq.b .done
    cmp.l #450,d0
    bne.b .done
    move.w #1,-12938(a4)       ; exercise actual engine-damage recovery once
.done
    rts
verify_read_joydat:
    bsr read_joydat
    bsr verify_drive_joydat
    rts
verify_drive_joydat:
    movem.l d1/a0,-(sp)
    move.l sim_drive_enabled(pc),d1
    btst #0,d1
    beq.b .done
    bsr sim_test_active
    beq.b .done
    move.l -17216(a4),d1
    sub.l sim_epoch(pc),d1
    move.w #$0100,d0           ; accelerate, including from idle
    cmp.l #100,d1
    bcs.b .done
    cmp.l #106,d1
    bcc.b .right
    move.w #$0200,d0           ; up + left
    bra.b .done
.right
    cmp.l #112,d1
    bcc.b .brake
    move.w #$0103,d0           ; up + right
    bra.b .done
.brake
    cmp.l #200,d1
    bcs.b .done
    cmp.l #300,d1
    bcc.b .coast
    moveq #1,d0               ; brake
    bra.b .done
.coast
    cmp.l #400,d1
    bcc.b .done
    moveq #0,d0               ; neutral joystick/coast
.done
    movem.l (sp)+,d1/a0
    rts
    ENDC

    IFD VERIFY
    include "simulation-verify.s"
    ENDC
