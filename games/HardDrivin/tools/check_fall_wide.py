import argparse,json,os,shutil,struct
from capture_demo import ROOT
from capture_session import Session
p=argparse.ArgumentParser();p.add_argument('name',nargs='?',default='s4-fall-wide');a=p.parse_args();os.chdir(ROOT);out=ROOT/'tmp/prof'/a.name;out.mkdir(exist_ok=False);shutil.copyfile(ROOT/'tmp/build/s4-fall-wide.slave',out/'slave.slave');s=Session(out,'a500',out/'slave.slave',0x8520)
try:
 s.boot();hits=[]
 for bank,b in s.dump_banks('wide'):
  i=b.find(b'HDFPWID1')
  if i>=0:hits.append(b[i+8:i+8+17640])
 assert len(hits)==1
 expected=[]
 for v in [-32768,-1,0,1,32767]:
  for frac in [-7,0,7]:
   for accel in [-32768,-2340,-5,0,5,2340,32767]:
    for n in [9,15,31,255,32767,32768,65535]:
     for carry in [-127,0,127]:
      numerator=-v*n*16-frac*n*2+accel*n*(8-n)+carry;q=abs(numerator)//128*(-1 if numerator<0 else 1);expected.append((((q+2147483648)%4294967296)-2147483648,numerator-q*128))
 got=list(struct.iter_unpack('>ii',hits[0]));assert got==expected,[(i,x,y) for i,(x,y) in enumerate(zip(got,expected)) if x!=y][:10]
 result=dict(passed=True,cases=len(got),largest_displacement=max(abs(x[0]) for x in got));(out/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
finally:s.close()
