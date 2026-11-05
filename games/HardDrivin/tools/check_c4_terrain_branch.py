from pathlib import Path
import ctypes as C,json,os,re,struct,subprocess
exec(Path('tools/check_p2_micro.py').read_text().split('for addr,name,path in ')[0])
s=Path('tmp/c4-unbounded-phase-helper.s').read_text();body=s[s.index('_phase_terrain_select:'):];cases=0
try:
 for forced in [False,True]:
  stem=Path('tmp/c4-terrain-branch-'+str(int(forced)))
  text=' org $10000\n'+('VERIFY_DISPATCH_NATIVE equ 1\n' if forced else '')+body+'\n_time_scalar_fields: dc.w 0\n_phase_steering_body: dc.l $3b398\n'
  stem.with_suffix('.s').write_text(text);subprocess.run([os.environ['VASM'],'-m68000','-devpac','-Fbin','-o',str(stem.with_suffix('.bin')),str(stem.with_suffix('.s'))],check=True,stdout=subprocess.DEVNULL)
  blob=stem.with_suffix('.bin').read_bytes();write(0x10000,blob);fields=0x10000+len(blob)-6
  write(0x3cdc4,bytes.fromhex('70014e754e7170024e75'));ok(u.uc_ctl(h,0x4000000a))
  for n in [0,1,2,7,8,9,15,65535]:
   for road in [0,255]:
    for obj in [0,255]:
     reg(17,0x2000);reg(5,0x40000);reg(8,0x4f000);pack(0x4f000,'I',0x19000);pack(fields,'H',n);pack(0x3e94a,'BB',road,obj)
     ok(u.uc_emu_start(h,0x10000,0x19000,1000000,100));assert reg(18)==0x19000 and reg(8)==0x4f004
     expected=1 if road or (not forced and n not in [0,8] and not obj) else 2
     assert reg(9)==expected,(forced,n,road,obj,reg(9));cases+=1
 report=dict(passed=True,cases=cases,scope='Actual assembled selector: zero/native-eight/forced-native preserve original branch, render-road retains road, object surfaces retain native priority, other positive intervals query road geometry. Stack balanced.')
 Path('tmp/c4-terrain-branch.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
finally:ok(u.uc_close(h))
