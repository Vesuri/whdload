from pathlib import Path
import math
root=Path(__file__).resolve().parents[1];src=root/'src'
# Polynomial coefficients are Taylor coefficients rounded once to binary64.
lines=['; Native 040 arithmetic for observed transcendental instructions.','; Range reduction uses a split pi/2; atan uses two half-angle reductions.','; FPSP remains available for exceptional arguments / non-default FPCR.', '; Trig fast range: |x| <= 2^20. Sine degree 17, cosine degree 18.', '; Atan reduces to |x| <= tan(pi/16), then uses degree 31.', '; Validated error bound: 2e-15 absolute (|result|<=1), relative otherwise.', '; Preserve FPCR, CCR, all GPRs and every non-destination FPU register.','        mc68040']
wrappers=[('tan',7,0,0x50f82,0x1c0f),('sin',7,0,0x5169e,0x1c0e),('cos',7,0,0x516b6,0x1c1d),('atan2',1,5,0x517a4,0x068a),('atan',7,0,0x517f2,0x1c0a),('asin',7,0,0x5183c,0x1c0c)]
for i,(name,inp,dst,off,ext) in enumerate(wrappers):
 lines += [f'native_{name}:','        move.w ccr,-(sp)','        movem.l d0-d2/a0,-(sp)','        fmovem.x fp0-fp7,-(sp)','        fmove.l fpcr,-(sp)',f'        fmove.x fp{inp},fp0','        tst.l (sp)',f'        bne .fallback','        fmove.x fp0,-(sp)','        move.w (sp),d0','        lea 12(sp),sp','        and.w #$7fff,d0','        cmp.w #$7fff,d0','        beq .fallback']
 if name in ('sin','cos','tan'):
  lines+=['        fabs.x fp0,fp1','        fcmp.s #1048576,fp1','        fbgt .fallback']
 if name=='asin':lines+=['        fabs.x fp0,fp1','        fcmp.s #1,fp1','        fbgt .fallback']
 lines += ['        ftst.x fp0','        fbeq .zero']
 lines += [f'        bsr math_{"atan" if name=="atan2" else name}',f'        fmove.x fp0,{4+dst*12}(sp)','        fmove.l fpsr,d0','        or.l #$208,d0','        fmove.l d0,fpsr','        bra .restore','.zero:']
 if name=='cos':lines+=['        fmove.s #1,fp0']
 lines += [f'        fmove.x fp0,{4+dst*12}(sp)','.restore:','        fmove.l (sp)+,fpcr','        fmovem.x (sp)+,fp0-fp7','        movem.l (sp)+,d0-d2/a0','        move.w (sp)+,ccr','        rts','.fallback:','        fmove.l (sp)+,fpcr','        fmovem.x (sp)+,fp0-fp7','        movem.l (sp)+,d0-d2/a0','        move.w (sp)+,ccr',f'        dc.w $f200,${ext:04x}','        rts','']
lines+='''math_sin:
        bsr math_sincos
        rts
math_cos:
        bsr math_sincos
        fmove.x fp1,fp0
        rts
math_tan:
        bsr math_sincos
        fdiv.x fp1,fp0
        rts
; fp0 angle -> fp0 sine, fp1 cosine; |angle| <= 2^20, FPCR=0.
math_sincos:
        fmove.x fp0,fp2
        fmul.d math_invpio2(pc),fp2
        fmove.l fp2,d0
        fmove.l d0,fp2
        fmove.x fp2,fp3
        fmul.d math_pio2_hi(pc),fp3
        fsub.x fp3,fp0
        fmul.d math_pio2_lo(pc),fp2
        fsub.x fp2,fp0
        fmove.l d0,fp3
        fmul.d math_pio2_tail(pc),fp3
        fsub.x fp3,fp0
        fmove.x fp0,fp2
        fmul.x fp0,fp2
'''.splitlines()
# Horner sin(x)=x*(1+x²*P); cos(x)=1+x²*Q.
for name,reg,n in [('sin',3,8),('cos',1,9)]:
 lines += [f'        fmove.d math_{name}{n}(pc),fp{reg}']
 for j in range(n-1,0,-1):lines += [f'        fmul.x fp2,fp{reg}',f'        fadd.d math_{name}{j}(pc),fp{reg}']
 lines += [f'        fmul.x fp2,fp{reg}',f'        fadd.s #1,fp{reg}']
 if name=='sin':lines+=['        fmul.x fp0,fp3']
