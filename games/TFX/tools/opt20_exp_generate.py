"""Generate a bounded native-040 exponential helper; invoke after operand audit."""
from pathlib import Path
from decimal import Decimal,localcontext
import math,struct
root=Path(__file__).resolve().parents[1];src=root/'src'
p=src/'native_math.i';s=p.read_bytes().decode('latin1');assert 'native_exp:' not in s
# Derive a three-part ln(2) reduction from a high-precision independent constant.
with localcontext() as c:
 c.prec=90;ln2=Decimal(2).ln();hi=struct.unpack('>d',struct.pack('>d',float(ln2))[:4]+bytes(4))[0];lo=float(ln2-Decimal.from_float(hi));tail=float(ln2-Decimal.from_float(hi)-Decimal.from_float(lo))
 constants={'exp_invln2':float(1/ln2),'exp_ln2_hi':hi,'exp_ln2_lo':lo,'exp_ln2_tail':tail}
for n in range(2,18):constants[f'exp_c{n}']=1/math.factorial(n)
lines=['; Bounded exp(x): |x| <= 64, FPCR=0; otherwise retain original FPSP.', '; Reduce x = k*ln(2)+r, evaluate degree-17 exp(r), multiply by exact 2^k.', '        mc68040','native_exp:','        move.w ccr,-(sp)','        movem.l d0-d2/a0,-(sp)','        fmovem.x fp0-fp7,-(sp)','        fmove.l fpcr,-(sp)','        fmove.x fp7,fp0','        tst.l (sp)','        bne .fallback','        fmove.x fp0,-(sp)','        move.w (sp),d0','        lea 12(sp),sp','        and.w #$7fff,d0','        cmp.w #$7fff,d0','        beq .fallback','        fabs.x fp0,fp1','        fcmp.s #64,fp1','        fbgt .fallback','        ftst.x fp0','        fbeq .zero','        bsr math_exp','        fmove.x fp0,4(sp)','        fmove.l fpsr,d0','        or.l #$208,d0','        fmove.l d0,fpsr','        bra .restore','.zero:','        fmove.s #1,fp0','        fmove.x fp0,4(sp)','.restore:','        fmove.l (sp)+,fpcr','        fmovem.x (sp)+,fp0-fp7','        movem.l (sp)+,d0-d2/a0','        move.w (sp)+,ccr','        rts','.fallback:','        fmove.l (sp)+,fpcr','        fmovem.x (sp)+,fp0-fp7','        movem.l (sp)+,d0-d2/a0','        move.w (sp)+,ccr','        dc.w $f200,$1c10 ; original fetox.x fp7,fp0','        rts','math_exp:','        fmove.x fp0,fp1','        fmul.d math_exp_invln2(pc),fp1','        fmove.l fp1,d0','        fmove.l d0,fp1','        fmove.x fp1,fp2','        fmul.d math_exp_ln2_hi(pc),fp2','        fsub.x fp2,fp0','        fmove.x fp1,fp2','        fmul.d math_exp_ln2_lo(pc),fp2','        fsub.x fp2,fp0','        fmul.d math_exp_ln2_tail(pc),fp1','        fsub.x fp1,fp0','        fmove.d math_exp_c17(pc),fp1']
for n in range(16,1,-1):lines+=['        fmul.x fp0,fp1',f'        fadd.d math_exp_c{n}(pc),fp1']
lines+=['        fmul.x fp0,fp1','        fadd.s #1,fp1','        fmul.x fp1,fp0','        fadd.s #1,fp0','        suba.w #12,sp','        add.w #16383,d0','        move.w d0,(sp)','        clr.w 2(sp)','        move.l #$80000000,4(sp)','        clr.l 8(sp)','        fmove.x (sp)+,fp1','        fmul.x fp1,fp0','        rts']
for name,v in constants.items():
 h=struct.pack('>d',v).hex();lines+=[f'math_{name}: dc.l ${h[:8]},${h[8:]}']
lines+=['        mc68020',''];s+='\r\n'+'\r\n'.join(lines);p.write_bytes(s.encode('latin1'))
p=src/'native_fpu_sites.i';s=p.read_bytes().decode('latin1');s=s.replace('        PL_L $51682,$4eb80000+$220 ; native exp\r\n','').replace('        patch $220,native_exp\r\n','');s=s.replace('        PL_L $5183c,$4eb80000+$21a ; native asin\r\n','        PL_L $5183c,$4eb80000+$21a ; native asin\r\n        PL_L $51682,$4eb80000+$220 ; native exp\r\n',1);s=s.replace('        patch $21a,native_asin\r\n','        patch $21a,native_asin\r\n        patch $220,native_exp\r\n',1);p.write_bytes(s.encode('latin1'))
