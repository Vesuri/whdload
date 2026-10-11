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
        cmp.l #$2f073e2f,($2730,a0)
        bne .bad
        cmp.w #$0008,($2734,a0)
        bne .bad
        cmp.l #$4e55fffc,($2746,a0)
        bne .bad
        cmp.l #$48e70300,($274a,a0)
        bne .bad
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
        cmp.l #INPUT_NEUTRAL_PLAY+120,d0
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
        IFD APPROACH_TYPE
        IFND SIM60
        FAIL "APPROACH_TYPE requires SIM60"
        ENDC
; Approach a live enemy through the native joystick/key input
; API, leaving actor state, projectile creation and RNG entirely to gameplay.
; The 2048-angle deadband allows native turn-rate braking; stop accelerating
; inside 18000 distance units, below the native enemy firing limit of 24576.
; APPROACH_FIRE instead keeps steering and fires while aligned, closing to 4000.
; APPROACH_CONTACT targets type-31 pickups or type-46 terrain regardless of health,
; keeps approaching to contact distance and never fires.
; APPROACH_TYPE=0 selects the nearest grounded hostile (or a boss), prioritizing
; the type-25 exit when it exists. It never alters an actor or level flag.
; APPROACH_STANDOFF also tracks the carrier and backs away when too close;
; enemies are held within +/-1000 of the requested distance using native input.
        IFD APPROACH_FIRE
fixture_approach_fire: dc.w 0
        ENDC
fixture_approach:
        movem.l d1-d2/a0-a2,-(sp)
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
.scan:  move.l (a0)+,a1
        cmp.w #25,(2,a1)
        beq .found
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
        bgt .scan_next
.candidate:
        cmp.l ($50,a1),d2
        ble .scan_next
        move.l ($50,a1),d2
        move.l a1,a2
.scan_next:
        dbf d1,.scan
        move.l a2,d1
        beq .done
        move.l a2,a1
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
        IFND APPROACH_FIRE
        IFND APPROACH_CONTACT
        cmp.l #18000,($50,a1)
        ble .done
        ENDC
        ENDC
        move.l ($43c0-$8000,a4),a2
        move.w ($5e,a1),d2 ; enemy-to-player heading, reverse for the approach
        add.w #$8000,d2
        sub.w ($18,a2),d2
        cmp.w #2048,d2
        bgt .positive
        cmp.w #-2048,d2
        blt .negative
        IFD APPROACH_FIRE
        lea (fixture_approach_fire,pc),a0
        cmp.w #25,(2,a1)
        beq .advance
        IFD APPROACH_STANDOFF
        cmp.w #7,(2,a1)
        beq .spacing ; carrier is a spacing target, never a firing target
        ENDC
        move.w #1,(a0)
        IFD APPROACH_STANDOFF
.spacing:
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
.done:  movem.l (sp)+,d1-d2/a0-a2
        rts
        ENDC
