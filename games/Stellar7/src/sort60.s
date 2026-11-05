; Native far-to-near selection order, with each view distance evaluated once.
; Object positions and the view do not change during this routine. Keep the
; level-1 type-46 override, strict comparisons and native zero-distance order.
        IFND SORT_INLINE_DISTANCE
SORT_INLINE_DISTANCE = 1 ; native-order checks and measured savings on both CPUs
        ENDC
s60_sort_native: ds.b 14
s60_sort_install:
        move.l (s60_code,pc),a1
        cmp.l #$4e55ffe8,($43de,a1)
        bne s60_bad
        cmp.l #$48e70732,($43e2,a1)
        bne s60_bad
        lea ($43de,a1),a0
        lea (s60_sort_native,pc),a3
        move.l #$4e55ffe8,d0
        move.l #$48e70732,d1
        bsr s60_draw_trampoline
        lea (s60_sort_patches,pc),a0
        jsr (resload_Patch,a2)
        rts
s60_sort_patches:
        PL_START
        IFD VERIFY
        IFD SORT_TWIN
        PL_P $43de,s60_sort_twin
        ELSE
        PL_P $43de,s60_sort
        ENDC
        ELSE
        PL_P $43de,s60_sort
        ENDC
        PL_NOP $43e4,2
        PL_END
s60_sort:
        movem.l d2-d7/a2-a6,-(sp)
        suba.w #1024,sp
        move.l sp,a6
        lea ($3fb2-S60_DATA,a4),a3
        move.w ($43b2-S60_DATA,a4),d7
        cmp.w #256,d7
        bls .valid
        move.l (_resload,pc),a2
        bra s60_bad
.valid: tst.w d7
        beq .done
        moveq #0,d4 ; maximum signed distance, to detect an all-zero list
        move.l ($5d90-S60_DATA,a4),a0
        move.l (2,a0),a2
        addq.l #8,a2
        IFNE SORT_WALK
        lsl.w #2,d7 ; byte count, at most 1024
        move.l a3,a5
        moveq #0,d6
.distance:
        move.l (a5)+,a0
        IFNE SORT_INLINE_DISTANCE
        ; Same signed-long wrapped arithmetic as $4388 / s60_distance.
        ; The sorter already saves D2 and owns A0/A2: no per-actor call frame.
        ; D0/D1 match the callee; ordering/fallback reinitialize scratch A0.
        move.l (8,a0),d0
        sub.l (a2),d0
        bpl .distance_x
        neg.l d0
.distance_x:
        move.l (12,a0),d1
        sub.l (4,a2),d1
        bpl .distance_z
        neg.l d1
.distance_z:
        cmp.l d1,d0
        ble .distance_ordered
        exg d0,d1
.distance_ordered:
        move.l d0,d2
        add.l d0,d0
        add.l d2,d0
        asr.l #3,d0
        add.l d0,d1
        move.l d1,d0
        IFD VERIFY
        IFD SORT_DISTANCE_BAD
        IFND SORT_TEST
        FAIL "SORT_DISTANCE_BAD requires SORT_TEST"
        ENDC
        move.l (s60_ticks,pc),d2
        cmp.l #SORT_TEST,d2
        bne .distance_not_bad
        eor.l #$100,d0 ; corrupt keys only at the synthetic fixture tick
.distance_not_bad:
        ENDC
        ENDC
        ELSE
        pea (8,a0)
        move.l a2,-(sp)
        S60_CALL $4388
        addq.l #8,sp
        ENDC
        cmp.w #1,($46a0-S60_DATA,a4)
        bne .store
        move.l (-4,a5),a0
        cmp.w #46,(2,a0)
        bne .store
        move.l #28672,d0
.store: move.l d0,(a6,d6.w)
        cmp.l d4,d0
        ble .stored
        move.l d0,d4
.stored:
        addq.w #4,d6
        cmp.w d7,d6
        bcs .distance
        tst.l d4
        ble .native
        IFNE SORT_ORDERED
        ; A positive nonincreasing list is unchanged by every strict native
        ; selection scan, including ties. Nonpositive suffixes are not safe.
        move.l a6,a0
        move.w d7,d3
        lsr.w #2,d3
        subq.w #1,d3
        move.l #$7fffffff,d1
.ordered:
        move.l (a0)+,d2 ; keep D0's last gathered distance on both exits
        ble .needs_sort
        cmp.l d1,d2
        bgt .needs_sort
        move.l d2,d1
        dbf d3,.ordered
        move.l a0,a1 ; same final selection pointer as the full cached scan
        cmp.w d7,d7 ; full scan ends equal, with X clear from its index increment
        bra .done
.needs_sort:
        ENDC
        moveq #0,d6
.outer:
        lea (a6,d6.w),a0
        move.w d7,d3
        sub.w d6,d3
        lsr.w #2,d3
        subq.w #1,d3
        moveq #0,d4
