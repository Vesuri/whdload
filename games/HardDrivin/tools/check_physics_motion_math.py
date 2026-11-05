import argparse,json,os,struct,shutil
from decimal import Decimal,getcontext
from capture_demo import ROOT
from capture_session import Session
p=argparse.ArgumentParser();p.add_argument('name',nargs='?',default='s4-crash-math');p.add_argument("--slave",default="s4-motion-math.slave");a=p.parse_args();os.chdir(ROOT);out=ROOT/'tmp/prof'/a.name;out.mkdir(exist_ok=False);shutil.copyfile(ROOT/"tmp/build"/a.slave,out/'slave.slave');s=Session(out,'a500',out/'slave.slave',0x8520)
try:
 s.boot();got={}
 for bank,b in s.dump_banks('motion'):
  for sig,size in [(b'HDANGLE1',1350),(b'HDSPIN02',3570),(b'HDFALL01',648),(b'HDPOS001',10584),(b'HDFPOS01',3240),(b'HDDRIFTM',1120),(b'HDCRASHT',74)]:
   i=b.find(sig)
   if i>=0:assert sig not in got;got[sig]=b[i+8:i+8+size]
 def trunc(n,d):return abs(n)//d*(-1 if n<0 else 1)
 angles=[]
 for rate in [-5,-1,0,1,5]:
  for fields in range(9):
   for current,last,carry in [(719,719,32768),(-719,721,16384),(100,20,-65535)]:
    if current-last not in [0,1440,-1440]:carry=0
    full=rate*fields*8192+carry;q=trunc(full,65536);angles.append((q,full-q*65536,current+q))
 getcontext().prec=60;spin_fields=list(range(9))+[9,15,31,127,255,894,895,65535];losses={n:int(((1-(Decimal(9)/10)**(Decimal(n)/8))*65536).to_integral_value()) for n in spin_fields};spins=[]
 for value in [-52,-11,-1,0,1,11,52]:
  for fields in spin_fields:
   for phase in [0,1,3,6,7]:
    v=value
    for _ in range((fields+phase)//8):
     v=trunc(v*9,10)
     if not v:break
    spins.append((v,(fields+phase)%8))
 falls=[]
 for rate in [-5,0,5]:
  for fields in range(9):
   for current,last,carry in [(49,49,-7),(49,49,7),(49,0,7)]:
    if current!=last:carry=0
    n=rate*fields+carry;q=trunc(n,8);falls.append((q,current+q,n-q*8))
 positions=[]
 for v in [-32768,-257,-1,0,1,257,32767]:
  for u in [-32768,-257,-1,0,1,257,32767]:
   for fields in range(9):
    for carry in [-127,0,127]:
     n=8*(v*(8+fields)-u*(8-fields))+carry
     q=trunc(n,128) if fields else 0
     positions.append((q,n-q*128) if fields else (0,carry))
 actual_positions=list(struct.iter_unpack('>ii',got[b'HDPOS001']))
 assert actual_positions==positions
 # Independent exact-rational subdivision property, both acceleration signs.
 from fractions import Fraction as F
 for start in [-100,0,100]:
  for acceleration in [-16,-8,0,8,16]:
   for count in [1,2,4,8]:
    h=F(1,count);v=F(start);distance=0
    for _ in range(count):
     u=v;v+=acceleration*h
     distance+=v*h+(1-h)*(v-u)/2
    assert distance==start+acceleration
 fall_positions=[]
 for v in [-32768,-1,0,1,32767]:
  for frac in [-7,0,7]:
   for accel in [-5,0,5]:
    for n in range(9):
     numerator=-v*n*16-frac*n*2+accel*n*(8-n)+127
     q=trunc(numerator,128)
     fall_positions.append((q,numerator-q*128))
 assert list(struct.iter_unpack('>ii',got[b'HDFPOS01']))==fall_positions
 drift=[]
 for v in [-32768,-301,-1,0,1,301,32767]:
  distance=sum(trunc(v*n,30) for n in range(30))
  for fields in range(1,9):
   ticks=0;total=0;h=0
   while ticks<240:
    for _ in range(min(fields,240-ticks)):
     total+=trunc(v*(29-ticks//8),30);ticks+=1
    x=trunc(total,8);h=((h<<5)|(h>>27))&0xffffffff;h^=x&0xffffffff;h^=240-ticks
   drift.append((distance,distance,distance,(240+fields-1)//fields,0,h))
 assert list(struct.iter_unpack('>iiihhI',got[b'HDDRIFTM']))==drift
 crash=list(struct.iter_unpack('>hhhh',got[b'HDCRASHT'][:64]))
 assert crash==[((200+n-1)//n,1,0,0) for n in range(1,9)]
 assert struct.unpack('>hhhhh',got[b'HDCRASHT'][64:])==(0,200,25,199,25)
 actual_falls=list(struct.iter_unpack('>ihh',got[b'HDFALL01']))
 actual_angles=list(struct.iter_unpack('>iih',got[b'HDANGLE1']));actual_spins=list(struct.iter_unpack('>hi',got[b'HDSPIN02']));diffs=dict(angles=[(i,x,y) for i,(x,y) in enumerate(zip(actual_angles,angles)) if x!=y],spins=[(i,x,y) for i,(x,y) in enumerate(zip(actual_spins,spins)) if x!=y]);diffs['fall']=[(i,x,y) for i,(x,y) in enumerate(zip(actual_falls,falls)) if x!=y];r=dict(passed=not any(diffs.values()),crash_sequences=len(crash),full_drift_sequences=len(drift),fall_position_cases=len(fall_positions),position_cases=len(positions),subdivision_cases=60,fall_cases=len(falls),angle_cases=len(angles),spin_cases=len(spins),losses=losses,differences=diffs);(out/'results.json').write_text(json.dumps(r,indent=2)+'\n');print(r);assert r['passed']
finally:s.close()