lines+='''        fmove.x fp3,fp0
        and.w #3,d0
        beq .out
        cmp.w #2,d0
        beq .negate
        fmove.x fp0,fp2
        fmove.x fp1,fp0
        fmove.x fp2,fp1
        cmp.w #1,d0
        bne .third
        fneg.x fp1
        rts
.third:
        fneg.x fp0
        rts
.negate:
        fneg.x fp0
        fneg.x fp1
.out:
        rts
; atan: reciprocal for |x|>1, then two exact half-angle identities.
math_atan:
        fmove.x fp0,fp6
        fabs.x fp0
        moveq #0,d1
        fcmp.s #1,fp0
        fble .small
        fmove.s #1,fp1
        fdiv.x fp0,fp1
        fmove.x fp1,fp0
        moveq #1,d1
.small:
        moveq #1,d2
.half:
        fmove.x fp0,fp1
        fmul.x fp0,fp1
        fadd.s #1,fp1
        fsqrt.x fp1
        fadd.s #1,fp1
        fdiv.x fp1,fp0
        dbf d2,.half
        fmove.x fp0,fp2
        fmul.x fp0,fp2
'''.splitlines()
lines+=['        fmove.d math_atan15(pc),fp1']
for j in range(14,0,-1):lines+=['        fmul.x fp2,fp1',f'        fadd.d math_atan{j}(pc),fp1']
lines+='''        fmul.x fp2,fp1
        fadd.s #1,fp1
        fmul.x fp1,fp0
        fmul.s #4,fp0
        tst.w d1
        beq .sign
        fmove.x math_pio2(pc),fp1
        fsub.x fp0,fp1
        fmove.x fp1,fp0
.sign:
        fmove.x fp6,-(sp)
        move.w (sp),d0
        lea 12(sp),sp
        tst.w d0
        bpl .out
        fneg.x fp0
.out:
        rts
math_asin:
        fabs.x fp0,fp1
        fcmp.s #1,fp1
        fbne .regular
        fmul.x math_pio2(pc),fp0
        rts
.regular:
        fmove.s #1,fp1
        fsub.x fp0,fp1
        fmove.s #1,fp2
        fadd.x fp0,fp2
        fmul.x fp2,fp1
        fsqrt.x fp1
        fdiv.x fp1,fp0
        bra math_atan
'''.splitlines()
import struct
constants={'invpio2':2/math.pi,'pio2_hi':1.57079632673412561417,'pio2_lo':6.07710050650619224932e-11,'pio2_tail':3.521559865183200388354395902437e-27}
for j in range(1,9):constants[f'sin{j}']=(-1.)**j/math.factorial(2*j+1)
for j in range(1,10):constants[f'cos{j}']=(-1.)**j/math.factorial(2*j)
for j in range(1,16):constants[f'atan{j}']=(-1.)**j/(2*j+1)
for name,v in constants.items():
 h=struct.pack('>d',v).hex();lines += [f'math_{name}: dc.l ${h[:8]},${h[8:]}']
lines += ['math_pio2: dc.l $3fff0000,$c90fdaa2,$2168c235','        mc68020','']
(src/'native_math.i').write_bytes('\r\n'.join(lines).encode())

# The extended flight also reaches the exponential wrapper.
import subprocess,sys
subprocess.run([sys.executable,str(Path(__file__).with_name("opt20_exp_generate.py"))],check=True)
