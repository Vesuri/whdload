from pathlib import Path
import ctypes as C,json,os,struct,subprocess,random
exec(Path('tools/check_p2_micro.py').read_text().split('for addr,name,path in ')[0])
texts=[subprocess.check_output(['git','show','7049f46:src/HardDrivinMotion.s'],text=True),Path('src/HardDrivinMotion.s').read_text()]
constants='''
_terrain_continuing equ $17000
_motion_crash_state equ $17010
_motion_state equ $17020
_motion_position_state equ $17060
_phase_reset equ $17800
_projection_reset equ $17800
_contact_reset equ $17800
_motion_drift_reset equ $17800
'''
for i,s in enumerate(texts):
 stem=Path('tmp/c4-reset-'+str(i));body=s[s.index('_motion_reset:'):s.index('MS_YAW equ')];stem.with_suffix('.s').write_text(' org $%x\nVERIFY_DRIVETRAIN_PHASE equ 1\n'%(0x10000+i*0x4000)+body+constants)
 subprocess.run([os.environ['VASM'],'-m68000','-devpac','-Fbin','-o',str(stem.with_suffix('.bin')),str(stem.with_suffix('.s'))],check=True,stdout=subprocess.DEVNULL);write(0x10000+i*0x4000,stem.with_suffix('.bin').read_bytes())
write(0x17800,bytes.fromhex('4e75'));write(0x20000,bytes.fromhex('40f900022000'))
rng=random.Random(117);count=0
try:
 for n in range(256):
  state=bytes(rng.randrange(256) for _ in range(128));ccr=rng.randrange(32);regs=[rng.randrange(1<<32) for _ in range(16)];out=[]
  for i in range(2):
   write(0x17000,state);reg(17,0x2000+ccr)
   for k,v in enumerate(regs,1):reg(k,v)
   reg(8,0x4f000);pack(0x4f000,'I',0x20000);ok(u.uc_emu_start(h,0x10000+i*0x4000,0x20006,1000000,10000));assert reg(18)==0x20006 and reg(8)==0x4f004
   out.append((read(0x17000,128),[reg(k) for k in range(1,17)],read(0x22000,2)))
  assert out[1][0][:2]==b'\0\0' and out[1][0][2:]==out[0][0][2:] and out[1][1:]==out[0][1:];count+=1
 report=dict(passed=True,cases=count,scope='Assembled candidate motion reset versus authoritative reset, with unchanged nested reset calls stubbed: only added state word changes, registers/stack/materialized CCR preserved. Does not prove all lifecycle callers invoke reset.')
 Path('tmp/c4-road-reset-check.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
finally:ok(u.uc_close(h))
