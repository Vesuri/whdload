"""Old/new assembled iterator equivalence, including all byte classes and flags."""
from pathlib import Path
import json,subprocess,os,struct,random,hashlib
exec(Path('tools/check_sweep_native.py').read_text().split('results=[]')[0])
versions=[subprocess.check_output(['git','show','HEAD:src/HardDrivinSweep.s']).decode(),Path('src/HardDrivinSweep.s').read_text()];modules=[]
for v,src in enumerate(versions):
 asm=' org $400100\nDS_ACTIVE equ 24\n_dispatch_state equ $407000\n_time_scalar_fields equ $407100\n jmp _sweep_finish\n dc.l _sweep_state\n'+src[src.index('_sweep_loop_ptr:'):]
 p=Path(f'tmp/c5-fused-world-{v}');p.with_suffix('.s').write_text(asm);subprocess.run([os.environ['VASM'],'-m68000','-Fbin','-devpac','-o',str(p.with_suffix('.bin')),str(p.with_suffix('.s'))],check=True,stdout=subprocess.DEVNULL);b=p.with_suffix('.bin').read_bytes();modules.append((b,struct.unpack_from('>I',b,6)[0]))
write(0x490000,bytes.fromhex('40f900470000'));rng=random.Random(8321);cases=[]
for i in range(1024):
 results=[];initial=[rng.randrange(0x100000000) for _ in range(16)]
 for module,state in modules:
  write(0x400100,module);ok(u.uc_ctl(h,0x4000000a));write(state,bytes(106))
  for k in range(1,17):reg(k,initial[k-1])
  reg(17,0x2000|(i%32));reg(5,a4);reg(8,0x4ffff0);pack(0x4ffff0,'I',0x490000)
  ok(u.uc_emu_start(h,0x400100,0x490000,1000000,10000));assert reg(8)==0x4ffff4;ok(u.uc_emu_start(h,0x490000,0x490006,1000000,1));results.append(([reg(k) for k in range(1,17)],read(0x470000,2),read(state,106)))
 assert results[0]==results[1],(i,results)
report=dict(passed=True,cases=1024,scope='Inactive/no-contact finish: all native registers, stack pointer, materializedCCR and106statebytes match preceding source.',source_sha256=[hashlib.sha256(x.encode()).hexdigest() for x in versions]);Path('tmp/c5-finish-inactive-check.json').write_text(json.dumps(report,indent=2)+'\n');print(report);ok(u.uc_close(h))
