;---------------------------------------------------------------------------
; The AGA game's chunky-to-planar conversion for the 68020/030 (RobinSonSRequiemAga.asm
; includes it): Mikael Kalms' public-domain c2p1x1_8_c5_030_2 (2000-04-17, in
; $AMIGA_SHARE/kalms-c2p), changed for START's planes and its rectangle.
;
; START's loop (hunk 2 +$2e84) converts the 3D window's rectangle row by row, a byte per
; pixel into eight planes, with byte reads and byte writes. It is entered with
;   a0          the rectangle's first chunky byte
;   a3/a4/a5/a6 planes 0, 2, 4 and 6 at the rectangle's first row; planes 1, 3, 5 and 7 are
;               C2P_BPL bytes after each (the planes of the two buffers interleave). Planes
;               0 and 1 are in the slave's reserved chip block, 2-7 elsewhere
;   d6.w        the width in 16 pixels, - 1;  d7.w the rows, - 1
;   hunk 2 +$2db2.w, +$2db4.w   the chunky and the plane modulos, added after each row
; Chunky bit n goes to plane n.
;
; Kalms' kernel converts 32 pixels per step in two passes: the first writes planes 0-3
; and keeps half of each step in a buffer, the second writes planes 4-7 from it. His
; kernel writes the four planes of a pass at one spacing from one base; here each pass has
; two bases, a1 (planes 0 and 1, or 4 and 5) and a6 (2 and 3, or 6 and 7), with the
; mask in a6 moved to an immediate. The rest of the kernel is his, instruction for
; instruction. _c2p030 runs both passes for each row with the rows' strides as START
; computes them, the buffer on the stack; a width that is not a multiple of 32 pixels
; (and 0) goes to START's loop.
;---------------------------------------------------------------------------

C2P_BPL         = 16000                 ; plane n to plane n + 1, as START's loop
C2P_MAXW        = 320
C2P_FRAME       = 36+C2P_MAXW/2+8


_c2p030
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
        lea     -C2P_FRAME(a7),a7
        movem.l d0-d3,(a7)              ; 0 width, 4 chunky stride, 8 plane stride, 12 rows
        movem.l a0/a3-a6,16(a7)         ; 16 chunky row, 20/24/28/32 planes 0, 2, 4, 6
.row    move.l  16(a7),a0
        move.l  20(a7),a1
        lea     C2P_BPL(a1),a1
        move.l  24(a7),a6
        lea     36(a7),a3
        move.l  (a7),d1
        bsr     c2p030_pass1
        lea     36(a7),a0
        move.l  28(a7),a1
        lea     C2P_BPL(a1),a1
        move.l  32(a7),a6
        move.l  (a7),d1
        bsr     c2p030_pass2
        move.l  4(a7),d0
        add.l   d0,16(a7)
        move.l  8(a7),d0
        add.l   d0,20(a7)
        add.l   d0,24(a7)
        add.l   d0,28(a7)
        add.l   d0,32(a7)
        subq.l  #1,12(a7)
        bpl     .row
        lea     C2P_FRAME(a7),a7
        rts
.old    move.l  _hunk2(pc),a1           ; START's loop: its first instruction, then the rest
        move.w  d6,$2db6(a1)
        add.l   #$2e8a,a1
        jmp     (a1)

