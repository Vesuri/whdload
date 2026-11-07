; VERIFY and CUSTOM5 only: follow the native Escape paths through the intro,
; then return the Begin selection at the main menu's own polling call.
; No gameplay state, timing, RNG or rendering changes.
fixture_install:
        move.l d7,a1
        add.l a1,a1
        add.l a1,a1
        addq.l #4,a1
        ; Fail closed on any unsupported executable layout.
        cmp.l #$4eba64ca,($4582,a1)
        bne .bad
        cmp.w #$2e00,($4586,a1)
        bne .bad
        move.l a1,a0
        adda.l #$10000,a0
        cmp.l #$4eba5684,($b1f4-$10000,a0)
        bne .bad
        cmp.w #$7245,($b1f8-$10000,a0)
        bne .bad
        cmp.l #$4eba4fb4,($b8c4-$10000,a0)
        bne .bad
        cmp.w #$7245,($b8c8-$10000,a0)
        bne .bad
        IFD NATIVE_SCENE
        bsr native_scene_install
        ENDC
        lea (fixture_patches,pc),a0
        jsr (resload_Patch,a2)
        move.l (_custom3,pc),d0
        beq .done
        move.l d7,a1
        add.l a1,a1
        add.l a1,a1
        addq.l #4,a1
        move.l a1,a0
        adda.l #$20000,a0
        IFD SIM60
        move.l (_custom1,pc),d0
        beq .native_input_guard
        cmp.w #$4ef9,($2730,a0)
        bne .bad
        lea (s60_history_key,pc),a3
        cmp.l ($2732,a0),a3
        bne .bad
        cmp.w #$4ef9,($2746,a0)
        bne .bad
        lea (s60_history_joy,pc),a3
        cmp.l ($2748,a0),a3
        bne .bad
        bra .input_guarded
.native_input_guard:
        ENDC
        cmp.l #$2f073e2f,($2730,a0)
        bne .bad
        cmp.w #$0008,($2734,a0)
        bne .bad
        cmp.l #$4e55fffc,($2746,a0)
        bne .bad
        cmp.l #$48e70300,($274a,a0)
        bne .bad
        IFD SIM60
.input_guarded:
        ENDC
        IFD PICKUP_USE
        IFND PICKUP_ENCOUNTER
        FAIL "PICKUP_USE requires PICKUP_ENCOUNTER"
        ENDC
        IFLT PICKUP_USE-1
        FAIL "PICKUP_USE requires a positive tick"
        ENDC
        move.l a1,a0
        adda.l #$196d0,a0
        cmp.l #$2f073e2f,(a0)
        bne .bad
        cmp.w #$0008,(4,a0)
        bne .bad
        ENDC
        IFD POWER_TRIGGER_TYPE
        IFND POWER_ROUTE
        FAIL "POWER_TRIGGER_TYPE requires POWER_ROUTE"
        ENDC
        ENDC
        IFD POWER_SLOT
        IFND POWER_ROUTE
        FAIL "POWER_SLOT requires POWER_ROUTE"
        ENDC
        IFLT POWER_SLOT
        FAIL "POWER_SLOT must be 0..6"
        ENDC
        IFGT POWER_SLOT-6
        FAIL "POWER_SLOT must be 0..6"
        ENDC
        ENDC
        IFD POWER_TRIGGER_DISTANCE
        IFND POWER_TRIGGER_TYPE
        FAIL "POWER_TRIGGER_DISTANCE requires POWER_TRIGGER_TYPE"
        ENDC
        ENDC
        IFD POWER_TRIGGER_ENERGY
        IFND POWER_TRIGGER_TYPE
        FAIL "POWER_TRIGGER_ENERGY requires POWER_TRIGGER_TYPE"
        ENDC
        ENDC
        IFD POWER_ROUTE
        IFND SIM60
        FAIL "POWER_ROUTE requires SIM60"
        ENDC
        IFD PICKUP_USE
        FAIL "POWER_ROUTE and PICKUP_USE are separate input routes"
        ENDC
        move.l a1,a0
        adda.l #$196d0,a0
        cmp.l #$2f073e2f,(a0)
        bne .bad
        cmp.w #$0008,(4,a0)
        bne .bad
        ENDC
        lea (fixture_input_patches,pc),a0
        jsr (resload_Patch,a2)
