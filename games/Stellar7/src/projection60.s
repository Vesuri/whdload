; Scalar radius projection: retain native signed multiply/divide, omit zero Y.
; Default within experimental SIM60 after native-twin and speed validation.
s60_radius_native: ds.b 14
s60_radius_install:
        move.l (s60_code,pc),a1
        move.l a1,a0
        adda.l #$16ff6,a0
        lea (s60_radius_native,pc),a3
        move.l #$48e73000,d0
        move.l #$206f000c,d1
        bsr s60_draw_trampoline
        lea (s60_radius_patches,pc),a0
        jsr (resload_Patch,a2)
        rts
s60_radius_patches:
        PL_START
        IFD VERIFY
        IFD RADIUS_TWIN
        PL_P $16ff6,s60_radius_twin
        ELSE
        PL_P $16ff6,s60_radius
        ENDC
        ELSE
        PL_P $16ff6,s60_radius
        ENDC
        PL_NOP $16ffc,2
        PL_END
s60_radius:
        movem.l d2-d3/a1,-(sp)
        move.l (16,sp),a0
        move.w ($5dd2-S60_DATA,a4),d0
        moveq #1,d3
        asl.l d0,d3
        move.l (4,a0),d2
        move.l (a0),d0
        IFNE RADIUS_SMALL
        ; Both factors fit unsigned words, making native $170f6 exact here.
        ; Its wider one-word-factor path drops part of the product; preserve
        ; that behavior through the fallback. The product fits signed-long,
        ; so use $171b8's short arm, retaining native $1707c division.
        cmp.l #128,d3
        bne .wide
        cmp.l #$0000ffff,d0
        bhi .wide
        lsl.l #7,d0
        move.l d2,-(sp)
        move.l d0,-(sp)
        move.l (s60_code,pc),a1
        adda.l #$1707c,a1
        jsr (a1)
        addq.l #8,sp
        bra .result
.wide:
        ENDC
        move.l d3,d1
        move.l (s60_code,pc),a1
        adda.l #$170f6,a1
        jsr (a1)
        move.l d0,-(sp)
        move.l d1,-(sp)
        move.l sp,a0
        move.l d2,d0
        move.l (s60_code,pc),a1
        adda.l #$171b8,a1
        jsr (a1)
        addq.l #8,sp
.result:
        moveq #0,d1
        tst.l d0
        movem.l (sp)+,d2-d3/a1
        rts
        IFD VERIFY
        IFD RADIUS_TWIN
s60_radius_results:
        dc.b 'V762'
        dc.l 0,0
        dc.w 0,0
        ds.l 7 ; first mismatch: radius, denominator, shift, native/fast D0/D1
s60_radius_twin:
        movem.l d2-d7/a1-a6,-(sp)
        move.l (52,sp),a2
        move.l a2,-(sp)
        bsr s60_radius_native
        addq.l #4,sp
        move.l d0,d6
        move.l d1,d7
        move.l a2,-(sp)
        bsr s60_radius
        addq.l #4,sp
        cmp.l d6,d0
        bne .error
        cmp.l d7,d1
        beq .done
.error: lea (s60_radius_results,pc),a0
        tst.l (8,a0)
        bne .count_error
        move.l (a2),(16,a0)
        move.l (4,a2),(20,a0)
        moveq #0,d2
        move.w ($5dd2-S60_DATA,a4),d2
        move.l d2,(24,a0)
        move.l d6,(28,a0)
        move.l d0,(32,a0)
        move.l d7,(36,a0)
        move.l d1,(40,a0)
.count_error:
        addq.l #1,(8,a0)
.done:  lea (s60_radius_results,pc),a0
        addq.l #1,(4,a0)
        move.l d6,d0
        move.l d7,d1
        tst.l d0
        movem.l (sp)+,d2-d7/a1-a6
        rts
        ENDC
        ENDC
