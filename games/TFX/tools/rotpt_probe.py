#!/usr/bin/env python3
"""Plan step 8 measurement: delta repetition in DoRotPt0's two-component case.

  rotpt_probe.py OUT

Env: PROBE (first probed swap, default 30), PROBE_FRAMES (default 2), VIEW_TAPE=1,
SCENE_NOMMU=1. Same controlled-time scene as cockpit_probe.py. For PROBE_FRAMES frames
it breaks after the MOVEM.W of the handler at $59748 (D0/D1 = the delta) and at the
object entries that load the rotation matrix ($57ac8, $57b36), and logs D0/D1, the
matrix registers D4-D7/A5 and the point pointer A6.
"""
import os,sys,json,re
from pathlib import Path
from replay_flight import ROOT,run
from baseline_matrix import VARIANTS
out=Path(sys.argv[1]).resolve();os.chdir(ROOT)
v=dict(VARIANTS['newfpu'],extra_args='--uae_fpu_no_unimplemented=true'+(' --cpu=68040-NOMMU --uae_cpu_cycle_exact=true --uae_cpu_memory_cycle_exact=true' if os.environ.get('SCENE_NOMMU') else ''))
v['swap']=0x1ac36;v['custom4']=18;v['custom5']=0
PROBE=int(os.environ.get('PROBE','30'));FRAMES=int(os.environ.get('PROBE_FRAMES','2'))
GAME={0x5974c:'delta2',0x57ac8:'object',0x57b36:'object1'}
REGS=['d0','d1','d4','d5','d6','d7','a0','a5','a6']
def observe(cmd,dump,bases,hs,out):
 base=bases[0]
 original=hs[0]['bytes'][0x1ac36:0x1ac46];assert dump('timestep-original.bin',base+0x1ac36,16)==original
 cmd(f'monitor tfxmem {base+0x1ac36:x} 70053940f45c'+'4e71'*5)
 joy=base+0x40f7e;tape=json.loads((ROOT/'tools/flight.tape.json').read_text())
 def joystick(value):
  cmd(f'monitor tfxmem {joy:x} 323c00004e71')
  latch=dump('joystick-latch.bin',base+0x40f60,2)
  cmd(f'monitor tfxmem {base+0x40f60:x} {bytes(x&~8 for x in latch).hex()}')
  cmd(f'monitor tfxmem {base+0x40ce5:x} {"ff" if value else "00"}')
 joystick(0)
 names={base+o:n for o,n in GAME.items()}
 def regs():
  cmd('maintenance flush register-cache');r=cmd('info registers')
  return {n:int(m[1],16) for n in REGS+['pc'] for m in [re.search(r'^'+n+r'\s+(0x[0-9a-f]+)',r,re.M)] if m}
 cmd('delete breakpoints');cmd(f'break *{base+0x19fc:#x}');swaps=0;log=[];probing=False
 viewkeys={5:(0x51,1),9:(0x51,0),15:(0x52,1),19:(0x52,0),25:(0x54,1),29:(0x54,0),35:(0x55,1),39:(0x55,0),45:(0x50,1),49:(0x50,0)}
 while True:
  cmd('continue');r=regs();pc=r['pc']
  if pc==base+0x19fc:
   swaps+=1
   if os.environ.get('VIEW_TAPE') and swaps in viewkeys:
    key,value=viewkeys[swaps];cmd(f'monitor key {key:x} {value}')
   for e in tape['flight_inputs']:
    if e['swap']==swaps:joystick(e['value'])
   if swaps==PROBE:
    probing=True
    for a in names:cmd(f'break *{a:#x}')
   if swaps==PROBE+FRAMES:break
   log.append(dict(event='swap',swap=swaps))
   continue
  assert probing and pc in names,hex(pc)
  log.append(dict(event=names[pc],regs=r))
 (out/'probe.json').write_text(json.dumps(dict(probe=PROBE,base=base,events=log)))
 print('events',len(log),flush=True)
run('040',out,Path(str(out)+'-seed'),observe,v)
