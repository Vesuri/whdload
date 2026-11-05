import json, os, shutil, struct, sys
from capture_demo import ROOT
from capture_session import Session
os.chdir(ROOT)
out=ROOT/'tmp/prof'/sys.argv[1]
out.mkdir(exist_ok=False)
shutil.copyfile(ROOT/'tmp/build/s4-projection-quant-math.slave',out/'slave.slave')
s=Session(out,'a500',out/'slave.slave',0x8520)
s.env['WHD_ARGS']+=' CUSTOM1=1'
def word(x): return (x+32768)%65536-32768
def project(v,t):
 sy,cy,sp,cp=t
 speed=word((v>>1)+v)
 y=word(speed*sp>>14)
 along=word(speed*cp>>14)
 return [word(along*sy>>14),y,word(along*cy>>14)]
try:
 s.boot()
 cases=json.loads((ROOT/'tmp/quantized-inputs.json').read_text())
 hits=[]
 for _,b in s.dump_banks('quantized'):
  i=b.find(b'HDPQMAT1')
  if i>=0: hits.append(b[i+8:i+8+len(cases)*18])
 assert len(hits)==1
 for i,(v,c,*t) in enumerate(cases):
  base=project(v,t)
  if c==0: expected=[0,0,0]
  elif abs(v)>21843:
   sy,cy,sp,cp=t
   speed=c*12288
   along=speed*cp//16384
   expected=[along*sy//16384,speed*sp//16384,along*cy//16384]
  else:
   expected=[word(n-o)*abs(c)*8192 for n,o in zip(project(v+(1 if c>0 else -1),t),base)]
  got=struct.unpack_from('>hhhiii',hits[0],i*18)
  assert got==tuple(base+expected),(i,v,c,t,got,base+expected)
 result=dict(passed=True,cases=len(cases))
 (out/'results.json').write_text(json.dumps(result,indent=2)+'\n')
 print(result)
finally: s.close()
