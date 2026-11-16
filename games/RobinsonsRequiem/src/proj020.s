; The objects' places on screen from the staged camera and objects with their fractions,
; and their boxes rounded once, for both games on the 68020 and up (docs/internals.md, "AGA
; improvements", item 16, and "ECS improvements", item 8).
;
; The 3D view projects an object through AGA hunk 1 +$ad9e (ECS +$9408): the position from
; the camera (words) rotated by the heading (the sine tables, products shifted down 9 bits),
; then the screen x and y and the scale as truncated quotients. The element projection
; (+$a7d4, ECS +$8e3e) and the map cells' objects (+$d712, ECS +$bd68: the trees) then size
; the image from the scale and move it by its hotspot's offset times the scale, each rounded
; on its own. Between the game's runs the camera and the moving objects are staged in whole
; units (_view, _eplan, _estage), and near the camera a unit across is 2 to 3 pixels. All of
; it moves a box's edges by a pixel or more, back and forth, between frames.
;
; Here the staged camera and objects keep their offsets' fractions (1/64 units, _pcam,
; _pfadd), and the projection is worked again from the position with its fraction (_pexact:
; the rotation kept in 1/64 units, x and y with 8 bits of fraction, the scale with 8 bits
; more), and each edge is rounded once: the first at the centre less the hotspot's offset
; times m, the second at the first plus the image's size times m, m the image's pixels per
; source pixel. Its depth, scale words and clipping stay the game's.
; - AGA +$a888 bsr.w +$ad9e (ECS +$8ef2, `6100 0514`, then `d66a 000a` add.w 10(a2),d3)
;   becomes jsr _proj, which returns past the box (+$a96c, ECS +$8fd6, `4cdf 7fff`) with
;   the game's variables set as it sets them (+$ee2e-+$ee3c, ECS +$d484-+$d492).
; - The cells' objects: +$d750 bsr.w +$ad9e (ECS +$bda6, then `3003 3204`) becomes jsr
;   _cproj, which keeps the exact position for +$d860 add.w d0,12(a0) and bsr.w +$ea3a (ECS
;   +$beb6, `d168 000c`, then `4cdf 7fff`), which become jsr _cbox and a nop: the box set
;   again from it before the drawing.
; An element clipped behind the view, a quotient the projection clamped, a position 8192
; units away or more, or a scale over 2048 keeps the game's own box. All sites are checked
; first. PROJ_OFF (a test define): not patched. The slaves call _projpatch with _hunk1 set,
; the AGA one always, the ECS one on the 68020 and up (the 68000 keeps the game's own path
; and whole units). Assembled for the 68020; the ECS slave goes back to the 68000 after it.

        MC68020

PFMAX   equ     48                      ; staged elements with fractions

; _projpatch: a1 the element projection's call (+$a888 / +$8ef2), d1 its box's first
; variable (+$ee2e / +$d484), d2 the cells' call (+$d750 / +$bda6), d3 their box (+$d860 /
; +$beb6), all offsets in hunk 1; all registers kept
_projpatch
        IFND PROJ_OFF
        movem.l d0-d3/a0-a3,-(a7)
        move.l  _hunk1(pc),a0
        add.l   a0,a1
        add.l   a0,d1
        add.l   a0,d2
        add.l   a0,d3
        cmp.l   #$61000514,(a1)         ; bsr.w the projection
        bne     .no
        cmp.l   #$d66a000a,4(a1)        ; add.w 10(a2),d3
        bne     .no
        cmp.l   #$4cdf7fff,$e4(a1)      ; movem.l (sp)+,d0-a6: past the box
        bne     .no
        lea     2(a1),a3
        add.w   (a3),a3                 ; the projection
        cmp.w   #$41f9,$a(a3)           ; its lea of the cosines
        bne     .no
        cmp.w   #$41f9,$14(a3)          ; and of the sines
        bne     .no
        move.l  d2,a0                   ; the cells' call
        cmp.w   #$6100,(a0)
        bne     .no
        lea     2(a0),a2
        add.w   (a2),a2
        cmp.l   a2,a3
        bne     .no
        cmp.l   #$30033204,4(a0)        ; move.w d3,d0; move.w d4,d1
        bne     .no
        move.l  d3,a0                   ; the cells' box
        cmp.l   #$d168000c,(a0)         ; add.w d0,12(a0)
        bne     .no
        cmp.w   #$6100,4(a0)            ; bsr.w the sprite routine
        bne     .no
        cmp.l   #$4cdf7fff,8(a0)
        bne     .no
        lea     _prvars(pc),a2
        move.l  a3,PR_PROJ(a2)
        move.l  $c(a3),PR_COS(a2)
        move.l  $16(a3),PR_SIN(a2)
        lea     6(a0),a3
        add.w   (a3),a3
        move.l  a3,PR_DRAW(a2)          ; the sprite routine
        lea     8(a1),a3
        move.l  a3,PR_BACK(a2)
        lea     $e4(a1),a3
        move.l  a3,PR_END(a2)
        move.l  d1,PR_BOX(a2)
        move.w  #$4eb9,(a1)
        pea     _proj(pc)
        move.l  (a7)+,2(a1)
        move.l  d2,a1
        move.w  #$4eb9,(a1)
        pea     _cproj(pc)
        move.l  (a7)+,2(a1)
        move.w  #$4eb9,(a0)
        pea     _cbox(pc)
        move.l  (a7)+,2(a0)
        move.w  #$4e71,6(a0)            ; nop
        move.l  _resload(pc),a2
        jsr     resload_FlushCache(a2)
