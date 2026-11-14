; The AGA game's sky copy with longword reads (docs/internals.md, "AGA improvements").
;
; START's 3D view copies the sky's rows (a resource in the chip heap) into the chunky view
; (fast) with move.w (a0)+,(a1)+, a word, one chip access, at a time: hunk 1 +$e262-$e291,
; which becomes jsr _skyrows and a branch to +$e292. _skyrows reads the sky in aligned
; longwords, two words an access on the A1200's 32-bit chip bus, and writes the same bytes
; to the same places. tools/rr_skycheck.py checks it against START's loop under Unicorn.
;
; In, START's registers at +$e262: d0.w the first segment's words - 1 (negative: none),
; d1.w the sky's row length in bytes, d5.w the view's modulo, d7.w rows - 1, a0 = a4 the
; first row's source, a1 the view. Each row: the first segment from the row's source, the
; second (<hunk 1 +$edfe> / 2 - d0 - 1 words, none if that is not positive) from the source
; less d1 (the sky wraps around), then the view's modulo. Out as START's loop: a0 = a4 a row
; past the last, a1 past the last row with its modulo, d7.w -1, the rest kept but d3, which
; the code after +$e292 sets (+$e2d8) or restores (+$e2e4) before reading.

_skyrows
        movem.l d0/d2/d4/d6,-(a7)
        move.l  _hunk1(pc),d3
        add.l   #$edfe,d3
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

; d4.w words from a0 to a1 (both advanced); d0 and d4 used
.seg    tst.w   d4
        beq     .done
        move.w  a0,d0
        btst    #1,d0
        beq     .al
        move.w  (a0)+,(a1)+             ; the source to a longword
        subq.w  #1,d4
.al     move.w  d4,d0
        lsr.w   #1,d0
        bra     .lt
.l      move.l  (a0)+,(a1)+
.lt     dbf     d0,.l
        btst    #0,d4
        beq     .done
        move.w  (a0)+,(a1)+
.done   rts
