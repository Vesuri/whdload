import json,os,shutil,struct,sys
from fractions import Fraction
from capture_demo import ROOT
from capture_session import Session
os.chdir(ROOT);name=sys.argv[1] if len(sys.argv)>1 else 's4-traffic-phase-wide';out=ROOT/'tmp/prof'/name;out.mkdir(exist_ok=False)
shutil.copyfile(ROOT/'tmp/build'/(name+'.slave'),out/'slave.slave')
shutil.copyfile(ROOT/'tmp/traffic-phase-inputs.json',out/'inputs.json')
s=Session(out,'a500',out/'slave.slave',0x8520)
try:
 s.boot();cases=json.loads((out/'inputs.json').read_text());hits=[]
 for bank,b in s.dump_banks('phase'):
  j=b.find(b'HDTRMIN1')
  if j>=0:mins=list(struct.unpack('>'+str(len(cases))+'i',b[j+8:j+8+4*len(cases)]))
  i=b.find(b'HDTRPHW1')
  if i>=0:hits.append(b[i+8:i+8+8*len(cases)])
 assert len(hits)==1;expected=[];capped=0
 for v,u,n,accel,carry in cases:
  if n>8 and accel and 0<v-u<accel*n:
   t=Fraction(v-u,accel)
   distance=Fraction(u)*t+Fraction(accel,2)*t*t+v*(n-t)
   capped+=1
  else:distance=Fraction(n*(u+v),2)
  displacement=distance/64+Fraction(v-u,16)+Fraction(carry,768)
  q=int(displacement);r=(displacement-q)*768
  assert r.denominator==1
  expected.append((q,int(r)))
 if 'mins' in locals():
  expected_mins=[]
  for v,u,n,accel,carry in cases:
   t=Fraction(-u,accel)-4 if accel else 0
   minimum=Fraction(2*u*t+accel*t*t+8*accel*t,128)+Fraction(carry,768) if n>8 and 0<t<n else 0
   expected_mins.append(min(0,int(minimum)))
  assert mins==expected_mins,[(i,x,y) for i,(x,y) in enumerate(zip(mins,expected_mins)) if x!=y]
 got=list(struct.iter_unpack('>ii',hits[0]));assert got==expected,[(i,cases[i],x,y) for i,(x,y) in enumerate(zip(got,expected)) if x!=y][:10]
 result=dict(passed=True,cases=len(cases),capped_cases=capped,minimum_cases=len(mins) if 'mins' in locals() else 0,turning_cases=sum(x<0 for x in mins) if 'mins' in locals() else 0,max_abs_phase=max(abs(q) for q,r in got));(out/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
finally:s.close()
