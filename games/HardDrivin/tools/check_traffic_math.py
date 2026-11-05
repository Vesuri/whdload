import argparse,json,os,struct,shutil
from capture_demo import ROOT
from capture_session import Session
p=argparse.ArgumentParser();p.add_argument('name',nargs='?',default='s4-traffic-math');p.add_argument('--slave',default='s4-traffic-math.slave');a=p.parse_args();os.chdir(ROOT);out=ROOT/'tmp/prof'/a.name;out.mkdir(exist_ok=False);shutil.copyfile(ROOT/'tmp/build'/a.slave,out/'slave.slave');s=Session(out,'a500',out/'slave.slave',0x8520)
try:
 s.boot();hits=[]
 for bank,b in s.dump_banks('traffic-math'):
  i=b.find(b'HDTRMAT1')
  if i>=0:hits.append(b[i+8:i+8+524])
 assert len(hits)==1;raw=hits[0];expected=[]
 def trunc(v):return abs(v)//8*(-1 if v<0 else 1)
 for speed in [-21,-1,0,1,21]:
  for frac in [-7,-1,0,1,7]:
   for mismatch in [0,1]:
    full=speed*8+(0 if mismatch else frac);rev=-full;q=trunc(rev);back=trunc(full);expected.append((q,rev-q*8,q,back,full-back*8))
 assert list(struct.iter_unpack('>hhhhh',raw[:500]))==expected
 assert struct.unpack('>hhhhhhhhhhhh',raw[500:])==(52,2,0,2,0,0,52,0,52,2,0,0)
 r=dict(passed=True,reversal_cases=len(expected),same_value_fraction_reversal=True,mismatch_invalidation=True,initialization_native_step=True,zero_time_no_movement=True);(out/'results.json').write_text(json.dumps(r,indent=2)+'\n');print(r)
finally:s.close()
