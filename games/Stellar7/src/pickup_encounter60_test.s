; Controlled real pickup encounter. Native allocation/list insertion is used;
; only placement, the scene-initializer's type-31 fields initial energy and one inventory count are
; supplied. Collision acquisition, healing, inventory, sound and removal run.
        IFD VERIFY
        IFD PICKUP_ENCOUNTER
        IFLT PICKUP_ENCOUNTER-1
        FAIL "PICKUP_ENCOUNTER requires a positive tick"
        ENDC
s60_pickup_encounter_results:
        dc.b 'PE61'
        dc.w 0,0 ; setups, errors
        dc.l 0,0,0 ; setup tick, allocated actor, session
        dc.w 0,0,0,0 ; level, world count before/after, original energy
        dc.w 0,1,0,0 ; inventory before/assigned, selected power, reserved
s60_test_pickup_encounter:
        movem.l d0-d7/a0-a6,-(sp)
        lea (s60_pickup_encounter_results,pc),a6
        tst.w (4,a6)
        bne .done
        move.l (s60_ticks,pc),d0
        cmp.l #PICKUP_ENCOUNTER,d0
        bne .done
        move.l d0,(8,a6)
        move.l (s60_sessions,pc),(16,a6)
        move.w ($46a0-S60_DATA,a4),(20,a6)
        move.w ($3fb0-S60_DATA,a4),(22,a6)
        move.w ($46c4-S60_DATA,a4),(26,a6)
        tst.l ($46c0-S60_DATA,a4)
        bne .bad
        move.l (s60_code,pc),a0
        adda.l #$913c,a0
        cmp.l #$48e70310,(a0)
        bne .bad
        cmp.l #$1e2f0011,(4,a0)
        bne .bad
        move.w #31,-(sp)
        S60_CALL $913c
        addq.l #2,sp
        tst.l d0
        beq .bad
        move.l d0,(12,a6)
        move.l d0,a3
        cmp.w #31,(2,a3)
        bne .bad
        ; Match native scene initialization at $a01c..$a02a.
        move.b #100,($55,a3)
        clr.b ($56,a3)
        lea ($56,a3),a0
        move.l a0,($1e,a3)
        move.l ($43c0-S60_DATA,a4),a0
        move.l (8,a0),d0
        add.l #3000,d0
        move.l d0,(8,a3)
        move.l (12,a0),(12,a3)
        moveq #0,d0
        move.b ($20f8-S60_DATA,a4),d0
        move.w d0,(28,a6)
        move.w ($20be-S60_DATA,a4),(32,a6)
        move.b #1,($20f8-S60_DATA,a4) ; make the native three-charge grant observable
        move.w #300,($46c4-S60_DATA,a4)
        move.w ($3fb0-S60_DATA,a4),(24,a6)
        move.w #1,(4,a6)
.done:  movem.l (sp)+,d0-d7/a0-a6
        rts
.bad:   addq.w #1,(6,a6)
        move.l (_resload,pc),a2
        bra s60_bad
        ENDC
        ENDC
