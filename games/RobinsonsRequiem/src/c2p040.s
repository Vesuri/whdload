;---------------------------------------------------------------------------
; The AGA game's chunky-to-planar conversion for the 68040 and 68060 (RobinSonSRequiemAga.asm
; includes it after c2p030.s; _c2ppatch picks it on those CPUs): Mikael Kalms'
; public-domain c2p1x1_8_c5_040 (2000-04-11, in $AMIGA_SHARE/kalms-c2p/normal), changed
; for START's planes and its rectangle.
;
; Entered as _c2p030 (c2p030.s): a0 the rectangle's first chunky byte, a3/a4/a5/a6 planes
; 0, 2, 4 and 6 at its first row, planes 1, 3, 5 and 7 C2P_BPL bytes after each, d6.w the
; width in 16 pixels - 1, d7.w the rows - 1, the modulos at hunk 2 +$2db2.w and +$2db4.w.
;
; Kalms' kernel converts 32 pixels per step in one pass and writes the eight planes in the
; order 7, 3, 6, 2, 5, 1, 4, 0 through one pointer, moved between them by eight deltas his
; init computes from one plane size. Here the deltas are the differences between START's
; eight plane addresses (the same at every row), computed per call; the kernel runs once
; per row with the row's chunky and plane 7 addresses. The rest of the kernel is his,
; instruction for instruction, but for his four cache-line touches (tst.b 16(a0) and
; 32(a0)), which read up to 17 bytes past the row: the chunky buffer is the first block
; from the fast pool's top. A width that is not a multiple of 32 pixels (and 0) goes to
; START's loop, as in _c2p030.
;---------------------------------------------------------------------------

C2P4_FRAME      = 24

_c2p040
        moveq   #0,d0
        move.w  d6,d0
        addq.w  #1,d0                   ; width in 16 pixels
        btst    #0,d0
        bne     .old
        lsl.l   #4,d0                   ; width in pixels: 32, 64, ...
        beq     .old
        cmp.l   #C2P_MAXW,d0
        bhi     .old
        move.l  _hunk2(pc),a1
        move.w  $2db2(a1),d1            ; chunky modulo
        ext.l   d1
        add.l   d0,d1                   ; chunky row stride
        move.w  $2db4(a1),d2            ; plane modulo
        ext.l   d2
        move.l  d0,d3
        lsr.l   #3,d3
        add.l   d3,d2                   ; plane row stride
        moveq   #0,d3
        move.w  d7,d3                   ; rows - 1
        ; the deltas: a1 visits p7 p3 p6 p2 p5 p1 p4 p0 (pN plane N), then p7 + 4
        lea     c2p040_d(pc),a1
        move.l  a6,d4
        sub.l   a4,d4                   ; p7 - p3 = p6 - p2
        move.l  d4,4*5(a1)              ; delta5: p7 - p3 (sub)
        move.l  d4,4*7(a1)              ; delta7: p6 - p2 (sub)
        move.l  a6,d4
        sub.l   a4,d4
        sub.l   #C2P_BPL,d4
        move.l  d4,4*6(a1)              ; delta6: p6 - p3 (add)
        move.l  a5,d4
        sub.l   a4,d4
        add.l   #C2P_BPL,d4
        move.l  d4,4*8(a1)              ; delta8: p5 - p2 (add)
        move.l  a5,d4
        sub.l   a3,d4                   ; p5 - p1 = p4 - p0
        move.l  d4,4*1(a1)              ; delta1: p5 - p1 (sub)
        move.l  d4,4*3(a1)              ; delta3: p4 - p0 (sub)
        sub.l   #C2P_BPL,d4
        move.l  d4,4*2(a1)              ; delta2: p4 - p1 (add)
        move.l  a6,d4
        sub.l   a3,d4
        add.l   #C2P_BPL+4,d4
        move.l  d4,4*4(a1)              ; delta4: p7 - p0 + 4 (add)
        lea     -C2P4_FRAME(a7),a7
        movem.l d0-d3,(a7)              ; 0 width, 4 chunky stride, 8 plane stride, 12 rows
        move.l  a0,16(a7)               ; 16 chunky row
        lea     C2P_BPL(a6),a1
        move.l  a1,20(a7)               ; 20 plane 7 at the row
.row    move.l  16(a7),a0
        move.l  20(a7),a1
        move.l  (a7),d0
        bsr     c2p040_row
        move.l  4(a7),d0
        add.l   d0,16(a7)
        move.l  8(a7),d0
        add.l   d0,20(a7)
        subq.l  #1,12(a7)
        bpl     .row
        lea     C2P4_FRAME(a7),a7
        rts
