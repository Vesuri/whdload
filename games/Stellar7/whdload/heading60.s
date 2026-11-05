; Guarded native heading-table fast path. Axis/equality, wide magnitudes and
; signed extremes retain the original routine, including its scratch results.
s60_heading_native: ds.b 14
s60_heading_table: dc.l 0
s60_heading_install:
        move.l (s60_code,pc),a1
        move.l a1,a0
        adda.l #$893a,a0
        lea (s60_heading_native,pc),a3
        move.l #$4e55fffc,d0
        move.l #$48e70f00,d1
        bsr s60_draw_trampoline
        move.l a1,a0
        adda.l #$89a4,a0
        cmp.w #$41f9,(a0)
        bne s60_bad
        lea (s60_heading_table,pc),a3
        move.l (2,a0),(a3)
        lea (s60_heading_patches,pc),a0
        jsr (resload_Patch,a2)
        rts
s60_heading_patches:
        PL_START
        PL_P $893a,s60_heading
        PL_NOP $8940,2
        PL_END
s60_heading:
        ; Guards leave D0/D1/A0/A1 untouched, so fallback needs only D2/D3.
        ; Read original signs from the arguments instead of keeping flag regs.
        movem.l d2-d3,-(sp)
        move.l (12,sp),d2
        bpl .x_abs
        neg.l d2
.x_abs: move.l (16,sp),d3
        bpl .z_abs
        neg.l d3
.z_abs: tst.l d2
        beq .native
        tst.l d3
        beq .native
        cmp.l d3,d2
        beq .native
        bcs .z_major
        cmp.l #65535,d2
        bhi .native ; also catches wrapped abs(MIN_LONG)
        move.l d3,d0
        lsl.l #8,d0
        add.l d0,d0
        divu d2,d0 ; min/max < 1: quotient <= 511, no overflow
        moveq #0,d1
        move.w d0,d1
        add.l d1,d1
        move.l (s60_heading_table,pc),a0
        adda.l d1,a0
        moveq #0,d0
        move.w (a0),d0
        bra .signs
.z_major:
        cmp.l #65535,d3
        bhi .native
        move.l d2,d0
        lsl.l #8,d0
        add.l d0,d0
        divu d3,d0
        moveq #0,d1
        move.w d0,d1
        add.l d1,d1
        move.l (s60_heading_table,pc),a0
        move.l a0,a1
        adda.l d1,a1
        move.w #1024,d1 ; table index left its upper word zero
        sub.w (a1),d1
        move.l d1,d0
.signs: tst.b (12,sp)
        bpl .z_sign
        move.w #2048,d2
        sub.w d0,d2
        move.w d2,d0
.z_sign:
        tst.b (16,sp)
        bpl .angle
        move.w #4096,d2
        sub.w d0,d2
        move.w d2,d0
.angle: sub.w #1024,d0
        movem.l (sp)+,d2-d3
        asl.w #4,d0 ; same final NZVC/X and low word as native
        rts
.native:
        movem.l (sp)+,d2-d3
        bra s60_heading_native