; Pass 1. a0 chunky row, d1.l pixels (a multiple of 32), a1 plane 0 + C2P_BPL, a6 plane 2,
; a3 the buffer (pixels / 2 bytes). Writes planes 0-3. Reads a longword past the row.
c2p030_pass1
        lea     4(a0,d1.l),a2
        move.l  #$f0f0f0f0,d6

        move.l  (a0)+,d2
        move.l  d2,d7
        lsl.l   #4,d7
        move.l  (a0)+,d0
        move.l  (a0)+,d3
        move.l  (a0)+,d1
        eor.l   d0,d7
        and.l   d6,d7
        eor.l   d7,d0
        lsr.l   #4,d7
        eor.l   d7,d2
        move.l  d3,d7
        lsl.l   #4,d7
        eor.l   d1,d7
        and.l   d6,d7
        eor.l   d7,d1
        move.l  d2,(a3)+
        lsr.l   #4,d7
        eor.l   d7,d3
        move.l  d3,(a3)+

        move.l  (a0)+,d4
        move.l  d4,d7
        lsl.l   #4,d7
        move.l  (a0)+,d2
        move.l  (a0)+,d5
        move.l  (a0)+,d3
        eor.l   d2,d7
        and.l   d6,d7
        eor.l   d7,d2
        lsr.l   #4,d7
        eor.l   d7,d4
        move.l  d5,d7
        lsl.l   #4,d7
        eor.l   d3,d7
        and.l   d6,d7
        eor.l   d7,d3
        move.l  d4,(a3)+
        lsr.l   #4,d7
        eor.l   d7,d5
        move.l  d5,(a3)+

        move.w  d2,d7                   ; Swap 16x2
        move.w  d0,d2
        swap    d2
        move.w  d2,d0
        move.w  d7,d2

        move.w  d3,d7
        move.w  d1,d3
        swap    d3
        move.w  d3,d1
        move.w  d7,d3

        bra.s   .start1
.x1
        move.l  (a0)+,d0
        move.l  (a0)+,d3
        move.l  (a0)+,d1
        move.l  d7,(a6)                 ; plane 2
        move.l  d2,d7
        lsl.l   #4,d7
        eor.l   d0,d7
        and.l   d6,d7
        eor.l   d7,d0
        lsr.l   #4,d7
        eor.l   d7,d2
        move.l  d3,d7
        lsl.l   #4,d7
        eor.l   d1,d7
        and.l   d6,d7
        eor.l   d7,d1
        move.l  d2,(a3)+
        lsr.l   #4,d7
        eor.l   d7,d3
        move.l  d3,(a3)+
        move.l  d5,a5

        move.l  (a0)+,d4
        move.l  d4,d7
        lsl.l   #4,d7
        move.l  (a0)+,d2
        move.l  (a0)+,d5
        move.l  (a0)+,d3
        move.l  a4,(a1)+                ; plane 1
        addq.l  #4,a6
        eor.l   d2,d7
        and.l   d6,d7
        eor.l   d7,d2
        lsr.l   #4,d7
        eor.l   d7,d4
        move.l  d5,d7
        lsl.l   #4,d7
        eor.l   d3,d7
        and.l   d6,d7
        eor.l   d7,d3
        lsr.l   #4,d7
        eor.l   d7,d5

        move.w  d2,d7                   ; Swap 16x2
        move.w  d0,d2
        swap    d2
        move.w  d2,d0
        move.l  d4,(a3)+
        move.w  d7,d2

        move.w  d3,d7
        move.w  d1,d3
        move.l  d5,(a3)+
        swap    d3
        move.w  d3,d1
        move.w  d7,d3

        move.l  a5,-C2P_BPL-4(a1)       ; plane 0
.start1
        move.l  #$33333333,d5

        move.l  d2,d7                   ; Swap 2x2
        lsr.l   #2,d7
        eor.l   d0,d7
        and.l   d5,d7
        eor.l   d7,d0
        lsl.l   #2,d7
        eor.l   d7,d2

        move.l  d3,d7
        lsr.l   #2,d7
        eor.l   d1,d7
        and.l   d5,d7
        eor.l   d7,d1
        lsl.l   #2,d7
        eor.l   d7,d3

        move.l  #$00ff00ff,d4
        move.l  #$55555555,d5

        move.l  d1,d7
        lsr.l   #8,d7
        eor.l   d0,d7
        and.l   d4,d7
        eor.l   d7,d0
        lsl.l   #8,d7
        eor.l   d7,d1

        move.l  d1,d7
        lsr.l   #1,d7
        eor.l   d0,d7
        and.l   d5,d7
        eor.l   d7,d0
        move.l  d0,C2P_BPL(a6)          ; plane 3
        add.l   d7,d7
        eor.l   d1,d7

        move.l  d3,d1
        lsr.l   #8,d1
        eor.l   d2,d1
        and.l   d4,d1
        eor.l   d1,d2
        lsl.l   #8,d1
        eor.l   d1,d3

        move.l  d3,d1
        lsr.l   #1,d1
        eor.l   d2,d1
        and.l   d1,d5
        eor.l   d5,d2
        move.l  d2,a4
        move.l  (a0)+,d2
        add.l   d5,d5
        eor.l   d3,d5

        cmpa.l  a0,a2
        bne     .x1

        move.l  d7,(a6)                 ; plane 2
        move.l  a4,(a1)+                ; plane 1
        move.l  d5,-C2P_BPL-4(a1)       ; plane 0
        rts

