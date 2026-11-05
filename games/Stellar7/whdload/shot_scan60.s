; Native $34d6 first projectile overlap, excluding the projectile's owner.
; Unlike $3a54, self is not excluded, first hit wins, and no links are written.
s60_shot_native: ds.b 14
s60_shot_install:
        move.l (s60_code,pc),a1
        lea ($34d6,a1),a0
        lea (s60_shot_native,pc),a3
        move.l #$48e70130,d0
        move.l #$266f0010,d1
        bsr s60_draw_trampoline
        move.l a1,a0
        adda.l #$85f6,a0
        cmp.l #$48e70330,(a0)
        bne s60_bad
        cmp.l #$266f0014,(4,a0)
        bne s60_bad
        lea (s60_shot_patches,pc),a0
        jsr (resload_Patch,a2)
        rts
s60_shot_patches:
        PL_START
        PL_P $34d6,s60_shot_scan
        PL_NOP $34dc,2
        PL_END
s60_shot_scan:
        movem.l d2-d7/a1-a3,-(sp)
        move.l (40,sp),a3
        move.w ($43b2-S60_DATA,a4),d2
        ble .empty
        cmp.w #256,d2
        bhi .native
        subq.w #1,d2
        lea ($3fb2-S60_DATA,a4),a1
        cmp.w #7,(2,a3)
        bne .geometry
        ; Every native predicate rejects a type-7 query. A0 still ends at
        ; the last list entry, not at the actor stored in that entry.
        move.w d2,d0
        lsl.w #2,d0
        lea (a1,d0.w),a0
        bra .miss
.geometry:
        move.l (4,a3),d4
        move.l (8,a3),d5
        move.l (12,a3),d6
        move.l (16,a3),d7
.loop:  move.l a1,a0
        move.l (a1)+,a2
        IFEQ SCAN_GEOMETRY_FIRST
        move.b ($54,a2),d0
        cmp.b #$fc,d0
        beq .next
        cmp.b #$fd,d0
        beq .next
        cmp.w #7,(2,a2)
        beq .next
        ENDC
        move.l (4,a2),d3
        add.l d4,d3
        asr.l #1,d3
        ; Same subtraction direction and signed wrapping as native $85f6.
        move.l (8,a2),d0
        sub.l d5,d0
        bpl .x_abs
        neg.l d0
.x_abs: cmp.l d3,d0
        bgt .next
        IFNE SCAN_GEOMETRY_FIRST
        move.b ($54,a2),d0
        cmp.b #$fc,d0
        beq .next
        cmp.b #$fd,d0
        beq .next
        cmp.w #7,(2,a2)
        beq .next
        ENDC
        move.l (12,a2),d0
        sub.l d6,d0
        bpl .z_abs
        neg.l d0
.z_abs: cmp.l d3,d0
        bgt .next
        move.l (16,a2),d0
        sub.l d7,d0
        bpl .y_abs
        neg.l d0
.y_abs: cmp.l d3,d0
        bgt .next
        move.l ($6a,a3),a0
        cmpa.l a2,a0
        beq .next
        move.l a2,d0
        bra .done
.next:  dbf d2,.loop
.miss:  moveq #0,d0
        add.w d0,d0 ; native positive-length loop leaves X clear
.empty: moveq #0,d0
.done:  movem.l (sp)+,d2-d7/a1-a3
        rts
.native:
        movem.l (sp)+,d2-d7/a1-a3
        bra s60_shot_native
