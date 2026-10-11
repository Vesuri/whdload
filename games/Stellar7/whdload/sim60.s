        IFND SCAN_GEOMETRY_FIRST
SCAN_GEOMETRY_FIRST = 1 ; native twins, boundary cases and extended combat verified
        ENDC
; Encoding-only branch optimization, validated on both CPUs and scoped to SIM60.
; Explicit .w branches (including the capture ABI entry) keep their size.
        IFND SHORT_BRANCHES
SHORT_BRANCHES = 1 ; native-reference checks and measured savings on both CPUs
        ENDC
        IFNE SHORT_BRANCHES
        OPT o1+
        ENDC
; Work-in-progress replacement loop. Compile only with -DSIM60 while validating.
; One simulation tick is 1/(5*N) s. Native frame counters retain their 5 Hz meaning.
; Unlike timing.s, the scheduler calls an update path and a separate draw path.
S60_CALL MACRO
        move.l (s60_code,pc),a0
        adda.l #\1,a0
        jsr (a0)
        ENDM
S60_DATA = $8000
        IFND HUD_CLOCK
HUD_CLOCK = 1 ; cockpit animation belongs to simulation, not presentation
        ENDC
        IFND PROJECT_BATCH
PROJECT_BATCH = 1 ; guarded native twins, cross-render state and display checks
        ENDC
        IFND EXIT_GUARD
EXIT_GUARD = 1 ; retain native inactive-game bypass after collision handling
        ENDC
        IFND SORT_ORDERED
SORT_ORDERED = 1 ; native-order checks and measured savings on both CPUs
        ENDC
        IFND PROJECT_SKIP
PROJECT_SKIP = 1 ; native-reference guard coverage and measured savings on both CPUs
        ENDC
        IFND RADIUS_SMALL
RADIUS_SMALL = 1 ; guarded native-equivalent scalar path, measured on both CPUs
        ENDC
        IFND DISTANCE_FAST
DISTANCE_FAST = 1 ; native-equivalent signed distance, measured faster on both CPUs
        ENDC
        IFD DISTANCE_TWIN
        IFEQ DISTANCE_FAST
        FAIL "DISTANCE_TWIN requires DISTANCE_FAST=1"
        ENDC
        ENDC
        IFND RECORD_CACHE
RECORD_CACHE = 1 ; tag validation, collision fixtures and measured savings
        ENDC
        IFND MOVE_LINEAR
MOVE_LINEAR = 1 ; full-wrapper twins, cross-render state and measured savings
        ENDC
        IFND LINEAR_ACTOR_HASH
LINEAR_ACTOR_HASH = 1 ; full-key validation; avoids measured yaw-index collisions
        ENDC
        IFND MOVE_IDLE
MOVE_IDLE = 1 ; full-state/CCR fixtures and measured savings on both CPUs
        ENDC
        IFND MOVE_ZERO
MOVE_ZERO = 1 ; native actor checks and measured update savings on both CPUs
        ENDC
        IFND MOVE_WORD_MUL
MOVE_WORD_MUL = 1 ; native actor checks and measured movement savings on both CPUs
        ENDC
        IFND FLAT_PITCH
FLAT_PITCH = 1 ; native-equivalent zero-pitch path, measured on both CPUs
        ENDC
        IFND STAR_IDLE
STAR_IDLE = 1 ; skip only proven-zero star arithmetic, retain bounds/respawns
        ENDC
        IFND SORT_WALK
SORT_WALK = 1 ; measured pointer traversal; zero selects indexed cached baseline
        ENDC
        IFND RADIUS_FAST
RADIUS_FAST = 1 ; measured faster on both CPUs; zero retains native scalar projection
        ENDC
        IFD RADIUS_TWIN
        IFEQ RADIUS_FAST
        FAIL "RADIUS_TWIN requires RADIUS_FAST=1"
        ENDC
        ENDC
        IFND HEADING_FAST
HEADING_FAST = 1 ; guarded native-equivalent heading, measured faster on both CPUs
        ENDC
        IFND SHOT_FAST
