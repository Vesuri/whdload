; VERIFY-only scene setup: finish the selected level wave by setting progress to
; the native level target and killing initial ordinary enemies through $3f04.
; The normal $9346 carrier, $93fc boss, damage and exit paths remain untouched.
        IFD VERIFY
        IFD BOSS_ENCOUNTER
        IFND BOSS_ENCOUNTER_LEVEL
BOSS_ENCOUNTER_LEVEL = 0
        ENDC
        IFLT BOSS_ENCOUNTER_LEVEL
        FAIL "BOSS_ENCOUNTER_LEVEL must be 0..6"
        ENDC
        IFGT BOSS_ENCOUNTER_LEVEL-6
        FAIL "BOSS_ENCOUNTER_LEVEL must be 0..6"
        ENDC
        IFD LEVEL_TEST
        IFND LEVEL_OBSERVE
        IFND LEVEL_LAST
        FAIL "Injected earlier exits require explicit LEVEL_LAST"
        ENDC
        IFNE LEVEL_LAST-BOSS_ENCOUNTER_LEVEL
        FAIL "Injected exits must stop before the selected boss encounter"
        ENDC
        IFEQ BOSS_ENCOUNTER_LEVEL
        FAIL "Level-zero boss encounter requires passive exit observation"
        ENDC
        ENDC
        ENDC
        IFD BOSS_FINISH_TEST
        IFNE BOSS_ENCOUNTER_LEVEL-6
        FAIL "BOSS_FINISH_TEST requires the final-level encounter"
        ENDC
        IFLT BOSS_FINISH_TEST-1
        FAIL "BOSS_FINISH_TEST must select a positive simulation tick"
        ENDC
        ENDC
        IFD BOSS_TERRAIN_TEST
        IFNE BOSS_ENCOUNTER_LEVEL-5
        FAIL "BOSS_TERRAIN_TEST requires level 5"
        ENDC
        IFD BOSS_FINISH_TEST
        FAIL "BOSS_TERRAIN_TEST cannot combine with BOSS_FINISH_TEST"
        ENDC
        IFLT BOSS_TERRAIN_TEST-1
        FAIL "BOSS_TERRAIN_TEST requires a positive tick"
        ENDC
        ENDC
s60_encounter_results:
        IFD BOSS_TERRAIN_TEST
        dc.b 'BE64'
        ELSE
        IFD BOSS_FINISH_TEST
        dc.b 'BE63'
        ELSE
        dc.b 'BE62'
        ENDC
        ENDC
        dc.w 0,0 ; setups, error
        dc.l 0 ; session
        dc.w 0,0,0,0 ; level, original progress, target, initial enemies cleared
        dc.w BOSS_ENCOUNTER_LEVEL ; requested scene; no injected exit in this level
        IFD BOSS_FINISH_TEST
        dc.w 0,0,0 ; finish setups, original health, assigned health
        dc.l 0 ; health setup tick; ending must still follow a native hit
        ENDC
        IFD BOSS_TERRAIN_TEST
        dc.w 0,0,0,0 ; terrain setups, prior state, assigned state, reserved
        dc.l 0 ; setup tick; allocation/contact remain native
        ENDC
s60_test_encounter:
        movem.l d0-d7/a0-a3,-(sp)
        lea (s60_encounter_results,pc),a0
        tst.w (4,a0)
        IFD BOSS_FINISH_TEST
        bne .finish
        ELSE
        IFD BOSS_TERRAIN_TEST
        bne .terrain
        ELSE
        bne .done
        ENDC
        ENDC
        cmp.w #BOSS_ENCOUNTER_LEVEL,($46a0-S60_DATA,a4)
        blt .done ; earlier levels can use the separately recorded exit fixture
        bgt .bad
        move.l (s60_ticks,pc),d0
        bne .bad
        move.l (s60_sessions,pc),d0
        move.l d0,(8,a0)
        cmp.l #BOSS_ENCOUNTER_LEVEL+1,d0
        bne .bad
        tst.l ($1e48-S60_DATA,a4)
        bne .bad
        tst.l ($1e4c-S60_DATA,a4)
        bne .bad
        move.w ($46a0-S60_DATA,a4),(12,a0)
        move.w ($1e70-S60_DATA,a4),(14,a0)
        moveq #0,d0
        move.b ($46b0-S60_DATA,a4),d0
        beq .bad
        move.w d0,(16,a0)
        move.w d0,($1e70-S60_DATA,a4)
        move.w #1,(4,a0)
        move.l (s60_code,pc),a1
        cmp.l #$48e70310,($3f04,a1)
        bne .bad
        cmp.l #$266f0010,($3f08,a1)
        bne .bad
.restart:
        move.w ($3fb0-S60_DATA,a4),d7
        ble .done
        cmp.w #256,d7
        bhi .bad
        lea ($3bb0-S60_DATA,a4),a2
        bra .test
.scan:  move.l (a2)+,a3
        cmp.b #$ff,($54,a3)
        bne .test
        move.w (2,a3),d0
        cmp.w #1,d0
        blt .test
        cmp.w #16,d0
        bgt .test
        moveq #0,d0
        move.b ($55,a3),d0
        ble .test
        move.w d0,-(sp)
        move.l a3,-(sp)
        S60_CALL $3f04
        addq.l #6,sp
        lea (s60_encounter_results,pc),a0
        tst.b ($55,a3)
        bne .bad
        addq.w #1,(18,a0)
        cmp.w #16,(18,a0)
        bhi .bad
        bra .restart ; removal changes world membership/order
.test:  dbf d7,.scan
        bra .done
        IFD BOSS_FINISH_TEST
.finish:
        tst.w (6,a0)
        bne .done
        tst.w (22,a0)
        bne .done
        move.l (s60_ticks,pc),d0
        cmp.l #BOSS_FINISH_TEST,d0
        bcs .done
        bne .bad
        cmp.w #6,($46a0-S60_DATA,a4)
        bne .bad
        tst.b ($1e53-S60_DATA,a4)
        beq .bad
        tst.w ($1e90-S60_DATA,a4)
        bne .bad
        move.l ($1e48-S60_DATA,a4),d1
        beq .bad
        move.l d1,a1
        cmp.w #44,(2,a1)
        bne .bad
        moveq #0,d1
        move.b ($55,a1),d1
        ble .bad
        move.w d1,(24,a0)
        move.b #1,($55,a1)
        move.w #1,(26,a0)
        move.w #1,(22,a0)
        move.l d0,(28,a0)
        bra .done
        ENDC
        IFD BOSS_TERRAIN_TEST
.terrain:
        tst.w (6,a0)
        bne .done
        tst.w (22,a0)
        bne .done
        move.l (s60_ticks,pc),d0
        cmp.l #BOSS_TERRAIN_TEST,d0
        bcs .done
        bne .bad
        cmp.w #5,($46a0-S60_DATA,a4)
        bne .bad
        move.l ($1e48-S60_DATA,a4),d1
        beq .bad
        move.l d1,a1
        cmp.w #44,(2,a1)
        bne .bad
        moveq #0,d1
        move.b ($59,a1),d1
        move.w d1,(24,a0)
        move.b #1,($59,a1) ; select only the native terrain-spawning state
        move.w #1,(26,a0)
        move.w #1,(22,a0)
        move.l d0,(30,a0)
        bra .done
        ENDC
.bad:   move.w #1,(4,a0)
        move.w #1,(6,a0)
.done:  movem.l (sp)+,d0-d7/a0-a3
        rts
        ENDC
        ENDC
