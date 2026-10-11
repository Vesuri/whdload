; Per-actor effect clocks: last explosion tick at 128, mesh animation at 132,
; oscillator at 140; validity bits 0/1/2 in byte 136. First callback is
; immediate, then >=12 ticks.
; Initializers clear validity even when restarting the same callback/counter.
s60_animation_start:
        movem.l d0-d1/a0/a6,-(sp)
        move.w (s60_running,pc),d0
        beq .done
        bsr s60_motion_record
        bclr #1,(136,a6)
.done:  movem.l (sp)+,d0-d1/a0/a6
        move.l (s60_code,pc),a0
        adda.l #$42b0,a0
        move.l a0,($1a,a3)
        rts
s60_explosion_start:
        movem.l d0-d1/a0/a3/a6,-(sp)
        move.w (s60_running,pc),d0
        beq .done
        move.l a2,a3
        bsr s60_motion_record
        bclr #0,(136,a6)
.done:  movem.l (sp)+,d0-d1/a0/a3/a6
        move.l (s60_code,pc),a0
        adda.l #$397e,a0
        move.l a0,($1a,a2)
        rts
; Called with D0 clock index after the wrapper saves original D0. Its actor
; argument is twelve bytes above our return address, before these saved regs.
s60_animation_due:
        movem.l d1-d2/a0/a3/a6,-(sp)
        move.l (32,sp),a3
        cmpa.w #0,a3
        beq .skip
        move.w d0,d2
        bsr s60_motion_record
        btst d2,(136,a6)
        sne d1
        bset d2,(136,a6)
        lea (140,a6),a0
        cmp.w #2,d2
        beq .clock
        lsl.w #2,d2
        lea (128,a6),a0
        adda.w d2,a0
.clock:
        move.l (s60_ticks,pc),d0
        tst.b d1
        beq .due
        move.l d0,d1
        sub.l (a0),d1
        cmp.l #S60_LEGACY_DIV,d1
        bcs .skip
.due:   move.l d0,(a0)
        moveq #1,d0
        bra .done
.skip:  moveq #0,d0
.done:  movem.l (sp)+,d1-d2/a0/a3/a6
        tst.w d0
        rts

; The two special actors can be reused by $922e. Replaying the complete pair
; resets their frame/direction and invalidates only the oscillator's clock.
s60_oscillator_start:
        movem.l d0-d1/a0/a3/a6,-(sp)
        move.w (s60_running,pc),d0
        beq .done
        move.l a2,a3
        bsr s60_motion_record
        bclr #2,(136,a6)
.done:  movem.l (sp)+,d0-d1/a0/a3/a6
        move.b #1,($59,a2)
        move.b #2,($56,a2)
        rts