SHOT_FAST = 1 ; native-equivalent first-hit scan, measured faster on both CPUs
        ENDC
        IFND RECENTER_FAST
RECENTER_FAST = 1 ; native twins, cross-render state and measured savings
        ENDC
        IFND AI_GEOMETRY_FUSED
AI_GEOMETRY_FUSED = 1 ; native twins, cross-render state and measured savings
        ENDC
        IFND S60_SUBSTEPS
S60_SUBSTEPS = 1
        ENDC
        IFNE (S60_SUBSTEPS-1)*(S60_SUBSTEPS-2)*(S60_SUBSTEPS-3)*(S60_SUBSTEPS-4)*(S60_SUBSTEPS-6)*(S60_SUBSTEPS-12)
        FAIL "S60_SUBSTEPS must be 1, 2, 3, 4, 6 or 12"
        ENDC
S60_RATE = 5*S60_SUBSTEPS
S60_LEGACY_DIV = S60_SUBSTEPS
        IFND DIV_ZERO
DIV_ZERO = 1 ; measured zero-numerator shortcut; zero retains DIVS at every site
        ENDC
; For N>1, TST zero has the same NZVC as DIVS #N; neither changes X.
; Nonzero numerators use DIVS, including its overflow behavior. N=1 uses
; native word wrapping and a zero remainder instead.
S60_DIV12 MACRO
        IFEQ S60_SUBSTEPS-1
        ; Word destinations retain native wrapping even when the full star
        ; displacement does not fit a signed DIVS quotient. Remainder is zero.
        and.l #$ffff,\1
        ELSE
        IFNE DIV_ZERO
        tst.l \1
        beq .div_done\@
        ENDC
        divs #S60_LEGACY_DIV,\1
.div_done\@:
        ENDC
        ENDM
        IFND SCAN_HOIST
SCAN_HOIST = 1 ; native comparisons and measured scan savings on both CPUs
        ENDC
        IFND SCAN_FAST
SCAN_FAST = 1 ; measured faster on both CPUs; zero selects the native baseline
        ENDC
        IFD VERIFY
        IFD SCAN_TWIN
        IFEQ SCAN_FAST
        FAIL "SCAN_TWIN requires SCAN_FAST=1"
        ENDC
        ENDC
        ENDC
        IFD VERIFY
        IFD PREFERENCES_TEST
S60_MODAL_TEST = 1
        ENDC
        IFD PAUSE_TEST
        IFND S60_MODAL_TEST
S60_MODAL_TEST = 1
        ENDC
        ENDC
        IFD DEATH_TEST
        IFND S60_MODAL_TEST
S60_MODAL_TEST = 1
        ENDC
        ENDC
        ENDC

timing_install:
        move.l d7,a1
        add.l a1,a1
        add.l a1,a1
        addq.l #4,a1
        lea (s60_code,pc),a0
        move.l a1,(a0)
        ; Restrict this development path to the inspected layout.
        cmp.w #$4a39,($2af6,a1)
        bne s60_bad
        cmp.w #$2039,($2b96,a1)
        bne s60_bad
        cmp.l #$61001172,($2c50,a1)
        bne s60_bad
        cmp.l #$4eba1558,($2c54,a1)
        bne s60_bad
        cmp.w #$4a79,($2d54,a1)
        bne s60_bad
        IFD VERIFY
        IFD LEVEL_TEST
        IFD LEVEL_EARLY
        cmp.w #$4a39,($2b4e,a1)
        bne s60_bad
        move.l ($2af8,a1),d0
        cmp.l ($2b50,a1),d0
        bne s60_bad
        ENDC
        ENDC
        ENDC
        bsr s60_motion_install
        bsr s60_draw_install
        IFNE HUD_CLOCK
        bsr s60_hud_install
        ENDC
        IFNE PROJECT_SKIP
        bsr s60_project_skip_install
        ENDC
        bsr s60_events_install
        bsr s60_pickup_install
        bsr s60_contact_install
        bsr s60_knock_install
        bsr s60_boss_install
        bsr s60_flying_install
        bsr s60_special_install
        bsr s60_ai_random_install
        IFNE AI_GEOMETRY_FUSED
        bsr s60_geometry_install
        ENDC
        bsr s60_modal_install
        bsr s60_sort_install
        IFNE DISTANCE_FAST
        bsr s60_distance_install
        ENDC
        IFNE HEADING_FAST
        bsr s60_heading_install
        ENDC
        IFNE SHOT_FAST
        bsr s60_shot_install
        ENDC
        bsr s60_powers_install
        bsr s60_shake_install
        bsr s60_post_install
        IFNE RADIUS_FAST
        bsr s60_radius_install
        ENDC
        IFNE SCAN_FAST
        bsr s60_scan_install
        ENDC
        IFD VERIFY
        IFD COLLISION_TEST
        bsr s60_collision_install
        ENDC
        ENDC
        move.l d7,a1
        add.l a1,a1
        add.l a1,a1
        addq.l #4,a1
        lea (s60_patches,pc),a0
        jsr (resload_Patch,a2)
        rts
