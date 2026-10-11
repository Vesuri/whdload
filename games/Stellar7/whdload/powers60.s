; Per-activation timer phases. Native words retain 5 Hz units for existing
; gameplay/HUD readers; their decrement and expiry paths run every 12 ticks.
; Each record is {ticks until decrement, last native word}.
s60_power_state: ds.b 20
s60_powers_reset:
        lea (s60_power_state,pc),a0
        moveq #4,d0
.loop:  clr.l (a0)+
        dbf d0,.loop
        rts
s60_powers_install:
        move.l (s60_code,pc),a1
        move.l a1,a0
        adda.l #$10000,a0
        cmp.l #$33fc0384,($3e3e,a1)
        bne s60_bad
        cmp.l #$33fc01f4,($ec6a-$10000,a0)
        bne s60_bad
        cmp.l #$33fc01f4,($ec8e-$10000,a0)
        bne s60_bad
        cmp.l #$33fc01f4,($eca4-$10000,a0)
        bne s60_bad
        cmp.l #$33fc00c8,($ecc0-$10000,a0)
        bne s60_bad
        cmp.w #$5379,($3dcc,a1)
        bne s60_bad
        cmp.w #$5379,($ecd2-$10000,a0)
        bne s60_bad
        cmp.w #$5379,($ed38-$10000,a0)
        bne s60_bad
        cmp.w #$5379,($ed6c-$10000,a0)
        bne s60_bad
        cmp.w #$5379,($ed86-$10000,a0)
        bne s60_bad
        lea (s60_power_patches,pc),a0
        jsr (resload_Patch,a2)
        rts
s60_power_patches:
        PL_START
        PL_PSS $3e3e,s60_power_set0,2
        PL_PSS $ec6a,s60_power_set1,2
        PL_PSS $ec8e,s60_power_set2,2
        PL_PSS $eca4,s60_power_set3,2
        PL_PSS $ecc0,s60_power_set4,2
        PL_P $3dcc,s60_power_tick0
        PL_P $ecd2,s60_power_tick1
        PL_P $ed38,s60_power_tick2
        PL_P $ed6c,s60_power_tick3
        PL_P $ed86,s60_power_tick4
        PL_END
S60_POWER_SET MACRO
        move.l a0,-(sp)
        lea (s60_power_state+\1,pc),a0
        move.w #S60_LEGACY_DIV,(a0)
        move.w #\2,(2,a0)
        move.l (sp)+,a0
        move.w #\2,(\3-S60_DATA,a4)
        rts
        ENDM
s60_power_set0: S60_POWER_SET 0,900,$1e9c
s60_power_set1: S60_POWER_SET 4,500,$1e9e
s60_power_set2: S60_POWER_SET 8,500,$1ea4
s60_power_set3: S60_POWER_SET 12,500,$1ea6
s60_power_set4: S60_POWER_SET 16,200,$1ea8

; A0 record, A1 native counter. D0 says whether to execute the native decrement.
; This also handles initialization by game paths other than the normal setters.
s60_power_due:
        move.w (s60_running,pc),d0
        beq .yes
        move.w (a1),d0
        cmp.w (2,a0),d0
        beq .count
        move.w d0,(2,a0)
        move.w #S60_LEGACY_DIV,(a0)
.count: subq.w #1,(a0)
        bne .no
        move.w #S60_LEGACY_DIV,(a0)
        subq.w #1,(2,a0)
.yes:   moveq #1,d0
        rts
.no:    moveq #0,d0
        rts
S60_POWER_TICK MACRO
        movem.l d0/a0-a1,-(sp)
        lea (s60_power_state+\1,pc),a0
        lea (\2-S60_DATA,a4),a1
        bsr s60_power_due
        tst.w d0
        bne .due\@
        movem.l (sp)+,d0/a0-a1
        S60_TAIL \4
.due\@:
        movem.l (sp)+,d0/a0-a1
        ; Set up continuation before SUBQ so native expiry branches see its CCR.
        move.l (s60_code,pc),-(sp)
        add.l #\3,(sp)
        subq.w #1,(\2-S60_DATA,a4)
        rts
        ENDM
s60_power_tick0: S60_POWER_TICK 0,$1e9c,$3dd2,$3e30
s60_power_tick1: S60_POWER_TICK 4,$1e9e,$ecd8,$ece4
s60_power_tick2: S60_POWER_TICK 8,$1ea4,$ed3e,$ed64
s60_power_tick3: S60_POWER_TICK 12,$1ea6,$ed72,$ed7e
s60_power_tick4: S60_POWER_TICK 16,$1ea8,$ed8c,$eda0

        IFD VERIFY
        IFD POWERS_TEST
; Activate through native routines at an off-phase tick. Use short durations
; only for this diagnostic so all five expiry paths can be checked promptly.
; POWERS_FULL keeps the real durations; POWERS_REFRESH retriggers speed power.
s60_test_powers:
        IFD POWERS_REFRESH
        move.l (s60_ticks,pc),d0
        cmp.l #POWERS_REFRESH,d0
        bne .activation
        S60_CALL $ecae ; unconditional native refresh, including equal values
.activation:
        ENDC
        move.l (s60_ticks,pc),d0
        cmp.l #POWERS_TEST,d0
        bne .done
        IFD POWERS_INVULNERABLE
        move.w #1,($1e90-S60_DATA,a4) ; diagnostic survives all timer deadlines
        ENDC
        S60_CALL $3e32
        S60_CALL $ec62
        S60_CALL $ec86
        S60_CALL $ec9c
        S60_CALL $ecae
        IFND POWERS_FULL
        move.w #2,($1e9c-S60_DATA,a4)
        move.w #2,($1e9e-S60_DATA,a4)
        move.w #2,($1ea4-S60_DATA,a4)
        move.w #2,($1ea6-S60_DATA,a4)
        move.w #2,($1ea8-S60_DATA,a4)
        ENDC
.done:  rts
        ENDC
        ENDC
