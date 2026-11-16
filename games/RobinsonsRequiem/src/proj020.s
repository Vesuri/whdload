; The objects' screen boxes rounded once, for both games on the 68020 and up
; (docs/internals.md, "AGA improvements", item 16, and "ECS improvements", item 8). The 3D
; view's element projection (AGA hunk 1 +$a7d4, ECS +$8e3e) projects an element through
; +$ad9e (ECS +$9408), which gives the screen x and y and the scale as truncated quotients,
; then sizes the image from the scale rounded up and moves it by its hotspot's offset times
; the scale rounded down. Each of those roundings moves a box edge by up to a pixel on its
; own, so an object coming closer (or the camera coming closer to it) jumps back and forth
; by a pixel between frames. Here the box is worked out from the projection's dividends
; with 8 bits of fraction, and each edge is rounded once: left = round(x - kx m), right =
; round(left edge + (w + 1) m), the same for y, where m is the image's pixels per source
; pixel (the game's scale with its doubling, bit 5 of the image's +1, and its element's
; shift, +28) and kx the image's half width less the frame's hotspot (+4, +6).
; AGA +$a888 bsr.w +$ad9e (ECS +$8ef2, `6100 0514`, then `d66a 000a` add.w 10(a2),d3)
; becomes jsr _proj, which calls the projection and returns past the box (+$a96c, ECS
; +$8fd6, `4cdf 7fff`) with the game's variables set as it sets them (the depth, the
; scale words, the box); an element clipped behind the view, a quotient the projection
; clamped, or a scale over 2048 takes the game's own path (back at +$a890, ECS +$8efa,
; after its add.w). All sites are checked first. PROJ_OFF (a test define): not patched.
; The slaves call _projpatch with _hunk1 set, the AGA one always, the ECS one on the 68020
; and up. Assembled for the 68020; the ECS slave goes back to the 68000 after it.

        MC68020

; _projpatch: a1 = the projection's call site's offset (+$a888 / +$8ef2), d1 = the box's
; first variable's offset (+$ee2e / +$d484); all registers kept
_projpatch
        IFND PROJ_OFF
        movem.l d0-d1/a0-a2,-(a7)
        move.l  _hunk1(pc),a0
        add.l   a0,a1
        cmp.l   #$61000514,(a1)         ; bsr.w the projection
        bne     .no
        cmp.l   #$d66a000a,4(a1)        ; add.w 10(a2),d3
        bne     .no
        cmp.l   #$4cdf7fff,$e4(a1)      ; movem.l (sp)+,d0-a6: past the box
        bne     .no
        lea     _prvars(pc),a2
        lea     2(a1),a0
        add.w   (a0),a0                 ; the projection
        move.l  a0,PR_PROJ(a2)
        lea     8(a1),a0
        move.l  a0,PR_BACK(a2)
        lea     $e4(a1),a0
        move.l  a0,PR_END(a2)
        add.l   _hunk1(pc),d1
        move.l  d1,PR_BOX(a2)
        move.w  #$4eb9,(a1)
        pea     _proj(pc)
        move.l  (a7)+,2(a1)
        move.l  _resload(pc),a2
        jsr     resload_FlushCache(a2)
.no     movem.l (a7)+,d0-d1/a0-a2
        ENDC
        rts

_prvars
PR_PROJ  equ     *-_prvars
        dc.l    0
PR_BACK  equ     *-_prvars
        dc.l    0
PR_END   equ     *-_prvars
        dc.l    0
PR_BOX   equ     *-_prvars
        dc.l    0

; the box's variables from PR_BOX (AGA +$ee2e, ECS +$d484)
PB_X     equ     0                       ; left
PB_Y     equ     2                       ; top
PB_Z     equ     4                       ; depth
PB_H     equ     8                       ; height - 1
PB_W     equ     10                      ; width - 1
PB_SX    equ     12                      ; the scale, twice
PB_SY    equ     14

; from +$a888 in the element projection (a0 the element, a1 its frame's header, a2 the
; view, a3 its image's header; d0-d2 its position from the camera); the routine saved d0-a6
_proj
        addq.l  #4,a7                   ; returns to PR_BACK or PR_END instead
        move.l  _prvars+PR_PROJ(pc),a4
        jsr     (a4)                    ; d0 x * fx, d2 y * fy, d1 the depth; d3, d4, d6
        cmp.w   #-1,d1                  ; clipped: d1 = -1, d0 = d2 = 0
        bne     .in
        tst.l   d0
        bne     .in
        tst.l   d2
        beq     .game
.in     cmp.w   #$7fff,d3               ; a quotient clamped
        beq     .game
        cmp.w   #$8000,d3
        beq     .game
        cmp.w   #$7fff,d4
        beq     .game
        cmp.w   #$8000,d4
        beq     .game
        move.w  d1,d7                   ; the y divisor, as +$ae1e
        add.w   116(a2),d7
        bgt     .dy
        moveq   #1,d7
.dy     ext.l   d7
        moveq   #0,d5
        move.w  122(a2),d5
        swap    d5
        divu.l  d7,d5                   ; the scale with 8 bits more
        cmp.l   #$80000,d5
        bhs     .game
        move.l  _prvars+PR_BOX(pc),a5
        move.w  d1,PB_Z(a5)
        move.w  d1,a6                   ; the depth
        divsl.l d7,d1:d2                ; y: the quotient and remainder
        asl.l   #8,d2
        asl.l   #8,d1
        divs.l  d7,d1
        add.l   d1,d2                   ; with 8 bits of fraction
        move.w  a6,d7                   ; the x divisor, as +$ae08
        add.w   112(a2),d7
        bgt     .dx
        moveq   #1,d7
.dx     ext.l   d7
        divsl.l d7,d1:d0                ; x
        asl.l   #8,d0
        asl.l   #8,d1
        divs.l  d7,d1
        add.l   d1,d0
        move.w  10(a2),d1               ; the view's centre
        ext.l   d1
        asl.l   #8,d1
        add.l   d1,d0                   ; d0 x, d2 y: 24.8
        move.w  12(a2),d1
        ext.l   d1
        asl.l   #8,d1
        add.l   d1,d2
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
        bsr     .edges
        move.w  d0,PB_X(a5)
        move.w  d1,PB_W(a5)
        move.l  d2,d0
        move.w  4(a3),d1                ; y: from its height
        move.w  6(a1),d6
        bsr     .edges
        move.w  d0,PB_Y(a5)
        move.w  d1,PB_H(a5)
        move.l  _prvars+PR_END(pc),-(a7)
        rts

.game   add.w   10(a2),d3               ; the instruction replaced
        move.l  _prvars+PR_BACK(pc),-(a7)
        rts

; d0 the image's centre (24.8), d1 its size - 1, d6 the hotspot's offset, d5 m (16.16)
; -> d0 the first pixel, d1 the size - 1 (0 at least); d3-d5 kept
.edges  move.w  d1,d7
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
