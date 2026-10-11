; Straight, flat motion: cache the native vector's quotient/remainder and
; integrate it directly. Called after the wrapper has taken every backup.
        IFNE MOVE_LINEAR
        IFEQ FLAT_PITCH
        FAIL "MOVE_LINEAR requires FLAT_PITCH=1"
        ENDC
s60_linear_cache: ds.b 16*16 ; yaw:speed key, packed DIVS X/Z, reserved
s60_linear_move:
        cmp.w #7,(2,a3)
        beq .fallback
        tst.w (20,a3)
        bne .fallback
        move.l (52,a3),d0
        or.l (56,a3),d0
        or.l (60,a3),d0
        bne .fallback ; all angular and linear velocities must be zero
        move.l (8,a6),d0
        or.w (12,a6),d0
        or.w (18,a6),d0
        tst.l d0 ; OR.W alone does not test the upper pitch-remainder word
        bne .fallback ; no angular or vertical fractional displacement
        move.w (14,a6),d0
        add.w #11,d0
        cmp.w #22,d0
        bhi .fallback
        move.w (16,a6),d0
        add.w #11,d0
        cmp.w #22,d0
        bhi .fallback ; malformed/out-of-range fractions retain ordinary DIVS
        moveq #0,d1
        move.w (24,a3),d1 ; yaw, not bank
        IFNE LINEAR_ACTOR_HASH
        move.l a3,d0
        ELSE
        move.w d1,d0
        ENDC
        swap d1
        move.w ($40,a3),d1
        beq .fallback ; zero key is reserved, and idle motion is already cheap
        IFNE LINEAR_ACTOR_HASH
        lsr.l #4,d0 ; selection only; the full yaw:speed key still validates reuse
        ELSE
        rol.w #4,d0
        ENDC
        and.w #15,d0
        lsl.w #4,d0
        lea (s60_linear_cache,pc),a5
        adda.w d0,a5
        cmp.l (a5),d1
        beq .integrate
        movem.l d1/a5,-(sp)
        move.l a3,-(sp)
        bsr s60_move_native
        addq.l #4,sp
        movem.l (sp)+,d1/a5
        move.l (8,a3),d0
        sub.l (32,a6),d0
        move.l (12,a3),d2
        sub.l (36,a6),d2
        move.l (32,a6),(8,a3)
        move.l (36,a6),(12,a3)
        ; Conservative bound also makes all subsequent quotient corrections
        ; fit a signed word. Publish the key only after both vectors pass.
        cmp.l #-32768,d0
        blt .fallback
        cmp.l #32768,d0
        bgt .fallback
        cmp.l #-32768,d2
        blt .fallback
        cmp.l #32768,d2
        bgt .fallback
        divs #12,d0
        move.l d0,(4,a5)
        divs #12,d2
        move.l d2,(8,a5)
        move.l d1,(a5)
.integrate:
        move.l (4,a5),d0
        move.w (14,a6),d1
        bsr s60_linear_divide
        move.w d0,(14,a6)
        ext.l d2
        move.l d2,(20,a6)
        add.l d2,(8,a3)
        move.l (8,a5),d0
        move.w (16,a6),d1
        bsr s60_linear_divide
        move.w d0,(16,a6)
        ext.l d2
        move.l d2,(24,a6)
        add.l d2,(12,a3)
        clr.l (28,a6)
        moveq #1,d0
        rts
.fallback:
        moveq #0,d0
        rts
; D0 = packed native DIVS remainder:quotient; D1 = old remainder (-11..11).
; Return D2.W quotient and D0.W remainder for truncation toward zero.
s60_linear_divide:
        move.w d0,d2
        swap d0
        add.w d1,d0
        cmp.w #12,d0
        bge .increment
        cmp.w #-12,d0
        ble .decrement
        tst.w d2
        beq .done
        bmi .negative
        tst.w d0
        bpl .done
.decrement:
        IFD VERIFY
        IFD LINEAR_BAD_CARRY
        nop ; negative control: omit the signed quotient correction
        ELSE
        subq.w #1,d2
        ENDC
        ELSE
        subq.w #1,d2
        ENDC
        add.w #12,d0
        rts
.negative:
        tst.w d0
        ble .done
.increment:
        addq.w #1,d2
        sub.w #12,d0
.done:  rts
        ENDC
