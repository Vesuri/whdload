import argparse,json,os,struct,shutil
from capture_demo import ROOT
from capture_session import Session
p=argparse.ArgumentParser();p.add_argument('name',nargs='?',default='s4-time-math-q16');a=p.parse_args();os.chdir(ROOT);out=ROOT/'tmp/prof'/a.name;out.mkdir(exist_ok=False);shutil.copyfile(ROOT/'tmp/build/s4-time-math.slave',out/'slave.slave');s=Session(out,'a500',out/'slave.slave',0x8520)
try:
 s.boot();hits=[];debts=[];q16=[];wide=[]
 for bank,b in s.dump_banks('math'):
  i=b.find(b'HDMATH01')
  if i>=0:hits.append(b[i+8:i+8+4860])
  i=b.find(b'HDDEBT01')
  if i>=0:debts.append(b[i+8:i+8+132])
  i=b.find(b'HDQ16001')
  if i>=0:q16.append(b[i+8:i+8+3528])
  i=b.find(b'HDWIDE01')
  if i>=0:wide.append(b[i+8:i+8+2400])
 assert len(hits)==1
 got=list(struct.iter_unpack('>hh',hits[0]));expected=[]
 for value in [-32768,-100,-3,-1,0,1,3,100,32767]:
  for fields in range(9):
   for carry in range(-7,8):
    n=value*fields+carry;q=abs(n)//8*(-1 if n<0 else 1);expected.append((q,n-q*8))
 assert got==expected,[(i,a,b) for i,(a,b) in enumerate(zip(got,expected)) if a!=b][:10]
 assert len(debts)==1
 assert list(struct.iter_unpack('>III',debts[0]))==[(n-min(n,8),min(n,8)*8192,min(n,8)) for n in [0,1,7,8,9,15,16,65535,524287,524288,0xffffffff]]
 qexpected=[]
 for value in [-16383,-2,-1,0,1,2,16383]:
  for fields in range(9):
   for carry in [-65535,-8192,-1,0,1,8192,65535]:
    n=value*fields*8192+carry;q=abs(n)//65536*(-1 if n<0 else 1);qexpected.append((q,n-q*65536))
 assert len(q16)==1 and list(struct.iter_unpack('>ii',q16[0]))==qexpected
 expected_wide=[]
 for values,unit,carries in [([-32768,-1,0,1,32767],8,[-7,0,7]),([-16383,-1,0,1,16383],65536,[-65535,0,65535])]:
  for value in values:
   for fields in [0,1,7,8,9,15,31,255,32768,65535]:
    for carry in carries:
     n=value*fields*(8192 if unit==65536 else 1)+carry;q=abs(n)//unit*(-1 if n<0 else 1);expected_wide.append((q,n-q*unit))
 assert len(wide)==1 and list(struct.iter_unpack('>ii',wide[0]))==expected_wide
 report=dict(wide_cases=len(expected_wide),q16_cases=441,debt_cases=11,passed=True,cases=len(got),values=[-32768,-100,-3,-1,0,1,3,100,32767],fields=[0,8],carry=[-7,7]);(out/'results.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
finally:s.close()
