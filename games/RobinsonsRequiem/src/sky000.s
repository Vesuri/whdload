; The ECS game's sky copy for the 68000 (RobinsonSRequiemEcs.asm includes it; docs/internals.md,
; "ECS improvements").
;
; START's 3D view copies the sky's rows into the chunky view with move.w (a0)+,(a1)+ and
; dbf, 22 cycles a word: hunk 1 +$c8b8-$c8e7, which becomes jsr _skyrows and a branch to
; +$c8e8. _skyrows copies the same words to the same places by longwords, jumping into an
; unrolled run of move.l (a0)+,(a1)+, 10 cycles a word. tools/rr_skycheck.py ecs checks it
; against START's loop under Unicorn.
;
; In, START's registers at +$c8b8: d0.w the first segment's words - 1 (negative: none),
; d1.w the sky's row length in bytes, d5.w the view's modulo, d7.w rows - 1, a0 = a4 the
; first row's source, a1 the view, all even. Each row: the first segment from the row's
; source, the second (<hunk 1 +$d454> / 2 - d0 - 1 words, none if that is not positive)
; from the source less d1 (the sky wraps around), then the view's modulo. Out as START's
; loop: a0 = a4 a row past the last, a1 past the last row with its modulo, d7.w -1, the
; rest kept but d3, which the code after +$c8e8 does not read before setting.

SKY_UNROLL      = 80                    ; longwords: a 320-pixel row

_skyrows
        movem.l d0/d2/d4/d6,-(a7)
        move.l  _hunk1(pc),d3
        add.l   #$d454,d3
        move.l  d3,a0
        move.w  (a0),d3
        lsr.w   #1,d3
        sub.w   d0,d3
        subq.w  #1,d3                   ; the second segment's words
        bgt     .n2
        moveq   #0,d3
.n2     move.w  d3,d6
        move.w  d0,d2
        addq.w  #1,d2                   ; the first segment's words
        tst.w   d0
        bpl     .row
        moveq   #0,d2
.row    move.l  a4,a0
        move.w  d2,d4
        bsr     .seg
        suba.w  d1,a0
        move.w  d6,d4
        bsr     .seg
        adda.w  d5,a1
        adda.w  d1,a4
        dbf     d7,.row
        move.l  a4,a0
        movem.l (a7)+,d0/d2/d4/d6
        rts

.run    REPT    SKY_UNROLL
        move.l  (a0)+,(a1)+
        ENDR
.runend rts

; d4.w words from a0 to a1 (both advanced); d4 used
.seg    lsr.w   #1,d4
        bcc     .long
        move.w  (a0)+,(a1)+
.long   cmp.w   #SKY_UNROLL,d4
        bls     .tail
        sub.w   #SKY_UNROLL,d4
        bsr     .run
        bra     .long
.tail   add.w   d4,d4
        neg.w   d4
        jmp     .runend(pc,d4.w)
