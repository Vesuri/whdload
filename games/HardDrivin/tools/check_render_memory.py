"""Assembled initialization-hook contract: pointer change only, D0/CCR preserved."""
from pathlib import Path
import os,subprocess,struct,json,hashlib
exec(Path('tools/check_sweep_native.py').read_text().split('import subprocess,sys')[0])
src=Path('src/HardDrivinRender.s').read_text()
body=src[src.index('_render_set_edges:'):src.index('_render_tags:')]
a=Path('tmp/s5-memory-contract');a.with_suffix('.s').write_text(' org $400100\n'+body+'\n_render_edges: dc.l $350000\n')
subprocess.run([os.environ['VASM'],'-m68000','-Fbin','-devpac','-o',str(a.with_suffix('.bin')),str(a.with_suffix('.s'))],check=True,stdout=subprocess.DEVNULL)
write(0x400100,a.with_suffix('.bin').read_bytes());write(0x490000,bytes.fromhex('40f900470000'))
checks=0
for value in [0,1,0x30000,0x200000,0x7fffffff,0x80000000,0xffffffff]:
 for ccr in range(32):
  for k in range(1,17):reg(k,k*0x1010101)
  reg(17,0x2000|ccr);reg(5,0x280000);reg(9,value);reg(8,0x4ffff0);pack(0x4ffff0,'I',0x490000)
  before=[reg(k) for k in range(1,17)];ok(u.uc_emu_start(h,0x400100,0x490000,1000000,100));ok(u.uc_emu_start(h,0x490000,0x490006,1000000,1))
  expected=before[:];expected[0]=0x350000;expected[7]+=4
  assert [reg(k) for k in range(1,17)]==expected
  assert read(0x280000-0x69e0,4)==struct.pack('>I',0x350000)
  got=struct.unpack('>H',read(0x470000,2))[0]&31;want=(ccr&16)|(4 if value==0 else 8 if value&0x80000000 else 0)
  assert got==want,(value,ccr,got,want);checks+=1
r=dict(passed=True,cases=checks,source_sha256=hashlib.sha256(src.encode()).hexdigest(),scope='Fast edge-pointer substitution; all registers, stack and five CCR bits. Original D0 and original native Chip reservation retained.')
Path('tmp/s5-memory-contract.json').write_text(json.dumps(r,indent=2)+'\n');print(r);ok(u.uc_close(h))
