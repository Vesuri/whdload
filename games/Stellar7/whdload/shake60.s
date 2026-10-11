; Damage shake uses native units and its own byte RNG at data $3558.
; First post-impact sample is immediate; subsequent samples require 12 ticks.
; Reset/menu callers still enter untouched $40ae directly with counter 1.
s60_shake_state: dc.l 0
        dc.w 0,0 ; last native counter, validity
s60_shake_install:
        move.l (s60_code,pc),a1
        cmp.l #$33fc0008,($3ce6,a1)
        bne s60_bad
        cmp.l #$33fc0008,($3d14,a1)
        bne s60_bad
        cmp.w #$2007,($3cee,a1)
        bne s60_bad
        cmp.w #$2007,($3d1c,a1)
        bne s60_bad
        move.l ($3cea,a1),d0
        cmp.l ($3d18,a1),d0
        bne s60_bad
        cmp.l ($40b0,a1),d0
        bne s60_bad
        lea (s60_shake_patches,pc),a0
        jsr (resload_Patch,a2)
        rts
s60_shake_patches:
        PL_START
        PL_PSS $3ce6,s60_shake_hit,2
        PL_PSS $3d14,s60_shake_hit,2
        PL_END
s60_shake_reset:
        lea (s60_shake_state,pc),a0
        clr.l (a0)+
        clr.l (a0)
        rts
s60_shake_hit:
        move.l a0,-(sp)
        bsr s60_shake_reset
        move.l (sp)+,a0
        move.w #8,($026a-S60_DATA,a4)
        rts
s60_shake_update:
        move.w (s60_rendering,pc),d0
        bne .done
        movem.l d2/a2,-(sp)
        lea (s60_shake_state,pc),a2
        move.w ($026a-S60_DATA,a4),d0
        beq .reset
        tst.w (6,a2)
        beq .due
        cmp.w (4,a2),d0
        bne .due ; a reset/external write must not inherit stale timing
        move.l (s60_ticks,pc),d0
        sub.l (a2),d0
        cmp.l #S60_LEGACY_DIV,d0
        bcs .return
.due:   move.l (s60_ticks,pc),d2
        S60_CALL $40ae
        move.w ($026a-S60_DATA,a4),d0
        beq .reset
        move.l d2,(a2)
        move.w d0,(4,a2)
        move.w #1,(6,a2)
        bra .return
.reset: bsr s60_shake_reset
.return:
        movem.l (sp)+,d2/a2
.done:  rts
