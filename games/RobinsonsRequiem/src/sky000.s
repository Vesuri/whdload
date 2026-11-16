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
;
; On the 68020 and up (ECS plan step 8) the rows are read from a copy of the image in fast
; memory (_skyget below), when the slave found room for it (K_BUF); a4 and a0 then come
; out in the image as before.

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
        bpl     .sky
        moveq   #0,d2
.sky    move.l  _kvars+K_BUF(pc),d3     ; no room: d3 = 0
        beq     .orig
        move.l  16+4(a7),a0             ; the image, START's move.l a0,-(sp) at +$c880
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

; The sky in fast memory (the AGA's plan step 12, src/sky030.s; ECS plan step 8). The image
; (a resource in the chip heap: width - 1 at +2, height - 1 at +4, the pixels from +6: START
; reads height + 1 rows of width + 1 bytes, and the fill below from the last row) is copied
; into the room _skycopy took (K_BUF, 16-aligned; none: no copy) at the image's address
; modulo 16, so the rows' longword alignment is START's, and the rows are read from the
; copy. The copy is made again when the image's address or size changes and after the
; sky's set-up (_skyset clears K_ORIG). MAPCHECK (a test define) compares the copy with the
; image at every call, counting differing longwords in K_BAD.
; In a0 the image; out d3 the copy's offset from the image (0: none, the image too large).

SKYMAX  equ     32768

_skyget movem.l d0-d2/a0-a2,-(a7)
        lea     _kvars(pc),a2
        moveq   #0,d3
        moveq   #0,d0
        move.w  2(a0),d0
        bmi     .x
        addq.l  #1,d0                   ; a row's bytes
        moveq   #0,d1
        move.w  4(a0),d1
        bmi     .x
        addq.l  #1,d1                   ; the rows START reads: the height + 1 (+$c8e4)
        mulu.w  d1,d0
        addq.l  #6,d0                   ; the bytes read from the image
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