s60_bad:
        pea (TDREASON_WRONGVER).w
        jmp (resload_Abort,a2)
s60_patches:
        PL_START
        PL_P $2af6,s60_entry
        IFD VERIFY
        IFD LEVEL_TEST
        IFD LEVEL_EARLY
        PL_PS $2b4e,s60_test_level_early ; complete six-byte native TST.B
        ENDC
        ENDC
        ENDC
        PL_W $2b96,$4e75 ; update-pre range returns before rendering
        PL_NOP $2b98,4   ; cover the remaining MOVE.L operand
        PL_W $2c50,$4e75 ; draw range returns before gameplay post-update
        PL_NOP $2c52,2   ; cover the remaining BSR displacement
        PL_W $2d54,$4e75 ; gameplay post-update range returns to scheduler
        PL_NOP $2d56,4   ; cover the remaining TST.W operand
        PL_NOP $2c84,4 ; input is sampled by each 1/(5*N) s update
        PL_NOP $2c92,4 ; recenter once per 1/(5*N) s update
        PL_END

; Read-only capture ABI. Entry+4 signature, Entry+8 fields below.
s60_entry:
        bra.w s60_loop
        dc.b 'S760'
s60_last: dc.l 0
s60_credit: dc.l 0
s60_ticks: dc.l 0
s60_renders: dc.l 0
s60_last_render: dc.l 0
s60_field_hz: dc.w 60
s60_phase: dc.w 0
s60_logic: dc.w 0
s60_rendering: dc.w 0
s60_running: dc.w 0
s60_modal_resumes: dc.w 0
s60_code: dc.l 0
s60_boundary_offset: dc.w s60_loop_complete-s60_entry
        dc.w s60_motion_table-s60_entry
        dc.w s60_star_remainders-s60_entry
        dc.w 29+((12-S60_SUBSTEPS)<<8) ; layout version low byte; 12-N high byte
        dc.w s60_jump_state-s60_entry
        dc.w s60_jump_state_end-s60_jump_state
        dc.w s60_cooldown_state-s60_entry
        dc.w 12
        dc.w s60_power_state-s60_entry
        dc.w 20
        IFD VERIFY
        IFD COLLISION_TEST
        dc.w s60_collision_results-s60_entry
        ELSE
        dc.w 0
        ENDC
        ELSE
        dc.w 0
        ENDC
        IFD VERIFY
        IFD SPECIAL_TEST
        dc.w s60_special_results-s60_entry
        ELSE
        dc.w 0
        ENDC
        ELSE
        dc.w 0
        ENDC
        IFD VERIFY
        IFD AI_STACK_TEST
        dc.w s60_ai_stack_results-s60_entry
        ELSE
        dc.w 0
        ENDC
        ELSE
        dc.w 0
        ENDC

        dc.w S60_REC ; ABI offset 70: motion record stride
        IFD VERIFY
        IFD FLYING_TEST
        dc.w s60_flying_results-s60_entry
        ELSE
        dc.w 0
        ENDC
        ELSE
        dc.w 0
        ENDC

        dc.w s60_knock_state-s60_entry ; ABI 74
        dc.w 6 ; ABI 76
        IFD VERIFY
        IFD KNOCK_TEST
        dc.w s60_knock_results-s60_entry ; ABI 78
        ELSE
        dc.w 0
        ENDC
        ELSE
        dc.w 0
        ENDC

        IFD VERIFY
        IFD CONTACT_TEST
        dc.w s60_contact_results-s60_entry ; ABI 80
        ELSE
        dc.w 0
        ENDC
        ELSE
        dc.w 0
        ENDC

        dc.w s60_pickup_state-s60_entry ; ABI 82
        dc.w 16 ; ABI 84
        IFD VERIFY
        IFD PICKUP_TEST
        dc.w s60_pickup_results-s60_entry ; ABI 86
        ELSE
        dc.w 0
        ENDC
        ELSE
        dc.w 0
        ENDC

        IFD VERIFY
        IFD BOSS_TEST
        dc.w s60_boss_results-s60_entry ; ABI 88
        ELSE
        dc.w 0
        ENDC
        ELSE
        dc.w 0
        ENDC

        IFD VERIFY
        IFD ANIMATION_TEST
        dc.w s60_animation_results-s60_entry ; ABI 90
        ELSE
        dc.w 0
        ENDC
        ELSE
        dc.w 0
        ENDC

        dc.w s60_shake_state-s60_entry ; ABI 92
        dc.w 8 ; ABI 94
        IFD VERIFY
        IFD SHAKE_TEST
        dc.w s60_shake_results-s60_entry ; ABI 96
        ELSE
        dc.w 0
        ENDC
        ELSE
        dc.w 0
        ENDC

        IFD VERIFY
        IFD POST_TEST
        dc.w s60_post_results-s60_entry ; ABI 98
        ELSE
        dc.w 0
        ENDC
        ELSE
        dc.w 0
        ENDC