.done:  rts
.bad:
        pea (TDREASON_WRONGVER).w
        jmp (resload_Abort,a2)
fixture_patches:
        PL_START
        PL_PS $4582,fixture_begin
        PL_PS $b1f4,fixture_escape
        PL_PS $b8c4,fixture_escape
        PL_END
fixture_begin:
        IFD SIM60
        IFD DEATH_TEST
        IFD DEATH_DECLINE
        bsr s60_test_death_menu
        ENDC
        ENDC
        ENDC
        moveq #1,d0
        move.l d0,d7
        rts
fixture_escape:
        moveq #$45,d0
        moveq #$45,d1
        rts

; Native input API fixtures. Inputs are indexed by simulation step, so renderer
; cadence cannot move an input edge. No positions, velocities or RNG are written.
fixture_input_patches:
        PL_START
        IFD POWER_ROUTE
        PL_P $196d0,fixture_power_route
        ENDC
        IFD PICKUP_USE
        PL_P $196d0,fixture_power_buttons
        ENDC
        PL_P $22730,fixture_key
        PL_P $22746,fixture_joy
        PL_NOP $2274c,2
        PL_END
        IFD PICKUP_USE
; Input-only sequence: second-button press/release selects the next power;
; both buttons after the last release activate it through native input dispatch.
; PICKUP_USE_SELECTS repeats the input edge to reach later inventory entries.
        IFND PICKUP_USE_SELECTS
PICKUP_USE_SELECTS EQU 1
        ENDC
        IFLT PICKUP_USE_SELECTS-1
        FAIL "PICKUP_USE_SELECTS must be in 1..7"
        ENDC
        IFGT PICKUP_USE_SELECTS-7
        FAIL "PICKUP_USE_SELECTS must be in 1..7"
        ENDC
fixture_power_buttons:
        moveq #0,d0
        move.l (s60_ticks,pc),d0
        cmp.l #PICKUP_USE+2*PICKUP_USE_SELECTS,d0
        beq .both
        IFEQ PICKUP_USE_SELECTS-1
        cmp.l #PICKUP_USE,d0
        bne .released
        ELSE
        sub.l #PICKUP_USE,d0
        cmp.l #2*PICKUP_USE_SELECTS,d0
        bcc .released
        btst #0,d0
        bne .released
        ENDC
        cmp.w #1,(4,sp)
        bne .released
.both:  moveq #1,d0
        rts
.released:
        moveq #0,d0
        rts
        ENDC
        IFD POWER_ROUTE
; Input-only combat sequence: select/activate clone, shield, jump, cloak,
; cannon and speed through the native two-button API. The mine is omitted;
; its placement and detonation use separate encounter checks.
fixture_power_route_slots:
        IFD POWER_SLOT
        dc.b POWER_SLOT
        ELSE
        dc.b 0,1,2,4,5,6
        ENDC
fixture_power_route_slots_end:
        even
        IFD POWER_TRIGGER_TYPE
; Start once per session when a live actor of the requested type appears.
; Only private input state changes; deployment, health and inventory are native.
fixture_power_trigger_session: dc.l 0
fixture_power_trigger_tick: dc.l 0
fixture_power_trigger_elapsed:
        move.l a1,-(sp)
        lea (fixture_power_trigger_session,pc),a0
        move.l (s60_sessions,pc),d0
        cmp.l (a0),d0
        beq .session
        move.l d0,(a0)
        clr.l (4,a0)
.session:
        move.l (s60_ticks,pc),d0
        cmp.l #POWER_ROUTE,d0
        bcs .waiting
        tst.l (4,a0)
        bne .elapsed
        move.w ($43b2-$8000,a4),d1
        ble .waiting
        cmp.w #256,d1
        bhi .waiting
        subq.w #1,d1
        lea ($3fb2-$8000,a4),a1
.scan:  move.l (a1)+,d2
        move.l a1,-(sp)
        move.l d2,a1
        cmp.w #POWER_TRIGGER_TYPE,(2,a1)
        bne .next
        tst.b ($55,a1)
        ble .next
        IFD POWER_TRIGGER_DISTANCE
        cmp.l #POWER_TRIGGER_DISTANCE,($50,a1)
        bgt .next
        ENDC
        move.l (sp)+,a1
        move.l d0,(4,a0)
        bra .elapsed
