; Post-update events run each tick; periodic spawning/warnings retain 5 Hz units.
; $2c58 handles a pending Quit to DOS request, not level completion.
s60_post_install:
        move.l (s60_code,pc),a1
        cmp.l #$700fc079,($2c96,a1)
        bne s60_bad
        cmp.w #$662e,($2c9e,a1)
        bne s60_bad
        ; A4 is not the game data base during installation: compare relocated
        ; operands instead of relying on the runtime base register.
        move.l ($2c9a,a1),d0
        cmp.l ($2d50,a1),d0
        bne s60_bad
        move.l a1,a0
        adda.l #$8000,a0
        cmp.l #$13fc0001,($4052,a0)
        bne s60_bad
        cmp.w #$4239,($407e,a0)
        bne s60_bad
        cmp.w #$4a39,($1348,a0)
        bne s60_bad
        move.l ($134a,a0),d0 ; native boss gate's relocated byte address
        cmp.l ($4056,a0),d0
        bne s60_bad
        cmp.l ($4080,a0),d0
        bne s60_bad
        IFD VERIFY
        IFD BOSS_GATE_TEST
        cmp.l #$102b0054,($4074,a0)
        bne s60_bad
        cmp.l #$0c0000ff,($4078,a0)
        bne s60_bad
        cmp.w #$6606,($407c,a0)
        bne s60_bad
        lea ($4074,a0),a3
        lea (s60_gate_native,pc),a0
        move.l (a3)+,(a0)+
        move.l (a3)+,(a0)+
        move.l (a3)+,(a0)+
        move.l (a3)+,(a0)+
        ENDC
        ENDC
        lea (s60_post_patches,pc),a0
        jsr (resload_Patch,a2)
        rts
s60_post_patches:
        PL_START
        PL_PSS $2c96,s60_post_periodic,2
        PL_NOP $c052,8 ; no-enemies predicate belongs to simulation
        PL_NOP $c07e,6
        PL_END
s60_post_periodic:
        move.w (s60_running,pc),d0
        beq .native
        move.w (s60_logic,pc),d0
        beq .skip
.native:
        moveq #15,d0
        and.w ($1e96-S60_DATA,a4),d0
        rts ; preserve native condition codes for BNE at $2c9e
.skip:
        add.l #$2cce-$2c9c,(sp) ; bypass periodic work, enter native death check
        rts

; Radar $c052/$c07e used to publish this flag only when a picture was drawn.
; Native $9348 consumes it when deciding whether to spawn the boss carrier.
; Recompute from the same active list before periodic spawning, every update.
; Match the native signed count and class-byte comparison (health/visibility
; are deliberately irrelevant). DBF avoids changing X while walking the list.
s60_boss_gate:
        movem.l d0-d1/a0-a1,-(sp)
        moveq #1,d1
        move.w ($43b2-S60_DATA,a4),d0
        ble .publish
        lea ($3fb2-S60_DATA,a4),a0
        bra .test
.loop:  move.l (a0)+,a1
        IFD VERIFY
        IFD BOSS_GATE_BAD
        cmp.b #$fe,($54,a1)
        ELSE
        cmp.b #$ff,($54,a1)
        ENDC
        ELSE
        cmp.b #$ff,($54,a1)
        ENDC
        beq .blocked
.test:  dbf d0,.loop
        bra .publish
.blocked:
        moveq #0,d1
.publish:
        move.b d1,($1efc-S60_DATA,a4)
        movem.l (sp)+,d0-d1/a0-a1
        rts
