#!/usr/bin/env python3
"""Plan step 3a: cockpit overdraw probe in a controlled game-time scene (not timing).

  cockpit_probe.py OUT

Env: DELTA_LISTING (slave listing), PROBE (first probed swap, default 30),
PROBE_FRAMES (default 3), NOFILL=1 (no background fills; buffers at panel and frame end),
VIEW_TAPE=1 (external-view key sequence of opt20_scene.py), SCENE_NOMMU=1.

For three frames after swap PROBE it logs every draw-routine entry in call order
(ScanFillDown with its trapezoid registers; sprite/image/line/fill entries with
registers and the top of the stack) and dumps the fast render buffer before and
after the cockpit panel image call (game:$3816). Before that call, frame 1 fills
the buffer with $00 and frame 2 with $ff: bits equal after the call in both
frames are written by the panel image regardless of the background (opaque).
Frame 3 is left untouched as the natural reference.
"""
import os,sys,json,re
from pathlib import Path
from replay_flight import ROOT,run
from baseline_matrix import VARIANTS
out=Path(sys.argv[1]).resolve();os.chdir(ROOT)
v=dict(VARIANTS['newfpu'],extra_args='--uae_fpu_no_unimplemented=true'+(' --cpu=68040-NOMMU --uae_cpu_cycle_exact=true --uae_cpu_memory_cycle_exact=true' if os.environ.get('SCENE_NOMMU') else ''))
v['swap']=0x1ac36;v['custom4']=18;v['custom5']=0
PROBE=int(os.environ.get('PROBE','30'))
FRAMES=int(os.environ.get('PROBE_FRAMES','3'));NOFILL=bool(os.environ.get('NOFILL'))
GAME={0x6c4f2:'ScanFillDown',0x3816:'panel_call',0x3818:'panel_done',0x4e23c:'_MaskSprite',0x4e6b4:'_DrawMonoImage',
      0x4f54e:'_DrawSpriteImage',0x50260:'_HoriMono',0x6280a:'_MonoHorizonProj',0x565c2:'Render',0x60bfc:'Polygon',
      0x3722:'panel_fn',0x4ddb4:'_DrawLineBox',0x5efba:'_DrawObjects',0x3875c:'@DrawLevel'}
SLAVE=['box_new','draw_line_normal_new','draw_line_strip_new','gouraud_fill_new','texture_fill']
# PROBE_SIZES=1 (step 3d): also the _MaskSprite blit entry, and each image call's 2-byte size header.
# The debugger stub takes about 20 software breakpoints: drop the 3D-only entries.
if os.environ.get('PROBE_SIZES'):
 SLAVE.append('mask_sprite8_040')
 for o in (0x6c4f2,0x565c2,0x60bfc,0x5efba,0x3875c):GAME.pop(o)
REGS=['d0','d1','d2','d3','d4','d5','d6','d7','a0','a1','a2','a3','a4','a5','a6','sp']
def observe(cmd,dump,bases,hs,out):
 base=bases[0]
 listing=Path(os.environ['DELTA_LISTING']).read_text(encoding='latin1')
 def offset(n):return int(re.search(r'^'+re.escape(n)+r'\s+00:([0-9A-Fa-f]+)',listing,re.M)[1],16)
 sb=int.from_bytes(dump('swap-target.bin',base+0x19fe,4),'big')-offset('do_swap_screen')
 def scalar(name):
  cmd(f'monitor tfxsync {sb+offset(name):x} 4')
  return int.from_bytes(dump(name+'.bin',sb+offset(name),4),'big')
 fast=scalar('fast_buf')
 # Same controlled-time and input fixtures as opt20_scene.py.
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
 names.update({sb+offset(n):n for n in SLAVE})
 def regs():
  cmd('maintenance flush register-cache');r=cmd('info registers')
  return {n:int(m[1],16) for n in REGS for m in [re.search(r'^'+n+r'\s+(0x[0-9a-f]+)',r,re.M)] if m}
 def buffer(name):
  cmd(f'monitor tfxsync {fast:x} 64000');return dump(name,fast,64000)
 cmd('delete breakpoints');cmd(f'break *{base+0x19fc:#x}');swaps=0;log=[];probing=False
 viewkeys={5:(0x51,1),9:(0x51,0),15:(0x52,1),19:(0x52,0),25:(0x54,1),29:(0x54,0),35:(0x55,1),39:(0x55,0),45:(0x50,1),49:(0x50,0)}
 while True:
  cmd('continue');r=regs();pc=int(re.search(r'= (0x[0-9a-f]+)',cmd('p/x $pc'))[1],16)
  if pc==base+0x19fc:
   swaps+=1
   if os.environ.get('VIEW_TAPE') and swaps in viewkeys:
    key,value=viewkeys[swaps];cmd(f'monitor key {key:x} {value}')
   for e in tape['flight_inputs']:
    if e['swap']==swaps:joystick(e['value'])
   if swaps==PROBE:
    probing=True
    for a in names:cmd(f'break *{a:#x}')
   if probing and swaps>PROBE:(out/f'frame{swaps-PROBE}-end.bin').write_bytes(buffer('end.bin'))
   if swaps==PROBE:(out/'frame0-end.bin').write_bytes(buffer('end.bin'))
   if swaps==PROBE+FRAMES:break
   log.append(dict(frame=swaps-PROBE+1 if probing else 0,event='swap',swap=swaps))
   continue
  assert probing and pc in names,hex(pc)
  frame=swaps-PROBE+1;name=names[pc];e=dict(frame=frame,event=name,regs=r)
  if name!='ScanFillDown':e['stack']=dump('stack.bin',r['sp'],32).hex()
  if os.environ.get('PROBE_SIZES') and name in ('_DrawMonoImage','_DrawSpriteImage'):
   ptr=int(e['stack'][32:40] if name=='_DrawMonoImage' else e['stack'][24:32],16);e['image']=ptr;e['size']=dump('size.bin',ptr,2).hex()
  if name=='panel_call':
   (out/f'frame{frame}-pre.bin').write_bytes(buffer('pre.bin'))
   if frame<3 and not NOFILL:
    # gdb rejects long monitor commands: 64-byte writes, each acknowledged.
    fill=('00' if frame==1 else 'ff')*64
    for o in range(0,64000,64):
     reply=cmd(f'monitor tfxmem {fast+o:x} {fill}');assert 'too long' not in reply and 'E01' not in reply,reply[-200:]
    assert set(buffer('filled.bin'))=={0 if frame==1 else 255}
  if name=='panel_done':(out/f'frame{frame}-post.bin').write_bytes(buffer('post.bin'))
  log.append(e)
 (out/'probe.json').write_text(json.dumps(dict(probe=PROBE,fast=fast,base=base,slave=sb,events=log)))
 print('events',len(log),flush=True)
run('040',out,Path(str(out)+'-seed'),observe,v)