.next:  move.l (sp)+,a1
        dbf d1,.scan
.waiting:
        moveq #-1,d0
        bra .done
.elapsed:
        sub.l (4,a0),d0
.done:  move.l (sp)+,a1
        rts
        ENDC
        IFD POWER_TRIGGER_ENERGY
; Once per session, when player energy first drops below POWER_TRIGGER_ENERGY,
; select and activate the shield alone (slot 1). Other powers wait for the
; boss: a clone deployed during a wave stopped the boss carrier arriving.
fixture_power_energy_session: dc.l 0
fixture_power_energy_tick: dc.l 0
fixture_power_energy_elapsed:
        lea (fixture_power_energy_session,pc),a0
        move.l (s60_sessions,pc),d0
        cmp.l (a0),d0
        beq .session
        move.l d0,(a0)
        clr.l (4,a0)
.session:
        move.l (s60_ticks,pc),d0
        tst.l (4,a0)
        bne .elapsed
        cmp.w #POWER_TRIGGER_ENERGY,($46c4-$8000,a4)
        bge .waiting
        move.l d0,(4,a0)
.elapsed:
        sub.l (4,a0),d0
        rts
.waiting:
        moveq #-1,d0
        rts
        ENDC
fixture_power_route:
        movem.l d1-d2/a0,-(sp)
        IFD POWER_TRIGGER_ENERGY
        bsr fixture_power_energy_elapsed
        cmp.l #S60_RATE,d0
        bcc .boss_route ; not triggered (-1) or finished
        divu #S60_RATE,d0
        moveq #1,d2
        bra .slot
.boss_route:
        ENDC
        IFD POWER_TRIGGER_TYPE
        bsr fixture_power_trigger_elapsed
        ELSE
        move.l (s60_ticks,pc),d0
        sub.l #POWER_ROUTE,d0
        bcs .released
        ENDC
        cmp.l #(fixture_power_route_slots_end-fixture_power_route_slots)*S60_RATE,d0
        bcc .released
        divu #S60_RATE,d0
        move.w d0,d1
        lea (fixture_power_route_slots,pc),a0
        moveq #0,d2
        move.b (a0,d1.w),d2
.slot:
        swap d0
        btst #0,d0
        bne .released
        cmp.w #1,(16,sp)
        beq .pressed ; second button selects on release
        cmp.w ($20be-$8000,a4),d2
        bne .released
.pressed:
        moveq #1,d0
        bra .done
.released:
        moveq #0,d0
.done:  movem.l (sp)+,d1-d2/a0
        rts
        ENDC
fixture_joy:
        IFD INPUT_NEUTRAL_PLAY
        IFND SIM60
        FAIL "INPUT_NEUTRAL_PLAY requires SIM60"
        ENDC
        IFND PREFERENCES_CHOICE
        FAIL "INPUT_NEUTRAL_PLAY requires the native Joystick preference toggle"
        ELSE
        IFNE PREFERENCES_CHOICE-2
        FAIL "INPUT_NEUTRAL_PLAY requires PREFERENCES_CHOICE=2"
        ENDC
        ENDC
        move.l (s60_ticks,pc),d0
        cmp.l #INPUT_NEUTRAL_PLAY,d0
        bcs .neutral
        cmp.l #INPUT_NEUTRAL_PLAY+2*S60_RATE,d0
        bcc .neutral
        moveq #4,d0 ; turn through the native joystick API for two seconds
        rts
.neutral:
        moveq #0,d0 ; release through the same API; do not write velocities
        rts
        ENDC
        IFD APPROACH_TYPE
        bra fixture_approach
        ENDC
        moveq #0,d0
        cmp.w #100,($1e96-$8000,a4)
        bcs .done
        cmp.w #140,($1e96-$8000,a4)
        bcc .done
        moveq #1,d0
        cmp.w #120,($1e96-$8000,a4)
        bcs .done
        moveq #9,d0
.done:  rts
fixture_key:
        IFD INPUT_NEUTRAL_PLAY
        moveq #0,d0
        rts
        ENDC
        IFD APPROACH_FIRE
        IFND APPROACH_TYPE
        FAIL "APPROACH_FIRE requires APPROACH_TYPE"
        ENDC
        moveq #0,d0
        cmp.w #$40,(4,sp)
        bne .fire_done
        move.w (fixture_approach_fire,pc),d0
