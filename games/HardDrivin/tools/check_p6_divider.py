from pathlib import Path
import json,os,subprocess,random
exec(Path('tools/check_native_engine_model.py').read_text().split('results=[]')[0])
p=Path('tmp/p6-divider')
subprocess.run([os.environ['VASM'],'-m68000','-devpac','-Fbin','-L',str(p.with_suffix('.lst')),'-o',str(p.with_suffix('.bin')),str(p.with_suffix('.s'))],check=True,stdout=subprocess.DEVNULL)
blob=p.with_suffix('.bin').read_bytes();write(0x420000,blob)
stop=0x490000;sp=0x4ffff0;write(stop,bytes.fromhex('40f900470000'));r=random.Random(9564)
values=[(n,d) for d in [1,2,65535,65536,65537,131071,131072,0x7fffffff,0x80000000,0xfffffffe,0xffffffff] for n in [0,1,d-1,d,min(d+1,0xffffffff),0x7fffffff,0x80000000,0xffffffff]]
values += [(r.randrange(0x100000000),r.randrange(1,0x100000000)) for _ in range(60000)]
values += [(min(0xffffffff,d*q+delta),d) for d in [65536,65537,70000,131071] for q in range(0,65536,7) for delta in [0,-1,1] if d*q+delta>=0]

try:
 for value in values:
  numerator,denominator=value
  out=[]
  for entry in [codebase+0x122be,0x420000]:
   for k in range(1,17):reg(k,k*0x1010101)
   reg(17,0x2010 if numerator&1 else 0x2000);reg(5,a4);reg(8,sp);pack(sp,'I',stop);reg(9,numerator);reg(10,denominator)
   result=u.uc_emu_start(h,entry,stop,1000000,10000)
   assert result==0,(value,hex(entry),hex(reg(18)),u.uc_strerror(result))
   assert reg(18)==stop and reg(8)==sp+4,(value,hex(entry),hex(reg(18)))
   ok(u.uc_emu_start(h,stop,stop+6,1000000,1))
   out.append(([reg(k) for k in range(1,17)],read(0x470000,2)))
  assert out[0]==out[1],(value,out)
 report=dict(passed=True,cases=len(values),bytes=len(blob),scope='Original unsigned long divider vs shortened wide loop: quotient, remainder, every register, stack and materialized CCR exact; short path, large divisors and quotient boundaries.')
 Path('tmp/p6-divider-check.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
finally:ok(u.uc_close(h))
