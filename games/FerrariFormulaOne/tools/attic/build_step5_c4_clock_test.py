from pathlib import Path
r=Path(__file__).resolve().parents[1]
# Direct calls to the installed, relocated clock wrapper, with native clock
# storage and mode fields restored before driving resumes.
times=[(0,0,0,0,0,0,0),(0,0,0,0,5,9,9),(0,3,5,9,5,9,9),(0,4,5,8,5,9,8),(0,4,5,8,5,9,9)]
weights=(360000,36000,6000,600,100,10,1)
def digits(n):
 out=[]
 for w in weights:out.append(n//w);n%=w
 return out
asm='''C4TestClocks:
 lea C4ClockSaved(pc),a0
 lea $226c0,a1
 moveq #4,d0
.save:
 move.l (a1)+,(a0)+
 dbra d0,.save
 move.w $1ed2c,(a0)+
 move.w $1c222,(a0)
'''
cases=[]
for ptr in (0x226c0,0x226ca):
 for mode,flag in [(12,0),(12,1),(0,0)]:
  for t in times:
   n=sum(a*b for a,b in zip(t,weights))+1
   if not(ptr==0x226c0 and mode==12 and flag==0 and digits(n)[1:4]==[4,5,9]):n+=1
   expected=digits(n);cases.append(dict(pointer=hex(ptr),mode=mode,flag=flag,start=t,expected=expected));i=len(cases)
   asm+=f' move.w #{mode},$1ed2c\n move.w #{flag},$1c222\n'
   for off,v in enumerate(t,3):asm+=f' move.b #{v},${ptr+off:x}\n'
   asm+=f' pea ${ptr:x}\n bsr.w FF1ClockTick\n addq.l #4,sp\n'
   for off,v in enumerate(expected,3):asm+=f' cmpi.b #{v},${ptr+off:x}\n bne.w C4ClockBad{i}\n'
   asm+=' lea C4ClockChecked(pc),a0\n addq.l #1,(a0)\n'
asm+=''' lea C4ClockSaved(pc),a0
 lea $226c0,a1
 moveq #4,d0
.restore:
 move.l (a0)+,(a1)+
 dbra d0,.restore
 move.w (a0)+,$1ed2c
 move.w (a0),$1c222
 rts
'''
for i in range(1,len(cases)+1):asm+=f'C4ClockBad{i}:\n lea error(pc),a0\n move.l #{1000+i},(a0)\n bra.w C1Fault\n'
asm+='C4ClockChecked: dc.l 0\nC4ClockSaved: ds.b 24\n'
import json
(r/'tmp/build/step5-c4-motion-port/clock-tests.s').write_text(asm)
(r/'manifest/step5-c4-clock-cases.json').write_text(json.dumps(cases,indent=2)+'\n')
s=(r/'tools/build_step5_c4_motion.py').read_text().replace("'step5-c4-motion'","'step5-c4-clock-test'")
pos="exec(compile(s,"
extra="""s=s.replace('base=(r/', \"p=o/'FerrariFormulaOne_CoarseInstall.s'\\nsrc=p.read_text().replace(' bsr.w FF1TimeInit',' bsr.w FF1TimeInit\\\\n bsr.w C4TestClocks')\\np.write_text(src)\\nbase=(r/\",1)
s=s.replace(\"public_bindings:\",\" include \\\"clock-tests.s\\\"\\\\npublic_bindings:\")
"""
s=s.replace(pos,extra+pos)
exec(compile(s,str(r/'tools/build_step5_c4_motion.py'),'exec'))
