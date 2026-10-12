; Ferrari Formula One: candidate exact-output 68020 square-root helper.
; Not installed by the slave. The native routine searches a bounded 0..1023
; result. Replace only its repeated squaring with a table; retain its search,
; upper-word behavior, D0-D3 outputs and CCR, including early perfect squares.
; The scaled word index is a 68020 instruction. Other registers are untouched.
FF1SquareRoot020:
        move.w  #512,d2
        move.w  #256,d3
        move.l  4(sp),d0
.loop:  move.l  FF1Squares(pc,d2.w*4),d1
        cmp.l   d1,d0
        bls.b   .lower
        add.w   d3,d2
        bra.b   .check
.lower: beq.b   .done
        sub.w   d3,d2
.check: tst.w   d3
        bne.b   .halve
        cmp.l   d1,d0
        bhi.b   .done
        subq.l  #1,d2
        bra.b   .done
.halve: lsr.w   #1,d3
        bra.b   .loop
.done:  move.w  d2,d0
        rts
FF1Squares:
FF1SquareValue set 0
        rept 1024
        dc.l FF1SquareValue*FF1SquareValue
FF1SquareValue set FF1SquareValue+1
        endr

; Exact floor square root over the full unsigned 32-bit input domain.
; D0.l input/result (0..65535); all other registers preserved, CCR scratch.
; 68000-safe. Separate entry: does NOT alter the native bounded helper above.
FF1SquareRootU32:
        movem.l d1-d4,-(sp)
        move.l  d0,d1
        moveq   #0,d2
        move.l  #32768,d3
.loop:
        move.l  d2,d4
        or.l    d3,d4
        move.l  d4,d0
        mulu.w  d0,d0
        cmp.l   d1,d0
        bhi.b   .next
        move.l  d4,d2
.next:
        lsr.l   #1,d3
        bne.b   .loop
        move.l  d2,d0
        movem.l (sp)+,d1-d4
        rts

; Exact floor sqrt of unsigned D1:D0, result D0.l (0..$ffffffff).
; Other registers preserved; CCR scratch. 68020+ full-product multiplication.
FF1SquareRootU64:
        movem.l d1-d7,-(sp)
        move.l  d1,d6
        move.l  d0,d7
        moveq   #0,d2
        move.l  #$80000000,d3
.loop:
        move.l  d2,d4
        or.l    d3,d4
        move.l  d4,d0
        mulu.l  d4,d5:d0
        cmp.l   d6,d5
        bhi.b   .next
        blo.b   .accept
        cmp.l   d7,d0
        bhi.b   .next
.accept:
        move.l  d4,d2
.next:
        lsr.l   #1,d3
        bne.b   .loop
        move.l  d2,d0
        movem.l (sp)+,d1-d7
        rts