.no     movem.l (a7)+,d0-d3/a0-a3
        ENDC
        rts

_prvars
PR_PROJ  equ     *-_prvars               ; the projection
        dc.l    0
PR_BACK  equ     *-_prvars               ; the element projection's own path
        dc.l    0
PR_END   equ     *-_prvars               ; past its box
        dc.l    0
PR_BOX   equ     *-_prvars               ; its box's variables
        dc.l    0
PR_COS   equ     *-_prvars               ; the sine tables (words, 512 = 1)
        dc.l    0
PR_SIN   equ     *-_prvars
        dc.l    0
PR_DRAW  equ     *-_prvars               ; the sprite routine
        dc.l    0
PR_CX    equ     *-_prvars               ; a cell object's x, y (24.8) and scale (16.16)
        dc.l    0
PR_CY    equ     *-_prvars
        dc.l    0
PR_CS    equ     *-_prvars
        dc.l    0
PR_REL   equ     *-_prvars               ; the position from the camera, as given
        dc.w    0,0,0
PR_GAME  equ     *-_prvars               ; the projection's d3-d6
        dc.l    0,0,0,0
PR_CF    equ     *-_prvars               ; the staged camera's fractions (x, y, z; 1/64)
        dc.w    0,0,0
PR_CFD   equ     *-_prvars               ; those of the last staged drawing
        dc.w    0,0,0
PR_CON   equ     *-_prvars               ; a staged drawing: PR_CF and the table apply
        dc.b    0
PR_CV    equ     *-_prvars               ; PR_CX-PR_CS set for the next cell object's box
        dc.b    0
PR_EN    equ     *-_prvars               ; the staged elements with fractions
        dc.w    0
PR_ET    equ     *-_prvars               ; each: its address, its fractions (x, y, z)
        ds.b    PFMAX*10
        even

; the box's variables from PR_BOX (AGA +$ee2e, ECS +$d484)
PB_X     equ     0                       ; left
PB_Y     equ     2                       ; top
PB_Z     equ     4                       ; depth
PB_H     equ     8                       ; height - 1
PB_W     equ     10                      ; width - 1
PB_SX    equ     12                      ; the scale, twice
PB_SY    equ     14

; for _view: the camera's fractions cleared (_pcclr); d1 the fraction of axis d5 (0, 2, 4:
; x, y, z) (_pcam); d0.w their or, d1.b set when they differ from the last staged drawing's
; (_pcst); a staged drawing starts (_pcon) and ends (_pcoff). For _estage: the table
; emptied (_pfclr); a4 an element, d2-d4 its fractions (_pfadd). All other registers kept.
_pcclr  move.l  a0,-(a7)
        lea     _prvars+PR_CF(pc),a0
        clr.l   (a0)+
        clr.w   (a0)
        move.l  (a7)+,a0
        rts
_pcam   move.l  a0,-(a7)
        lea     _prvars+PR_CF(pc),a0
        move.w  d1,(a0,d5.w)
        move.l  (a7)+,a0
        rts
_pcst   move.l  a0,-(a7)
        lea     _prvars(pc),a0
        move.w  PR_CF(a0),d0
        or.w    PR_CF+2(a0),d0
        or.w    PR_CF+4(a0),d0
        move.l  PR_CF(a0),d1
        cmp.l   PR_CFD(a0),d1
        bne     .d
        move.w  PR_CF+4(a0),d1
        cmp.w   PR_CFD+4(a0),d1
