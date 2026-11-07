; Keep native flying-AI decisions at one call per N active ticks. Capture
; its height/bank increments, then distribute those increments with integers.
; Record: 4 phase, 6 height delta, 62 height remainder, 64 bank delta,
; 66 bank remainder. Native decisions/side effects execute only once.
s60_flying_install:
        move.l (s60_code,pc),a0
        adda.l #$f192,a0
        cmp.l #$4e55fffc,(a0)
        bne s60_bad
        cmp.l #$48e72110,(4,a0)
        bne s60_bad
        rts
s60_flying_ai:
        movem.l d2-d4/a2-a3/a6,-(sp)
        bsr s60_motion_record
        tst.w (4,a6)
        bne .integrate
        move.w #S60_LEGACY_DIV,(4,a6)
        ; The starting height and bank stay on the stack: native library stubs
        ; (e.g. $876, reached when the flyer fires and starts a sound) load
        ; arguments into D2-D4 without restoring them.
        move.l ($10,a3),-(sp)
        move.w ($16,a3),-(sp)
        move.l a3,-(sp)
        S60_CALL $f192
        addq.l #4,sp
        move.w (sp)+,d3
        move.l (sp)+,d2
        move.l ($10,a3),d0
        sub.l d2,d0
        move.w d0,(6,a6)
        move.l d2,($10,a3)
        move.w ($16,a3),d0
        sub.w d3,d0
        move.w d0,(64,a6)
        move.w d3,($16,a3)
.integrate:
        move.w (6,a6),d0
        ext.l d0
        move.w (62,a6),d1
        ext.l d1
        add.l d1,d0
        divs #S60_LEGACY_DIV,d0
        move.w d0,d1
        ext.l d1
        add.l d1,($10,a3)
        swap d0
        move.w d0,(62,a6)
        move.w (64,a6),d0
        ext.l d0
        move.w (66,a6),d1
        ext.l d1
        add.l d1,d0
        divs #S60_LEGACY_DIV,d0
        add.w d0,($16,a3)
        swap d0
        move.w d0,(66,a6)
        subq.w #1,(4,a6)
        movem.l (sp)+,d2-d4/a2-a3/a6
        rts