.fire_done:
        rts
        ENDC
        IFD APPROACH_TYPE
        moveq #0,d0 ; let the enemy fire; do not destroy it with player shots
        rts
        ENDC
        moveq #0,d0
        cmp.w #$40,(4,sp)
        bne .done
        cmp.w #105,($1e96-$8000,a4)
        bcs .done
        cmp.w #135,($1e96-$8000,a4)
        bcc .done
        moveq #1,d0
.done:  rts

        IFD APPROACH_RAM
        IFND APPROACH_TYPE
        FAIL "APPROACH_RAM requires APPROACH_TYPE"
        ENDC
        IFD APPROACH_FIRE
        FAIL "APPROACH_RAM does not fire"
        ENDC
        IFD APPROACH_CONTACT
        FAIL "APPROACH_RAM and APPROACH_CONTACT are separate routes"
        ENDC
        ENDC
        IFD APPROACH_CONTACT
        IFND APPROACH_TYPE
        FAIL "APPROACH_CONTACT requires APPROACH_TYPE=31 or 46"
        ELSE
        IFNE APPROACH_TYPE-46
        IFNE APPROACH_TYPE-31
        FAIL "APPROACH_CONTACT requires APPROACH_TYPE=31 or 46"
        ENDC
        ENDC
        ENDC
        IFD APPROACH_FIRE
        FAIL "APPROACH_CONTACT does not fire"
        ENDC
        ENDC
        IFD APPROACH_STANDOFF
        IFND APPROACH_FIRE
        FAIL "APPROACH_STANDOFF requires APPROACH_FIRE"
        ENDC
        IFND APPROACH_TYPE
        FAIL "APPROACH_STANDOFF requires APPROACH_TYPE=0"
        ENDC
        IFNE APPROACH_TYPE
        FAIL "APPROACH_STANDOFF requires APPROACH_TYPE=0"
        ENDC
        IFLT APPROACH_STANDOFF-2000
        FAIL "APPROACH_STANDOFF must be 2000..30000"
        ENDC
        IFGT APPROACH_STANDOFF-30000
        FAIL "APPROACH_STANDOFF must be 2000..30000"
        ENDC
        ENDC
        IFD APPROACH_BOSS_STANDOFF
        IFND APPROACH_STANDOFF
        FAIL "APPROACH_BOSS_STANDOFF requires APPROACH_STANDOFF"
        ENDC
        ENDC
        IFD APPROACH_REACH
        IFND APPROACH_STANDOFF
        FAIL "APPROACH_REACH requires APPROACH_STANDOFF"
        ENDC
        ENDC
        IFD APPROACH_AVOID_WARP
        IFND APPROACH_STANDOFF
        FAIL "APPROACH_AVOID_WARP requires APPROACH_STANDOFF"
        ENDC
        ENDC
        IFD APPROACH_TYPE
        IFND SIM60
        FAIL "APPROACH_TYPE requires SIM60"
        ENDC
; Approach a live enemy through the native joystick/key input
; API, leaving actor state, projectile creation and RNG entirely to gameplay.
; The 2048-angle deadband allows native turn-rate braking; stop accelerating
; inside 18000 distance units, below the native enemy firing limit of 24576.
; APPROACH_FIRE instead keeps steering and fires while aligned, closing to 4000.
; APPROACH_RAM continues to contact distance without firing or changing actors.
; APPROACH_CONTACT targets type-31 pickups or type-46 terrain regardless of health,
; keeps approaching to contact distance and never fires.
; APPROACH_TYPE=0 selects the nearest grounded hostile (or a boss), prioritizing
; the type-25 exit when it exists. It never alters an actor or level flag.
; APPROACH_STANDOFF also tracks the carrier and backs away when too close;
; enemies are held within +/-1000 of the requested distance using native input.
; APPROACH_BOSS_STANDOFF holds bosses at their own distance. APPROACH_REACH also
; turns towards the nearest flyer when nothing grounded is left (without
; driving), and fires at flyers and bosses only within a grounded shot's reach.
; APPROACH_AVOID_WARP turns away from a type-26 warp within 5000 and drives off,
; so no level is skipped.
        IFD APPROACH_FIRE
