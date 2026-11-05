import argparse,json,os,struct,shutil
from decimal import Decimal,getcontext
from capture_demo import ROOT
from capture_session import Session
p=argparse.ArgumentParser();p.add_argument('name',nargs='?',default='s4-retention-math');a=p.parse_args();os.chdir(ROOT);out=ROOT/'tmp/prof'/a.name;out.mkdir(exist_ok=False);shutil.copyfile(ROOT/'tmp/build/s4-retention-math.slave',out/'slave.slave');s=Session(out,'a500',out/'slave.slave',0x8520)
try:
 s.boot();hits=[]
 for bank,b in s.dump_banks('retention'):
  i=b.find(b'HDRETN01')
  if i>=0:hits.append(b[i+8:i+8+3570])
 assert len(hits)==1
 got=list(struct.iter_unpack('>Hi',hits[0]));expected=[];getcontext().prec=60
 fields_list=list(range(9))+[9,15,31,255,705,706,32768,65535]
 losses={n:int(((1-(Decimal(7)/8)**(Decimal(n)/8))*65536).to_integral_value()) for n in fields_list}
 for value in [31,32,50,99,100]:
  for fields in fields_list:
   for carry in [-65535,-8192,-1,0,1,8192,65535]:
    if fields==8:expected.append((value*7//8,0))
    else:
     x=value*65536+carry;y=x-x*losses[fields]//65536;expected.append((y//65536,y%65536))
 diffs=[(i,x,y) for i,(x,y) in enumerate(zip(got,expected)) if x!=y];r=dict(passed=not diffs,cases=len(got),losses=losses,differences=diffs);(out/'results.json').write_text(json.dumps(r,indent=2)+'\n');print(r);assert r['passed']
finally:s.close()