s60_sessions: dc.l 0 ; ABI 100: gameplay entries, survives per-session tick reset
        IFD VERIFY
        IFD DEATH_TEST
        dc.w s60_death_results-s60_entry ; ABI 104
        ELSE
        dc.w 0
        ENDC
        ELSE
        dc.w 0
        ENDC

s60_modal_depth: dc.w 0 ; ABI 106: outer modal owns the pause interval

        IFD VERIFY
        IFD SCAN_TWIN
        dc.w s60_scan_results-s60_entry ; ABI 108
        ELSE
        dc.w 0
        ENDC
        ELSE
        dc.w 0
        ENDC

        IFD VERIFY
        IFD RADIUS_TWIN
        dc.w s60_radius_results-s60_entry ; ABI 110
        ELSE
        dc.w 0
        ENDC
        ELSE
        dc.w 0
        ENDC

        IFD VERIFY
        IFD SORT_TWIN
        dc.w s60_sort_results-s60_entry ; ABI 112
        ELSE
        dc.w 0
        ENDC
        ELSE
        dc.w 0
        ENDC

        IFD VERIFY
        IFD FLAT_TEST
        dc.w s60_flat_results-s60_entry ; ABI 114
        ELSE
        dc.w 0
        ENDC
        ELSE
        dc.w 0
        ENDC

        IFD VERIFY
        IFD DISTANCE_TWIN
        dc.w s60_distance_results-s60_entry ; ABI 116
        ELSE
        dc.w 0
        ENDC
        ELSE
        dc.w 0
        ENDC

        IFD VERIFY
        IFD PROJECT_TEST
        dc.w s60_project_test_results-s60_entry ; ABI 118
        ELSE
        dc.w 0
        ENDC
        ELSE
        dc.w 0
        ENDC

        dc.w s60_terrain_state-s60_entry ; ABI 120
        dc.w 8 ; ABI 122
        IFD VERIFY
        IFD TERRAIN_TEST
        dc.w s60_terrain_results-s60_entry ; ABI 124
        ELSE
        dc.w 0
        ENDC
        ELSE
        dc.w 0
        ENDC

        IFD VERIFY
        IFD HEADING_TEST
        dc.w s60_heading_results-s60_entry ; ABI 126
        ELSE
        dc.w 0
        ENDC
        ELSE
        dc.w 0
        ENDC

        IFD VERIFY
        IFD SHOT_TEST
        dc.w s60_shot_results-s60_entry ; ABI 128
        ELSE
        dc.w 0
        ENDC
        ELSE
        dc.w 0
        ENDC

        IFD VERIFY
        IFD LEVEL_TEST
        dc.w s60_level_results-s60_entry ; ABI 130
        ELSE
        dc.w 0
        ENDC
        ELSE
        dc.w 0
        ENDC

        dc.w s60_friction_state-s60_entry ; ABI 132
        dc.w 8 ; ABI 134

