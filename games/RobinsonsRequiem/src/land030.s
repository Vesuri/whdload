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
; _landinst: a0 START's hunk 1, a1 LCOPY bytes, 16-byte aligned, for the copy. Checks the
; loop's words (a checksum with the relocated addresses taken back to their offsets),
; copies _lloop to a1, relocates the copy's addresses of hunk 1 and writes the two jmps; d0
; non-zero if it did. The caller flushes the caches.

LSTART  equ     $d9ba
LEND    equ     $dbb0
LSUM    equ     $870e378f               ; the checksum of START's +$d9ba-+$dbaf

_landinst
        movem.l d1-d4/a1-a3,-(a7)
        moveq   #0,d0
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
        lea     _lloop(pc),a1           ; the copy
        move.l  a3,a2
        move.w  #LCOPY/2-1,d1
.c      move.w  (a1)+,(a2)+
        dbf     d1,.c
        lea     _lloop(pc),a2           ; its addresses in hunk 1
        add.w   #LREL,a2
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
        lea     LDB8E(a3),a1
        move.l  a1,(a2)
        moveq   #1,d0
.x      movem.l (a7)+,d1-d4/a1-a3
        rts
; START's relocated addresses in the loop, hunk 1 offsets; 0 ends
.rel    dc.w    $da72,$db24,$db40,$db8a,$db90,$db98,0

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

