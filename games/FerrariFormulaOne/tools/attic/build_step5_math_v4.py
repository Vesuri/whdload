from pathlib import Path
r=Path(__file__).resolve().parents[1]
s=(r/'tools/build_step5_math.py').read_text().replace("step5-math-v3","step5-math-v4")
s=s.replace(' lea fastdiv(pc),a1\n cmpi.w #2,d0\n bne.b plant\n lea verifydiv(pc),a1', ''' lea FF1Divide000(pc),a1
 cmpi.w #3,d0
 blo.b selected
 lea FF1Divide020(pc),a1
selected:
 lea candidate(pc),a0
 move.l a1,(a0)
 cmpi.w #2,d0
 beq.b verify
 cmpi.w #4,d0
 bne.b plant
verify:
 lea verifydiv(pc),a1''')
s=s.replace(' cmpi.w #3,d0\n bne.b finish',' cmpi.w #5,d0\n bne.b finish')
a=s.index('; Unsigned magnitude division');b=s.index('verifydiv:',a)
s=s[:a]+' include "'+str(r.parent.parent/'Games/FerrariFormulaOne_Math.s')+'"\n'+s[b:]
s=s.replace(' bsr.w fastdiv',' move.l candidate(pc),a1\n jsr (a1)')
s=s.replace('cache_called: dc.l 0','cache_called: dc.l 0\ncandidate: dc.l 0')
s=s.replace("('control','fast','verify','cache')", "('control','fast000','verify000','fast020','verify020','cache')")
s=s.replace("('fast','verify','cache')", "('fast000','verify000','fast020','verify020','cache')")
exec(compile(s,str(r/'tools/build_step5_math.py'),'exec'))
