from pathlib import Path
import random,subprocess,os,json,struct
exec(Path('tools/check_sweep_native.py').read_text().split('results=[]')[0])
old=subprocess.check_output(['git','show','b8a625c:src/HardDrivinSweep.s'],text=True);new=Path('src/HardDrivinSweep.s').read_text()
for tag,text,addr in [('old',old,0x440100),('new',new,0x450100)]:
 body=text[text.index('.endpoints:'):text.index(' lea SW_BOX(a6),a0\n move.w 2(a0),d0')]
 p=Path('tmp/sweep-endpoints-'+tag);p.with_suffix('.s').write_text(f' org ${addr:x}\n_test:\n'+body+' moveq #1,d0\n rts\n.overflow:\n moveq #0,d0\n rts\n')
 subprocess.run([os.environ['VASM'],'-m68000','-Fbin','-devpac','-o',str(p.with_suffix('.bin')),str(p.with_suffix('.s'))],check=True,stdout=subprocess.DEVNULL);write(addr,p.with_suffix('.bin').read_bytes())
ok(u.uc_ctl(h,0x4000000a));rng=random.Random(68000);cases=[]
for x in [-32768,-32767,-1,0,1,32766,32767]:
 for d in [-32768,-32767,-1,0,1,32766,32767]:cases.append(([x]*3,[d]*3))
for i in range(20000):cases.append(([rng.randrange(-32768,32768) for _ in range(3)],[rng.randrange(-32768,32768) for _ in range(3)]))
valid=0
try:
 for raw,delta in cases:
  states=[]
  for addr in [0x440100,0x450100]:
   write(0x410000,b'\xab'*24);pack(0x420000,'3h',*delta);pack(0x430000,'3h',*raw)
   reg(17,0x2000);reg(1,0x410000);reg(2,0x420000);reg(3,0x430000);reg(16,2);reg(8,0x4ffff0);pack(0x4ffff0,'I',0x490000)
   ok(u.uc_emu_start(h,addr,0x490000,1000000,1000));states.append((reg(9),read(0x410000,24)));assert reg(8)==0x4ffff4
  assert states[0]==states[1],(raw,delta,states)
  expected=all(-32768<=x-d<=32767 for x,d in zip(raw,delta));assert states[1][0]==int(expected);valid+=expected
 report=dict(passed=True,cases=len(cases),valid=valid,scope='Assembled old longword range check and new SUB.W overflow check agree on all stored endpoints and early overflow, including signed-word extrema and failures on each axis.')
 Path('tmp/sweep-endpoints-check.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
finally:ok(u.uc_close(h))
