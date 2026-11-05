; Native target-reticle cache: refresh on every eighth legacy update, even
; when that update is not presented. Rendering only reads the cached flag.
        IFNE RETICLE_CLOCK
        IFD VERIFY
        IFD RETICLE_TEST
s60_reticle_original: ds.b 8
        ENDC
        ENDC
s60_reticle_install:
        move.l (s60_code,pc),a1
        move.l a1,a0
        adda.l #$bd02,a0
        cmp.l #$7007c079,(a0)
        bne s60_bad
        cmp.l #$660a4eba,(8,a0)
        bne s60_bad
        cmp.l #$3c4613c0,(12,a0)
        bne s60_bad
        move.l ($2af8,a1),d0
        add.l #$1e96-$1e53,d0
        cmp.l (4,a0),d0
        bne s60_bad
        add.l #$46e0-$1e96,d0
        cmp.l (16,a0),d0
        bne s60_bad
        IFD VERIFY
        IFD RETICLE_TEST
        lea (s60_reticle_original,pc),a3
        move.l (a0),(a3)
        move.l (4,a0),(4,a3)
        ENDC
        ENDC
        lea (s60_reticle_patches,pc),a0
        jsr (resload_Patch,a2)
        rts
s60_reticle_patches:
        PL_START
        PL_P $bd02,s60_reticle_draw
        PL_NOP $bd08,2
        PL_END
s60_reticle_draw:
        move.w (s60_running,pc),d0
        IFD VERIFY
        IFD RETICLE_BAD_RENDER
        ; Negative control: the native-reference fixture must catch this.
        ELSE
        bne .draw
        ENDC
        ELSE
        bne .draw
        ENDC
        bsr s60_reticle_sample ; inactive callers keep the native gate
.draw:  S60_TAIL $bd16
s60_reticle_sample:
        moveq #7,d0
        and.w ($1e96-S60_DATA,a4),d0
        bne .done
        S60_CALL $f954 ; unchanged native target test, no RNG use
        move.b d0,($46e0-S60_DATA,a4)
.done:  rts
s60_reticle_update:
        movem.l d0-d1/a0-a1,-(sp)
        move.w (s60_running,pc),d0
        beq .done
        move.w (s60_rendering,pc),d0
        bne .done
        move.w (s60_logic,pc),d0
        beq .done
        bsr s60_reticle_sample
.done:  movem.l (sp)+,d0-d1/a0-a1
        rts
        ENDC
