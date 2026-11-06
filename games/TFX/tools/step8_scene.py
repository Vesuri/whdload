#!/usr/bin/env python3
"""Controlled game-time visual test; not a performance measurement."""
import os,sys,json,re,struct
from pathlib import Path
from replay_flight import ROOT,run
from baseline_matrix import VARIANTS
from amigaxdev import barto
out=Path(sys.argv[1]).resolve();machine=sys.argv[2] if len(sys.argv)>2 else '040';os.chdir(ROOT)
v=dict(VARIANTS['newfpu'],extra_args='--uae_fpu_no_unimplemented=true'+(' --cpu=68040-NOMMU --uae_cpu_cycle_exact=true --uae_cpu_memory_cycle_exact=true' if os.environ.get('SCENE_NOMMU') else ''))
# Stop at the FIRST timestep computation, before the first simulation update.
v['swap']=0x1ac36
def observe(cmd,dump,bases,hs,out):
 base=bases[0];swaps=0;tape=json.loads((ROOT/'tools/flight.tape.json').read_text())
 original=hs[0]['bytes'][0x1ac36:0x1ac46]
 assert dump('timestep-original.bin',base+0x1ac36,16)==original
 # MOVEQ #5,D0; MOVE.W D0,-2980(A4); five NOPs. D1 is overwritten before use.
 replacement=bytes.fromhex('70053940f45c'+'4e71'*5)
 cmd(f'monitor tfxmem {base+0x1ac36:x} {replacement.hex()}')
 assert dump('timestep-fixture.bin',base+0x1ac36,16)==replacement
 joy=base+0x40f7e
 assert dump('joystick-original.bin',joy,6)==hs[0]['bytes'][0x40f7e:0x40f84]
 def joystick(value):
  payload=bytes.fromhex('323c00004e71')
  cmd(f'monitor tfxmem {joy:x} {payload.hex()}')
  # Deliver the resolved right-arrow latch synchronously, as ReadDJoy does.
  latch=dump('joystick-latch.bin',base+0x40f60,2)
  cmd(f'monitor tfxmem {base+0x40f60:x} {bytes(x&~8 for x in latch).hex()}')
  cmd(f'monitor tfxmem {base+0x40ce5:x} {"ff" if value else "00"}')
 joystick(0)
 cmd('delete breakpoints');cmd(f'break *{base+0x19fc:#x}');cmd(f'break *{base+0x4c474:#x}');publications=[]
 while True:
  reply=cmd('continue');cmd('maintenance flush register-cache')
  pc=int(re.search(r'= (0x[0-9a-f]+)',cmd('p/x $pc'))[1],16)
  if pc==base+0x19fc:
   swaps+=1
   for e in tape['flight_inputs']:
    if e['swap']==swaps:
     assert e['event']=='JOY2_RIGHT';joystick(e['value'])
   continue
  assert pc==base+0x4c474
  copper=int(re.search(r'= (0x[0-9a-f]+)',cmd('p/x $a0'))[1],16);publications.append(dict(swap=swaps,copper=copper))
  if swaps in [1,10,30,45,57]:
   def register(name):
    cmd('maintenance flush register-cache');return int(re.search(r'= (0x[0-9a-f]+)',cmd('p/x $'+name))[1],16)
   original_sr=register('sr');cmd(f'monitor tfxreg 16 {original_sr|0x700:x}')
   cmd('stepi');resume_pc=register('pc');assert resume_pc==base+0x4c47a
   resume_sr=(register('sr')&~0x700)|(original_sr&0x700)
   saved={n:register(n) for n in ['d'+str(i) for i in range(8)]+['a'+str(i) for i in range(7)]+['sp']}
   # Hold the CPU in the fixture's last NOP slot; DMA keeps displaying this frame.
   hold=base+0x1ac44;cmd(f'monitor tfxmem {hold:x} 60fe');cmd(f'monitor tfxreg 17 {hold:x}')
   p=out/f'swap-{swaps:03d}.trace';cmd(f'monitor profile 2 "" "{p}"');t=barto.load(p);f=t.fields[-1]
   assert register('pc')==hold and all(register(n)==value for n,value in saved.items())
   cmd(f'monitor tfxmem {hold:x} 4e71');cmd(f'monitor tfxreg 17 {resume_pc:x}');cmd(f'monitor tfxreg 16 {resume_sr:x}')
   # The last full field must fetch all eight planes selected by this publication.
   words=dict(struct.unpack_from('>HH',t.chip,o) for o in range(copper,copper+192,4))
   planes=[(words[0xe0+4*i]<<16)|words[0xe2+4*i] for i in range(8)]
   first={}
   for o in range(0,len(f.dma),f.dma_size):
    if struct.unpack_from('<h',f.dma,o+29)[0]==6:first.setdefault(struct.unpack_from('<H',f.dma,o)[0],struct.unpack_from('<I',f.dma,o+12)[0])
   assert [first[0x110+2*i] for i in range(8)]==planes
   (out/f'swap-{swaps:03d}.png').write_bytes(f.shot)
   print(out.name,'published scene',swaps,flush=True)
  if swaps==57:break
 assert [p['swap'] for p in publications]==list(range(1,58))
 (out/'publications.json').write_text(json.dumps(publications,indent=2))
 (out/'controlled-time.json').write_text(json.dumps(dict(fixture='fixed timestep clamp',offset=0x1ac36,original=original.hex(),replacement=replacement.hex(),delta=5,swaps=swaps,input_fixture='native resolved right-arrow latch; neutral hardware input',input_tape=tape['flight_inputs']),indent=2))

run(machine,out,Path(os.environ.get('TEST_SEED',str(out)+'-seed')),observe,v)
