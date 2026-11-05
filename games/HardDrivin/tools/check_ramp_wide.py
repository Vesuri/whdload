import json,os,shutil,struct
from capture_demo import ROOT
from capture_session import Session
os.chdir(ROOT);out=ROOT/'tmp/prof/s4-ramp-wide';out.mkdir(exist_ok=False);shutil.copyfile(ROOT/'tmp/build/s4-ramp-wide.slave',out/'slave.slave');shutil.copyfile(ROOT/'tmp/ramp-wide-inputs.json',out/'inputs.json');s=Session(out,'a500',out/'slave.slave',0x8520)
def trunc(n,d):return abs(n)//d*(-1 if n<0 else 1)
try:
 s.boot();got={};inputs=json.loads((out/'inputs.json').read_text())
 for bank,b in s.dump_banks('ramps'):
  for sig,size in [(b'HDRAMPT1',len(inputs['throttle'])*8),(b'HDRAMPR1',len(inputs['rpm'])*6)]:
   i=b.find(sig)
   if i>=0:assert sig not in got;got[sig]=b[i+8:i+8+size]
 throttle=[]
 for v,rate,n,carry,last in inputs['throttle']:
  if v!=last:carry=0
  total=rate*n*8192+carry;q=trunc(total,65536);rem=total-q*65536;value=v+q
  if value<=0 and rem<0 or value>=100 and rem>0:rem=0
  value=max(0,min(100,value));throttle.append((value,value,rem))
 assert list(struct.iter_unpack('>HHi',got[b'HDRAMPT1']))==throttle,(list(struct.iter_unpack('>HHi',got[b'HDRAMPT1'])),throttle)
 rpm=[]
 for v,d,n,carry,last,gear,oldgear in inputs['rpm']:
  if v!=last or gear!=oldgear:carry=0
  rate=450 if d>0 else -450 if d<0 else 0;total=rate*n+carry;q=trunc(total,8);rem=total-q*8
  if d==0 or d>0 and q>=d or d<0 and q<=d:q=d;rem=0
  last=v+q
  if last>=6500:last=6500;rem=0
  rpm.append((q,last,rem))
 assert list(struct.iter_unpack('>hhh',got[b'HDRAMPR1']))==rpm,(list(struct.iter_unpack('>hhh',got[b'HDRAMPR1'])),rpm)
 result=dict(passed=True,throttle_cases=len(throttle),rpm_cases=len(rpm));(out/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
finally:s.close()
