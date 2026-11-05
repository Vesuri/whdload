"""Check Q6 phase forecast projection with actual 68000 assembly."""
from pathlib import Path
import math,json,random,subprocess,os
exec(Path('tools/check_native_engine_model.py').read_text().split('results=[]')[0])
subprocess.run([os.environ['VASM'],'-m68000','-Fbin','-devpac','-o','tmp/c1-phase-project.bin','tmp/c1-phase-project.s'],check=True,stdout=subprocess.DEVNULL)
write(0x400100,Path('tmp/c1-phase-project.bin').read_bytes());rng=random.Random(64314)
def project(v,t):
 sy,cy,sp,cp=t;base=v+(v>>1);y=base*sp//16384;z0=base*cp//16384
 return [z0*sy//16384,y,z0*cy//16384]
try:
 for i in range(20000):
  v=rng.randrange(-2000,2001);f=rng.randrange(64);a,b=[rng.randrange(1440) for _ in range(2)]
  tr=[round(fn(ang*math.pi/720)*16384) for ang in (a,b) for fn in (math.sin,math.cos)]
  if i%3==0:tr=[(16384,0,0,16384),(-16384,0,0,16384),(0,16384,0,16384),(0,-16384,0,16384)][i%4]
  lo,hi=project(v,tr),project(v+1,tr)
  expected=[x*65536+(y-x)*f*1024 for x,y in zip(lo,hi)]
  pack(a4-0x6bb8,'4h',*tr);reg(17,0x2000)
  for k in range(1,17):reg(k,k*0x10101)
  reg(1,0x410000);reg(5,a4);reg(9,v*65536+f*1024);reg(8,0x4ffff0);pack(0x4ffff0,'I',0x490000)
  saved=[reg(k) for k in range(1,17)]
  ok(u.uc_emu_start(h,0x400100,0x490000,1000000,1000))
  actual=list(struct.unpack('>3i',read(0x410000,12)))
  assert actual==expected,(v,f,tr,actual,expected)
  assert reg(8)==0x4ffff4 and all(reg(k)==saved[k-1] for k in range(1,17) if k!=8)
 report=dict(passed=True,cases=20000,scope='Private 68000 Q6 forecast interpolation between adjacent native rounded vectors; signed velocity -2000..2000, cardinal and general orientations, independent Q14 yaw/pitch, all registers and stack. No live integration or contact claim.')
 Path('tmp/c1-phase-project-check.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
finally:ok(u.uc_close(h))