.d      sne     d1
        move.l  (a7)+,a0
        rts
_pcon   move.l  a0,-(a7)
        lea     _prvars(pc),a0
        move.l  PR_CF(a0),PR_CFD(a0)
        move.w  PR_CF+4(a0),PR_CFD+4(a0)
        st      PR_CON(a0)
        move.l  (a7)+,a0
        rts
_pcoff  move.l  a0,-(a7)
        lea     _prvars(pc),a0
        sf      PR_CON(a0)
        move.l  (a7)+,a0
        rts
_pfclr  move.l  a0,-(a7)
        lea     _prvars(pc),a0
        clr.w   PR_EN(a0)
        move.l  (a7)+,a0
        rts
_pfadd  movem.l d0/a0,-(a7)
        lea     _prvars(pc),a0
        move.w  PR_EN(a0),d0
        cmp.w   #PFMAX,d0
        bhs     .full
        addq.w  #1,PR_EN(a0)
        mulu.w  #10,d0
        lea     PR_ET(a0,d0.w),a0
        move.l  a4,(a0)+
        move.w  d2,(a0)+
        move.w  d3,(a0)+
        move.w  d4,(a0)
.full   movem.l (a7)+,d0/a0
        rts

; PR_REL with the fractions (the camera's in a staged drawing, a0's from the table when
; d7 is set) -> d0-d2 in 1/64 units; d7 -1 when too far. d3-d6 kept.
_prel   movem.l d3-d4/a4-a5,-(a7)
        lea     _prvars(pc),a5
        movem.w PR_REL(a5),d0-d2        ; sign-extended
        move.l  d0,d3
        bpl     .a0
        neg.l   d3
.a0     move.l  d1,d4
        bpl     .a1
        neg.l   d4
.a1     or.l    d4,d3
        move.l  d2,d4
        bpl     .a2
        neg.l   d4
.a2     or.l    d4,d3
        cmp.l   #8192,d3
        bhs     .far
        asl.l   #6,d0
        asl.l   #6,d1
        asl.l   #6,d2
        tst.b   PR_CON(a5)
        beq     .ok
        sub.w   PR_CF(a5),d0            ; less the camera's fraction (word arithmetic:
        sub.w   PR_CF+2(a5),d1          ; the values fit in 20 bits, so extend again)
        sub.w   PR_CF+4(a5),d2
        ext.l   d0
        ext.l   d1
        ext.l   d2
        tst.l   d7
        beq     .ok
        move.w  PR_EN(a5),d3
        lea     PR_ET(a5),a4
        bra     .lt
.l      cmp.l   (a4),a0
        beq     .hit
        lea     10(a4),a4
.lt     dbf     d3,.l
        bra     .ok
.hit    move.w  4(a4),d3
        ext.l   d3
        add.l   d3,d0
        move.w  6(a4),d3
        ext.l   d3
        add.l   d3,d1
        move.w  8(a4),d3
        ext.l   d3
        add.l   d3,d2
.ok     moveq   #0,d7
        bra     .ret
.far    moveq   #-1,d7
.ret    movem.l (a7)+,d3-d4/a4-a5
        rts