.old    move.l  _hunk2(pc),a1           ; START's loop: its first instruction, then the rest
        move.w  d6,$2db6(a1)
        add.l   #$2e8a,a1
        jmp     (a1)

; One row. a0 chunky row, d0.l pixels (a multiple of 32), a1 plane 7 at the row. Trashes
; d0-d7/a0-a6 but a2.
c2p040_row
        add.l   a0,d0
        move.l  d0,-(sp)

        move.l  (a0)+,d0
        move.l  (a0)+,d1
        move.l  (a0)+,d2
        move.l  (a0)+,d3
        move.l  (a0)+,d4
        move.l  (a0)+,d5
        move.l  (a0)+,a5
        move.l  (a0)+,a6

        swap    d4                      ; Swap 16x4, part 1
        swap    d5
        eor.w   d0,d4
        eor.w   d1,d5
        eor.w   d4,d0
        eor.w   d5,d1
        eor.w   d0,d4
        eor.w   d1,d5
        swap    d4
        swap    d5

        move.l  d4,d6                   ; Swap 2x4, part 1
        move.l  d5,d7
        lsr.l   #2,d6
        lsr.l   #2,d7
        eor.l   d0,d6
        eor.l   d1,d7
        and.l   #$33333333,d6
        and.l   #$33333333,d7
        eor.l   d6,d0
        eor.l   d7,d1
        lsl.l   #2,d6
        lsl.l   #2,d7
        eor.l   d6,d4
        eor.l   d7,d5

        exg     d4,a5
        exg     d5,a6

        swap    d4                      ; Swap 16x4, part 2
        swap    d5
        eor.w   d2,d4
        eor.w   d3,d5
        eor.w   d4,d2
        eor.w   d5,d3
        eor.w   d2,d4
        eor.w   d3,d5
        swap    d4
        swap    d5

        move.l  d4,d6                   ; Swap 2x4, part 1
        move.l  d5,d7
        lsr.l   #2,d6
        lsr.l   #2,d7
        eor.l   d2,d6
        eor.l   d3,d7
        and.l   #$33333333,d6
        and.l   #$33333333,d7
        eor.l   d6,d2
        eor.l   d7,d3
        lsl.l   #2,d6
        lsl.l   #2,d7
        eor.l   d6,d4
        eor.l   d7,d5

        move.l  d1,d6                   ; Swap 4x1, part 1
        move.l  d3,d7
        lsr.l   #4,d6
        lsr.l   #4,d7
        eor.l   d0,d6
        eor.l   d2,d7
        and.l   #$0f0f0f0f,d6
        and.l   #$0f0f0f0f,d7
        eor.l   d6,d0
        eor.l   d7,d2
        lsl.l   #4,d6
        lsl.l   #4,d7
        eor.l   d6,d1
        eor.l   d7,d3

        move.l  d2,d6                   ; Swap 8x2, part 1
        move.l  d3,d7
        lsr.l   #8,d6
        lsr.l   #8,d7
        eor.l   d0,d6
        eor.l   d1,d7
        and.l   #$00ff00ff,d6
        and.l   #$00ff00ff,d7
        eor.l   d6,d0
        eor.l   d7,d1
        lsl.l   #8,d6
        lsl.l   #8,d7
        eor.l   d6,d2
        eor.l   d7,d3

        bra     .start

        cnop    0,4
