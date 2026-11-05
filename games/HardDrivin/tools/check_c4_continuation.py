from pathlib import Path
import ctypes as C,json,os,struct,subprocess
exec(Path('tools/check_p2_micro.py').read_text().split('for addr,name,path in ')[0])
s=Path('tmp/c4-fixture-source/HardDrivinTime.s').read_text();body=s[s.index('_private_terrain_select:'):s.index('; Preserve the displaced native writes')]
count=0
try:
 for forced in [False,True]:
  stem=Path('tmp/c4-continuation-'+str(forced));tail='\n_private_road_mask: moveq #3,d2\n rts\n_private_road_bounds: move.w _bounds_result(pc),d0\n rts\n_private_road_continuing: dc.w 0\n_private_road_selected: dc.w 0\n_bounds_result: dc.w 0\n_time_scalar_fields: dc.w 0\n_phase_steering_body: dc.l $3b398\n'
  stem.with_suffix('.s').write_text(' org $10000\n'+('VERIFY_DISPATCH_NATIVE equ 1\n' if forced else '')+body+tail);subprocess.run([os.environ['VASM'],'-m68000','-devpac','-Fbin','-o',str(stem.with_suffix('.bin')),str(stem.with_suffix('.s'))],check=True,stdout=subprocess.DEVNULL)
  blob=stem.with_suffix('.bin').read_bytes();write(0x10000,blob);state=0x10000+len(blob)-12
  write(0x3c022,bytes.fromhex('4e75'));write(0x3cdc4,bytes.fromhex('70014e754e7170024e75'));ok(u.uc_ctl(h,0x4000000a))
  for n in [0,1,8,9]:
   for road in [0,255]:
    for obj in [0,255]:
     for prior in [0,1]:
      for mask in [0,8,15]:
       for inside in [0,1]:
        reg(17,0x2000);reg(5,0x40000);reg(8,0x4f000);pack(0x4f000,'I',0x19000);pack(state,'4H',prior,0,inside,n);pack(0x3e94a,'BB',road,obj);pack(0x39910,'B',mask)
        ok(u.uc_emu_start(h,0x10000,0x19000,1000000,1000));assert reg(18)==0x19000 and reg(8)==0x4f004
        expected=bool(road or (not forced and n not in [0,8] and not obj and prior and mask and inside))
        assert reg(9)==(1 if expected else 2),(forced,n,road,obj,prior,mask,inside,reg(9))
        assert struct.unpack('>H',read(state,2))[0]==int(expected);count+=1
 report=dict(passed=True,cases=count,scope='Assembled continuation selector state transitions with geometry result stubbed: original flags/native modes preserved; no added road without prior road and contact; loss/rejection clears eligibility. Geometry/gap checks validated separately; no overhead or whole-route proof.')
 Path('tmp/c4-continuation-check.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
finally:ok(u.uc_close(h))
