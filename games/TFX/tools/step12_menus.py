#!/usr/bin/env python3
"""Observe native non-action menus and fades; no game patches."""
import sys,os,shutil
from pathlib import Path
import replay_flight as replay
from baseline_matrix import VARIANTS
from amigaxdev import barto
out=Path(sys.argv[1]).resolve();machine=sys.argv[2];os.chdir(replay.ROOT)
v=dict(VARIANTS['integer' if machine=='020' else 'newfpu'],custom4=2,extra_args='--uae_fpu_no_unimplemented=true')
if machine=='040' and not os.environ.get('TRACE_MMU'):v['extra_args']+=' --cpu=68040-NOMMU --uae_cpu_cycle_exact=true --uae_cpu_memory_cycle_exact=true'
def shot(cmd,out,name):
 p=out/(name+'.trace');cmd(f'monitor profile 1 "" "{p}"');t=barto.load(p);(out/(name+'.png')).write_bytes(t.fields[-1].shot)
def observe(cmd,dump,bases,hs,out):
 shutil.copy(__file__,out/'step12_menus.py')
 for n in range(8):
  cmd('monitor key 44 1');cmd('monitor fields 8');cmd('monitor key 44 0')
  for fields in [1,8,32,120]:
   cmd(f'monitor fields {fields}');shot(cmd,out,f'menu-{n}-{fields}')
  print(machine,'menu',n,flush=True)
 for n,(dx,dy,click) in enumerate([(127,0,False),(33,77,False),(0,0,True),(0,10,True),(0,20,True)]+[(0,0,True)]*8+[(40,83,True)]+[(0,0,True)]*3):
  cmd(f'monitor mouse {dx} {dy}');cmd('monitor fields 40')
  if click:
   cmd('monitor input JOY1_FIRE_BUTTON 1');cmd('monitor fields 40');cmd('monitor input JOY1_FIRE_BUTTON 0')
  cmd('monitor fields 120');shot(cmd,out,f'route-{n}');print(machine,'route',n,flush=True)
source=Path(replay.__file__).read_text().replace("cmd('monitor fields 1500');print", "cmd('monitor fields 1500'); menu_shot(cmd,out,'pilot-menu');print")
source=source.replace("cmd(f'break *{anchor:#x}');cmd('monitor key 44 1')", "observer(cmd,dump,bases,hs,out);return {}")
ns=dict(replay.__dict__);ns.update(__name__='step12_menus_boot',menu_shot=shot)
exec(compile(source,replay.__file__,'exec'),ns)
ns['run'](machine,out,Path(str(out)+'-seed'),observe,v)