; Pass 2. a0 the buffer, d1.l pixels, a1 plane 4 + C2P_BPL, a6 plane 6. Writes planes 4-7.
; Reads a longword past the buffer.
c2p030_pass2
        lsr.l   #1,d1
        lea     4(a0,d1.l),a2

        move.l  (a0)+,d0
        move.l  #$55555555,d4
        move.l  #$33333333,d5
        move.l  #$00ff00ff,d6
        move.l  (a0)+,d1
        move.l  (a0)+,d2
        move.l  (a0)+,d3

        move.w  d2,d7                   ; Swap 16x2
        move.w  d0,d2
        swap    d2
        move.w  d2,d0
        move.w  d7,d2

        move.w  d3,d7
        move.w  d1,d3
        swap    d3
        move.w  d3,d1
        move.w  d7,d3

        move.l  d2,d7                   ; Swap 2x2
        lsr.l   #2,d7
        eor.l   d0,d7
        and.l   d5,d7
        eor.l   d7,d0
        lsl.l   #2,d7
        eor.l   d7,d2

        move.l  d3,d7
        lsr.l   #2,d7
        eor.l   d1,d7
        and.l   d5,d7
        eor.l   d7,d1
        lsl.l   #2,d7
        eor.l   d7,d3

        move.l  d1,d7
        lsr.l   #8,d7
        bra.s   .start2
.x2
        move.l  (a0)+,d1
        move.l  (a0)+,d2
        move.l  (a0)+,d3
        move.l  d7,(a6)                 ; plane 6
        move.w  d2,d7                   ; Swap 16x2
        move.w  d0,d2
        swap    d2
        move.w  d2,d0
        move.w  d7,d2

        move.w  d3,d7
        move.w  d1,d3
        swap    d3
        move.w  d3,d1
        move.w  d7,d3

        move.l  d2,d7                   ; Swap 2x2
        lsr.l   #2,d7
        eor.l   d0,d7
        move.l  a4,(a1)+                ; plane 5
        addq.l  #4,a6
        and.l   d5,d7
        eor.l   d7,d0
        lsl.l   #2,d7
        eor.l   d7,d2

        move.l  d3,d7
        lsr.l   #2,d7
        eor.l   d1,d7
        and.l   d5,d7
        eor.l   d7,d1
        lsl.l   #2,d7
        eor.l   d7,d3

        move.l  d1,d7
        lsr.l   #8,d7
        move.l  a5,-C2P_BPL-4(a1)       ; plane 4
.start2
        eor.l   d0,d7
        and.l   d6,d7
        eor.l   d7,d0
        lsl.l   #8,d7
        eor.l   d7,d1

        move.l  d1,d7
        lsr.l   #1,d7
        eor.l   d0,d7
        and.l   d4,d7
        eor.l   d7,d0
        add.l   d7,d7
        eor.l   d1,d7

        move.l  d3,d1
        move.l  d0,C2P_BPL(a6)          ; plane 7
        lsr.l   #8,d1
        eor.l   d2,d1
        and.l   d6,d1
        eor.l   d1,d2
        lsl.l   #8,d1
        eor.l   d1,d3

        move.l  d3,d1
        lsr.l   #1,d1
        eor.l   d2,d1
        and.l   d4,d1
        eor.l   d1,d2
        add.l   d1,d1
        eor.l   d1,d3

        move.l  (a0)+,d0
        move.l  d2,a4
        move.l  d3,a5

        cmpa.l  a0,a2
        bne     .x2

        move.l  d7,(a6)                 ; plane 6
        move.l  a4,(a1)+                ; plane 5
        move.l  a5,-C2P_BPL-4(a1)       ; plane 4
        rts

