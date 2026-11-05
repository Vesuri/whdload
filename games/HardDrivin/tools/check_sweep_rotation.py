"""Compare sweep rotation with actual pristine collision transformation."""
from pathlib import Path
import json,math,subprocess,os,random
exec(Path('tools/check_native_engine_model.py').read_text().split('results=[]')[0])
s=Path('src/HardDrivinSweep.s').read_text()
s=s[s.index('_sweep_rotate:\n'):s.index('_sweep_finish:\n')]
p=Path('tmp/sweep-rotate.s');p.write_text(' org $400100\n'+s)
subprocess.run([os.environ['VASM'],'-m68000','-Fbin','-devpac','-o','tmp/sweep-rotate.bin',str(p)],check=True,stdout=subprocess.DEVNULL)
write(0x400100,Path('tmp/sweep-rotate.bin').read_bytes())
rng=random.Random(14680);count=15000
try:
 for i in range(count):
  xyz=[rng.randrange(-32768,32768) for _ in range(3)]
  angles=[rng.randrange(1440) for _ in range(2)]
  if i>=5000:angles=[360 if i<10000 else rng.choice([0,360,720,1080]),0 if i>=10000 else angles[1]]
  if i%10==0:xyz=[rng.choice([-32768,-32767,-1,0,1,32766,32767]) for _ in range(3)]
  trigs=[round(f(a*math.pi/720)*16384) for a in angles for f in (math.sin,math.cos)]
  pack(g(0xe93a),'4h',*trigs);pack(0x350000,'3h',*xyz)
  reg(17,0x2000);reg(5,a4);reg(4,0x350000);reg(6,0x4ffe00);reg(8,0x4ffff0)
  ok(u.uc_emu_start(h,codebase+0xbb6e,codebase+0xbbd2,1000000,1000))
  assert reg(8)==0x4ffff0
  actual=[struct.unpack('>h',read(0x4ffe00-off,2))[0] for off in [16,18,20]]
  for k,v in zip([9,10,11],xyz):reg(k,v&0xffffffff)
  pack(0x4ffff0,'I',0x490000)
  ok(u.uc_emu_start(h,0x400100,0x490000,1000000,1000))
  predicted=[(reg(k)+32768)%65536-32768 for k in [9,10,11]]
  assert actual==predicted,(xyz,angles,actual,predicted)
  assert reg(8)==0x4ffff4
 report=dict(passed=True,cases=count,scope='Tracked sweep rotation versus native BB6E..BBD2 and original math helpers. Full signed-word coordinates, random Q14 angles plus explicit quarter-turn/flat-pitch paths and signed endpoints. Not swept curved motion.')
 Path('tmp/sweep-rotation-check.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
finally:ok(u.uc_close(h))