fixture_approach_fire: dc.w 0
        ENDC
        IFD APPROACH_LOCK
        IFNE APPROACH_TYPE
        FAIL "APPROACH_LOCK requires APPROACH_TYPE=0"
        ENDC
fixture_approach_target: dc.l 0
        ENDC
        IFND APPROACH_AIM
APPROACH_AIM EQU 2048
        ENDC
        IFLT APPROACH_AIM-1
        FAIL "APPROACH_AIM must be 1..2048"
        ENDC
        IFGT APPROACH_AIM-2048
        FAIL "APPROACH_AIM must be 1..2048"
        ENDC
fixture_approach:
        movem.l d1-d4/a0-a3,-(sp)
        moveq #0,d0
        IFD APPROACH_FIRE
        lea (fixture_approach_fire,pc),a0
        clr.w (a0)
        ENDC
        move.w ($43b2-$8000,a4),d1
        ble .done
        cmp.w #256,d1
        bhi .done
        subq.w #1,d1
        lea ($3fb2-$8000,a4),a0
        IFEQ APPROACH_TYPE
        move.l #$7fffffff,d2
        suba.l a2,a2
        IFD APPROACH_REACH
        move.l d2,d4
        suba.l a3,a3
        ENDC
.scan:  move.l (a0)+,a1
        cmp.w #25,(2,a1)
        beq .found
        IFD APPROACH_AVOID_WARP
        cmp.w #26,(2,a1)
        bne .not_warp
        cmp.l #5000,($50,a1)
        ble .avoid
        bra .scan_next
.not_warp:
        ENDC
        cmp.b #$ff,($54,a1)
        bne .scan_next
        tst.b ($55,a1)
        ble .scan_next
        cmp.w #7,(2,a1)
        IFD APPROACH_STANDOFF
        beq .candidate ; move away before its native boss deployment
        ELSE
        beq .scan_next
        ENDC
        cmp.w #44,(2,a1)
        bge .candidate
        cmp.l #300,(16,a1)
        IFD APPROACH_REACH
        ble .candidate
        cmp.l ($50,a1),d4 ; a flyer: only a fallback to track
        ble .scan_next
        move.l ($50,a1),d4
        move.l a1,a3
        bra .scan_next
        ELSE
        bgt .scan_next
        ENDC
.candidate:
        IFD APPROACH_LOCK
        ; Retain a live target only while it is still in the active list and
        ; passes the native hostility/health/height checks above. Exits win.
        cmpa.l (fixture_approach_target,pc),a1
        bne .nearest
        moveq #-1,d2
        move.l a1,a2
        bra .scan_next
.nearest:
        ENDC
        cmp.l ($50,a1),d2
        ble .scan_next
        move.l ($50,a1),d2
        move.l a1,a2
.scan_next:
        dbf d1,.scan
        move.l a2,d1
        IFD APPROACH_REACH
        bne .chosen
        moveq #-1,d4 ; nothing grounded: face the nearest flyer without driving
        move.l a3,d1
        ENDC
        beq .done
.chosen:
        move.l d1,a1
        bra .found
        ENDC
.find:  move.l (a0)+,a1
        cmp.w #APPROACH_TYPE,(2,a1)
        bne .next
        IFD APPROACH_CONTACT
        bra .found ; terrain need not have enemy health
        ELSE
        tst.b ($55,a1)
        bgt .found
        ENDC
.next:  dbf d1,.find
        IFD APPROACH_CONTACT
        IFEQ APPROACH_TYPE-46
        moveq #5,d0 ; forward + turn while waiting for native terrain spawning
        ENDC
        ENDC
        bra .done
.found:
        IFD APPROACH_LOCK
        lea (fixture_approach_target,pc),a0
        clr.l (a0)
        cmp.w #7,(2,a1)
        beq .target_saved ; carrier is only a temporary spacing target
        move.l a1,(a0)
