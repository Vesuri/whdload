from pathlib import Path
import ctypes as C,json,os,random,struct,subprocess
exec(Path('tools/check_p2_micro.py').read_text().split('for addr,name,path in ')[0])
stem=Path('tmp/c4-road-bounds');stem.with_suffix('.s').write_text(' org $10000\n'+Path('tools/c4_road_bounds.s').read_text());subprocess.run([os.environ['VASM'],'-m68000','-devpac','-Fbin','-o',str(stem.with_suffix('.bin')),str(stem.with_suffix('.s'))],check=True,stdout=subprocess.DEVNULL);write(0x10000,stem.with_suffix('.bin').read_bytes())
rng=random.Random(101317);cases=0;inside=0
try:
 for i in range(5000):
  w=rng.choice([-1,1])*rng.randint(1,500);slope=rng.randint(-500,500);shear=rng.randint(-500,500);length=rng.choice([-1,1])*rng.randint(1,500);cx=rng.randint(-1000,1000);cz=rng.randint(-1000,1000)
  if i%10==0:cx=w;cz=slope
  det=w*length-slope*shear
  vertices=[(w*s+shear*t+cx,0,slope*s+length*t+cz) for t in [-1,0,1] for s in [-1,1]]
  mask=rng.randrange(4)
  tnum=-cz*w+cx*slope
  if det<0:tnum=-tnum
  expected=det!=0 and abs(-cx*length+cz*shear)<=abs(det) and ((mask&2 and -abs(det)<=tnum<=0) or (mask&1 and 0<=tnum<=abs(det)))
  expected=bool(expected)
  write(0x20000,struct.pack('>18h',*(x for v in vertices for x in v)));reg(17,0x2000);reg(2,0x20000);reg(11,mask);reg(8,0x4f000);pack(0x4f000,'I',0x19000)
  rc=u.uc_emu_start(h,0x10000,0x19000,1000000,1000)
  if rc:print('failure',i,[(k,hex(reg(k))) for k in range(1,19)],vertices)
  ok(rc);assert reg(18)==0x19000 and reg(8)==0x4f004
  assert reg(9)==int(expected),(i,vertices,det,expected,reg(9));cases+=1;inside+=expected
 report=dict(passed=True,cases=cases,inside=inside,scope='Actual 68000 projected-road guard versus independent inverse affine coordinates for 5000 straight/sheared/rotated strips, both orientations, shared edge and boundary points, with all four road-gap masks. Not arbitrary folded or degenerate course geometry.')
 Path('tmp/c4-road-bounds-check.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
finally:ok(u.uc_close(h))
