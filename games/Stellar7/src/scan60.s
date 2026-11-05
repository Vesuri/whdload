; Inline the native $85f6 overlap test while scanning the same active list.
; Retain signed long wrap, inclusive boundaries, all link writes and last hit.
; Selected by default in SIM60; SCAN_FAST=0 retains the native baseline.
s60_scan_native: ds.b 14
s60_scan_install:
        move.l (s60_code,pc),a1
        lea ($3a54,a1),a0
        lea (s60_scan_native,pc),a3
        move.l #$4e55fff4,d0
        move.l #$48e70130,d1
        bsr s60_draw_trampoline
        ; The inlined body is tied to this exact native overlap layout.
        move.l a1,a0
        adda.l #$85f6,a0
        cmp.l #$48e70330,(a0)
        bne s60_bad
        cmp.l #$266f0014,(4,a0)
        bne s60_bad
        lea (s60_scan_patches,pc),a0
        jsr (resload_Patch,a2)
        rts
s60_scan_patches:
        PL_START
        IFD VERIFY
        IFD SCAN_TWIN
        PL_P $3a54,s60_scan_twin
        ELSE
        PL_P $3a54,s60_scan
        ENDC
        ELSE
        PL_P $3a54,s60_scan
        ENDC
        PL_NOP $3a5a,2
        PL_END
s60_scan:
        IFNE SCAN_HOIST
        movem.l d1-d7/a2-a3,-(sp)
        move.l (40,sp),a2
        ELSE
        movem.l d1-d3/a2-a3,-(sp)
        move.l (24,sp),a2
        ENDC
        moveq #0,d3
        move.w ($43b2-S60_DATA,a4),d2
        ble .done
        cmp.w #256,d2
        bhi .native
        subq.w #1,d2
        lea ($3fb2-S60_DATA,a4),a3
        IFNE SCAN_HOIST
        ; Only owner links are written in this scan. Query geometry is fixed.
        cmp.w #7,(2,a2)
        bne .query_geometry
        ; Native A0 is the final active-list slot, including excluded actors.
        move.w d2,d0
        lsl.w #2,d0
        lea (a3,d0.w),a0
        bra .flags
.query_geometry:
        move.l (4,a2),d4
        move.l (8,a2),d5
        move.l (12,a2),d6
        move.l (16,a2),d7
        ENDC
.loop:  move.l (a3)+,a0
        cmpa.l a2,a0
        beq .next
        IFEQ SCAN_GEOMETRY_FIRST
        move.b ($54,a0),d0
        cmp.b #$fd,d0
        beq .next
        cmp.b #$fc,d0
        beq .next
        cmp.w #7,(2,a0)
        beq .next
        IFEQ SCAN_HOIST
        cmp.w #7,(2,a2)
        beq .next
        ENDC
        ENDC
        move.l (4,a0),d1
        IFNE SCAN_HOIST
        add.l d4,d1
        ELSE
        add.l (4,a2),d1
        ENDC
        asr.l #1,d1
        IFNE SCAN_HOIST
        move.l d5,d0
        ELSE
        move.l (8,a2),d0
        ENDC
        sub.l (8,a0),d0
        bpl .x_abs
        neg.l d0
.x_abs: cmp.l d1,d0
        bgt .next
        IFNE SCAN_GEOMETRY_FIRST
        move.b ($54,a0),d0
        cmp.b #$fd,d0
        beq .next
        cmp.b #$fc,d0
        beq .next
        cmp.w #7,(2,a0)
        beq .next
        IFEQ SCAN_HOIST
        cmp.w #7,(2,a2)
        beq .next
        ENDC
        ENDC
        IFNE SCAN_HOIST
        move.l d6,d0
        ELSE
        move.l (12,a2),d0
        ENDC
        sub.l (12,a0),d0
        bpl .z_abs
        neg.l d0