.target_saved:
        ENDC
        IFND APPROACH_FIRE
        IFND APPROACH_CONTACT
        IFND APPROACH_RAM
        cmp.l #18000,($50,a1)
        ble .done
        ENDC
        ENDC
        ENDC
        move.l ($43c0-$8000,a4),a2
        move.w ($5e,a1),d2 ; enemy-to-player heading, reverse for the approach
        add.w #$8000,d2
        sub.w ($18,a2),d2
        cmp.w #APPROACH_AIM,d2
        bgt .positive
        cmp.w #-APPROACH_AIM,d2
        blt .negative
        IFD APPROACH_FIRE
        lea (fixture_approach_fire,pc),a0
        cmp.w #25,(2,a1)
        beq .advance
        IFD APPROACH_STANDOFF
        cmp.w #7,(2,a1)
        beq .spacing ; carrier is a spacing target, never a firing target
        ENDC
        IFD APPROACH_REACH
        ; Hold fire on flyers and bosses until a grounded shot can reach them. The
        ; level 0 and 3 bosses ($10bf8/$10d2a) test hits at the projectile's height.
        cmp.w #44,(2,a1)
        bge .boss_reach
        cmp.l #300,(16,a1)
        ble .fire
        bra .fire_reach
.boss_reach:
        cmp.w #0,($46a0-$8000,a4)
        beq .fire
        cmp.w #3,($46a0-$8000,a4)
        beq .fire
.fire_reach:
        bsr .reach
        blt .spacing
.fire:
        ENDC
        move.w #1,(a0)
        IFD APPROACH_STANDOFF
.spacing:
        IFD APPROACH_REACH
        tst.l d4
        bmi .done
        ENDC
        IFD APPROACH_BOSS_STANDOFF
        ; A boss keeps its distance; close in further so its hits are reachable.
        ; The level 2 boss only dives at a player more than 4000 away ($10ab0),
        ; so it keeps the normal standoff.
        cmp.w #44,(2,a1)
        blt .standoff
        cmp.w #2,($46a0-$8000,a4)
        beq .standoff
        cmp.l #APPROACH_BOSS_STANDOFF-1000,($50,a1)
        blt .reverse
        cmp.l #APPROACH_BOSS_STANDOFF+1000,($50,a1)
        ble .done
        bra .advance
.standoff:
        ENDC
        cmp.l #APPROACH_STANDOFF-1000,($50,a1)
        blt .reverse
        cmp.l #APPROACH_STANDOFF+1000,($50,a1)
        ble .done
        cmp.w #7,(2,a1)
        beq .done
        bra .advance
.reverse:
        moveq #2,d0 ; native $ffa4 reduces forward velocity
        bra .done
        ELSE
        cmp.l #4000,($50,a1)
        ble .done
        ENDC
.advance:
        ENDC
        moveq #1,d0 ; forward
        bra .done
.positive:
        moveq #4,d0 ; native $febe increases yaw velocity
        bra .done
.negative:
        moveq #8,d0 ; native $fee6 decreases yaw velocity
        IFD APPROACH_AVOID_WARP
        bra .done
; A type-26 warp ($35e4/$360a) adds two levels on contact; face away and drive.
.avoid: move.l ($43c0-$8000,a4),a2
        move.w ($5e,a1),d2 ; warp-to-player heading points away from it
        sub.w ($18,a2),d2
        cmp.w #APPROACH_AIM,d2
        bgt .positive
        cmp.w #-APPROACH_AIM,d2
        blt .negative
        moveq #1,d0
        ENDC
.done:  movem.l (sp)+,d1-d4/a0-a3
        rts
        IFD APPROACH_REACH
; Native $85f6 hits when every axis differs by at most the mean radius (+4).
; A grounded player projectile (radius 134) reaches A1 when d3 = r+134-2y >= 0.
.reach: move.l (4,a1),d3
        add.l #134,d3
        sub.l (16,a1),d3
        sub.l (16,a1),d3
        rts
        ENDC
        ENDC

; Native-timing performance scene. All hooks are VERIFY/CUSTOM5 only.
; SIM60 is compiled to reuse the encounter setup, but CUSTOM1 must stay off.
        IFD NATIVE_SCENE
        IFND SIM60
        FAIL "NATIVE_SCENE requires SIM60 compiled, with CUSTOM1 disabled"
        ENDC
        IFNE NATIVE_SCENE
        IFNE NATIVE_SCENE-6
        FAIL "NATIVE_SCENE supports level zero boss or level six type-10"
        ENDC
        ENDC
        IFD BOSS_ENCOUNTER
        IFNE NATIVE_SCENE
        FAIL "Native boss setup requires NATIVE_SCENE=0"
        ENDC
        ELSE
        IFEQ NATIVE_SCENE
        FAIL "NATIVE_SCENE=0 requires BOSS_ENCOUNTER"
        ENDC
        ENDC
        IFD LEVEL_TEST
        FAIL "Native scene uses its own level setup, not LEVEL_TEST"
        ENDC
