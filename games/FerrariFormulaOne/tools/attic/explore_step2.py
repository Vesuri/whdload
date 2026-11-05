#!/usr/bin/env python3
import os,sys,json,signal,shutil,struct
from pathlib import Path
sys.path.insert(0,os.path.expanduser('~/.local/share/amiga/pylib'))
from amigaxdev.gdbserve import Server
root=Path(__file__).resolve().parents[1];os.chdir(root)
name=sys.argv[1];out=root/'tmp/step2'/name;out.mkdir(parents=True,exist_ok=True)
os.environ.update(SLAVE=str(root/'tmp/build/release/FerrariFormulaOne.slave'),WARP='1',WINDOW='none',WHD_ARGS='CUSTOM1=0',DETERMINISTIC='1')
s=Server('ff1map',root=str(root),profile_window=False);log=[];overlays=[];events=[]
try:
 g=s.boot()
 def cmd(c):
  v=g.cmd(c,timeout=180);log.append(c+'\n'+v);return v
 def until(addr):
  cmd('delete');cmd(f'break *{addr:#x}');v=cmd('continue');assert 'Breakpoint' in v,v
 def val(e):return int(cmd('p/x '+e).split('=')[-1].strip(),16)
 def dump(label):cmd(f'dump binary memory tmp/step2/{name}/{label}.bin 0 0x80000')
 for n in range(30 if name == 'native-a' else 0):
  until(0x19a86);entry=val('$d0+*(unsigned int*)($a3+28)');a3=val('$a3');
  overlays.append({'event':n,'entry':entry,'a3':a3,'record':cmd('x/8wx $a3'),'d0_before':val('$d0'),'sr':val('$sr')})
  dump(f'overlay-{n}-before');until(0x19a8c);dump(f'overlay-{n}-after')
  print('overlay',n,hex(entry),flush=True)
  if entry==0x64a68:break
 for n in range(125):
  until(0x65606)
  if n in (0,1,10,50,100,124):dump(f'update-{n}')
  # one contiguous read keeps the observation inexpensive
  events.append({'update':n,'fields':val('*(unsigned short*)0x24ad2'),'countdown':val('*(unsigned short*)0x66f94'),'segment':val('*(unsigned short*)0x6a60a'),'speed':val('*(unsigned short*)0x2275a'),'draw_index':val('*(unsigned short*)0x66f88'),'sr':val('$sr')})
  if n%25==0:print(name,'update',n,events[-1],flush=True)
 cmd('delete');cmd(f'monitor profile 24 "" "{out}/display.bin"')
 dump('after-display')
 shutil.copy(root/'amiga/.run/launch.json',out/'launch.json')
 (out/'result.json').write_text(json.dumps({'overlays':overlays,'updates':events},indent=2)+'\n')
finally:
 (out/'capture.log').write_text('\n'.join(log))
 if s.g:
  s.g.p.kill()
  try:os.kill(int((root/'amiga/.run/fsuae.pid').read_text()),signal.SIGKILL)
  except ProcessLookupError:pass
