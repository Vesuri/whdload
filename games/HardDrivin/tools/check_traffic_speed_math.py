import json,os,shutil,struct
from capture_demo import ROOT
from capture_session import Session
os.chdir(ROOT);out=ROOT/'tmp/prof/s4-traffic-speed-wide';out.mkdir(exist_ok=False);shutil.copyfile(ROOT/'tmp/build/s4-traffic-speed-wide.slave',out/'slave.slave');shutil.copyfile(ROOT/'tmp/traffic-speed-inputs.json',out/'inputs.json');s=Session(out,'a500',out/'slave.slave',0x8520)
def trunc(n):return abs(n)//8*(-1 if n<0 else 1)
try:
 s.boot();inputs=json.loads((out/'inputs.json').read_text());hits=[]
 for bank,b in s.dump_banks('traffic'):
  i=b.find(b'HDTRSPD1')
  if i>=0:hits.append(b[i+8:i+8+len(inputs)*8])
 assert len(hits)==1;expected=[]
 for v,frac,last,accel,target,n,initial in inputs:
  old=v*8+(frac if last==v else 0);full=old
  if accel:
   cap=((target+accel-1)//accel)*accel*8
   if full<cap:full=min(cap,full+accel*(8 if initial else n))
  v=trunc(full);expected.append((v,full-v*8,v,old))
 got=list(struct.iter_unpack('>hhhh',hits[0]));assert got==expected,(got,expected)
 result=dict(passed=True,cases=len(got));(out/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
finally:s.close()