s60_loop:
        movem.l d2-d7/a2-a6,-(sp)
        lea (s60_last,pc),a2
        move.l ($24a8-S60_DATA,a4),(a2)
        clr.l (s60_ticks-s60_last,a2)
        clr.l (s60_renders-s60_last,a2)
        clr.w (s60_modal_resumes-s60_last,a2)
        clr.l (s60_last_render-s60_last,a2)
        clr.w (s60_phase-s60_last,a2)
        clr.w (s60_modal_depth-s60_last,a2)
        move.l ($4).w,a0
        moveq #0,d0
        move.b (VBlankFrequency,a0),d0
        cmp.w #50,d0
        beq s60_loop_rate
        cmp.w #60,d0
        bne s60_loop_exit ; unsupported clock: do not guess
s60_loop_rate:  move.w d0,(s60_field_hz-s60_last,a2)
        move.l d0,(s60_credit-s60_last,a2)
        move.w #1,(s60_running-s60_last,a2)
        bsr s60_motion_reset
        bsr s60_stars_reset
        bsr s60_events_reset
        bsr s60_powers_reset
        bsr s60_knock_reset
        bsr s60_pickup_reset
        bsr s60_shake_reset
        IFNE HUD_CLOCK
        bsr s60_hud_reset
        ENDC
        lea (s60_sessions,pc),a0
        addq.l #1,(a0)
        IFD VERIFY
        IFD DEATH_TEST
        bsr s60_test_death_resume
        ENDC
        ENDC
        IFD VERIFY
        IFD LEVEL_TEST
        bsr s60_test_level_resume
        ENDC
        ENDC
s60_loop_poll:
        ; Snapshot elapsed time once per catch-up batch. Time spent updating
        ; and drawing is added by the next poll, never discarded. Refreshing
        ; credit after every tick can starve presentation on a slow machine.
        bsr s60_clock
s60_loop_batch:
        tst.b ($1e53-S60_DATA,a4)
        beq s60_loop_exit
        tst.w ($46d6-S60_DATA,a4)
        bne s60_loop_quit
        moveq #0,d0
        move.w (s60_field_hz-s60_last,a2),d0
        cmp.l (s60_credit-s60_last,a2),d0
        bhi s60_loop_draw
        sub.l d0,(s60_credit-s60_last,a2)
        clr.w (s60_logic-s60_last,a2)
        tst.w (s60_phase-s60_last,a2)
        bne s60_loop_step
        move.w #1,(s60_logic-s60_last,a2)
s60_loop_step:  bsr s60_update
        addq.l #1,(s60_ticks-s60_last,a2)
        addq.w #1,(s60_phase-s60_last,a2)
        cmp.w #S60_LEGACY_DIV,(s60_phase-s60_last,a2)
        bcs s60_loop_complete
        clr.w (s60_phase-s60_last,a2)
s60_loop_complete:
        nop ; read-only debugger boundary after each complete simulation tick
        IFD VERIFY
        IFD FRAME_TEST
        bsr s60_test_frame
        ENDC
        ENDC
        bra s60_loop_batch
