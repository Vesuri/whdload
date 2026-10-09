; VERIFY and CUSTOM5 only: follow the native Escape paths through the intro,
; then return the Begin selection at the main menu's own polling call.
; No gameplay state, timing, RNG or rendering changes.
fixture_install:
        move.l d7,a1
        add.l a1,a1
        add.l a1,a1
        addq.l #4,a1
        ; Fail closed on any unsupported executable layout.
        cmp.l #$4eba64ca,($4582,a1)
        bne .bad
        cmp.w #$2e00,($4586,a1)
        bne .bad
        move.l a1,a0
        adda.l #$10000,a0
        cmp.l #$4eba5684,($b1f4-$10000,a0)
        bne .bad
        cmp.w #$7245,($b1f8-$10000,a0)
        bne .bad
        cmp.l #$4eba4fb4,($b8c4-$10000,a0)
        bne .bad
        cmp.w #$7245,($b8c8-$10000,a0)
        bne .bad
        lea (fixture_patches,pc),a0
        jsr (resload_Patch,a2)
        rts
.bad:
        pea (TDREASON_WRONGVER).w
        jmp (resload_Abort,a2)
fixture_patches:
        PL_START
        PL_PS $4582,fixture_begin
        PL_PS $b1f4,fixture_escape
        PL_PS $b8c4,fixture_escape
        PL_END
fixture_begin:
        moveq #1,d0
        move.l d0,d7
        rts
fixture_escape:
        moveq #$45,d0
        moveq #$45,d1
        rts
