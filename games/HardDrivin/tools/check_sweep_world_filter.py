"""Reject no exact rotated-box crossing in the supported nonwrapping range."""
from pathlib import Path
from fractions import Fraction
import random,math,json,subprocess,os
exec(Path('tools/check_native_engine_model.py').read_text().split('results=[]')[0])
s=Path('src/HardDrivinSweep.s').read_text();s=s[s.index('_sweep_world_bounds:\n'):s.index('_sweep_rewind:\n')]
p=Path('tmp/sweep-filter.s');p.write_text(' org $400100\nSW_START equ 0\nSW_LIMITS equ 82\nSW_RAW equ 68\nSW_DELTA equ 12\nSW_REJECTED equ 78\n bsr _sweep_world_bounds\n bra _sweep_world_near\n'+s)
subprocess.run([os.environ['VASM'],'-m68000','-Fbin','-devpac','-o','tmp/sweep-filter.bin',str(p)],check=True,stdout=subprocess.DEVNULL)
write(0x400100,Path('tmp/sweep-filter.bin').read_bytes());rng=random.Random(165)

def rotate(v,tr):
 x,y,z=v;sa,ca,sb,cb=tr
 x1=(x*ca-z*sa)//16384;z1=(x*sa+z*ca)//16384
 return (x1,(y*cb-z1*sb)//16384,(y*sb+z1*cb)//16384)
def crosses(a,b,lo,hi):
 first,last=Fraction(0),Fraction(1)
 for x,y,l,r in zip(a,b,lo,hi):
  if x==y:
   if not l<=x<=r:return False
  else:
   p,q=sorted([Fraction(l-x,y-x),Fraction(r-x,y-x)]);first=max(first,p);last=min(last,q)
 return first<=last
hits=rejected=0
try:
 for i in range(10000):
  a=[rng.randrange(-8000,8001) for _ in range(3)]
  b=[-x+rng.randrange(-1000,1001) for x in a]
  angles=[rng.randrange(1440) for _ in range(2)]
  tr=[round(f(t*math.pi/720)*16384) for t in angles for f in (math.sin,math.cos)]
  mph=rng.randrange(1501);width=30+(mph>>3);depth=40+mph//3
  exact=crosses(rotate(a,tr),rotate(b,tr),[-width,-width,3],[width,width,depth])
  hits+=exact
  pack(0x410000+68,'3h',*a);pack(0x410000+12,'3h',*[x-y for x,y in zip(a,b)])
  pack(0x410000,'3i',0,0,0);pack(0x430000-0x6704,'3i',*[(x-y)*8 for x,y in zip(a,b)])
  for off,v in [(-22,width),(-24,width),(-26,depth)]:pack(0x420000+off,'h',v)
  reg(17,0x2000);reg(5,0x430000);reg(7,0x410000);reg(6,0x420000);reg(4,0x350000);reg(14,0x12345678);reg(15,0x13579ace)
  reg(8,0x4ffff0);pack(0x4ffff0,'I',0x490000)
  ok(u.uc_emu_start(h,0x400100,0x490000,1000000,1000))
  assert not exact or reg(9)==1,(a,b,angles,mph)
  assert reg(8)==0x4ffff4 and reg(4)==0x350000 and reg(14)==0x12345678 and reg(15)==2*width+depth+4
  rejected+=reg(9)==0
 report=dict(passed=True,cases=10000,exact_contacts=hits,rejected=rejected,scope='Actual world filter rejects no exact rational rotated-box crossing over nonwrapping signed-word geometry, MPH0..1500, two independent Q14 angles. Not arbitrary overflowing transforms.')
 Path('tmp/sweep-world-filter-check.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
finally:ok(u.uc_close(h))