s60_loop_draw:
        IFD VERIFY
        move.l (_custom4,pc),d0
        cmp.l #1,d0
        bls s60_loop_render
        move.l (s60_ticks-s60_last,a2),d1
        sub.l (s60_last_render-s60_last,a2),d1
        cmp.l d0,d1
        bcs s60_loop_poll
s60_loop_render:
        IFD SLOW_DRAW
        move.l ($24a8-S60_DATA,a4),d0
        add.l #SLOW_DRAW,d0
s60_loop_delay: cmp.l ($24a8-S60_DATA,a4),d0
        bgt s60_loop_delay
        ENDC
        ENDC
        move.w #1,(s60_rendering-s60_last,a2)
        bsr s60_render
        clr.w (s60_rendering-s60_last,a2)
        addq.l #1,(s60_renders-s60_last,a2)
        move.l (s60_ticks-s60_last,a2),(s60_last_render-s60_last,a2)
        bra s60_loop_poll
s60_loop_quit:
        bsr s60_input_restore
        clr.w (s60_running-s60_last,a2)
        movem.l (sp)+,d2-d7/a2-a6
        move.l (s60_code,pc),-(sp)
        add.l #$2d5e,(sp)
        rts
s60_loop_exit:
        IFD VERIFY
        IFD LEVEL_TEST
        bsr s60_test_level_exit
        ENDC
        ENDC
        IFD VERIFY
        IFD DEATH_TEST
        bsr s60_test_death_exit
        ENDC
        ENDC
        bsr s60_input_restore
        clr.w (s60_running-s60_last,a2)
        movem.l (sp)+,d2-d7/a2-a6
        move.l (s60_code,pc),-(sp)
        add.l #$2d7c,(sp)
        rts

s60_clock:
        move.l ($24a8-S60_DATA,a4),d0
        sub.l (a2),d0
        add.l d0,(a2)
        ; Do not truncate a long elapsed interval to the MULU word operand.
        IFEQ S60_SUBSTEPS-12
        move.l d0,d1
        lsl.l #6,d0
        lsl.l #2,d1
        sub.l d1,d0 ; elapsed * (64 - 4) = elapsed * S60_RATE
        ELSE
        move.l d0,d1
        lsl.l #2,d0
        add.l d1,d0 ; elapsed * 5, retaining the full long operand
        IFEQ S60_SUBSTEPS-2
        lsl.l #1,d0
        ENDC
        IFEQ S60_SUBSTEPS-4
        lsl.l #2,d0
        ENDC
        IFEQ S60_SUBSTEPS-3
        move.l d0,d1
        lsl.l #1,d0
        add.l d1,d0
        ENDC
        IFEQ S60_SUBSTEPS-6
        move.l d0,d1
        lsl.l #1,d0
        add.l d1,d0
        lsl.l #1,d0
        ENDC
        ENDC
        add.l d0,(s60_credit-s60_last,a2)
        rts

s60_update:
        IFD VERIFY
        IFD QUANTA_TEST
        bsr s60_test_quanta
        ENDC
        IFD FRICTION_TEST
        bsr s60_test_friction
        ENDC
        IFD INPUT_NEUTRAL_TEST
        bsr s60_test_input_neutral
        ENDC
        ENDC
        IFD VERIFY
        IFD GEOMETRY_TEST
        IFEQ AI_GEOMETRY_FUSED
        FAIL "GEOMETRY_TEST requires AI_GEOMETRY_FUSED=1"
        ENDC
        IFND GEOMETRY_TWIN
        FAIL "GEOMETRY_TEST requires GEOMETRY_TWIN"
        ENDC
        bsr s60_test_geometry
        ENDC
        ENDC
        IFD VERIFY
        IFD PICKUP_ENCOUNTER
        bsr s60_test_pickup_encounter
        ENDC
        ENDC
        IFD VERIFY
        IFD BOSS_ENCOUNTER
        bsr s60_test_encounter
        ENDC
        ENDC
        IFD VERIFY
        IFD BOSS_GATE_TEST
        bsr s60_test_boss_gate
        ENDC
        ENDC
        IFD VERIFY
        IFD IDLE_TEST
        bsr s60_test_idle
        ENDC
        ENDC
        ; Continuous input and collision integration use S60_RATE. Native AI
        ; decisions and legacy counters are separately scheduled at 5 Hz.
        IFD VERIFY
        IFD JUMP_TEST
        move.l (s60_ticks,pc),d0
        cmp.l #JUMP_TEST,d0
        bne .no_test_jump
        S60_CALL $ec74 ; native activation, diagnostic fixture only
