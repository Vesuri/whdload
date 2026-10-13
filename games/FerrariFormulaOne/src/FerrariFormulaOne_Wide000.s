; Full-width arithmetic for the opt-in 68000 200 ms conversion.
; No hooks or CPU selection are installed here. CPU-only code/data use public
; memory under the host's ownership. All instructions are valid on MC68000.
;
; D0/D1 unsigned 32-bit operands -> D1:D0 exact unsigned 64-bit product.
; D2-D7/A0-A6 preserved; CCR scratch. Four 16-bit partial products.
FF1MultiplyU64_000:
 movem.l d2-d5,-(sp)
 move.l d0,d2
 move.l d1,d3
 move.l d0,d4
 mulu.w d1,d0
 swap d2
 mulu.w d2,d1
 swap d3
 mulu.w d3,d4
 mulu.w d3,d2
 moveq #0,d5
 add.l d4,d1
 addx.l d5,d5
 swap d5
 add.l d5,d2
 move.l d1,d4
 swap d1
 andi.l #$ffff,d1
 add.l d1,d2
 swap d4
 clr.w d4
 moveq #0,d5
 add.l d4,d0
 addx.l d5,d2
 move.l d2,d1
 movem.l (sp)+,d2-d5
 rts

; Same ABI, signed operands and signed full-width result. Correct the unsigned
; product's upper half by the other operand for each negative input. This also
; covers -2^31 without negating it in a signed 32-bit temporary.
FF1MultiplyS64_000:
 movem.l d2-d3,-(sp)
 move.l d0,d2
 move.l d1,d3
 bsr.w FF1MultiplyU64_000
 tst.l d2
 bpl.b .b
 sub.l d3,d1
.b:
 tst.l d3
 bpl.b .done
 sub.l d2,d1
.done:
 movem.l (sp)+,d2-d3
 rts

; Exact floor sqrt of unsigned D1:D0 -> D0 (0..$ffffffff).
; All other registers preserved; CCR scratch. Restoring base-four algorithm:
; remainder and trial retain their high words, including near 2^64-1.
FF1SquareRootU64_000:
 movem.l d1-d7,-(sp)
 moveq #0,d2
 moveq #0,d3
 moveq #0,d4
 moveq #31,d7
.loop:
 ; Shift the next two input bits into the 64-bit remainder D3:D2.
 add.l d0,d0
 addx.l d1,d1
 addx.l d2,d2
 addx.l d3,d3
 add.l d0,d0
 addx.l d1,d1
 addx.l d2,d2
 addx.l d3,d3
 ; Trial = 4*partial_root+1 in D6:D5.
 move.l d4,d5
 moveq #0,d6
 add.l d5,d5
 addx.l d6,d6
 add.l d5,d5
 addx.l d6,d6
 addq.l #1,d5
 add.l d4,d4
 cmp.l d6,d3
 blo.b .next
 bhi.b .accept
 cmp.l d5,d2
 blo.b .next
.accept:
 sub.l d5,d2
 subx.l d6,d3
 addq.l #1,d4
.next:
 dbra d7,.loop
 move.l d4,d0
 movem.l (sp)+,d1-d7
 rts

; D0 signed 32-bit, D1.low signed 16-bit -> D1:D0 exact signed 64-bit product.
; D1.high is ignored. D2-D7/A0-A6 preserved; CCR scratch. Two word products:
; unsigned low(A)*unsigned(B), plus signed high(A)*signed(B) shifted by 16.
; For B<0, subtract low(A) from the high partial product before composing.
FF1MultiplyS32x16_000:
 IFD FF1_WIDE_AB
 ; Equal-layout diagnostic control; absent from the ordinary helper build.
 move.w FF1WideControl(pc),-(sp)
 tst.w (sp)+
 beq.b .fast
 ext.l d1
 bra.w FF1MultiplyS64_000
.fast:
 ENDC
 movem.l d2-d3,-(sp)
 move.l d0,d2
 moveq #0,d3
 move.w d0,d3
 mulu.w d1,d0
 swap d2
 muls.w d1,d2
 tst.w d1
 bpl.b .compose
 sub.l d3,d2
.compose:
 move.l d2,d1
 swap d1
 ext.l d1
 swap d2
 clr.w d2
 moveq #0,d3
 add.l d2,d0
 addx.l d3,d1
 movem.l (sp)+,d2-d3
 rts

 IFD FF1_WIDE_AB
FF1WideControl: dc.w 0
 ENDC
