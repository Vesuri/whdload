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
        bpl     .sky
        moveq   #0,d2
.sky    moveq   #0,d3
        tst.l   _kvars+K_BUF(pc)
        beq     .orig
        move.l  16+4(a7),a0             ; the image, START's move.l a0,-(sp) at +$e22a
        bsr     _skyget
        add.l   d3,a4
.orig   move.l  d3,-(a7)
.row    move.l  a4,a0
        move.w  d2,d4
        bsr     .seg
        suba.w  d1,a0
        move.w  d6,d4
        bsr     .seg
        adda.w  d5,a1
        adda.w  d1,a4
        dbf     d7,.row
        sub.l   (a7)+,a4                ; back in the image
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

; The sky in fast memory (docs/performance.md, plan step 12). The image (a resource in the
; chip heap: width - 1 at +2, height at +4, the pixels from +8) is copied into the room
; _skycopy took (K_BUF, 16-aligned; none: no copy) at the image's address modulo 16, so
; the rows' longword alignment is START's, and the rows are read from the copy. The copy
; is made again when the image's address or size changes and after the sky's set-up
; (_skyset clears K_ORIG). MAPCHECK (a test define) compares the copy with the image at
; every call, counting differing longwords in K_BAD.
; In a0 the image; out d3 the copy's offset from the image (0: none, the image too large).

SKYMAX  equ     32768

_skyget movem.l d0-d2/a0-a2,-(a7)
        lea     _kvars(pc),a2
        moveq   #0,d3
        moveq   #0,d0
        move.w  2(a0),d0
        addq.l  #1,d0                   ; a row's bytes
        moveq   #0,d1
        move.w  4(a0),d1                ; the rows
        mulu.l  d1,d0
        addq.l  #8,d0                   ; the image's bytes
        cmp.l   #SKYMAX,d0
        bhi     .x
        cmp.l   K_ORIG(a2),a0
        bne     .copy
        cmp.l   K_SIZE(a2),d0
        beq     .ok
.copy   move.l  a0,K_ORIG(a2)
        move.l  d0,K_SIZE(a2)
        move.l  a0,d1
        and.l   #15,d1
        add.l   K_BUF(a2),d1
        move.l  d1,K_COPY(a2)
        move.l  a0,d2
        moveq   #3,d1
        and.l   d1,d2                   ; the image's offset in its first longword
        add.l   d2,d0
        addq.l  #3,d0
        lsr.l   #2,d0                   ; the longwords
        move.l  a0,a1
        suba.l  d2,a1
        move.l  K_COPY(a2),a0
        suba.l  d2,a0
        bra     .lt
.l      move.l  (a1)+,(a0)+
.lt     dbf     d0,.l
        move.l  K_ORIG(a2),a0
.ok     move.l  K_COPY(a2),d3
        sub.l   a0,d3
        IFD MAPCHECK
        move.l  K_SIZE(a2),d0
        lsr.l   #2,d0
        move.l  K_COPY(a2),a1
        bra     .kt
.k      cmpm.l  (a0)+,(a1)+
        beq     .kt
        addq.l  #1,K_BAD(a2)
.kt     dbf     d0,.k
        addq.l  #1,K_CALLS(a2)
        ENDC
.x      movem.l (a7)+,d0-d2/a0-a2
        rts

_kvars
_kbuf   dc.l    0                       ; the copy's room (0: none)
_korig  dc.l    0                       ; the image copied (0: to be copied)
_ksize  dc.l    0                       ; its bytes
_kcopy  dc.l    0                       ; the copy
_kbad   dc.l    0                       ; MAPCHECK: longwords that differed
_kcalls dc.l    0                       ; MAPCHECK: calls with the copy
K_BUF   equ     _kbuf-_kvars
K_ORIG  equ     _korig-_kvars
K_SIZE  equ     _ksize-_kvars
K_COPY  equ     _kcopy-_kvars
K_BAD   equ     _kbad-_kvars
K_CALLS equ     _kcalls-_kvars
