from pathlib import Path
import subprocess,os,struct,json
exec(Path('tools/check_native_engine_model.py').read_text().split('results=[]')[0])
s=Path('src/HardDrivinScalar.s').read_text();block=s[s.index('_time_rpm_engaged:'):s.index('_time_rpm_delta:')]
p=Path('tmp/p4-rpm-clamp');p.with_suffix('.s').write_text(' org $420000\nVERIFY_DRIVETRAIN_PHASE equ 1\nPH_ACTIVE equ 2\n_phase_state equ $420100\n'+block+'\n_time_rpm_delta: illegal\n')
subprocess.run([os.environ['VASM'],'-m68000','-devpac','-Fbin','-o',str(p.with_suffix('.bin')),str(p.with_suffix('.s'))],check=True,stdout=subprocess.DEVNULL)
write(0x420000,p.with_suffix('.bin').read_bytes());write(0x430000,read(codebase+0xb8d2,0xb8ec-0xb8d2)+bytes.fromhex('4e75'))
stop=0x490000;sp=0x4ffff0;write(stop,bytes.fromhex('40f900470000'));pack(0x420102,'H',1)
try:
 for rate in range(65536):
  out=[]
  for entry in [0x430000,0x420000]:
   for k in range(1,17):reg(k,k*0x1010101)
   reg(5,a4);reg(8,sp);reg(13,0xa55a0000|rate);reg(17,0x2010 if rate&1 else 0x2000)
   pack(a4-0x66d6,'H',(rate*31337)&65535);pack(sp,'I',stop)
   ok(u.uc_emu_start(h,entry,stop,1000000,100));assert reg(18)==stop and reg(8)==sp+4
   ok(u.uc_emu_start(h,stop,stop+6,1000000,1))
   out.append(([reg(k) for k in range(1,18)],read(a4-0x66d6,2),read(0x470000,2)))
  assert out[0]==out[1],(rate,out)
 report=dict(passed=True,cases=65536,scope='Every signed-word D4 input against copied original B8D2..B8EC instructions; nonzero D4 high word, varying native RPM, all registers, stack and materialized SR exact. Active-phase path only; fallback covered by whole-engine fixtures.')
 Path('tmp/p4-rpm-clamp-check.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
finally:ok(u.uc_close(h))
