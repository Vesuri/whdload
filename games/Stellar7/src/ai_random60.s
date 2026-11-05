; The native flying-AI state-3 fallback reads -1(A5) without initializing it.
; Rendering can change that stack residue. Sample the game's RNG only when
; this fallback needs its random byte; preserve the original path outside SIM60.
s60_ai_random_install:
        move.l (s60_code,pc),a1
        move.l a1,a0
        adda.l #$f29e,a0
        cmp.l #$102dffff,(a0)
        bne s60_bad
        cmp.w #$7202,(4,a0)
        bne s60_bad
        lea (s60_ai_random_patches,pc),a0
        jsr (resload_Patch,a2)
        rts
s60_ai_random_patches:
        PL_START
        PL_PS $f29e,s60_ai_random_byte
        PL_END
s60_ai_random_byte:
        move.w (s60_running,pc),d1
        beq .native
        movem.l a0-a1,-(sp)
        S60_CALL $116ec
        movem.l (sp)+,a0-a1
        and.l #255,d0
        moveq #2,d1
        rts
.native:
        move.b (-1,a5),d0
        moveq #2,d1
        rts
