from pathlib import Path
r=Path(__file__).resolve().parents[3]/'Games'
p=r/'FerrariFormulaOne_Physics200.s';s=p.read_text();old=' beq.w .p2_rotate';assert s.count(old)==1
s=s.replace(old,''' IFD FF1_C4_ROTATE_FAST
C4RotateDispatch equ *
 IFD FF1_C4_ROTATE_FAST_TEST
 beq.w .r3_rotate
 ELSE
 beq.w .p2_rotate
 ENDC
 ELSE
 beq.w .p2_rotate
 ENDC''');p.write_text(s)
p=r/'FerrariFormulaOne_Coarse200MulInline.s';s=p.read_text()
s=s.replace('.p2_rotate:', ' IFD FF1_C4_ROTATE_FAST\nC4RotateGeneral equ *\n ENDC\n.p2_rotate:',1)
for component,tag in [('xc','X'),('zc','Z')]:
 old=f' bne.b .p2_{component}_general';assert s.count(old)==1
 s=s.replace(old,f''' IFD FF1_C4_ROTATE_FAST
C4RotateWord{tag}Gate equ *
 IFD FF1_C4_ROTATE_FAST_TEST
 bne.w .r3_{component}_short
 ELSE
 bne.w .p2_{component}_general
 ENDC
 ELSE
{old}
 ENDC''')
 old=f'.p2_{component}_general:'
 s=s.replace(old,f''' IFD FF1_C4_ROTATE_FAST
C4RotateWord{tag}Fast equ *
.r3_{component}_short:
 ; A signed-word component needs only one exact signed multiply.
 move.w d0,d6
 ext.l d6
 cmp.l d0,d6
 bne.b .p2_{component}_general
 muls.w d1,d0
 move.l d0,d1
 add.l d1,d1
 subx.l d1,d1
 bra.b .p2_{component}_done
C4RotateWord{tag}General equ *
 ENDC
{old}''')
extra=''' IFD FF1_C4_ROTATE_FAST
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

'''
s=s.replace('FF1MulInlineControl:',extra+'FF1MulInlineControl:',1);p.write_text(s)
