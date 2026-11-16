; The AGA landscape's inner loop in the 68030's instruction cache (docs/performance.md,
; plan step 15).
;
; START's landscape (hunk 1 +$d88c) takes a near and a far sample a step for every column
; of a row in its inner loop, +$d9ba-+$dbaf, 3,600 steps a frame in the jungle. The loop's
; common path is about 284 bytes spread over 500 with the map's edges and the tile
; objects inline, more than the 030's 256-byte instruction cache: every 16-byte line of it
; missed at every step. _lloop is that common path only, 254 bytes run from a 16-byte
; aligned copy (the slave's hunk is only 8-byte aligned), with the 68020's scaled index for
; the row table (movea.l (a2,d6.w*4),a0 for move.w d6,d0; add.w d0,d0; add.w d0,d0;
; movea.l (0,a2,d0.w),a0: d0.w is cleared after both), lea (a0,d7.w*2),a0 for the two
; adda.w, and the far sample's larger and smaller height (+$db44-+$db62) in four bytes
; less. Every other branch goes back to the same instruction in START's loop, which is left
; as it is but for its two entries: +$d9ba (the step's start, from the row's set-up +$d9b2
; and the loop's own end) and +$db8e (the step's end, from the tile objects' path +$e0e2
; and the edges' paths), each a jmp to the same place in the copy. So START's rare paths
; run as before and come back to the copy. Its stores, calls (+$b6ea the spans, +$d712),
; and flags at every branch are START's.
;
; _bloop, the option "Smooth landscape" (docs/internals.md), is the same loop with each
; sample's height blended. START's walkers hold a map position as a cell and a 16-bit
; fraction (the low word the cell, the high word the fraction), one axis a row stepping by
; whole cells and the other by a fraction, and START takes the height of the cell the
; position falls in. So turning moves most samples to the next cell at once and the hills
; are drawn differently at every heading. _bloop takes the screen height (START's table at
; a6) of both the cell and the next one along the axis with the fraction, and puts the
; sample between them by the fraction. A sample with no fraction, or whose next cell is
; past the map's last row or column, is START's. The colour, the stores of the cell and its
; height (+$d888, +$a220), the cell the spans take their shading from (a0) and every
; other path are START's.
;
; _landinst: d0 0 for _lloop, else _bloop; a0 START's hunk 1, a1 LCOPYMAX bytes, 16-byte
; aligned, for the copy. Checks the loop's words (a checksum with the relocated addresses
; taken back to their offsets), copies the loop to a1, relocates the copy's addresses of
; hunk 1 and writes the two jmps; d0 non-zero if it did. The caller flushes the caches.

LSTART  equ     $d9ba
LEND    equ     $dbb0
LSUM    equ     $870e378f               ; the checksum of START's +$d9ba-+$dbaf

_landinst
        movem.l d1-d4/a1-a4,-(a7)
        lea     _lloopd(pc),a4
        tst.l   d0
        beq.s   .d
        lea     _bloopd(pc),a4
        move.l  a0,d1                   ; START's span and its variables for _bspan
        add.l   #$b6ea,d1
        lea     _bspan0(pc),a2
        move.l  d1,(a2)
        move.l  a0,d1
        add.l   #$a226,d1
        lea     _bpx(pc),a2
        move.l  d1,(a2)
.d      moveq   #0,d0
        move.l  a1,a3                   ; the copy
        move.l  a0,d2
        move.l  a0,a1
        add.l   #LSTART,a1
        lea     .rel(pc),a2
        moveq   #0,d3                   ; the checksum: rotated left, plus each word
.sum    move.l  a1,d1
        sub.l   d2,d1                   ; the word's offset
        cmp.l   #LEND,d1
        bhs     .cmp
        cmp.w   (a2),d1                 ; a relocated address: back to its offset
        bne     .w
        addq.l  #2,a2
        move.l  (a1)+,d1
        sub.l   d2,d1
        move.l  d1,d4                   ; as two words
        clr.w   d4
        swap    d4
        rol.l   #1,d3
        add.l   d4,d3
        moveq   #0,d4
        move.w  d1,d4
        rol.l   #1,d3
        add.l   d4,d3
        bra     .sum
.w      moveq   #0,d1
        move.w  (a1)+,d1
        rol.l   #1,d3
        add.l   d1,d3
        bra     .sum
.cmp    cmp.l   #LSUM,d3
        bne     .x
        move.l  a4,a1                   ; the copy
        add.w   (a4),a1
        move.l  a3,a2
        move.w  2(a4),d1
        lsr.w   #1,d1
        subq.w  #1,d1
.c      move.w  (a1)+,(a2)+
        dbf     d1,.c
        move.l  a4,a2                   ; its addresses in hunk 1
        add.w   (a4),a2
        add.w   4(a4),a2
.r      move.w  (a2)+,d1
        beq     .j
        add.l   d2,(a3,d1.w)
        bra     .r
.j      move.l  a0,a2
        add.l   #LSTART,a2
        move.w  #$4ef9,(a2)+            ; jmp
        move.l  a3,(a2)
        move.l  a0,a2
        add.l   #$db8e,a2
        move.w  #$4ef9,(a2)+
        move.l  a3,a1
        add.w   6(a4),a1
        move.l  a1,(a2)
        lea     _bloopd(pc),a1
        cmp.l   a1,a4
        bne.s   .o
        lea     _bspan(pc),a1           ; _bloop's call of _bspan, the slave's own address
        move.l  a1,BJSR(a3)
.o      moveq   #1,d0
.x      movem.l (a7)+,d1-d4/a1-a4
        rts
; START's relocated addresses in the loop, hunk 1 offsets; 0 ends
.rel    dc.w    $da72,$db24,$db40,$db8a,$db90,$db98,0
; each loop: its offset from here, its copy's bytes, its addresses' list, its +$db8e
_lloopd dc.w    _lloop-_lloopd,LCOPY,LREL,LDB8E
_bloopd dc.w    _bloop-_bloopd,BCOPY,BREL,BDB8E

; the loop, run from its copy: START's registers and flags; an address (x).l is hunk 1 +x
; in the copy
_lloop                                  ; +$d9ba
        move.w  -608(a1),d0
        move.w  -606(a1),d1
        cmp.w   d0,d1
        bge.s   .1
        move.w  d0,d1
.1      cmp.w   -640(a1),d3
        ble.s   .far
.near   move.w  d0,-606(a1)             ; +$d9d2
        clr.w   d0
        add.l   a4,d6
        addx.w  d0,d6
        add.l   a5,d7
        addx.w  d0,d7
        move.l  -636(a1),d2
        add.l   d2,-640(a1)
        cmp.w   -660(a1),d6
        bhi     .xda14
        cmp.w   -658(a1),d7
        bhi     .xd9f8
        movea.l (a2,d6.w*4),a0          ; +$da5c
        lea     (a0,d7.w*2),a0
        clr.w   d0
        move.b  1(a0),d0
        move.l  a0,($d888).l
.a1     add.w   d0,d0                   ; +$da76
        add.w   -602(a1),d0
        move.w  (0,a6,d0.w),d0
        add.w   -622(a1),d0
        move.w  d0,-608(a1)
        cmp.w   d1,d0
        ble.s   .2
        move.w  d0,d1
.2      cmp.w   -640(a1),d3
        bgt.s   .near
.far    cmp.w   -660(a1),d4             ; +$da98
        bhi     .xdac4
        cmp.w   -658(a1),d5
        bhi     .xdaa8
        movea.l (a2,d4.w*4),a0          ; +$db0c
        lea     (a0,d5.w*2),a0
        clr.w   d0
        swap    d1
        move.w  (a0),d1
        move.b  d1,d0
        move.w  d0,($a220).l
.a2     andi.w  #$3f00,d1
        lsr.w   #3,d1
        addi.w  #-3072,d1
        swap    d1
        add.w   d0,d0
        move.w  (0,a6,d0.w),d0
        add.w   -630(a1),d0
        move.w  d0,($a21e).l
.a3     move.w  d0,-582(a1)             ; the new height
        move.w  -604(a1),d2             ; the last
        move.w  d0,-604(a1)
        cmp.w   d0,d2
        ble.s   .5
        move.w  d2,-582(a1)             ; -582: the larger, d0 the smaller
        bra.s   .3
.5      move.w  d2,d0
.3      sub.w   d0,d1
        ble.s   .4
        jsr     ($b6ea).l
.a4
.4      swap    d1
        tst.b   (20,a1,d1.w)
        bne.s   .xdb76
        clr.w   ($d86e).l               ; +$db88
.a5
.db8e   move.w  d3,($a226).l            ; +$db8e
.a6     clr.w   d0
        cmp.w   ($a20e).l,d3
.c1     bgt.s   .xdbb0
        add.l   a4,d4
        addx.w  d0,d4
        add.l   a5,d5
        addx.w  d0,d5
        add.l   a3,d3
        addx.w  d0,d3
        bra     _lloop
; back to START's loop: the row's end, the tile objects, the edges
.xdbb0  jmp     ($dbb0).l
.c7
.xdb76  jmp     ($db76).l
.c6
.xda14  jmp     ($da14).l
.c2
.xd9f8  jmp     ($d9f8).l
.c3
.xdac4  jmp     ($dac4).l
.c4
.xdaa8  jmp     ($daa8).l
.c5
LDB8E   equ     .db8e-_lloop
LHOT    equ     .xdbb0-_lloop           ; the common path's bytes
LCOPY   equ     .c5-_lloop              ; the copy's
LREL    equ     .lrel-_lloop
; _lloop's: the longword at each label less 4, offsets from _lloop
.lrel   dc.w    .a1-4-_lloop,.a2-4-_lloop,.a3-4-_lloop,.a4-4-_lloop,.a5-4-_lloop
        dc.w    .a6-4-_lloop,.c1-4-_lloop,.c2-4-_lloop,.c3-4-_lloop,.c4-4-_lloop
        dc.w    .c5-4-_lloop,.c6-4-_lloop,.c7-4-_lloop,0


; the loop with the heights blended (see above), run from its copy as _lloop
_bloop                                  ; +$d9ba
        move.w  -608(a1),d0
        move.w  -606(a1),d1
        cmp.w   d0,d1
        bge.s   .1
        move.w  d0,d1
.1      cmp.w   -640(a1),d3
        ble     .far
.near   move.w  d0,-606(a1)             ; +$d9d2
        clr.w   d0
        add.l   a4,d6
        addx.w  d0,d6
        add.l   a5,d7
        addx.w  d0,d7
        move.l  -636(a1),d2
        add.l   d2,-640(a1)
        cmp.w   -660(a1),d6
        bhi     .xda14
        cmp.w   -658(a1),d7
        bhi     .xd9f8
        movea.l (a2,d6.w*4),a0          ; +$da5c
        lea     (a0,d7.w*2),a0
        clr.w   d0
        move.b  1(a0),d0
        move.l  a0,($d888).l
.a1     move.l  d7,d2                   ; the next cell along the axis with the fraction
        swap    d2
        tst.w   d2
        beq.s   .nx
        cmp.w   -658(a1),d7
        bhs.s   .nn
        addq.l  #2,a0
        bra.s   .nb
.nx     move.l  d6,d2
        swap    d2
        tst.w   d2
        beq.s   .nn
        cmp.w   -660(a1),d6
        bhs.s   .nn
        movea.l 4(a2,d6.w*4),a0
        lea     (a0,d7.w*2),a0
.nb     move.l  d4,-(a7)
        moveq   #0,d4
        move.b  1(a0),d4
        add.w   d4,d4
        add.w   -602(a1),d4
        move.w  (a6,d4.w),d4            ; its screen height
        add.w   d0,d0
        add.w   -602(a1),d0
        move.w  (a6,d0.w),d0            ; this cell's
        sub.w   d0,d4
        lsr.w   #1,d2
        muls.w  d2,d4                   ; the difference by the fraction, rounded
        add.l   d4,d4
        add.l   #$8000,d4
        swap    d4
        add.w   d4,d0
        move.l  (a7)+,d4
        bra.s   .y1
.nn     add.w   d0,d0                   ; +$da76
        add.w   -602(a1),d0
        move.w  (0,a6,d0.w),d0
.y1     add.w   -622(a1),d0
        move.w  d0,-608(a1)
        cmp.w   d1,d0
        ble.s   .2
        move.w  d0,d1
.2      cmp.w   -640(a1),d3
        bgt     .near
.far    cmp.w   -660(a1),d4             ; +$da98
        bhi     .xdac4
        cmp.w   -658(a1),d5
        bhi     .xdaa8
        movea.l (a2,d4.w*4),a0          ; +$db0c
        lea     (a0,d5.w*2),a0
        clr.w   d0
        swap    d1
        move.w  (a0),d1
        move.b  d1,d0
        move.w  d0,($a220).l
.a2     andi.w  #$3f00,d1
        lsr.w   #3,d1
        addi.w  #-3072,d1
        swap    d1
        move.l  a0,-(a7)                ; the cell, for the span's shading
        move.l  d5,d2                   ; the next cell along the axis with the fraction
        swap    d2
        tst.w   d2
        beq.s   .fx
        cmp.w   -658(a1),d5
        bhs.s   .fn
        addq.l  #2,a0
        bra.s   .fb
.fx     move.l  d4,d2
        swap    d2
        tst.w   d2
        beq.s   .fn
        cmp.w   -660(a1),d4
        bhs.s   .fn
        movea.l 4(a2,d4.w*4),a0
        lea     (a0,d5.w*2),a0
.fb     move.l  d6,-(a7)
        moveq   #0,d6
        move.b  1(a0),d6
        add.w   d6,d6
        move.w  (a6,d6.w),d6
        add.w   d0,d0
        move.w  (a6,d0.w),d0
        sub.w   d0,d6
        lsr.w   #1,d2
        muls.w  d2,d6
        add.l   d6,d6
        add.l   #$8000,d6
        swap    d6
        add.w   d6,d0
        move.l  (a7)+,d6
        bra.s   .y2
.fn     add.w   d0,d0
        move.w  (0,a6,d0.w),d0
.y2     movea.l (a7)+,a0
        add.w   -630(a1),d0
        move.w  d0,($a21e).l
.a3     move.w  d0,-582(a1)             ; the new height
        move.w  -604(a1),d2             ; the last
        move.w  d0,-604(a1)
        cmp.w   d0,d2
        ble.s   .5
        move.w  d2,-582(a1)             ; -582: the larger, d0 the smaller
        bra.s   .3
.5      move.w  d2,d0
.3      sub.w   d0,d1
        ble.s   .4
        jsr     ($0).l                  ; _bspan, set by _landinst: START's span, then
.jb                                     ; its near part
.4      swap    d1
        tst.b   (20,a1,d1.w)
        bne.s   .xdb76
        clr.w   ($d86e).l               ; +$db88
.a5
.db8e   move.w  d3,($a226).l            ; +$db8e
.a6     clr.w   d0
        cmp.w   ($a20e).l,d3
.c1     bgt.s   .xdbb0
        add.l   a4,d4
        addx.w  d0,d4
        add.l   a5,d5
        addx.w  d0,d5
        add.l   a3,d3
        addx.w  d0,d3
        bra     _bloop
.xdbb0  jmp     ($dbb0).l
.c7
.xdb76  jmp     ($db76).l
.c6
.xda14  jmp     ($da14).l
.c2
.xd9f8  jmp     ($d9f8).l
.c3
.xdac4  jmp     ($dac4).l
.c4
.xdaa8  jmp     ($daa8).l
.c5
BDB8E   equ     .db8e-_bloop
BCOPY   equ     .c5-_bloop
BJSR    equ     .jb-4-_bloop            ; the copy's address of _bspan
BREL    equ     .lrel-_bloop
.lrel   dc.w    .a1-4-_bloop,.a2-4-_bloop,.a3-4-_bloop,.a5-4-_bloop
        dc.w    .a6-4-_bloop,.c1-4-_bloop,.c2-4-_bloop,.c3-4-_bloop,.c4-4-_bloop
        dc.w    .c5-4-_bloop,.c6-4-_bloop,.c7-4-_bloop,0
LCOPYMAX equ    BCOPY

; _bspan, from _bloop in place of START's span call (+$b6ea; its registers: d0 the span's
; top, d1 the colour and its rows, d3 x, a0 the far line's cell, d4/d5 the far line's
; walker, a1 the variables). START's span first; then the part of the span nearer than the
; far cell's edge in the near cell's colour (_bsplit). Every register and START's variables
; are back as START's span left them.
_bspan  movem.l d0-d7/a0-a6,-(a7)       ; the call's registers
        move.l  _bpx(pc),a0
        move.w  (a0),-(a7)              ; the last x (+$a226), before the span clips it
        movem.l 2(a7),d0-d7/a0-a6
        pea     .r(pc)
        move.l  _bspan0(pc),-(a7)
        rts
