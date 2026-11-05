#!/usr/bin/env python3
"""Matched-state native20/50 details around the second shallow support transition."""
from pathlib import Path
from copy import deepcopy
import json
from coupled_vehicle_core import seed,advance,summarize
root=Path('tmp/prof');cases=[]
for phase in ('nominal','minus64','plus64'):
 cap=root/('natural-crest20'if phase=='nominal'else'phase-'+phase+'-native20');b,read,param=seed(cap)
 while b['contact']['entry'][0]<=280:b,_=advance(b,20,read,param)
 initial=deepcopy(b);paths={}
 for hz in (20,50):
  b=deepcopy(initial);b['contact']['entry'][0]=14*hz+1
  if hz==50:
   for o in (0xc6,0xcb):b['car'][o]=(5*b['car'][o]+1)//2
  rows=[]
  while b['contact']['entry'][0]<=hz*143//10:
   t=b['contact']['entry'][0];before=summarize(b);b,rec=advance(b,hz,read,param);c=rec['contact'];out=c['output']
   rows.append(dict(ms=t*1000//hz,before=before,after=summarize(b),entry=c['entry'],selected=c['selected'],output=out))
  paths[str(hz)]=rows
 cases.append(dict(phase=phase,initial=summarize(initial),paths=paths))
(root/'coupled-second-transition-probe.json').write_text(json.dumps(dict(scope=__doc__,cases=cases),indent=2)+'\n')
for c in cases:
 print(c['phase'],'initial',c['initial'])
 for hz,rows in c['paths'].items():
  for r in rows[:(2 if hz=='20'else 5)]:print(hz,r['ms'],'pitch',r['before']['pitch'],r['after']['pitch'],'planes',[v['plane']for v in r['selected']],'q',[v['clearance']for v in r['selected']],'branches',[v['branch']for v in r['output']['wheels']])
