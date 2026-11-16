; The ECS game's chunky-to-planar conversion for the 68020 and up (RobinsonSRequiemEcs.asm
; includes it; docs/internals.md, "ECS improvements"), chosen at install from AttnFlags.
;
; The same entry and exit as _c2p000 (src/c2p000.s), and the same arithmetic for each 16
; pixels, with longword plane writes: on the 68020 and up the chunky buffer is in fast
; memory (ECS plan step 7) and the plane writes are most of the conversion's chip time.
; Each pair of 16-pixel blocks gives the four plane words of both, joined into a longword
; per plane by a 16-bit exchange, half the plane writes of _c2p000. A row whose planes do
; not start on a longword starts with one block written as words; an odd block left at
; the end is written as words too. tools/rr_ecsc2pcheck.py checks it against START's loop
; under Unicorn (68020).

; 16 pixels from a0 (advanced) to d0 = planes 1:0, d2 = planes 3:2, as _c2p000's block;
; d1, d3 and d4 used, d7 = $0f0f0f0f
C2PBLK  MACRO
        movem.l (a0)+,d0-d3             ; pixels 0-3, 4-7, 8-11, 12-15
        move.l  d1,d4                   ; d0/d1: d0's low nibbles <-> d1's high ones
        lsr.l   #4,d4
        eor.l   d0,d4
        and.l   d7,d4
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
        and.l   d7,d4
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
        and.l   #$00ff00ff,d4
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
        ENDM

_c2p020
        move.l  _c2pmod(pc),a5
        moveq   #0,d0
        move.w  d6,d0
        addq.w  #1,d0                   ; blocks of 16 pixels
        moveq   #0,d1                   ; a block as words first
        move.w  a1,d2
        and.w   #2,d2
        beq     .al
        moveq   #1,d1
        subq.w  #1,d0
.al     move.w  d0,d2
        lsr.w   #1,d2
        subq.w  #1,d2                   ; pairs - 1 (-1: none)
        and.w   #1,d0                   ; a block as words last
        move.w  d0,-(a7)                ; 6(a7)
        move.w  d1,-(a7)                ; 4(a7)
        move.w  d2,-(a7)                ; 2(a7)
        move.w  d7,-(a7)                ; (a7): rows - 1, counted as dbf does
        move.l  #$0f0f0f0f,d7
.row    tst.w   4(a7)
        beq     .pairs
        bsr     .b16
        bsr     .w16
.pairs  move.w  2(a7),d6
        bmi     .last
.pair   C2PBLK
        move.l  d0,a3                   ; the first block's planes 1:0
        move.l  d2,d5                   ; and 3:2
        C2PBLK
        move.l  a3,d1                   ; 16-bit exchange: d1 = planes 1, d0 = planes 0
        move.w  d0,d4
        move.w  d1,d0
        swap    d0
        move.w  d0,d1
        move.w  d4,d0
        move.l  d0,(a1)+                ; plane 0
        move.l  d1,C2P_ECSBPL-4(a1)     ; plane 1
        move.w  d2,d4                   ; the same: d5 = planes 3, d2 = planes 2
        move.w  d5,d2
        swap    d2
        move.w  d2,d5
        move.w  d4,d2
        move.l  d2,(a2)+                ; plane 2
        move.l  d5,C2P_ECSBPL-4(a2)     ; plane 3
        dbf     d6,.pair
.last   tst.w   6(a7)
        beq     .next
        bsr     .b16
        bsr     .w16
.next   adda.w  (a5),a0
        adda.w  a6,a1
        adda.w  a6,a2
        subq.w  #1,(a7)
        bcc     .row
        addq.l  #8,a7
        movem.l (a7)+,d0-a6
        rts

; One block's plane words as words: d0 planes 1:0, d2 planes 3:2
.w16    move.w  d0,(a1)+
        swap    d0
        move.w  d0,C2P_ECSBPL-2(a1)
        move.w  d2,(a2)+
        swap    d2
        move.w  d2,C2P_ECSBPL-2(a2)
        rts

.b16
        C2PBLK
        rts