.no_test_jump:
        ENDC
        ENDC
        IFD VERIFY
        IFD PAUSE_TEST
        bsr s60_test_pause
        ENDC
        IFD PREFERENCES_TEST
        bsr s60_test_preferences
        ENDC
        ENDC
        IFD VERIFY
        IFD POWERS_TEST
        bsr s60_test_powers
        ENDC
        ENDC
        IFD VERIFY
        IFD COLLISION_TEST
        bsr s60_test_collision
        ENDC
        ENDC
        IFD VERIFY
        IFD SPECIAL_TEST
        bsr s60_test_special
        ENDC
        ENDC
        IFD VERIFY
        IFD AI_STACK_TEST
        bsr s60_test_ai_stack
        ENDC
        ENDC
        IFD VERIFY
        IFD FLYING_TEST
        bsr s60_test_flying
        ENDC
        ENDC
        IFD VERIFY
        IFD KNOCK_TEST
        bsr s60_test_knock
        ENDC
        ENDC
        IFD VERIFY
        IFD KNOCK_PLAY
        bsr s60_test_knock_play
        ENDC
        ENDC
        IFD VERIFY
        IFD CONTACT_TEST
        bsr s60_test_contact
        ENDC
        ENDC
        IFD VERIFY
        IFD PICKUP_TEST
        bsr s60_test_pickup
        ENDC
        ENDC
        IFD VERIFY
        IFD BOSS_TEST
        bsr s60_test_boss
        ENDC
        ENDC
        IFD VERIFY
        IFD ANIMATION_TEST
        bsr s60_test_animation
        ENDC
        ENDC
        IFD VERIFY
        IFD SHAKE_TEST
        bsr s60_test_shake
        ENDC
        ENDC
        IFD VERIFY
        IFD POST_TEST
        bsr s60_test_post
        ENDC
        ENDC
        IFD VERIFY
        IFD DEATH_TEST
        bsr s60_test_death
        ENDC
        ENDC
        IFD VERIFY
        IFD SCAN_TEST
        bsr s60_test_scan
        ENDC
        ENDC
        IFD VERIFY
        IFD RADIUS_TEST
        bsr s60_test_radius
        ENDC
        ENDC
        IFD VERIFY
        IFD SORT_TEST
        bsr s60_test_sort
        ENDC
        ENDC
        IFD VERIFY
        IFD FLAT_TEST
        bsr s60_test_flat
        ENDC
        ENDC
        IFD VERIFY
        IFD DISTANCE_TEST
        bsr s60_test_distance
        ENDC
        ENDC
        IFD VERIFY
        IFD SHOT_TEST
        bsr s60_test_shot
        ENDC
        ENDC
        IFD VERIFY
        IFD HEADING_TEST
        bsr s60_test_heading
        ENDC
        ENDC
        IFD VERIFY
        IFD TERRAIN_TEST
        bsr s60_test_terrain
        ENDC
        ENDC
        IFD VERIFY
        IFD BATCH_TEST
        bsr s60_test_batch
        ENDC
        ENDC
        IFD VERIFY
        IFD HUD_TEST
        bsr s60_test_hud
        ENDC
        ENDC
        IFD VERIFY
        IFD LINEAR_TEST
        bsr s60_test_linear
        ENDC
        ENDC
        bsr s60_input_quanta
        S60_CALL $fcf4
        bsr s60_jump_update
        bsr s60_pickup_update
        bsr s60_knock_update
        S60_CALL $2b38
        IFNE EXIT_GUARD
        tst.b ($1e53-S60_DATA,a4)
        beq .inactive
        ENDC
        bsr s60_project
        bsr s60_stars_update
        bsr s60_cooldowns_update
        bsr s60_shake_update
        IFNE HUD_CLOCK
        bsr s60_hud_update
        ENDC
