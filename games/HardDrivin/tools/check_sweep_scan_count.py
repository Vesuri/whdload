from pathlib import Path
import json,subprocess,os,struct
exec(Path('tools/check_sweep_native.py').read_text().split('results=[]')[0])
source=Path('src/HardDrivinSweep.s').read_text();source=source[source.index('_sweep_loop_ptr:'):]
asm=' org $400100\nDS_ACTIVE equ 24\n_dispatch_state equ $407000\n_time_scalar_fields equ $407100\n jmp _sweep_world\n dc.l _sweep_state\n'+source
p=Path('tmp/sweep-scan-count');p.with_suffix('.s').write_text(asm)
subprocess.run([os.environ['VASM'],'-m68000','-Fbin','-devpac','-o',str(p.with_suffix('.bin')),str(p.with_suffix('.s'))],check=True,stdout=subprocess.DEVNULL)
b=p.with_suffix('.bin').read_bytes();state=struct.unpack_from('>I',b,6)[0];write(0x400100,b);ok(u.uc_ctl(h,0x4000000a));checks=[]
try:
 for count in [0,1,2,98]:
  for first in sorted(set([-1,0,count//2,count-1])):
   if first>=count:continue
   for previous in [0,0xfffffff0]:
    write(state,bytes(82));pack(state+50,'H',1);pack(state+74,'I',previous)
    pack(g(0x9962),'IH',0x350000,count);write(g(0xe931),b'\0');pack(g(0x98fc),'3i',320000,0,0)
    for i in range(count):
     o=0x350000+56*i;write(o,bytes(56));write(o+28,bytes([8 if i==first else 1]));write(o+30,b'\1');write(o+25,b'\1')
    reg(17,0x2000);reg(5,a4);reg(7,state);reg(6,0x4ffe00)
    for off in [-22,-24,-26]:pack(0x4ffe00+off,'h',40)
    reg(8,0x4ffff0);pack(0x4ffff0,'I',0x490000);ok(u.uc_emu_start(h,0x400100,0x490000,1000000,20000));assert reg(8)==0x4ffff4
    scanned=struct.unpack('>I',read(state+74,4))[0];overflow=struct.unpack('>I',read(state+62,4))[0]
    expected=count if first<0 else first+1
    assert scanned==(previous+expected)&0xffffffff,(count,first,scanned,previous)
    assert overflow==int(first>=0) and read(state+66,2)==b'\0\0'
    checks.append(dict(count=count,first_eligible=first,previous=previous,scanned=scanned,overflow=overflow))
 report=dict(passed=True,cases=len(checks),scope='Actual pool iterator counts every visited object, including non-solid entries, empty pools, early range overflow at first/middle/last candidate, and 32-bit counter wrap.',checks=checks)
 Path('tmp/sweep-scan-count.json').write_text(json.dumps(report,indent=2)+'\n');print({k:v for k,v in report.items() if k!='checks'})
finally:ok(u.uc_close(h))