; d0-d2 the position from the camera in 1/64 units, a2 the view -> d0 x (24.8), d2 y
; (24.8), d5 the scale (16.16: 256 times the game's d6); d7 0, or -1 for the game's own.
; As +$ad9e with the rotation's 9-bit shift kept in 1/64 units: the depth z = y cos - x
; sin, x = x cos + y sin, y = -(z + sin(-pitch) z), x * 118(a2) / (z + 112(a2)) and
; y * 122(a2) / (z + 116(a2)), each divisor 1 at least, 256 * 122(a2) / (z + 116(a2)).
_pexact move.l  _prvars+PR_COS(pc),a4
        move.w  56(a2),d7
        add.w   d7,d7
        move.w  (a4,d7.w),d3            ; cos
        ext.l   d3
        move.l  _prvars+PR_SIN(pc),a4
        move.w  (a4,d7.w),d4            ; sin
        ext.l   d4
        move.l  d0,d5
        muls.l  d4,d5
        move.l  d1,d6
        muls.l  d3,d6
        sub.l   d5,d6
        asr.l   #8,d6
        asr.l   #1,d6                   ; d6 z
        muls.l  d3,d0
        muls.l  d4,d1
        add.l   d1,d0
        asr.l   #8,d0
        asr.l   #1,d0                   ; d0 x
        move.w  52(a2),d7
        neg.w   d7
        add.w   d7,d7
        move.w  (a4,d7.w),d7            ; sin(-pitch)
        ext.l   d7
        muls.l  d6,d7
        asr.l   #8,d7
        asr.l   #1,d7
        add.l   d7,d2
        neg.l   d2                      ; d2 y
        move.w  116(a2),d7              ; the y divisor
        ext.l   d7
        asl.l   #6,d7
        add.l   d6,d7
        bgt     .y1
        moveq   #64,d7
.y1     moveq   #0,d5
        move.w  122(a2),d5
        cmp.w   #512,d5
        bhs     .bad
        swap    d5
        lsl.l   #6,d5
        divu.l  d7,d5                   ; the scale
        cmp.l   #$80000,d5
        bhs     .bad
        move.w  122(a2),d4
        ext.l   d4
        muls.l  d4,d2
        divsl.l d7,d4:d2                ; y: the quotient and remainder
        asl.l   #8,d2
        asl.l   #8,d4
        divs.l  d7,d4
        add.l   d4,d2
        move.w  112(a2),d7              ; the x divisor
        ext.l   d7
        asl.l   #6,d7
        add.l   d6,d7
        bgt     .x1
        moveq   #64,d7
.x1     move.w  118(a2),d4
        ext.l   d4
        muls.l  d4,d0
        divsl.l d7,d4:d0
        asl.l   #8,d0
        asl.l   #8,d4
        divs.l  d7,d4
        add.l   d4,d0
        moveq   #0,d7
        rts
.bad    moveq   #-1,d7
        rts

; d0 the image's centre (24.8), d1 its size - 1, d6 the hotspot's offset, d5 m (16.16)
; -> d0 the first pixel, d1 the size - 1 (0 at least); d2-d5 kept
_pedges move.w  d1,d7
        lsr.w   #1,d7
        sub.w   d6,d7                   ; the half size less the hotspot's offset
        ext.l   d7
        muls.l  d5,d7
        asr.l   #8,d7
        sub.l   d7,d0                   ; the first edge, 24.8
        moveq   #0,d7
        move.w  d1,d7
        addq.l  #1,d7
        mulu.l  d5,d7
        lsr.l   #8,d7
        add.l   d0,d7                   ; the second edge
        move.l  #128,d6                 ; round
        add.l   d6,d0
        asr.l   #8,d0
        add.l   d6,d7
        asr.l   #8,d7
        sub.l   d0,d7
        subq.l  #1,d7
        bpl     .e1
        moveq   #0,d7
.e1     move.l  d7,d1
        rts

; the game's clip and clamps after the projection: Z set when its own path is to be taken
_pgame  cmp.w   #-1,d1                  ; clipped: d1 = -1, d0 = d2 = 0
        bne     .in
        tst.l   d0
        bne     .in
        tst.l   d2
        beq     .own
.in     cmp.w   #$7fff,d3               ; a quotient clamped
        beq     .own
        cmp.w   #$8000,d3
        beq     .own
        cmp.w   #$7fff,d4
        beq     .own
        cmp.w   #$8000,d4
.own    rts

; from +$a888 in the element projection (a0 the element, a1 its frame's header, a2 the
; view, a3 its image's header; d0-d2 its position from the camera); the routine saved d0-a6
_proj   addq.l  #4,a7                   ; returns to PR_BACK or PR_END instead
        lea     _prvars(pc),a5
        movem.w d0-d2,PR_REL(a5)
        move.l  PR_PROJ(a5),a4
        jsr     (a4)                    ; d3 x, d4 y, d5 the depth, d6 the scale
        bsr     _pgame
        beq     .game
        movem.l d3-d6,PR_GAME(a5)
        moveq   #-1,d7                  ; with the element's fractions
        bsr     _prel
        tst.l   d7
        bne     .own
        bsr     _pexact
        tst.l   d7
        bne     .own
        move.l  _prvars+PR_BOX(pc),a5
        move.w  _prvars+PR_GAME+8+2(pc),PB_Z(a5)
        move.w  10(a2),d1               ; the view's centre
        ext.l   d1
        asl.l   #8,d1
        add.l   d1,d0                   ; d0 x, d2 y: 24.8
        move.w  12(a2),d1
        ext.l   d1
        asl.l   #8,d1
        add.l   d1,d2
        move.l  _prvars+PR_GAME+12(pc),d6
        moveq   #0,d3                   ; the scale's adjustments, as +$a8a6-$a8e2
        move.b  28(a0),d3
        btst    #5,1(a3)
        beq     .s1
        add.w   d6,d6
        add.l   d5,d5
.s1     move.w  d6,PB_SX(a5)
        move.w  d6,PB_SY(a5)
        cmp.b   #8,d3
        blt     .s2
        subq.w  #8,d3
        mulu.w  d3,d6
        lsr.l   #3,d6
        move.w  d6,PB_SX(a5)
        move.w  d6,PB_SY(a5)
        mulu.l  d3,d5
        lsr.l   #3,d5
        moveq   #3,d3
.s2     addq.b  #1,d3
        add.l   d5,d5
        lsr.l   d3,d5                   ; d5 m, 16.16: pixels per source pixel
        move.w  2(a3),d1                ; x: the edges from the image's width
        move.w  4(a1),d6
        bsr     _pedges
        move.w  d0,PB_X(a5)
        move.w  d1,PB_W(a5)
        move.l  d2,d0
        move.w  4(a3),d1                ; y: from its height
        move.w  6(a1),d6
        bsr     _pedges
        move.w  d0,PB_Y(a5)
        move.w  d1,PB_H(a5)
        move.l  _prvars+PR_END(pc),-(a7)
        rts
.own    movem.l _prvars+PR_GAME(pc),d3-d6
.game   add.w   10(a2),d3               ; the instruction replaced
        move.l  _prvars+PR_BACK(pc),-(a7)
        rts

; from +$d750 in the cells' objects (a2 the view, d0-d2 the position from the camera):
; the projection, and the exact position kept when the game will draw the object
_cproj  movem.l d7/a4-a5,-(a7)
        lea     _prvars(pc),a5
        sf      PR_CV(a5)
        movem.w d0-d2,PR_REL(a5)
        move.l  PR_PROJ(a5),a4
        jsr     (a4)
        bsr     _pgame
        beq     .out
        cmp.w   146(a2),d5              ; as +$d75c: nearer, not drawn
        blt     .out
        movem.l d0-d6,-(a7)
        moveq   #0,d7                   ; no element's fractions
        bsr     _prel
        tst.l   d7
        bne     .x
        bsr     _pexact
        tst.l   d7
        bne     .x
        lea     _prvars(pc),a5
        move.l  d0,PR_CX(a5)
        move.l  d2,PR_CY(a5)
        move.l  d5,PR_CS(a5)
        st      PR_CV(a5)
.x      movem.l (a7)+,d0-d6
.out    movem.l (a7)+,d7/a4-a5
        move.w  d3,d0                   ; the instruction replaced
        rts

; from +$d860 (a0 the object's element, a1 the map's object, a2 its frame's header, a3 its
; image's header; d0 the x offset): the box from _cproj's position, then the drawing. The
; routine saved d0-a6 and restores them after the nop.
_cbox   add.w   d0,12(a0)               ; the instruction replaced
        lea     _prvars(pc),a5
        tst.b   PR_CV(a5)
        beq     .draw
        sf      PR_CV(a5)
        move.l  PR_CX(a5),d0
        move.w  -620(a1),d1             ; the centre, as +$d768
        ext.l   d1
        asl.l   #8,d1
        add.l   d1,d0
        move.l  PR_CY(a5),d2
        move.w  -618(a1),d1
        ext.l   d1
        asl.l   #8,d1
        add.l   d1,d2
        move.l  PR_CS(a5),d5
        moveq   #0,d3                   ; the shift, as +$d7e8-+$d7f6
        move.b  28(a0),d3
        btst    #5,1(a3)
        bne     .s
        addq.b  #1,d3
.s      add.l   d5,d5
        lsr.l   d3,d5                   ; m
        move.w  2(a3),d1
        move.w  4(a2),d6
        bsr     _pedges
        move.w  d0,12(a0)
        move.w  d1,40(a0)
        move.l  d2,d0
        move.w  4(a3),d1
        move.w  6(a2),d6
        bsr     _pedges
        move.w  d0,14(a0)
        move.w  d1,42(a0)
.draw   move.l  _prvars+PR_DRAW(pc),a4
        jmp     (a4)
