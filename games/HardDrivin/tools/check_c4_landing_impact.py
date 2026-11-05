from pathlib import Path
import ctypes as C,json,os,struct,subprocess
exec(Path('tools/check_p2_micro.py').read_text().split('for addr,name,path in ')[0])
for forced,addr in [(False,0x10000),(True,0x14000)]:
 stem=Path('tmp/c4-landing-impact-'+str(forced));stem.with_suffix('.s').write_text(f' org ${addr:x}\n'+('VERIFY_DISPATCH_NATIVE equ 1\n' if forced else '')+Path('tools/c4_landing_impact.s').read_text()+f'\n_time_scalar_fields equ ${addr+0x1000:x}\n_motion_fall_ground equ $18000\n');subprocess.run([os.environ['VASM'],'-m68000','-devpac','-Fbin','-o',str(stem.with_suffix('.bin')),str(stem.with_suffix('.s'))],check=True,stdout=subprocess.DEVNULL);write(addr,stem.with_suffix('.bin').read_bytes())
motion=Path('src/HardDrivinMotion.s').read_text()
reference=motion[motion.index('_motion_fall_ground:'):motion.index('_motion_fall_ground_end:')]+motion[motion.index('_motion_fall_reset_fraction:'):motion.index('_motion_contact_rates:')]
stem=Path('tmp/c4-landing-reference');stem.with_suffix('.s').write_text(' org $18000\n'+reference+'\n_code_start: dc.l $6370\n_motion_state equ $1f000\nMS_FALL_CARRY equ 18\nMS_FALL_ACCEL equ 30\n');subprocess.run([os.environ['VASM'],'-m68000','-devpac','-Fbin','-o',str(stem.with_suffix('.bin')),str(stem.with_suffix('.s'))],check=True,stdout=subprocess.DEVNULL);write(0x18000,stem.with_suffix('.bin').read_bytes())
for target in [0x13000,0x13006,0x13000-0x46]:write(target,bytes.fromhex('40f900022000'))
count=0;native_cases=0
try:
 for forced,addr in [(False,0x10000),(True,0x14000)]:
  for n in [0,1,2,7,8,9,16]:
   for fall in [-32768,0,49,50,51,131,32767]:
    for crash in [0,25]:
     for slope in [0,255]:
      for ccr in [0,15,16,31]:
       native=forced or n in [0,8];impact=not native and crash==0 and fall>50;target=0x13000-0x46 if impact else 0x13006 if slope else 0x13000
       def setup():
        reg(17,0x2000+ccr)
        for k in range(1,17):reg(k,0x12340000+k)
        reg(5,0x40000);reg(8,0x4f000);pack(0x4f000,'I',0x13000);pack(addr+0x1000,'H',n);pack(0x40000-0x69fa,'B',crash);pack(0x40000-0x66f2,'h',fall);pack(0x40000-0x86f,'B',slope)
       setup();before=[reg(k) for k in range(1,17)];ok(u.uc_emu_start(h,addr,target,1000000,1000));assert reg(18)==target and reg(8)==0x4f004
       ok(u.uc_emu_start(h,target,target+6,1000000,10));actual_ccr=struct.unpack('>H',read(0x22000,2))[0]
       actual=[reg(k) for k in range(1,18)];assert actual[:7]+actual[8:16]==before[:7]+before[8:]
       assert actual_ccr&16==ccr&16
       if native:
        setup();ok(u.uc_emu_start(h,0x18000,target+6,1000000,1000));native_ccr=struct.unpack('>H',read(0x22000,2))[0];assert reg(18)==target+6 and native_ccr==actual_ccr,(forced,n,fall,crash,slope,ccr,native_ccr,actual_ccr);native_cases+=1
       count+=1
 report=dict(passed=True,cases=count,native_equivalence_cases=native_cases,scope='Actual assembled impact hook versus existing motion ground hook for zero/eight and forced-native modes; impact threshold boundaries, existing crashes, slope branch, registers, stack, X flag. Not full trajectory or impact-policy acceptance.')
 Path('tmp/c4-landing-impact-check.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
finally:ok(u.uc_close(h))