.x
        move.l  (a0)+,d0
        move.l  (a0)+,d1
        move.l  (a0)+,d2
        move.l  (a0)+,d3
        move.l  (a0)+,d4
        move.l  (a0)+,d5
        move.l  (a0)+,a5
        move.l  (a0)+,a6

        move.l  d6,(a1)

        swap    d4                      ; Swap 16x4, part 1
        swap    d5
        eor.w   d0,d4
        eor.w   d1,d5
        eor.w   d4,d0
        eor.w   d5,d1
        eor.w   d0,d4
        sub.l   c2p040_d+4*1(pc),a1
        eor.w   d1,d5
        swap    d4
        swap    d5

        move.l  d4,d6                   ; Swap 2x4, part 1
        move.l  d7,(a1)
        move.l  d5,d7
        lsr.l   #2,d6
        lsr.l   #2,d7
        eor.l   d0,d6
        eor.l   d1,d7
        and.l   #$33333333,d6
        and.l   #$33333333,d7
        eor.l   d6,d0
        eor.l   d7,d1
        lsl.l   #2,d6
        lsl.l   #2,d7
        eor.l   d6,d4
        eor.l   d7,d5

        exg     d4,a5
        add.l   c2p040_d+4*2(pc),a1
        exg     d5,a6

        swap    d4                      ; Swap 16x4, part 2
        swap    d5
        eor.w   d2,d4
        eor.w   d3,d5
        eor.w   d4,d2
        eor.w   d5,d3
        eor.w   d2,d4
        eor.w   d3,d5
        swap    d4
        swap    d5

        move.l  a3,(a1)
        move.l  d4,d6                   ; Swap 2x4, part 2
        move.l  d5,d7
        lsr.l   #2,d6
        lsr.l   #2,d7
        eor.l   d2,d6
        eor.l   d3,d7
        and.l   #$33333333,d6
        and.l   #$33333333,d7
        eor.l   d6,d2
        eor.l   d7,d3
        lsl.l   #2,d6
        lsl.l   #2,d7
        eor.l   d6,d4
        eor.l   d7,d5

        move.l  d1,d6                   ; Swap 4x1, part 1
        move.l  d3,d7
        lsr.l   #4,d6
        lsr.l   #4,d7
        eor.l   d0,d6
        eor.l   d2,d7
        and.l   #$0f0f0f0f,d6
        and.l   #$0f0f0f0f,d7
        sub.l   c2p040_d+4*3(pc),a1
        eor.l   d6,d0
        eor.l   d7,d2
        lsl.l   #4,d6
        lsl.l   #4,d7
        eor.l   d6,d1
        move.l  a4,(a1)
        eor.l   d7,d3

        move.l  d2,d6                   ; Swap 8x2, part 1
        move.l  d3,d7
        lsr.l   #8,d6
        lsr.l   #8,d7
        eor.l   d0,d6
        eor.l   d1,d7
        and.l   #$00ff00ff,d6
        and.l   #$00ff00ff,d7
        eor.l   d6,d0
        eor.l   d7,d1
        lsl.l   #8,d6
        lsl.l   #8,d7
        eor.l   d6,d2
        add.l   c2p040_d+4*4(pc),a1
        eor.l   d7,d3
.start

        move.l  d2,d6                   ; Swap 1x2, part 1
        move.l  d3,d7
        lsr.l   #1,d6
        lsr.l   #1,d7
        eor.l   d0,d6
        eor.l   d1,d7
        and.l   #$55555555,d6
        and.l   #$55555555,d7
        eor.l   d6,d0
        eor.l   d7,d1
        move.l  d0,(a1)
        add.l   d6,d6
        add.l   d7,d7
        eor.l   d6,d2
        eor.l   d7,d3

        move.l  a5,d6
        move.l  a6,d7
        move.l  d2,a3
        move.l  d3,a4

        move.l  d5,d2                   ; Swap 4x1, part 2
        move.l  d7,d3
        lsr.l   #4,d2
        lsr.l   #4,d3
        sub.l   c2p040_d+4*5(pc),a1
        eor.l   d4,d2
        eor.l   d6,d3
        and.l   #$0f0f0f0f,d2
        and.l   #$0f0f0f0f,d3
        eor.l   d2,d4
        move.l  d1,(a1)
        eor.l   d3,d6

        lsl.l   #4,d2
        lsl.l   #4,d3
        eor.l   d2,d5
        eor.l   d3,d7

        move.l  d4,d2                   ; Swap 8x2, part 2
        move.l  d5,d3
        lsr.l   #8,d2
        lsr.l   #8,d3
        add.l   c2p040_d+4*6(pc),a1
        eor.l   d6,d2
        eor.l   d7,d3
        and.l   #$00ff00ff,d2
        and.l   #$00ff00ff,d3
        eor.l   d2,d6
        move.l  a3,(a1)
        eor.l   d3,d7

        lsl.l   #8,d2
        lsl.l   #8,d3
        eor.l   d2,d4
        eor.l   d3,d5

        move.l  d4,d2                   ; Swap 1x2, part 2
        move.l  d5,d3
        sub.l   c2p040_d+4*7(pc),a1
        lsr.l   #1,d2
        lsr.l   #1,d3
        eor.l   d6,d2
        eor.l   d7,d3
        and.l   #$55555555,d2
        move.l  a4,(a1)
        and.l   #$55555555,d3

        eor.l   d2,d6
        eor.l   d3,d7
        add.l   d2,d2
        add.l   d3,d3
        eor.l   d2,d4
        eor.l   d3,d5

        add.l   c2p040_d+4*8(pc),a1
        move.l  d4,a3
        move.l  d5,a4

        cmp.l   (sp),a0
        bne     .x

        move.l  d6,(a1)
        sub.l   c2p040_d+4*1(pc),a1
        move.l  d7,(a1)
        add.l   c2p040_d+4*2(pc),a1
        move.l  a3,(a1)
        sub.l   c2p040_d+4*3(pc),a1
        move.l  a4,(a1)

        addq.l  #4,sp
        rts

        cnop    0,4
c2p040_d        dc.l    0,0,0,0,0,0,0,0,0       ; Kalms' delta0-8 (delta0 unused)
