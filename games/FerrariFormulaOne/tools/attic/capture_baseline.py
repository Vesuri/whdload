#!/usr/bin/env python3
"""Fresh boot, first race timing site and matched completed visits; no game writes."""
import os,sys,json,hashlib,shutil,time
from pathlib import Path
sys.path.insert(0,os.environ.get('AMIGA_PYLIB',os.path.expanduser('~/.local/share/amiga/pylib')))
from amigaxdev.gdbserve import Server
root=Path(__file__).resolve().parents[1]
os.chdir(root)
kind=sys.argv[1]; custom=int(sys.argv[2]); name=sys.argv[3] if len(sys.argv)>3 else f'{kind}-c{custom}'
slave=root/('tmp/game/FerrariFormulaOne_v1.01_0481/FerrariFormulaOne/FerrariFormulaOne.slave' if kind=='shipped' else 'tmp/build/release/FerrariFormulaOne.slave')
if os.environ.get('SLAVE_OVERRIDE'):slave=Path(os.environ['SLAVE_OVERRIDE']).resolve()
out=root/'tmp/baseline'/name; out.mkdir(parents=True,exist_ok=True)
os.environ.update(SLAVE=str(slave),WARP=os.environ.get('WARP','1'),WINDOW=os.environ.get('WINDOW','none'),WHD_ARGS=f'CUSTOM1={custom}',BOOT_BREAK='0x6a304',DETERMINISTIC='1')
s=Server('ff1baseline',root=str(root),profile_window=False)
try:
 g=s.boot();g.stop()
 log=[]
 def cmd(c):
  v=g.cmd(c,timeout=300);log.append(c+'\n'+v);return v
 cmd('delete')
 cmd('break *0x6a304')
 v=cmd('continue');assert 'Breakpoint' in v,v
 if os.environ.get('GREEN_ANCHOR'):
  cmd('condition $bpnum *(unsigned short*)0x66f94 == 0')
  v=cmd('continue');assert 'Breakpoint' in v,v
  cmd('condition $bpnum')
 for count in (0,1,10,100):
  if count:
   delta=count-last
   if delta>1:cmd(f'ignore $bpnum {delta-1}')
   v=cmd('continue');assert 'Breakpoint' in v,v
  last=count
  cmd(f'dump binary memory tmp/baseline/{name}/race-{count}.bin 0 0x80000')
  cmd(f'dump binary memory tmp/baseline/{name}/slow-{count}.bin 0xc00000 0xd80000')
  (out/f'registers-{count}.txt').write_text(cmd('info registers'))
  print(name,'race visit',count,flush=True)
 cmd('delete')
 s.handle(g,'shot '+str(out/'race.png'))
 shutil.copy(root/'amiga/.run/launch.json',out/'launch.json')
 (out/'capture.log').write_text('\n'.join(log))
 (out/'result.json').write_text(json.dumps({'name':name,'custom1':custom,'slave_sha256':hashlib.sha256(slave.read_bytes()).hexdigest(),'anchor': 'runtime 0x6a304, verified SPS race offset 0x589c','visits':[0,1,10,100],'warp':os.environ['WARP']=='1','scope':'read-only correctness capture; no timing claim','green_anchor':bool(os.environ.get('GREEN_ANCHOR'))},indent=2)+'\n')
finally:
 if s.g:
  s.g.p.kill()
 pid=root/'amiga/.run/fsuae.pid'
 if s.g and pid.exists():
  import signal
  try:os.kill(int(pid.read_text()),signal.SIGKILL)
  except ProcessLookupError:pass
