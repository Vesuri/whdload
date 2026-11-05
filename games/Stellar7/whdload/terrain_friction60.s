; Native terrain friction is an immediate discrete velocity quartering, followed
; by at most one quartering per N simulation ticks. Its contact flag also
; applies outside level five, so this clock is independent of terrain damage.
s60_friction_install:
        move.l (s60_code,pc),a1
        move.l a1,a0
        adda.l #$100a8,a0
        cmp.w #$4a79,(a0)
        bne s60_bad
        move.l (2,a0),d0
        cmp.l ($36e8,a1),d0 ; same relocated contact flag as native producer
        bne s60_bad
        cmp.w #$6726,(6,a0)
        bne s60_bad
        lea (s60_friction_patches,pc),a0
        jsr (resload_Patch,a2)
        rts
s60_friction_patches:
        PL_START
        PL_PS $100a8,s60_friction_due
        PL_END
s60_friction_state:
        dc.w 0,0 ; valid, padding
        dc.l 0 ; last tick that applied the native damping block
s60_friction_reset:
        lea (s60_friction_state,pc),a0
        clr.l (a0)
        clr.l (4,a0)
        rts
s60_friction_due:
        movem.l d0-d1/a0,-(sp)
        move.w sr,d1 ; preserve native TST's unchanged X flag
        IFD VERIFY
        IFD FRICTION_OLD
        bra .native
        ENDC
        ENDC
        move.w (s60_running,pc),d0
        beq .native
        move.w (s60_rendering,pc),d0
        bne .skip
        tst.w ($46d8-S60_DATA,a4)
        beq .native
        lea (s60_friction_state,pc),a0
        tst.w (a0)
        beq .accept
        move.l (s60_ticks,pc),d0
        sub.l (4,a0),d0
        cmp.l #S60_LEGACY_DIV,d0
        bcs .skip
.accept:
        move.w #1,(a0)
        move.l (s60_ticks,pc),(4,a0)
.native:
        move.w d1,ccr
        movem.l (sp)+,d0-d1/a0
        tst.w ($46d8-S60_DATA,a4)
        rts
.skip:
        move.w d1,ccr
        movem.l (sp)+,d0-d1/a0
        cmp.w d0,d0 ; native BEQ skips damping; CMP leaves X unchanged
        rts
