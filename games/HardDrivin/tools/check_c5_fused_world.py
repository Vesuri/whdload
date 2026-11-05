"""Old/new assembled iterator equivalence, including all byte classes and flags."""
from pathlib import Path
import json,subprocess,os,struct,random,hashlib
exec(Path('tools/check_sweep_native.py').read_text().split('results=[]')[0])
versions=[subprocess.check_output(['git','show','HEAD:src/HardDrivinSweep.s']).decode(),Path('src/HardDrivinSweep.s').read_text()];modules=[]
for v,src in enumerate(versions):
 asm=' org $400100\nDS_ACTIVE equ 24\n_dispatch_state equ $407000\n_time_scalar_fields equ $407100\n jmp _sweep_world\n dc.l _sweep_state\n'+src[src.index('_sweep_loop_ptr:'):]
 p=Path(f'tmp/c5-fused-world-{v}');p.with_suffix('.s').write_text(asm);subprocess.run([os.environ['VASM'],'-m68000','-Fbin','-devpac','-o',str(p.with_suffix('.bin')),str(p.with_suffix('.s'))],check=True,stdout=subprocess.DEVNULL);b=p.with_suffix('.bin').read_bytes();modules.append((b,struct.unpack_from('>I',b,6)[0]))
write(0x490000,bytes.fromhex('40f900470000'));rng=random.Random(8321);cases=[]
for i in range(1536):
 count=rng.choice([0,1,2,7,98,129]);active=(i//256)%4!=0;native_hit=i%7==0;move=rng.choice([0,4,80,300,40000,-40000]);results=[]
 objects=bytearray(count*56)
 for j in range(count):
  struct.pack_into('>hhh',objects,j*56+8,rng.randrange(-2000,2001),rng.randrange(-80,81),rng.randrange(-2000,2001));objects[j*56+28]=(i%256 if j%2==0 else rng.choice([8,64,1]));objects[j*56+30]=rng.choice([0,1,255]);objects[j*56+25]=rng.choice([1,1,95])
 for module,state in modules:
  write(0x400100,module);ok(u.uc_ctl(h,0x4000000a));write(state,bytes(106));pack(state+50,'H',int(active));pack(state+74,'I',0xfffffff0);pack(g(0x9962),'IH',0x350000,count);write(0x350000,bytes(objects));write(g(0xe931),bytes([255 if native_hit else 0]));pack(g(0x98fc),'3i',move*8,0,0);pack(g(0x98ea),'3h',0,0,0);pack(g(0xe93a),'4h',0,16384,0,16384)
  for k in range(1,17):reg(k,k*0x1010101)
  reg(17,0x2010 if i%2 else 0x2000);reg(5,a4);reg(7,state);reg(6,0x4ffe00)
  for off in [-22,-24,-26]:pack(0x4ffe00+off,'h',40)
  reg(8,0x4ffff0);pack(0x4ffff0,'I',0x490000);ok(u.uc_emu_start(h,0x400100,0x490000,1000000,100000));assert reg(8)==0x4ffff4;ok(u.uc_emu_start(h,0x490000,0x490006,1000000,1));results.append((read(state,106),read(0x350000,count*56),[reg(k) for k in range(1,17)],read(0x470000,2)))
 assert results[0]==results[1],(i,count,active,native_hit,move,results)
 cases.append(i)
report=dict(passed=True,cases=len(cases),scope='Previous/current assembled world iterator: all256class bytes, active/type filters, empty/multiple pools, overflow and wrapped counters; all106statebytes, objectrecords, registers, stack and materializedCCR.',source_sha256=[hashlib.sha256(x.encode()).hexdigest() for x in versions]);Path('tmp/c5-fused-world-check.json').write_text(json.dumps(report,indent=2)+'\n');print(report);ok(u.uc_close(h))
