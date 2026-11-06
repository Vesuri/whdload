#!/usr/bin/env python3
"""Follow-camera Gouraud run probe (controlled game-time scene, not timing).

  gouraud_probe.py OUT

Env: DELTA_LISTING (slave listing), PROFILE_SLAVE, PROBE (first probed swap, default 60),
PROBE_FRAMES (default 10). F5 is pressed at swap 25 (4-swap hold) as in follow.tape.json.
At every gouraud_fill_new entry (tfx.020 $4f840) it logs y (A5) and dumps the inline scan table at SP+4 (16-byte records lx, rx, lc,
rc in 16.16 until rx < lx).
"""
import os,sys,json,re,struct
from pathlib import Path
from replay_flight import ROOT,run
from baseline_matrix import VARIANTS
out=Path(sys.argv[1]).resolve();os.chdir(ROOT)
v=dict(VARIANTS['newfpu'],extra_args='--uae_fpu_no_unimplemented=true')
v['swap']=0x1ac36;v['custom4']=18;v['custom5']=0
PROBE=int(os.environ.get('PROBE','60'));FRAMES=int(os.environ.get('PROBE_FRAMES','10'))
def observe(cmd,dump,bases,hs,out):
 base=bases[0]
 listing=Path(os.environ['DELTA_LISTING']).read_text(encoding='latin1')
 def offset(n):return int(re.search(r'^'+re.escape(n)+r'\s+00:([0-9A-Fa-f]+)',listing,re.M)[1],16)
 sb=int.from_bytes(dump('swap-target.bin',base+0x19fe,4),'big')-offset('do_swap_screen')
 original=hs[0]['bytes'][0x1ac36:0x1ac46];assert dump('timestep-original.bin',base+0x1ac36,16)==original
 cmd(f'monitor tfxmem {base+0x1ac36:x} 70053940f45c'+'4e71'*5)
 joy=base+0x40f7e;tape=json.loads((ROOT/'tools/flight.tape.json').read_text())
 def joystick(value):
  cmd(f'monitor tfxmem {joy:x} 323c00004e71')
  latch=dump('joystick-latch.bin',base+0x40f60,2)
  cmd(f'monitor tfxmem {base+0x40f60:x} {bytes(x&~8 for x in latch).hex()}')
  cmd(f'monitor tfxmem {base+0x40ce5:x} {"ff" if value else "00"}')
 joystick(0)
 fill=sb+offset('gouraud_fill_new')
 assert dump('entry-code.bin',fill,4).hex()=='48e7fffe',dump('entry-code.bin',fill,4).hex()  # MOVEM.L D0-D7/A0-A6,-(SP)
 cmd('delete breakpoints');cmd(f'break *{base+0x19fc:#x}');swaps=0;calls=[]
 while True:
  cmd('continue');cmd('maintenance flush register-cache')
  pc=int(re.search(r'= (0x[0-9a-f]+)',cmd('p/x $pc'))[1],16)
  if pc==base+0x19fc:
   swaps+=1
   if swaps==25:cmd('monitor key 54 1')
   if swaps==29:cmd('monitor key 54 0')
   for e in tape['flight_inputs']:
    if e['swap']==swaps:joystick(e['value'])
   if swaps==PROBE:cmd(f'break *{fill:#x}')
   if swaps==PROBE+FRAMES:break
   continue
  assert pc==fill,hex(pc)
  sp=int(re.search(r'= (0x[0-9a-f]+)',cmd('p/x $sp'))[1],16)
  y=int(re.search(r'= (0x[0-9a-f]+)',cmd('p/x $a5'))[1],16);table=sp+4
  if not calls:print('first call sp',hex(sp),'table',hex(table),flush=True)
  rows=[];a=table
  while True:
   cmd(f'monitor tfxsync {a:x} 256');blob=dump('table.bin',a,256);done=False
   for o in range(0,256,16):
    lx,rx,lc,rc=struct.unpack_from('>4I',blob,o)
    if (rx>>16)-(lx>>16)<0 or (rx>>16)-(lx>>16)>=0x8000:done=True;break
    rows.append([lx,rx,lc,rc])
   if done:break
   a+=256
  calls.append(dict(frame=swaps-PROBE+1,y=y&0xffff,rows=rows))
 (out/'gouraud.json').write_text(json.dumps(dict(probe=PROBE,calls=calls)))
 print('calls',len(calls),'rows',sum(len(c['rows']) for c in calls),flush=True)
run('040',out,Path(str(out)+'-seed'),observe,v)