.z_abs: cmp.l d1,d0
        bgt .next
        IFNE SCAN_HOIST
        move.l d7,d0
        ELSE
        move.l (16,a2),d0
        ENDC
        sub.l (16,a0),d0
        bpl .y_abs
        neg.l d0
.y_abs: cmp.l d1,d0
        bgt .next
        move.l a2,($66,a0)
        move.l a0,d3
.next:  dbf d2,.loop
        ; Native positive-length scans end with ADDQ to their small loop index,
        ; clearing X. Preserve that as well as MOVE.L result's N/Z/V/C flags.
.positive_done:
        move.l a3,a0
        subq.l #4,a0
.flags: moveq #0,d0
        add.w d0,d0
.done:  move.l d3,d0
        IFNE SCAN_HOIST
        movem.l (sp)+,d1-d7/a2-a3
        ELSE
        movem.l (sp)+,d1-d3/a2-a3
        ENDC
        rts
.native:
        IFNE SCAN_HOIST
        movem.l (sp)+,d1-d7/a2-a3
        ELSE
        movem.l (sp)+,d1-d3/a2-a3
        ENDC
        bra s60_scan_native

        IFD VERIFY
        IFD SCAN_TWIN
s60_scan_results:
        dc.b 'L760'
        dc.l 0,0 ; twin calls, mismatches
        dc.w 0,0 ; synthetic cases, failing synthetic cases
s60_scan_pre: ds.l 256
s60_scan_expected: ds.l 256
; Each call runs original and optimized bodies from identical owner links.
; Snapshot and restoration are separate passes, including duplicate pointers.
s60_scan_links_save:
        lea ($3fb2-S60_DATA,a4),a3
        move.w d7,d2
        ble .done
        subq.w #1,d2
.loop:  move.l (a3)+,a0
        move.l ($66,a0),(a1)+
        dbf d2,.loop
.done:  rts
s60_scan_links_restore:
        lea ($3fb2-S60_DATA,a4),a3
        move.w d7,d2
        ble .done
        subq.w #1,d2
.loop:  move.l (a3)+,a0
        move.l (a1)+,($66,a0)
        dbf d2,.loop
.done:  rts
s60_scan_twin:
        movem.l d1-d7/a1-a6,-(sp)
        move.l (56,sp),a2
        move.w ($43b2-S60_DATA,a4),d7
        cmp.w #256,d7
        ble .size_ok
        move.l (_resload,pc),a2
        bra s60_bad
.size_ok:
        lea (s60_scan_pre,pc),a1
        bsr s60_scan_links_save
        move.l a2,-(sp)
        bsr s60_scan_native
        addq.l #4,sp
        move.l a0,-(sp) ; native final raw list slot
        move.l d0,d6
        lea (s60_scan_expected,pc),a1
        bsr s60_scan_links_save
        lea (s60_scan_pre,pc),a1
        bsr s60_scan_links_restore
        move.l a2,-(sp)
        bsr s60_scan
        addq.l #4,sp
        cmpa.l (sp)+,a0
        beq .a0_ok
        bsr .error
.a0_ok:
        cmp.l d6,d0
        beq .links
        bsr .error
.links: lea ($3fb2-S60_DATA,a4),a3
        lea (s60_scan_expected,pc),a1
        move.w d7,d2
        ble .restore
        subq.w #1,d2
.compare:
        move.l (a3)+,a0
        move.l ($66,a0),d0
        cmp.l (a1)+,d0
        beq .next
        bsr .error
.next:  dbf d2,.compare
.restore:
        lea (s60_scan_expected,pc),a1
        bsr s60_scan_links_restore
        lea (s60_scan_results,pc),a0
        addq.l #1,(4,a0)
        move.l d6,d0
        movem.l (sp)+,d1-d7/a1-a6
        rts
.error: lea (s60_scan_results,pc),a0
        addq.l #1,(8,a0)
        rts
        ENDC
        ENDC
