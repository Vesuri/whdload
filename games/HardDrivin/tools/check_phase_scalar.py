"""Actual 68000 incremental phase kernel versus exact rational arithmetic."""
from pathlib import Path
from fractions import Fraction as F
import json,random,subprocess,os
exec(Path('tools/check_native_engine_model.py').read_text().split('results=[]')[0])
subprocess.run([os.environ['VASM'],'-m68000','-Fbin','-devpac','-o','tmp/phase-scalar.bin','tmp/phase-scalar.s'],check=True,stdout=subprocess.DEVNULL)
write(0x400100,Path('tmp/phase-scalar.bin').read_bytes())
rng=random.Random(88016);cases=10000
try:
 for i in range(cases):
  anchor=F(rng.randrange(32768*8),8)
  old=rng.randrange(32768);end=rng.randrange(32768)
  phase=rng.randrange(8);remaining=8-phase;dt=rng.randrange(1,remaining+1)
  current=anchor+(old-anchor)*phase/8
  expected=current+(end-anchor)*dt/8;forecast=current+(end-anchor)*remaining/8
  pack(0x410000,'II',int(anchor*65536),int(current*65536))
  reg(17,0x2000)
  for k in range(1,17):reg(k,k*0x10101)
  reg(1,0x410000);reg(9,end);reg(10,dt);reg(11,remaining);reg(8,0x4ffff0);pack(0x4ffff0,'I',0x490000)
  saved=[reg(k) for k in range(1,17)]
  ok(u.uc_emu_start(h,0x400100,0x490000,1000000,1000))
  actual=struct.unpack('>I',read(0x410004,4))[0]
  assert actual==expected*65536 and reg(9)==forecast*65536,(anchor,current,end,dt,remaining,actual,expected)
  assert read(0x410000,4)==struct.pack('>I',int(anchor*65536))
  assert reg(8)==0x4ffff4
  assert all(reg(k)==saved[k-1] for k in range(1,17) if k not in [8,9,12,13,14])
 report=dict(passed=True,cases=cases,kernel_bytes=Path('tmp/phase-scalar.bin').stat().st_size,scope='Private assembled 68000 scalar update/forecast with nonnegative word endpoints and Q3 phase anchors. Exact Q16 implementation of incremental prototype; no engine, gear, position or live-game integration.')
 Path('tmp/phase-scalar-check.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
finally:ok(u.uc_close(h))
