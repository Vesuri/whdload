"""Compare assembled cached limits with the previous assembled endpoint predicate."""
from pathlib import Path
import json,random,subprocess,os,struct
exec(Path('tools/check_sweep_native.py').read_text().split('results=[]')[0])
old=subprocess.check_output(['git','show','b8a625c:src/HardDrivinSweep.s'],text=True)
new=Path('src/HardDrivinSweep.s').read_text()
for tag,text,addr in [('old',old,0x440100),('new',new,0x450100)]:
 body=text[text.index('_sweep_world_bounds:'):text.index('_sweep_rewind:')]
 p=Path('tmp/sweep-bounds-'+tag)
 p.with_suffix('.s').write_text(f' org ${addr:x}\nSW_START equ 0\nSW_DELTA equ 12\nSW_RAW equ 68\nSW_REJECTED equ 78\nSW_LIMITS equ 82\n bsr _sweep_world_bounds\n bra _sweep_world_near\n'+body)
 subprocess.run([os.environ['VASM'],'-m68000','-Fbin','-devpac','-o',str(p.with_suffix('.bin')),str(p.with_suffix('.s'))],check=True,stdout=subprocess.DEVNULL)
 write(addr,p.with_suffix('.bin').read_bytes())
ok(u.uc_ctl(h,0x4000000a));rng=random.Random(20261013);cases=[]
# Both sides of every limit, zero and full signed-word movement, negative/large extents.
for delta in [-32768,-100,0,100,32767]:
 for extent in [-32768,-1,0,40,32767]:
  radius=3*extent+4
  for raw in [-32768,32767,0,-radius+min(delta,0)-1,-radius+min(delta,0),radius+max(delta,0),radius+max(delta,0)+1]:
   if -32768<=raw<=32767:cases.append(([raw]*3,[delta]*3,[extent]*3))
for i in range(20000):cases.append(([rng.randrange(-32768,32768) for _ in range(3)],[rng.randrange(-32768,32768) for _ in range(3)],[rng.randrange(-32768,32768) for _ in range(3)]))
rejected=0
try:
 for raw,delta,extents in cases:
  start=[rng.randrange(-1000000000,1000000000) for _ in range(3)]
  end=[((s>>3)+d)*8+rng.randrange(8) for s,d in zip(start,delta)]
  snapshots=[]
  for addr in [0x440100,0x450100]:
   write(0x410000,bytes(106));pack(0x410000,'3i',*start);pack(0x41000c,'3h',*delta);pack(0x410044,'3h',*raw);pack(0x41004e,'I',0xffffffff)
   pack(g(0x98fc),'3i',*end)
   for off,v in zip([-22,-24,-26],extents):pack(0x420000+off,'h',v)
   reg(17,0x2000);reg(5,a4);reg(6,0x420000);reg(7,0x410000);reg(4,0x350000);reg(14,0x12345678)
   reg(8,0x4ffff0);pack(0x4ffff0,'I',0x490000);ok(u.uc_emu_start(h,addr,0x490000,1000000,1000))
   assert reg(8)==0x4ffff4 and reg(4)==0x350000 and reg(14)==0x12345678
   snapshots.append((reg(9),reg(15),read(0x410000,82)))
  assert snapshots[0]==snapshots[1],(raw,delta,extents,snapshots)
  rejected+=snapshots[1][0]==0
 report=dict(passed=True,cases=len(cases),rejected=rejected,scope='Old and new assembled 68000 predicates agree exactly on acceptance, radius, existing state/counter wrap and preserved pool registers. Full signed-word raw/delta/extents, bound equality and adjacent values, fractional signed-long start/end. Cached limits are additional private scratch only.')
 Path('tmp/sweep-bounds-equivalence.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
finally:ok(u.uc_close(h))
