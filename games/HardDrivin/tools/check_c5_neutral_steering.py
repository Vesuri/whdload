"""Private candidate: skip repeated neutral steering within one phase frame."""
from pathlib import Path
import ctypes as C,json,os,random,re,struct,subprocess
exec(Path('tools/check_c3_steering_native_frame.py').read_text().split('rng=random.Random')[0])
source=subprocess.check_output(['git','show','85b70ba:src/HardDrivinPhase.s'],text=True)
body=source[source.index('_phase_frame:'):source.index('_phase_engine_call:')]
current=Path('src/HardDrivinPhase.s').read_text()
candidate=current[current.index('_phase_frame:'):current.index('_phase_engine_call:')]
# Preserve conversion to MPH for every engine segment; only steering is skipped.
constants=source[source.index('PH_VALID equ'):source.index(" dc.b 'HDPHASE1'")]
addr=sy['_phase_frame']+0x2000
assert addr+2000 < 0xe00000
bodies=[]
for name,txt in [('old',body),('candidate',candidate)]:
 stem=Path('tmp/c5-neutral-'+name)
 symbols='\n'.join('%s equ $%x'%(k,v) for k,v in sy.items() if k!='_phase_frame')
 stem.with_suffix('.s').write_text(' org $%x\n'%addr+'DS_ACTIVE equ 24\n'+constants+symbols+'\n'+txt)
 subprocess.run([os.environ['VASM'],'-m68000','-devpac','-Fbin','-o',str(stem.with_suffix('.bin')),str(stem.with_suffix('.s'))],check=True,stdout=subprocess.DEVNULL)
 bodies.append(stem.with_suffix('.bin').read_bytes())
rng=random.Random(131009);cases=0
try:
 for n in [1,7,8,9,15,16,24,31]:
  for mouse in [0,300,301,319,320,321,339,340,639]:
   for velocity in [-500,0,100,500]:
    rpm=rng.randrange(1000,6501);gear=rng.randrange(1,5);angles=[rng.randrange(-720,721),rng.randrange(-180,181),rng.randrange(-180,181)];outputs=[]
    for blob in bodies:
     for a,b in images:write(a,b)
     write(addr,blob);write(a4-0x7fe0,bytes.fromhex('4e75'));ok(u.uc_ctl(h,0x4000000a))
     for k in range(1,17):reg(k,k*0x10101)
     reg(17,0x2000);reg(5,a4)
     for off,value in [(0x9606,0),(0x9605,0),(0x9910,15),(0x993e,255),(0x991c,22),(0x9911,0),(0x991d,0),(0x95ff,0),(0xe94a,255),(0xaf31,0),(0xf790,0),(0xf791,255),(0xaddc,0)]:pack(a4+off-65536,'B',value)
     for off,value in [(0x9928,velocity),(0x992a,rpm),(0x9936,gear),(0x990e,0),(0x95fa,mouse)]:pack(a4+off-65536,'h',value)
     import drivetrain_model as model
     pack(a4-0x66da,'h',model.engine_speed(rpm,gear));pack(a4-0x66c0,'I',a4-0x68c6+gear*8);pack(a4-0x6bb8,'4h',16384,0,0,16384)
     for off,value in zip([0x994a,0x9946,0x9948,0x9914,0x9916,0x991a],angles+[0,0,0]):pack(a4+off-65536,'h',value)
     pack(a4-0x66d4,'h',model.convert(rpm,*model.TABLE[gear]));pack(sy['_dispatch_state']+28,'h',mouse)
     pack(sy['_time_scalar_fields'],'H',n);write(sy['_dispatch_state']+24,b'\x01')
     for symbol,size in [('_phase_state',78),('_phase_speed_cache',8),('_time_scalar_state',16),('_drivetrain_state',16),('_projection_state',36),('_motion_position_state',20),('_motion_state',32),('_phase_steering_pending',2)]:write(sy[symbol],bytes(size))
     frames=[]
     for step in range(12):
      held=[mouse,320,301,339,400,320][step%6]
      pack(sy['_dispatch_state']+28,'h',held)
      pack(sy['_time_scalar_fields'],'H',n)
      pack(a4-0x66e4,'B',22 if step<5 or step>8 else 0)
      pack(a4-0x66ef,'B',255 if 5<=step<=8 else 0)
      pack(a4-0x66f0,'B',[15,3,0][step%3])
      pack(a4-0x66ec,'h',step%3-1);pack(a4-0x66ea,'h',step%3-1)
      invoke(code+0xb35e);invoke(addr)
      frames.append((read(a4-0x6800,0x6800),read(a4-0x6bb8,12),read(sy['_motion_state'],32),read(sy['_phase_state'],78),read(sy['_time_scalar_state'],16),read(sy['_time_scalar_fields'],2)))
     outputs.append(frames)
    assert outputs[0]==outputs[1],(n,mouse,velocity,[(j,[(k,[(hex(i),a,b) for i,(a,b) in enumerate(zip(q,r)) if a!=b][:30]) for k,(q,r) in enumerate(zip(x,y)) if q!=r]) for j,(x,y) in enumerate(zip(*outputs)) if x!=y])
    cases+=1
 report=dict(passed=True,cases=cases,frames=cases*12,scope='Private assembled phase frame versus current phase frame: globals, trig, motion, phase and scalar state; intervals1..31, neutral and non-neutral steering, signed and zero velocity. Twelve consecutive frames with steering, throttle/brake, contact mask and pitch/roll rate changes. No terrain pass, no performance claim.')
 Path('tmp/c5-neutral-steering-check.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
finally:ok(u.uc_close(h))