.scan:  move.l (a0)+,d1
        cmp.l d4,d1
        ble .next
        move.l d1,d4
        move.l a0,a1 ; one past selection; retained if suffix has no positive key
.next:  dbf d3,.scan
        move.l a1,d5
        sub.l a6,d5
        subq.w #4,d5
        cmp.w d6,d5
        beq .advance
        move.l (a3,d6.w),d2
        move.l (a3,d5.w),(a3,d6.w)
        move.l d2,(a3,d5.w)
        move.l (a6,d6.w),d2
        move.l (a6,d5.w),(a6,d6.w)
        move.l d2,(a6,d5.w)
.advance:
        addq.w #4,d6
        cmp.w d7,d6
        bcs .outer
        ELSE
        moveq #0,d6
.distance:
        cmp.w d7,d6
        bge .sorted_start
        move.w d6,d0
        lsl.w #2,d0
        move.l (a3,d0.w),a0
        pea (8,a0)
        move.l a2,-(sp)
        S60_CALL $4388
        addq.l #8,sp
        move.w d6,d1
        lsl.w #2,d1
        cmp.w #1,($46a0-S60_DATA,a4)
        bne .store
        move.l (a3,d1.w),a0
        cmp.w #46,(2,a0)
        bne .store
        move.l #28672,d0
.store: move.l d0,(a6,d1.w)
        cmp.l d4,d0
        ble .stored
        move.l d0,d4
.stored:
        addq.w #1,d6
        bra .distance
.sorted_start:
        tst.l d4
        ble .native ; original D5 determines its first selection in this case
        moveq #0,d6
.outer: cmp.w d7,d6
        bge .done
        ; Native starts each scan at zero and retains its last selected index.
        ; Once only zero distances remain, that index can precede this suffix.
        moveq #0,d4
        move.w d6,d3
.scan:  cmp.w d7,d3
        bge .selected
        move.w d3,d0
        lsl.w #2,d0
        move.l (a6,d0.w),d1
        cmp.l d4,d1
        ble .next
        move.l d1,d4
        move.w d3,d5
.next:  addq.w #1,d3
        bra .scan
.selected:
        cmp.w d6,d5
        beq .advance
        move.w d6,d0
        move.w d5,d1
        lsl.w #2,d0
        lsl.w #2,d1
        move.l (a3,d0.w),d2
        move.l (a3,d1.w),(a3,d0.w)
        move.l d2,(a3,d1.w)
        move.l (a6,d0.w),d2
        move.l (a6,d1.w),(a6,d0.w)
        move.l d2,(a6,d1.w)
.advance:
        addq.w #1,d6
        bra .outer
        ENDC
.done:  adda.w #1024,sp
        movem.l (sp)+,d2-d7/a2-a6
        rts
.native:
        adda.w #1024,sp
        movem.l (sp)+,d2-d7/a2-a6
        bra s60_sort_native

        IFD VERIFY
        IFD SORT_TWIN
s60_sort_results: dc.b 'O761'
        dc.l 0
        dc.w 0
; Compare every real call against the original routine in the emulated CPU.
; Save input list, run original, save expected list, restore input, run cache.
; Distance evaluation and sorting have no side effects outside this list.
s60_sort_twin:
        movem.l d2-d7/a2-a6,-(sp)
        suba.w #2048,sp
        move.l sp,a6
        lea (1024,a6),a2
        lea ($3fb2-S60_DATA,a4),a3
        moveq #0,d7
        move.w ($43b2-S60_DATA,a4),d7
        cmp.w #256,d7
        bhi .bad
        moveq #0,d6
.save:  cmp.w d7,d6
        bge .original
        move.w d6,d0
        lsl.w #2,d0
        move.l (a3,d0.w),(a6,d0.w)
        addq.w #1,d6
        bra .save
.original:
        bsr s60_sort_native
        moveq #0,d6
.restore:
        cmp.w d7,d6
        bge .cached
        move.w d6,d0
        lsl.w #2,d0
        move.l (a3,d0.w),(a2,d0.w)
        move.l (a6,d0.w),(a3,d0.w)
        addq.w #1,d6
        bra .restore
.cached:
        bsr s60_sort
        moveq #0,d6
.compare:
        cmp.w d7,d6
        bge .done
        move.w d6,d0
        lsl.w #2,d0
        move.l (a3,d0.w),d1
        cmp.l (a2,d0.w),d1
        bne .bad
        addq.w #1,d6
        bra .compare
.done:
        lea (s60_sort_results,pc),a0
        addq.l #1,(4,a0)
        adda.w #2048,sp
        movem.l (sp)+,d2-d7/a2-a6
        rts
.bad:   move.l (_resload,pc),a2
        bra s60_bad
        ENDC
        ENDC
