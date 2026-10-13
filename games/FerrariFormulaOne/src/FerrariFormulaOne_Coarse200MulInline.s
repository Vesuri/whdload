; Included within FF1VelocityRotate000's local-label scope after its native body.
; Both cosine products dominate the measured general-helper call cost. Inline
; those exact operations using the outer frame's already-saved D6/D7 scratch.
; Sine products retain the shared helper and its existing zero shortcut.
 IFD FF1_C4_ROTATE_FAST
C4RotateGeneral equ *
 ENDC
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
 IFD FF1_C4_ROTATE_FAST
C4RotateWordXGate equ *
 IFD FF1_C4_ROTATE_FAST_TEST
 bne.w .r3_xc_short
 ELSE
 bne.w .p2_xc_general
 ENDC
 ELSE
 bne.b .p2_xc_general
 ENDC
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
 IFD FF1_C4_ROTATE_FAST
C4RotateWordXFast equ *
.r3_xc_short:
 ; A signed-word component needs only one exact signed multiply.
 move.w d0,d6
 ext.l d6
 cmp.l d0,d6
 bne.b .p2_xc_general
 muls.w d1,d0
 move.l d0,d1
 add.l d1,d1
 subx.l d1,d1
 bra.b .p2_xc_done
C4RotateWordXGeneral equ *
 ENDC
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
 IFD FF1_C4_ROTATE_FAST
C4RotateWordZGate equ *
 IFD FF1_C4_ROTATE_FAST_TEST
 bne.w .r3_zc_short
 ELSE
 bne.w .p2_zc_general
 ENDC
 ELSE
 bne.b .p2_zc_general
 ENDC
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
 IFD FF1_C4_ROTATE_FAST
C4RotateWordZFast equ *
.r3_zc_short:
 ; A signed-word component needs only one exact signed multiply.
 move.w d0,d6
 ext.l d6
 cmp.l d0,d6
 bne.b .p2_zc_general
 muls.w d1,d0
 move.l d0,d1
 add.l d1,d1
 subx.l d1,d1
 bra.b .p2_zc_done
C4RotateWordZGeneral equ *
 ENDC
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

 IFD FF1_C4_ROTATE_FAST
C4RotateFast equ *
.r3_rotate:
 ; Frequent zero-sine Q15 rotation still shrinks by one coefficient unit.
 ; floor(n*32767/32768) = n-ceil(n/32768), including negative fractions.
 cmpi.w #32767,d0
 bne.w .p2_rotate
 tst.w d1
 bne.w .p2_rotate
 move.l (a0),d4
 move.l d4,d6
 swap d6
 ext.l d6
 add.l d6,d6
 tst.w d4
 beq.b .r3_x_ceil
 addq.l #1,d6
 cmpi.w #$8000,d4
 bls.b .r3_x_ceil
 addq.l #1,d6
.r3_x_ceil:
 sub.l d6,d4
 move.l d4,(sp)
 move.l 4(a0),d4
 move.l d4,d6
 swap d6
 ext.l d6
 add.l d6,d6
 tst.w d4
 beq.b .r3_z_ceil
 addq.l #1,d6
 cmpi.w #$8000,d4
 bls.b .r3_z_ceil
 addq.l #1,d6
.r3_z_ceil:
 sub.l d6,d4
 move.l d4,4(a0)
 move.l (sp),(a0)
 moveq #0,d1
 bra.w .p2_done
 ENDC

FF1MulInlineControl:
 IFD FF1_C4_MUL_INLINE_TEST
 dc.w 0
 ELSE
 dc.w 1
 ENDC
