; Funeral draw-and-step calls retain one authoritative pass per 60 ms.
; Extra pictures replay the pre-step records with fractional horizontal motion.
; Native respawns, random state and salute animation advance only once.
funeral_draw:
        movem.l d0-d7/a0-a6,-(sp)
        bsr.w funeral_rate
        mulu.w #3,d0
        add.w funeral_fraction(pc),d0
        divu.w #50,d0
        swap d0
        lea funeral_fraction(pc),a0
        move.w d0,(a0)
        swap d0
        move.w d0,d6
        move.l MODAL_FIELD(a4),d7
        lea FUNERAL_STATE(a4),a0
        lea funeral_before(pc),a1
        bsr.w funeral_copy
        move.w #1,MODAL_COUNTDOWN(a4)
        bsr.w funeral_native
        lea FUNERAL_STATE(a4),a0
        lea funeral_after(pc),a1
        bsr.w funeral_copy
        move.l BAR_RNG(a4),-(sp)
        move.w MODAL_COUNTDOWN(a4),-(sp)
        move.l d7,d5
funeral_wait:
        move.l MODAL_FIELD(a4),d4
        sub.l d7,d4
        cmp.w d6,d4
        bhs.s .done
        move.l MODAL_FIELD(a4),d0
        cmp.l d5,d0
        beq.s funeral_wait
        move.l d0,d5
        lea funeral_before(pc),a0
        lea FUNERAL_STATE(a4),a1
        bsr.w funeral_copy
        ; Seven live salute elements move (-6,-6) per native pass.
        ; Borrow only their displayed positions; restore native state below.
        lea FUNERAL_STATE+20(a4),a2
        moveq #6,d3
        moveq #-6,d0
        muls.w d4,d0
        divs.w d6,d0
.salute:
        tst.w (a2)
        beq.s .next_salute
        add.w d0,(a2)
        add.w d0,2(a2)
.next_salute:
        addq.l #4,a2
        dbra d3,.salute
        move.w BAR_MOVING_COUNT(a4),d3
        cmpi.w #64,d3
        bhi.s .done
        lea BAR_MOVING(a4),a2
        bra.s .test
.sample:
        move.w 4(a2),d0
        muls.w d4,d0
        divs.w d6,d0
        add.w d0,(a2)
        addq.l #8,a2
.test:
        dbra d3,.sample
        move.w #1,MODAL_COUNTDOWN(a4)
        bsr.w funeral_native
        bra.s funeral_wait
.done:
        lea funeral_after(pc),a0
        lea FUNERAL_STATE(a4),a1
        bsr.w funeral_copy
        move.w (sp)+,MODAL_COUNTDOWN(a4)
        move.l (sp)+,BAR_RNG(a4)
        movem.l (sp)+,d0-d7/a0-a6
        rts
funeral_copy:
        move.w #FUNERAL_BYTES/4-1,d0
.loop:  move.l (a0)+,(a1)+
        dbra d0,.loop
        rts
funeral_fraction: dc.w 0
funeral_before: ds.b FUNERAL_BYTES
funeral_after: ds.b FUNERAL_BYTES
