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
        move.l (_custom3,pc),d0
        beq .done
        move.l d7,a1
        add.l a1,a1
        add.l a1,a1
        addq.l #4,a1
        move.l a1,a0
        adda.l #$20000,a0
        cmp.l #$2f073e2f,($2730,a0)
        bne .bad
        cmp.w #$0008,($2734,a0)
        bne .bad
        cmp.l #$4e55fffc,($2746,a0)
        bne .bad
        cmp.l #$48e70300,($274a,a0)
        bne .bad
        lea (fixture_input_patches,pc),a0
        jsr (resload_Patch,a2)
.done:  rts
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

; Native input API fixtures. Inputs are indexed by simulation step, so renderer
; cadence cannot move an input edge. No positions, velocities or RNG are written.
fixture_input_patches:
        PL_START
        PL_P $22730,fixture_key
        PL_P $22746,fixture_joy
        PL_NOP $2274c,2
        PL_END
fixture_joy:
        moveq #0,d0
        cmp.w #100,($1e96-$8000,a4)
        bcs .done
        cmp.w #140,($1e96-$8000,a4)
        bcc .done
        moveq #1,d0
        cmp.w #120,($1e96-$8000,a4)
        bcs .done
        moveq #9,d0
.done:  rts
fixture_key:
        moveq #0,d0
        cmp.w #$40,(4,sp)
        bne .done
        cmp.w #105,($1e96-$8000,a4)
        bcs .done
        cmp.w #135,($1e96-$8000,a4)
        bcc .done
        moveq #1,d0
.done:  rts
