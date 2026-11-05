from pathlib import Path
import json,os,subprocess,random
exec(Path('tools/check_native_engine_model.py').read_text().split('results=[]')[0])
p=Path('tmp/p4-native-root')
subprocess.run([os.environ['VASM'],'-m68000','-devpac','-Fbin','-L',str(p.with_suffix('.lst')),'-o',str(p.with_suffix('.bin')),str(p.with_suffix('.s'))],check=True,stdout=subprocess.DEVNULL)
blob=p.with_suffix('.bin').read_bytes();assert len(blob)<=0x68,len(blob);write(0x420000,blob)
stop=0x490000;sp=0x4ffff0;write(stop,bytes.fromhex('40f900470000'));r=random.Random(9564)
values=list(range(350001))+[max(0,min(0xffffffff,k*k+d)) for k in range(65537) for d in [-2,-1,0,1,2]]+[r.randrange(0x100000000) for _ in range(10000)]
try:
 for value in values:
  out=[]
  for entry in [codebase+0x9564,0x420000]:
   for k in range(1,17):reg(k,k*0x1010101)
   reg(17,0x2010 if value&1 else 0x2000);reg(5,a4);reg(8,sp);pack(sp,'II',stop,value)
   result=u.uc_emu_start(h,entry,stop,1000000,10000)
   assert result==0,(value,hex(entry),hex(reg(18)),u.uc_strerror(result))
   assert reg(18)==stop and reg(8)==sp+4,(value,hex(entry),hex(reg(18)))
   ok(u.uc_emu_start(h,stop,stop+6,1000000,1))
   out.append(([reg(k) for k in range(1,17)],read(0x470000,2)))
  assert out[0]==out[1],(value,out)
 report=dict(passed=True,cases=len(values),bytes=len(blob),scope='Original native 9564 root versus same Newton recurrence with guarded one-DIVU path; all registers, stack and materialized flags exact. Zero, square boundaries, all inputs through350000 and every unsigned-long square boundary and random unsigned long inputs.')
 Path('tmp/p4-native-root-check.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
finally:ok(u.uc_close(h))
