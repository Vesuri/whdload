#!/usr/bin/env python3
"""Matched9.5s native approach: explicit ordering diagnostic versus baseline."""
from pathlib import Path
from copy import deepcopy
import json
from coupled_vehicle_core import seed,advance,summarize
from explicit_order_contact_model import solve
r=Path('tmp/prof');cases=[]
for phase in ('nominal','minus64','plus64'):
 cap=r/('natural-crest20'if phase=='nominal'else'phase-'+phase+'-native20');b,read,param=seed(cap);ref={v['tick']:v for v in json.loads((cap/'bridge.json').read_text())['rows']}
 while b['contact']['entry'][0]<=190:b,_=advance(b,20,read,param)
 initial=deepcopy(b);variants={}
 for name,hz,solver in [('native20',20,None),('baseline50',50,None),('explicit50',50,solve)]:
  b=deepcopy(initial);b['contact']['entry'][0]=19*hz//2+1
  if hz==50:
   for o in (0xc6,0xcb):b['car'][o]=(5*b['car'][o]+1)//2
  rows=[]
  while b['contact']['entry'][0]<=13*hz:
   t=b['contact']['entry'][0];b,rec=advance(b,hz,read,param,solver=solver);s=summarize(b)
   if hz==20:assert s['position']+[s['pitch'],s['speed']]==[ref[t][k]for k in ('x','y','z','pitch','speed')]
   ms=t*1000//hz
   if ms in (9600,9700,10000,11000,11600,13000):rows.append(dict(time_ms=ms,state=s,velocity_fifths=[5*b['contact']['entry'][21+w]+b['contact']['entry'][25+w]for w in range(4)]))
  variants[name]=rows
 errors={}
 for name in ('baseline50','explicit50'):
  errors[name]=[]
  for a,b in zip(variants['native20'],variants[name]):
   assert a['time_ms']==b['time_ms'];x,y=a['state'],b['state'];errors[name].append(dict(time_ms=a['time_ms'],y=y['position'][1]-x['position'][1],z=y['position'][2]-x['position'][2],pitch=y['pitch']-x['pitch'],speed=y['speed']-x['speed']))
 cases.append(dict(phase=phase,variants=variants,errors=errors))
(r/'explicit-order-matched-approach.json').write_text(json.dumps(dict(scope=__doc__,cases=cases),indent=2)+'\n')
for c in cases:print(c['phase'],c['errors'])
