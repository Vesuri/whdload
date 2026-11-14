; The ECS game's chunky-to-planar conversion for the 68000 (RobinsonSRequiemEcs.asm includes
; it; docs/internals.md, "ECS improvements").
;
; START's loop (hunk 2 +$1a5e-$1b97) converts the 3D window's rectangle row by row, 16
; pixels at a time, into four planes, a bit at a time with add/addx: about 40 cycles a pixel.
; A chunky byte carries a dither: pixel 4n+j of a row is the high nibble of its byte when j
; is even, the low nibble when it is odd. Nibble bit k goes to plane k, pixel 0 of 16 to bit
; 15. Entered (jmp, START's registers on the stack) with
;   a0      the rectangle's first chunky byte (even)
;   a1, a2  planes 0 and 2 at the rectangle's first row; planes 1 and 3 are 16,000 bytes on
;   d6.w    the width in 16 pixels, - 1;  d7.w the rows, - 1
;   a6.w    the plane modulo; <hunk 2 +$46>.w the chunky modulo (_c2pmod has its address)
; and ends as START's routine does (+$1b98: movem.l (a7)+,d0-a6 / rts).
;
; This one merges a longword at a time. Each pair of chunky longwords (pixels 0-3 and 4-7)
; becomes one longword of nibbles, byte j holding pixels j and j+4: a 4-bit exchange and a
; byte select. The two longwords of 16 pixels then go through four exchanges (8, 1, 16 and
; 2 bits) into the four plane words. About 32 cycles a pixel. tools/rr_ecsc2pcheck.py checks
; it against START's loop under Unicorn.

C2P_ECSBPL      = 16000                 ; plane 0 to 1, 2 to 3

_c2p000
        move.l  _c2pmod(pc),a5
        move.w  d6,a4
        move.w  d7,-(a7)                ; rows - 1, counted as dbf does
        move.l  #$0f0f0f0f,d5
        move.l  #$00ff00ff,d7
.row    move.w  a4,d6
.blk    movem.l (a0)+,d0-d3             ; pixels 0-3, 4-7, 8-11, 12-15
        move.l  d1,d4                   ; d0/d1: d0's low nibbles <-> d1's high ones
        lsr.l   #4,d4
        eor.l   d0,d4
        and.l   d5,d4
        eor.l   d4,d0
        lsl.l   #4,d4
        eor.l   d4,d1
        move.b  d1,d0                   ; d0 bytes 0 and 2, d1 bytes 1 and 3: pixels j, j+4
        swap    d0
        swap    d1
        move.b  d1,d0                   ; d0 = bytes 2, 3, 0, 1
        move.l  d3,d4                   ; the same for d2/d3
        lsr.l   #4,d4
        eor.l   d2,d4
        and.l   d5,d4
        eor.l   d4,d2
        lsl.l   #4,d4
        eor.l   d4,d3
        move.b  d3,d2
        swap    d2
        swap    d3
        move.b  d3,d2
        move.l  d2,d4                   ; 8-bit exchange
        lsr.l   #8,d4
        eor.l   d0,d4
        and.l   d7,d4
        eor.l   d4,d0
        lsl.l   #8,d4
        eor.l   d4,d2
        move.l  d2,d4                   ; 1-bit exchange
        lsr.l   #1,d4
        eor.l   d0,d4
        and.l   #$55555555,d4
        eor.l   d4,d0
        add.l   d4,d4
        eor.l   d4,d2
        move.w  d2,d4                   ; 16-bit exchange: d2 = d0.l:d2.l, d0 = d0.h:d2.h
        move.w  d0,d2
        swap    d2
        move.w  d2,d0
        move.w  d4,d2
        move.l  d0,d4                   ; 2-bit exchange
        lsr.l   #2,d4
        eor.l   d2,d4
        and.l   #$33333333,d4
        eor.l   d4,d2
        lsl.l   #2,d4
        eor.l   d4,d0
        move.w  d0,(a1)+                ; plane 0
        swap    d0
        move.w  d0,C2P_ECSBPL-2(a1)     ; plane 1
        move.w  d2,(a2)+                ; plane 2
        swap    d2
        move.w  d2,C2P_ECSBPL-2(a2)     ; plane 3
        dbf     d6,.blk
        adda.w  (a5),a0
        adda.w  a6,a1
        adda.w  a6,a2
        subq.w  #1,(a7)
        bcc     .row
        addq.l  #2,a7
        movem.l (a7)+,d0-a6
        rts