.r      movem.l d0-d7/a0-a6,-(a7)       ; START's span's
        IFND BSPLIT_OFF                 ; (a test define: the heights blended only)
        bsr     _bsplit
        ENDC
        movem.l (a7)+,d0-d7/a0-a6
        lea     62(a7),a7
        rts

_bspan0 dc.l    0                       ; START's span, hunk 1 +$b6ea
_bpx    dc.l    0                       ; hunk 1 +$a226, the last x; +$a23c-+$a241 the span's
_bw     dcb.w   24,0                    ; _bsplit's

; The span covers the map from the far line (d4/d5) to the next line (one cell nearer along
; the axis with the fraction, -668 or -672). START paints it all in the far line's cell's
; colour, but from that cell's edge on the map is the next cell's. At each end of the span
; (this sample and the last, the walker less its step) the far cell's part of the depth, t
; (0 to 1); the edge's height there, the far line's (-604 now, the last from -582 and d0)
; and the near line's (_bh) put apart by t; then START's span again from that edge (its top,
; slanted from the last end to this one as START's) to the span's bottom, with the near
; cell for its colour and shading. Nothing when the near part is empty or off the map.
; Called with: +4 START's span's registers (B), +64 the last x, +66 the call's (A).
_bsplit
        move.l  _bpx(pc),a0
        tst.b   $22(a0)                 ; +$a248: the span finds the cell under the pointer
        bne     .x                      ; (+$b8f2), the far one as START's
        move.l  102(a7),a1
        move.l  106(a7),a2
        move.l  122(a7),a6
        lea     _bw(pc),a3
        move.l  114(a7),d0              ; a4: whole cells, the fraction in d5's axis
        cmp.l   #1,d0
        beq.s   .ya
        cmp.l   #$ffff,d0
        beq.s   .ya
        moveq   #1,d7                   ; the fraction in d4's axis (x)
        move.l  82(a7),d2
        move.w  88(a7),d3               ; the other axis's cell
        move.l  114(a7),d4
        move.w  120(a7),d5              ; its step
        move.w  -672(a1),d6             ; the next line's side
        bra.s   .go
.ya     moveq   #0,d7
        move.l  86(a7),d2
        move.w  84(a7),d3
        move.l  118(a7),d4
        move.w  116(a7),d5
        move.w  -668(a1),d6
.go     swap    d2                      ; this end, 16.16
        swap    d4
        move.l  d2,d1
        sub.l   d4,d1                   ; the last
        move.l  d2,(a3)
        move.l  d1,4(a3)
        move.w  d3,8(a3)
        sub.w   d5,d3
        move.w  d3,10(a3)
        move.l  d2,d0
        clr.w   d0                      ; the far cell's edge on the far line's side
        tst.w   d6
        bmi.s   .neg
        add.l   #$10000,d0              ; and on the near side
        move.l  d0,d4
        sub.l   d2,d4
        move.l  d0,d5
        sub.l   d1,d5
        bra.s   .cl
.neg    move.l  d2,d4
        sub.l   d0,d4
        move.l  d1,d5
        sub.l   d0,d5
.cl     tst.l   d4
        bpl.s   .c1
        moveq   #0,d4
.c1     cmp.l   #$10000,d4
        ble.s   .c2
        move.l  #$10000,d4
.c2     tst.l   d5
        bpl.s   .c3
        moveq   #0,d5
.c3     cmp.l   #$10000,d5
        ble.s   .c4
        move.l  #$10000,d5
.c4     cmp.l   #$10000,d4
        bne.s   .vis
        cmp.l   #$10000,d5
        beq     .x                      ; all the far cell's
.vis    move.l  d4,12(a3)               ; t, this end
        move.l  d5,16(a3)               ; the last
        move.l  (a3),d0                 ; the near cell
        swap    d0
        add.w   d6,d0
        move.w  8(a3),d1
        tst.w   d7
        bne.s   .nx
        cmp.w   -660(a1),d1
        bhi     .x
        cmp.w   -658(a1),d0
        bhi     .x
        movea.l (a2,d1.w*4),a0
        lea     (a0,d0.w*2),a0
        bra.s   .nc
.nx     cmp.w   -660(a1),d0
        bhi     .x
        cmp.w   -658(a1),d1
        bhi     .x
        movea.l (a2,d0.w*4),a0
        lea     (a0,d1.w*2),a0
.nc     move.l  a0,20(a3)
        IFND BSKIP_OFF
        move.l  32+66(a7),a4            ; the far cell: the same tile and shading, nothing
        move.w  (a0),d0                 ; to draw (the shading as START's span's, +$ba7c)
        move.w  (a4),d1
        eor.w   d1,d0
        andi.w  #$3f00,d0
        bne.s   .dif
        bsr     _bshade
        move.w  d0,d1
        move.l  a4,a0
        bsr     _bshade
        move.l  20(a3),a0
        cmp.w   d0,d1
        beq     .x
        ENDC
.dif    move.w  (a0),d0                 ; its colour, as START's
        andi.w  #$3f00,d0
        lsr.w   #3,d0
        addi.w  #-3072,d0
        move.w  d0,24(a3)
        move.w  d6,d5                   ; the near line, a cell on
        ext.l   d5
        swap    d5
        clr.w   d5
        move.l  (a3),d0
        add.l   d5,d0
        move.w  8(a3),d1
        bsr     _bh
        bcs     .x
        move.w  d0,26(a3)               ; its height, this end
        move.l  4(a3),d0
        add.l   d5,d0
        move.w  10(a3),d1
        bsr     _bh
        bcs     .x
        move.w  d0,28(a3)               ; the last
        move.w  -604(a1),d0             ; the far line's, this end
        move.w  -582(a1),d1
        add.w   68(a7),d1
        sub.w   d0,d1                   ; the last
        move.w  26(a3),d2               ; the edge, this end
        sub.w   d0,d2
        ext.l   d2
        muls.l  12(a3),d2
        add.l   #$8000,d2
        swap    d2
        add.w   d0,d2
        move.w  28(a3),d3               ; the last
        sub.w   d1,d3
        ext.l   d3
        muls.l  16(a3),d3
        add.l   #$8000,d3
        swap    d3
        add.w   d1,d3
        cmp.w   d0,d2                   ; neither end above the far line (the near line
        bge.s   .t1                     ; above it: the span is START's only)
        move.w  d0,d2
.t1     cmp.w   d1,d3
        bge.s   .t2
        move.w  d1,d3
.t2     move.w  68(a7),d4               ; the span's bottom
        add.w   72(a7),d4
        move.w  d2,d5
        cmp.w   d3,d5
        ble.s   .m
        move.w  d3,d5                   ; the near part's top
.m      move.w  68(a7),d6               ; on a row of the parity of START's span's top: its
        eor.w   d5,d6                   ; dither then the same (START takes it from the top
        btst    #0,d6                   ; row, +$bba4)
        beq.s   .m0
        addq.w  #1,d2                   ; else a row lower
        addq.w  #1,d3
        addq.w  #1,d5
.m0     move.w  d2,d6
        cmp.w   d3,d6
        bge.s   .mm
        move.w  d3,d6                   ; and its lower end
.mm     sub.w   d5,d4                   ; its rows
        ble     .x
        move.w  d5,42(a3)
        move.w  d4,44(a3)
        move.w  -582(a1),30(a3)         ; START's span's state
        move.w  -604(a1),32(a3)
        move.l  _bpx(pc),a0
        move.w  (a0),34(a3)
        move.l  $16(a0),36(a3)
        move.w  $1a(a0),40(a3)
        move.w  64(a7),(a0)             ; the last x as at START's span
        move.w  d6,-582(a1)
        move.w  d2,-604(a1)
        movem.l 66(a7),d0-d7/a0-a6      ; the call's registers but d0, d1 and a0
        lea     _bw(pc),a0
        move.w  42(a0),d0
        move.w  24(a0),d1
        swap    d1
        move.w  44(a0),d1
        move.l  20(a0),a0
        pea     .r(pc)
        move.l  _bspan0(pc),-(a7)
        rts
.r      lea     _bw(pc),a3
        move.l  102(a7),a1
        move.w  30(a3),-582(a1)
        move.w  32(a3),-604(a1)
        move.l  _bpx(pc),a0
        move.w  34(a3),(a0)
        move.l  36(a3),$16(a0)
        move.w  40(a3),$1a(a0)
.x      rts

; _bshade: a0 a cell, a1 the variables: d0.w the slope's part of its shading as START's span
; takes it (+$ba7c-+$ba9a: the top two bits of the cell, the next and the next row's)
_bshade movem.l d1/a0,-(a7)
        move.b  (a0),d0
        andi.w  #192,d0
        add.w   d0,d0
        move.b  2(a0),d1
        andi.w  #192,d1
        add.w   d1,d0
        adda.w  -964(a1),a0
        move.w  (a0),d1
        andi.w  #192,d1
        add.w   d1,d0
        movem.l (a7)+,d1/a0
        rts

; _bh: d0 16.16 on the axis with the fraction, d1.w the other axis's cell, d7 1 if the
; fraction is in x; a1, a2, a6 the loop's. d0.w the height on the screen there as the loop's
; near line (-602, -622), blended as _bloop's; carry set off the map
_bh     movem.l d1-d4/a0,-(a7)
        move.l  d0,d2
        swap    d2                      ; the cell
        move.w  d0,d3                   ; the fraction
        tst.w   d7
        bne.s   .x
        cmp.w   -660(a1),d1
        bhi     .off
        cmp.w   -658(a1),d2
        bhi     .off
        movea.l (a2,d1.w*4),a0
        lea     (a0,d2.w*2),a0
        moveq   #0,d4
        move.b  1(a0),d4
        tst.w   d3
        beq.s   .one
        cmp.w   -658(a1),d2
        bhs.s   .one
        moveq   #0,d1
        move.b  3(a0),d1
        bra.s   .two
.x      cmp.w   -660(a1),d2
        bhi     .off
        cmp.w   -658(a1),d1
        bhi     .off
        movea.l (a2,d2.w*4),a0
        lea     (a0,d1.w*2),a0
        moveq   #0,d4
        move.b  1(a0),d4
        tst.w   d3
        beq.s   .one
        cmp.w   -660(a1),d2
        bhs.s   .one
        movea.l 4(a2,d2.w*4),a0
        lea     (a0,d1.w*2),a0
        moveq   #0,d1
        move.b  1(a0),d1
.two    add.w   d1,d1
        add.w   -602(a1),d1
        move.w  (a6,d1.w),d1
        add.w   d4,d4
        add.w   -602(a1),d4
        move.w  (a6,d4.w),d4
        sub.w   d4,d1
        lsr.w   #1,d3
        muls.w  d3,d1
        add.l   d1,d1
        add.l   #$8000,d1
        swap    d1
        add.w   d1,d4
        bra.s   .y
.one    add.w   d4,d4
        add.w   -602(a1),d4
        move.w  (a6,d4.w),d4
.y      add.w   -622(a1),d4
        move.w  d4,d0
        movem.l (a7)+,d1-d4/a0
        andi    #$fe,ccr
        rts
.off    movem.l (a7)+,d1-d4/a0
        ori     #1,ccr
        rts
