; Native knockback overrides input for one legacy movement interval, then
; halves (toward zero, with the native -32768 wrap). Movement itself uses S60_RATE.
; State: ticks left, current applied speed, last published pending impulse.
s60_knock_state: dc.w 0,0,0
s60_knock_reset:
        lea (s60_knock_state,pc),a0
        clr.l (a0)
        clr.w (4,a0)
        rts
s60_knock_install:
        move.l (s60_code,pc),a1
        cmp.l #$33e80040,($378c,a1)
        bne s60_bad
        cmp.w #$3039,($2b0c,a1)
        bne s60_bad
        cmp.w #$6724,($2b12,a1)
        bne s60_bad
        lea (s60_knock_patches,pc),a0
        jsr (resload_Patch,a2)
        rts
s60_knock_patches:
        PL_START
        PL_PSS $378c,s60_knock_collision,2
        PL_END
s60_knock_collision:
        move.w ($40,a0),($026c-S60_DATA,a4)
        ; Every impact restarts the interval, including an identical impulse.
        movem.l d0/a0,-(sp)
        move.w (s60_running,pc),d0
        beq .done
        lea (s60_knock_state,pc),a0
        clr.w (a0)
.done:  movem.l (sp)+,d0/a0
        rts
s60_knock_update:
        lea (s60_knock_state,pc),a1
        move.w ($026c-S60_DATA,a4),d0
        cmp.w (4,a1),d0
        beq .phase
        clr.w (a1) ; recognize external initialization/reset too
.phase: tst.w (a1)
        bne .apply
        move.w d0,(4,a1)
        tst.w d0
        beq .done
        move.w #S60_LEGACY_DIV,(a1)
        move.w d0,(2,a1)
        bgt .positive
        neg.w d0
        asr.w #1,d0
        neg.w d0
        bra .publish
.positive:
        asr.w #1,d0
.publish:
        move.w d0,($026c-S60_DATA,a4)
        move.w d0,(4,a1)
.apply:
        move.l ($43c0-S60_DATA,a4),a0
        move.w (2,a1),($40,a0)
        subq.w #1,(a1)
.done:  rts
