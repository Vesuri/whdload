"""Private full native-step frame check, including signed rollback and neutral."""
from pathlib import Path
import ctypes as C,json,os,random,re,struct
exec(Path('tools/check_p2_micro.py').read_text().split('for addr,name,path in ')[0])
ok(u.uc_mem_map(h,0,0x10000,7));ok(u.uc_mem_map(h,0x50000,0xfb0000,7))
root=Path('tmp/prof/c3-steering-phase-v2-a500');meta=json.loads((root/'metadata.json').read_text());lay=meta['layout'];a4=lay['a4'];code=lay['code_base'];stop=0x41000;sp=0x4f000
listing=Path('tmp/build/c3-steering-phase.lst').read_text(encoding='latin1');sy={n:int(v,16) for n,v in re.findall(r'^(_\w+)\s+00:([0-9A-F]+)',listing,re.M)};base=lay['published']-sy['_code_start'];sy={k:base+v for k,v in sy.items()}
images=[(addr,(root/f'timing-state-{name}.bin').read_bytes()) for name,addr in [('chip',0),('slow',0xc00000)]]
import sys
sys.path.insert(0,'tools')
from game_image import hunks
hs=hunks();native=bytearray(hs[0]['data']);bases=[r['base'] for r in lay['regions']]
for off,dest in hs[0]['relocs']:struct.pack_into('>I',native,off,struct.unpack_from('>I',native,off)[0]+bases[dest])
def invoke(addr):
 reg(8,sp);pack(sp,'I',stop);ok(u.uc_emu_start(h,addr,stop,1000000,100000));assert reg(18)==stop and reg(8)==sp+4
blob=Path("tmp/spin-recovery-candidate.bin").read_bytes()
rng=random.Random(101314);cases=0;negative=0
try:
 for velocity in [-2000,-500,-100,-2,-1,0,1,2,100,500,2000]:
  for mask in [0,3,15]:
   for gear in range(5):
    for automatic in [0,1]:
     # Native automatic gear handling assumes first gear or above.
     if automatic and gear==0:continue
     rpm=rng.randrange(6501);throttle=rng.randrange(101);request=0;outputs=[];angles=[rng.randrange(-720,721),rng.randrange(-180,181),rng.randrange(-180,181)];rates=[rng.choice([-3,0,3]) for _ in range(3)]
     for enabled in [False,True]:
      for addr,body in images:write(addr,body)
      if not enabled:write(code,bytes(native))
      else:
       write(0x80000,blob)
       write(0x81000,Path("tmp/steering-current-frame.bin").read_bytes())
       write(code+0xb38a,bytes.fromhex("4eb9")+struct.pack(">I",0x80000))
       write(code+0xb62a,bytes.fromhex("4eb9")+struct.pack(">I",0x80004))
      # Disable audio output only in this private process, preserving engine/pose arithmetic.
      write(a4-0x7fe0,bytes.fromhex('4e75'))
      ok(u.uc_ctl(h,0x4000000a))
      for k in range(1,17):reg(k,k*0x10101)
      reg(17,0x2000);reg(5,a4)
      for off,value in [(0x9606,0),(0x9605,0),(0x9910,mask),(0x993e,automatic),(0x991c,throttle),(0x9911,0),(0x991d,request),(0x95ff,0),(0xe94a,255),(0xaf31,0),(0xf790,0),(0xf791,255),(0xaddc,0)]:pack(a4+off-65536,'B',value)
      for off,value in [(0x9928,velocity),(0x992a,rpm),(0x9936,gear),(0x990e,0)]:pack(a4+off-65536,'h',value)
      import drivetrain_model as model
      pack(a4-0x66da,'h',model.engine_speed(rpm,gear));pack(a4-0x66c0,'I',a4-0x68c6+gear*8)
      pack(a4-0x6bb8,'4h',16384,0,0,16384)
      for off,value in zip([0x994a,0x9946,0x9948,0x9914,0x9916,0x991a],angles+rates):pack(a4+off-65536,'h',value)
      pack(a4-0x66d4,'h',model.convert(rpm,*model.TABLE[gear]))
      pack(a4-0x6a06,'h',rng.choice([0,200,320,400,639]) if not enabled else mouse)
      mouse=struct.unpack('>h',read(a4-0x6a06,2))[0]
      pack(sy['_dispatch_state']+28,'h',mouse)
      pack(sy['_time_scalar_fields'],'H',8);write(sy['_dispatch_state']+24,b'\x01')
      for symbol,size in [('_phase_state',78),('_phase_speed_cache',8),('_time_scalar_state',16),('_drivetrain_state',16),('_projection_state',36),('_motion_position_state',20),('_motion_state',32)]:write(sy[symbol],bytes(size))
      invoke(code+0xb35e)
      if enabled:
       invoke(0x81000);assert struct.unpack('>I',read(sy['_phase_state']+56,4))[0]==1
      else:invoke(code+0xb662);invoke(code+0xb500)
      outputs.append(read(a4-0x670a,0x5c))
     assert outputs[0]==outputs[1],(velocity,mask,gear,automatic,rpm,throttle,mouse,angles,rates,[(hex(0x98f6+i),a,b) for i,(a,b) in enumerate(zip(*outputs)) if a!=b])
     cases+=1;negative+=velocity<0
 report=dict(passed=True,cases=cases,negative_velocity_cases=negative,scope='Current phase frame versus pristine native engine and position, T=8 integer starts, signed velocity -2000..2000, automatic/manual gears, neutral and zero/partial/full wheel contact. Private audio output stub only. Varied yaw/pitch/roll and angular rates, native orientation plus car globals exact; runtime phase entry required.')
 Path('tmp/physics-skid-native-frame.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
finally:ok(u.uc_close(h))
