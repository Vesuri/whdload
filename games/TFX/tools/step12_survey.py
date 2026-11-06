#!/usr/bin/env python3
"""Read-only palette/view survey, native input only; no guest patches."""
import os,sys,json,re,struct,hashlib
from pathlib import Path
import replay_flight as replay
from baseline_matrix import VARIANTS
from amigaxdev import barto
out=Path(sys.argv[1]).resolve();machine=sys.argv[2];os.chdir(replay.ROOT)
v=dict(VARIANTS['integer' if machine=='020' else 'newfpu'])
v['extra_args']='--uae_fpu_no_unimplemented=true'
# Reuse boot/location/tape with two observation-only menu captures.
source=Path(replay.__file__).read_text()
source=source.replace("cmd('monitor fields 1500');print", "cmd('monitor fields 1500'); menu_shot(cmd,out,'pilot-menu');print")
source=source.replace("for i,k in enumerate(tape['enrolment']):", "for i,k in enumerate(tape['enrolment']):")
source=source.replace("cmd(f'break *{anchor:#x}');cmd('monitor key 44 1')", "menu_shot(cmd,out,'pilot-ready');cmd(f'break *{anchor:#x}');cmd('monitor key 44 1')")
def shot(cmd,out,name):
 p=out/(name+'.trace');cmd(f'monitor profile 1 "" "{p}"');t=barto.load(p);(out/(name+'.png')).write_bytes(t.fields[-1].shot)
def observe(cmd,dump,bases,hs,out):
 cmd('delete breakpoints')
 palette_addr=int.from_bytes(dump('palette-pointer.bin',bases[0]+(0x4a882 if machine=='020' else 0x4c33a),4),'big')
 for name,key in [('cockpit',None),('left',0x51),('right',0x52),('rear',0x53),('track',0x54),('flyby',0x55),('track2',0x56),('centre',0x59),('cockpit-return',0x50)]:
  if key is not None:
   cmd(f'monitor key {key:x} 1');cmd('monitor fields 40');cmd(f'monitor key {key:x} 0')
  cmd('monitor fields 100');shot(cmd,out,name)
  dump(name+'-palette.bin',palette_addr,768)
  print(machine,name,flush=True)
 cmd('monitor key 0 1');cmd('monitor fields 8');cmd('monitor key 0 0');cmd('monitor fields 100');shot(cmd,out,'settings')
ns=dict(replay.__dict__);ns['__name__']='step12_survey_boot';ns['menu_shot']=shot
exec(compile(source,replay.__file__,'exec'),ns)
ns['run'](machine,out,Path(str(out)+'-seed'),observe,v)