.powers:
        S60_CALL $3dc4
        S60_CALL $ecca
        bsr s60_boss_gate
        S60_CALL $2c58 ; death and pending quit requests are checked every tick
.recenter:
        IFNE RECENTER_FAST
        IFD VERIFY
        IFD RECENTER_TEST
        bsr s60_test_recenter
        ENDC
        ENDC
        bsr s60_recenter
        ELSE
        S60_CALL $3ab8
        ENDC
        IFD VERIFY
        IFD LEVEL_TEST
        IFND LEVEL_EARLY
        bsr s60_test_level
        ENDC
        ENDC
        ENDC
        rts
        IFNE EXIT_GUARD
.inactive:
        ; Native $2b54 branches to $2c50 when collisions request exit.
        ; Omit projection callbacks, star integration and damage shake, while
        ; retaining the normal post-update timers, death check and recentering.
        bsr s60_cooldowns_update
        bra .powers
        ENDC

s60_project:
        IFNE PROJECT_BATCH
        bsr s60_project_batch
        tst.w d0
        bne .done
        ENDC
        move.w ($43b2-S60_DATA,a4),-(sp)
        pea ($3fb2-S60_DATA,a4)
        move.l ($5d90-S60_DATA,a4),-(sp)
        S60_CALL $12aa4
        lea (10,sp),sp
.done:  rts

        INCLUDE project_batch60.s
        INCLUDE motion60.s
        INCLUDE input60_test.s
        INCLUDE quanta60_test.s
        INCLUDE linear60.s
        INCLUDE linear60_test.s
        INCLUDE idle60_test.s
        INCLUDE flat60_test.s
        INCLUDE draw60.s
        INCLUDE events60.s
        INCLUDE terrain60_test.s
        INCLUDE modal60.s
        INCLUDE level60_test.s
        INCLUDE boss_gate60_test.s
        INCLUDE encounter60_test.s
        INCLUDE shot_scan60.s
        INCLUDE shot_scan60_test.s
        INCLUDE heading60.s
        INCLUDE heading60_test.s
        INCLUDE distance60.s
        INCLUDE distance60_test.s
        INCLUDE sort60.s
        INCLUDE sort60_test.s
        INCLUDE powers60.s

        INCLUDE collision60_test.s

        INCLUDE special60.s

        INCLUDE special60_test.s

        INCLUDE ai_stack_test.s

        INCLUDE ai_random60.s
        INCLUDE ai_geometry60.s

        INCLUDE flying60.s
        INCLUDE flying60_test.s

        INCLUDE knock60.s
        INCLUDE knock60_test.s

        INCLUDE contact60.s
        INCLUDE contact60_test.s

        INCLUDE pickup60.s
        INCLUDE pickup60_test.s
        INCLUDE pickup_encounter60_test.s

        INCLUDE boss60.s
        INCLUDE boss60_test.s

        INCLUDE animation60.s
        INCLUDE animation60_test.s

        INCLUDE shake60.s
        INCLUDE shake60_test.s

        INCLUDE post60.s
        INCLUDE post60_test.s

        INCLUDE death60_test.s

        INCLUDE projection_skip60.s
        INCLUDE projection_skip60_test.s
        INCLUDE projection60.s
        INCLUDE projection60_test.s
        INCLUDE scan60.s
        INCLUDE scan60_test.s

        INCLUDE project_batch60_test.s

        INCLUDE frame60_test.s

        INCLUDE hud60.s

        INCLUDE hud60_test.s


        IFNE RECENTER_FAST
        INCLUDE recenter60.s
        INCLUDE recenter60_test.s
        ENDC

        IFNE SHORT_BRANCHES
        OPT o1-
        ENDC

        include "friction60_test.s"
