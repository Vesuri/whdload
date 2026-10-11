        IFD VERIFY
        IFD SORT_TEST
        IFND SORT_TWIN
        FAIL "SORT_TEST requires SORT_TWIN"
        ENDC
s60_sort_actors: ds.b 17*$6e
s60_sort_view: ds.b 6
s60_sort_counts: dc.w 0,1,16,256
s60_test_sort:
        move.l (s60_ticks,pc),d0
        cmp.l #SORT_TEST,d0
        bne .done
        move.w (s60_sort_results+8,pc),d0
        bne .done
        movem.l d2-d7/a2-a6,-(sp)
        move.l ($5d90-S60_DATA,a4),-(sp)
        move.w ($46a0-S60_DATA,a4),-(sp)
        move.w ($43b2-S60_DATA,a4),-(sp)
        suba.w #1024,sp
        move.l sp,a6
        move.l a6,a1
        lea ($3fb2-S60_DATA,a4),a0
        move.w #255,d0
.save:  move.l (a0)+,(a1)+
        dbf d0,.save
        lea (s60_sort_view,pc),a0
        move.l a0,($5d90-S60_DATA,a4)
        lea (s60_sort_actors+16*$6e,pc),a1
        move.l a1,(2,a0)
        moveq #0,d4
.case:  lea (s60_sort_actors,pc),a0
        move.w #17*$6e/2-1,d0
.clear: clr.w (a0)+
        dbf d0,.clear
        clr.w ($46a0-S60_DATA,a4)
        move.w d4,d7
        and.w #15,d7
        cmp.w #7,d7
        bne .actors_start
        move.w #1,($46a0-S60_DATA,a4)
.actors_start:
        lea (s60_sort_actors,pc),a2
        moveq #0,d6
.actor: move.w #1,(2,a2)
        move.w d6,d0
        addq.w #1,d0
        mulu #100,d0
        cmp.w #8,d7
        bcc .extra
        tst.w d7
        beq .store
        cmp.w #1,d7
        bne .ties
        move.l #1700,d1
        sub.l d0,d1
        move.l d1,d0
        bra .store
.ties:  cmp.w #2,d7
        bne .zeros
        moveq #100,d0
        bra .store
.zeros: cmp.w #3,d7
        bne .mixed
        moveq #0,d0
        bra .store
.mixed: cmp.w #4,d7
        bne .min
        btst #0,d6
        bne .store
        moveq #0,d0
        bra .store
.min:   cmp.w #5,d7
        bne .max
        move.l #$80000000,d0
        bra .store
.max:   cmp.w #6,d7
        bne .override
        move.l #$7fffffff,d0
        move.l d0,(12,a2)
        bra .store
.override:
        btst #0,d6
        bne .store
        move.w #46,(2,a2)
        bra .store
.extra:
        move.l #1700,d1
        sub.l d0,d1
        move.l d1,d0 ; descending positive default
        cmp.w #8,d7
        bne .zero_tail
        move.w d6,d0
        lsr.w #1,d0
        mulu #100,d0
        move.l #1600,d1
        sub.l d0,d1
        move.l d1,d0
        bra .store
.zero_tail:
        cmp.w #9,d7
        bne .negative_tail
        cmp.w #15,d6
        bne .store
        moveq #0,d0
        bra .store
.negative_tail:
        cmp.w #10,d7
        bne .last_inversion
        cmp.w #15,d6
        bne .store
        move.l #$80000000,d0
        bra .store
.last_inversion:
        cmp.w #11,d7
        bne .first_inversion
        cmp.w #15,d6
        bne .store
        move.l #300,d0
        bra .store
.first_inversion:
        cmp.w #12,d7
        bne .single_positive
        tst.w d6
        bne .store
        move.l #1400,d0
        bra .store
.single_positive:
        cmp.w #13,d7
        bne .ties_zero
        tst.w d6
        beq .store
        moveq #0,d0
        bra .store
.ties_zero:
        cmp.w #14,d7
        bne .largest
        moveq #100,d0
        cmp.w #8,d6
        bcs .store
        moveq #0,d0
        bra .store
.largest:
        move.l #$7fffffff,d0
        sub.l d6,d0
.store: move.l d0,(8,a2)
        adda.w #$6e,a2
        addq.w #1,d6
        cmp.w #16,d6
        bne .actor
        lea ($3fb2-S60_DATA,a4),a1
        move.w #255,d6
        moveq #0,d0
.list:  move.w d0,d1
        and.w #15,d1
        mulu #$6e,d1
        lea (s60_sort_actors,pc),a0
        adda.w d1,a0
        move.l a0,(a1)+
        addq.w #1,d0
        dbf d6,.list
        move.w d4,d0
        lsr.w #4,d0
        add.w d0,d0
        lea (s60_sort_counts,pc),a0
        move.w (a0,d0.w),($43b2-S60_DATA,a4)
        moveq #0,d5 ; defined native fallback selection when every key <= 0
        bsr s60_sort_twin
        lea (s60_sort_results,pc),a0
        addq.w #1,(8,a0)
        addq.w #1,d4
        cmp.w #64,d4
        bne .case
        move.l a6,a0
        lea ($3fb2-S60_DATA,a4),a1
        move.w #255,d0
.restore:
        move.l (a0)+,(a1)+
        dbf d0,.restore
        adda.w #1024,sp
        move.w (sp)+,($43b2-S60_DATA,a4)
        move.w (sp)+,($46a0-S60_DATA,a4)
        move.l (sp)+,($5d90-S60_DATA,a4)
        movem.l (sp)+,d2-d7/a2-a6
.done:  rts
        ENDC
        ENDC
