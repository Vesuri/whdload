import argparse,json,os,struct,shutil
from capture_demo import ROOT
from capture_session import Session
p=argparse.ArgumentParser();p.add_argument('name',nargs='?',default='s4-projection-math');a=p.parse_args();os.chdir(ROOT);out=ROOT/'tmp/prof'/a.name;out.mkdir(exist_ok=False);shutil.copyfile(ROOT/'tmp/build/s4-projection-math.slave',out/'slave.slave');s=Session(out,'a500',out/'slave.slave',0x8520)
try:
 s.boot();got={}
 for bank,b in s.dump_banks('projection'):
  for sig,size in [(b'HDVPCMP1',720),(b'HDVPDEL1',10584),(b'HDVPROJ1',36)]:
   i=b.find(sig)
   if i>=0:assert sig not in got;got[sig]=b[i+8:i+8+size]
 expected=[]
 for carry in range(-7,8):
  for sy,cy,sp,cp in [(0,16384,0,16384),(11585,11585,8192,14189),(-11585,11585,-8192,14189),(16384,0,16384,0)]:
   v=carry*12288;y=v*sp//16384;along=v*cp//16384;expected.append((along*sy//16384,y,along*cy//16384))
 assert list(struct.iter_unpack('>iii',got[b'HDVPCMP1']))==expected
 deltas=[]
 for v in [-86016,-65535,-1,0,1,65535,86016]:
  for u in [-86016,-65535,-1,0,1,65535,86016]:
   for n in range(9):
    for carry in [-65535,0,65535]:
     full=(v*(8+n)-u*(8-n))//16+carry;q=abs(full)//65536*(-1 if full<0 else 1)
     deltas.append((q,full-q*65536) if n else (0,carry))
 assert list(struct.iter_unpack('>ii',got[b'HDVPDEL1']))==deltas
 assert got[b'HDVPROJ1']==bytes(36)
 r=dict(passed=True,projection_cases=len(expected),euler_cases=len(deltas),reset_cleared=True);(out/'results.json').write_text(json.dumps(r,indent=2)+'\n');print(r)
finally:s.close()
