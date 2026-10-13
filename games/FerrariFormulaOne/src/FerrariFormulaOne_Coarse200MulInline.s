; Included within FF1VelocityRotate000's local-label scope after its native body.
; Both cosine products dominate the measured general-helper call cost. Inline
; those exact operations using the outer frame's already-saved D6/D7 scratch.
; Sine products retain the shared helper and its existing zero shortcut.
.p2_rotate:
 move.w d0,d2
 ext.l d2
 move.w d1,d3
 ext.l d3
 move.l (a0),d0
 move.l d2,d1
 ; D6/D7 are scratch in this rotation and already saved by its caller frame.
 tst.w d1
 beq.b .p2_xc_zero
 tst.w d0
 bne.b .p2_xc_general
 swap d0
 muls.w d1,d0
 move.l d0,d1
 swap d1
 ext.l d1
 swap d0
 clr.w d0
 bra.b .p2_xc_done
.p2_xc_zero:
 moveq #0,d0
 moveq #0,d1
 bra.b .p2_xc_done
.p2_xc_general:
 move.l d0,d6
 moveq #0,d7
 move.w d0,d7
 mulu.w d1,d0
 swap d6
 muls.w d1,d6
 tst.w d1
 bpl.b .p2_xc_compose
 sub.l d7,d6
.p2_xc_compose:
 move.l d6,d1
 swap d1
 ext.l d1
 swap d6
 clr.w d6
 moveq #0,d7
 add.l d6,d0
 addx.l d7,d1
.p2_xc_done:
 move.l d0,d4
 move.l d1,d5
 move.l 4(a0),d0
 move.l d3,d1
 bsr.w FF1MultiplyS32x16_000
 sub.l d0,d4
 subx.l d1,d5
 bsr.w FF1Q15Product000
 tst.l d1
 bne.w .p2_done
 move.l d4,(sp)
 move.l (a0),d0
 move.l d3,d1
 bsr.w FF1MultiplyS32x16_000
 move.l d0,d4
 move.l d1,d5
 move.l 4(a0),d0
 move.l d2,d1
 ; D6/D7 are scratch in this rotation and already saved by its caller frame.
 tst.w d1
 beq.b .p2_zc_zero
 tst.w d0
 bne.b .p2_zc_general
 swap d0
 muls.w d1,d0
 move.l d0,d1
 swap d1
 ext.l d1
 swap d0
 clr.w d0
 bra.b .p2_zc_done
.p2_zc_zero:
 moveq #0,d0
 moveq #0,d1
 bra.b .p2_zc_done
.p2_zc_general:
 move.l d0,d6
 moveq #0,d7
 move.w d0,d7
 mulu.w d1,d0
 swap d6
 muls.w d1,d6
 tst.w d1
 bpl.b .p2_zc_compose
 sub.l d7,d6
.p2_zc_compose:
 move.l d6,d1
 swap d1
 ext.l d1
 swap d6
 clr.w d6
 moveq #0,d7
 add.l d6,d0
 addx.l d7,d1
.p2_zc_done:
 add.l d0,d4
 addx.l d1,d5
 bsr.w FF1Q15Product000
 tst.l d1
 bne.w .p2_done
 move.l d4,4(a0)
 move.l (sp),(a0)
.p2_done:
 addq.l #4,sp
 movem.l (sp)+,d0/d2-d7
 rts

FF1MulInlineControl:
 IFD FF1_C4_MUL_INLINE_TEST
 dc.w 0
 ELSE
 dc.w 1
 ENDC
