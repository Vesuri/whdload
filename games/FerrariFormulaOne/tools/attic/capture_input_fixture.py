#!/usr/bin/env python3
import os,sys,json,signal,struct,time,re,shutil
from pathlib import Path
sys.path.insert(0,os.environ.get('AMIGA_PYLIB',os.path.expanduser('~/.local/share/amiga/pylib')))
from amigaxdev.gdbserve import Server
root=Path(__file__).resolve().parents[1];os.chdir(root)
kind=sys.argv[1];custom=int(sys.argv[2]);name=f'{kind}-c{custom}-accepted-pit'
slave=root/f'tmp/build/input-fixture/{kind}.slave'
original=root/('tmp/game/FerrariFormulaOne_v1.01_0481/FerrariFormulaOne/FerrariFormulaOne.slave' if kind=='shipped' else 'tmp/build/release/FerrariFormulaOne.slave')
normal=original.read_bytes()[32:-4];patch=normal.index(bytes.fromhex('e580e580204048c1'));keyboard=normal.index(bytes.fromhex('78004600e218'))
out=root/'tmp/baseline'/name;out.mkdir(parents=True,exist_ok=True)
os.environ.update(SLAVE=str(slave),WARP='1',WINDOW='none',WHD_ARGS=f'CUSTOM1={custom}',DETERMINISTIC='1')
s=Server('ff1input',root=str(root),profile_window=False);log=[];events=[]
try:
 g=s.boot()
 def cmd(c):
  v=g.cmd(c,timeout=120);log.append(c+'\n'+v);return v
 def until(addr,condition=None):
  cmd('delete');cmd(f'break *{addr:#x}')
  if condition:cmd('condition $bpnum '+condition)
  v=cmd('continue');assert 'Breakpoint' in v,v
 def value(expr):return int(cmd('p/x '+expr).split('=')[-1].strip(),16)
 def shot(label):
  cmd('delete');s.handle(g,'shot '+str(out/(label+'.png')))
  cmd(f'dump binary memory tmp/baseline/{name}/{label}.bin 0 0x80000')
  events.append({'name':label,'fields':value(f'*(unsigned int*){fieldaddr:#x}')})
  print(name,label,events[-1]['fields'],flush=True)
 until(0x1a5d2)
 cmd('delete');s.handle(g,'shot '+str(out/'title-menu.png'))
 until(0x6a304)
 base=value('*(unsigned int*)0x6551a')-patch
 listing=(root/f'tmp/build/input-fixture/{kind}.list').read_text()
 fieldoffset=int(re.search(r'^fields\s+00:([0-9A-F]+)',listing,re.M).group(1),16)
 fieldaddr=base+len(normal)+fieldoffset
 shot('race-entry')
 until(0x23708);assert value('$d0')==0x40
 until(0x6a304);shot('takeover')
 until(0x23708);assert value('$d0')==0x45
 until(0x23708);assert value('$d0')==0x45
 shot('paused-before-resume')
 until(0x6a304);shot('resumed')
 until(0x2482a,f'*(unsigned int*){fieldaddr:#x} >= 620');until(0x6a304);shot('steered')
 until(0x23708);assert value('$d0')==0x27
 until(0x2482a,f'*(unsigned int*){fieldaddr:#x} >= 2690');shot('accept-target')
 until(0x2482a,f'*(unsigned int*){fieldaddr:#x} >= 3500');shot('tow-pits')
 until(base+keyboard);assert value('$d0')==0x4d
 events.append({'name':'F10-native-decode','encoded_key':0x4d,'pc':base+keyboard})
 cmd('delete');g.cont();time.sleep(1);g.stop();shot('quit-shell')
 shutil.copy(root/'amiga/.run/launch.json',out/'launch.json')
 (out/'result.json').write_text(json.dumps({'kind':kind,'custom1':custom,'events':events,'scope':'game input-consumer fixture and native F10 decode/abort; not physical device delivery'},indent=2)+'\n')
finally:
 (out/'capture.log').write_text('\n'.join(log))
 if s.g:
  s.g.p.kill()
  try:os.kill(int((root/'amiga/.run/fsuae.pid').read_text()),signal.SIGKILL)
  except ProcessLookupError:pass