native_scene_results:
        dc.b 'NR60'
        dc.w 0,0,NATIVE_SCENE,0 ; requested exits, restored flag, target, reserved
native_scene_saved: ds.b 6
native_scene_install:
        movem.l d0-d2/a0-a3,-(sp)
        move.l (_custom1,pc),d0
        bne .bad ; never combine native observation hooks with SIM60 timing
        move.l (_custom3,pc),d0
        beq .bad ; scene requires its native input pilot
        move.l (14,a1),d0 ; native startup's relocated A4 value
        sub.l #$8000,d0
        move.l d0,d1
        add.l #$1e53,d1
        cmp.w #$4a39,($2af6,a1)
        bne .bad
        cmp.l ($2af8,a1),d1
        bne .bad
        add.l #$1e96,d0
        cmp.w #$5279,($2d4e,a1)
        bne .bad
        cmp.l ($2d50,a1),d0
        bne .bad
        lea (native_scene_saved,pc),a0
        IFD BOSS_ENCOUNTER
        move.l ($2af6,a1),(a0)
        move.w ($2afa,a1),(4,a0)
        ELSE
        move.l ($2d4e,a1),(a0)
        move.w ($2d52,a1),(4,a0)
        ENDC
        lea (s60_code,pc),a0
        move.l a1,(a0)
        lea (s60_sessions,pc),a0
        move.l #1,(a0)
        lea (native_scene_patches,pc),a0
        jsr (resload_Patch,a2)
        movem.l (sp)+,d0-d2/a0-a3
        rts
.bad:
        pea (TDREASON_WRONGVER).w
        jmp (resload_Abort,a2)
native_scene_patches:
        PL_START
        IFD BOSS_ENCOUNTER
        PL_PS $2af6,native_scene_begin
        ENDC
        IFNE NATIVE_SCENE
        PL_PS $2d4e,native_scene_finish
        ENDC
        PL_END
        IFD BOSS_ENCOUNTER
native_scene_begin:
        move.l d0,-(sp)
        moveq #0,d0
        addx.w d0,d0 ; retain incoming X without privileged SR access
        move.w d0,-(sp)
        bsr s60_test_encounter ; controlled setup only; no SIM60 tick executes
        bsr native_scene_restore
        move.w (sp)+,d0
        lsr.w #1,d0 ; restore incoming X
        move.l (sp)+,d0
        tst.b ($1e53-$8000,a4) ; exact displaced native test/CCR
        rts
        ENDC
        IFNE NATIVE_SCENE
native_scene_finish:
        movem.l d0/a0,-(sp)
        cmp.w #NATIVE_SCENE,($46a0-$8000,a4)
        blt .earlier
        bsr native_scene_restore ; remove setup overhead before measured gameplay
        bra .done
.earlier:
        cmp.w #16,($1e96-$8000,a4) ; after this update: native frame 17
        bne .done
        tst.b ($1e53-$8000,a4)
        beq .done
        tst.w ($1e90-$8000,a4)
        bne .done
        clr.b ($1e53-$8000,a4) ; native cleanup/load/increment takes the exit
        lea (native_scene_results,pc),a0
        addq.w #1,(4,a0)
.done:
        movem.l (sp)+,d0/a0
        addq.w #1,($1e96-$8000,a4) ; exact displaced increment/CCR
        rts
        ENDC
native_scene_restore:
        movem.l d0-d1/a0-a2,-(sp)
        move.l (s60_code,pc),a0
        IFD BOSS_ENCOUNTER
        adda.l #$2af6,a0
        ELSE
        adda.l #$2d4e,a0
        ENDC
        lea (native_scene_saved,pc),a1
        move.l (a1),(a0)
        move.w (4,a1),(4,a0)
        lea (native_scene_results,pc),a1
        move.w #1,(6,a1)
        move.l (_resload,pc),a2
        jsr (resload_FlushCache,a2)
        movem.l (sp)+,d0-d1/a0-a2
        rts
        ENDC
