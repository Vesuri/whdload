#!/usr/bin/env python3
"""Independent matched native landing restarts; diagnostic, not runtime resets.
Scoped straight stock-car model; native reconstruction checked against captures.
"""
from pathlib import Path
from copy import deepcopy
import json,hashlib
from coupled_vehicle_core import seed,advance,summarize
from native_contact_response import UnsupportedContact
root=Path('tmp/prof');reports=[]
for phase in ('nominal','minus64','plus64'):
 cap=root/('natural-crest20' if phase=='nominal' else 'phase-'+phase+'-native20');b,read,param=seed(cap);states={};refs={v['tick']:v for v in json.loads((cap/'bridge.json').read_text())['rows']};native_steps=0
 while b['contact']['entry'][0]<=318:
  t=b['contact']['entry'][0];b,_=advance(b,20,read,param);v=summarize(b)
  assert v['position']+[v['pitch'],v['speed']]==[refs[t][k]for k in ('x','y','z','pitch','speed')]
  native_steps+=1
  if t>=250 and t%2==0:states[t]=deepcopy(b)
 rows=[]
 for start in range(250,312,2):
  b=deepcopy(states[start]);b['contact']['entry'][0]=start*5//2+1
  for o in (0xc6,0xcb):b['car'][o]=(5*b['car'][o]+1)//2
  common=[];contacts=[];failure=None;previous=None
  try:
   while b['contact']['entry'][0]<=795:
    t=b['contact']['entry'][0];b,rec=advance(b,50,read,param);out=rec['contact']['output'];branches=[w['branch']for w in out['wheels']]
    if branches!=previous:
     contacts.append(dict(tick=t,branches=branches,state=summarize(b),clearances=[w['suspension_clearance']for w in out['wheels']],extension=b['contact']['entry'][13:17],velocity=b['contact']['entry'][21:25]));previous=branches
    if t%5==0:
     x,y=summarize(states[t*2//5]),summarize(b)
     common.append(dict(tick=t,position=[v-u for u,v in zip(x['position'],y['position'])],pitch=y['pitch']-x['pitch'],speed=y['speed']-x['speed']))
  except UnsupportedContact as e:failure=dict(tick=t,reason=str(e))
  rows.append(dict(start_tenths=start//2,unsupported=failure,errors=common,transitions=contacts,max_y=max(abs(v['position'][1])for v in common),max_pitch=max(abs(v['pitch'])for v in common)))
 reports.append(dict(phase=phase,native_steps_exact=native_steps,restarts=rows))
report=dict(scope=__doc__,cases=reports,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest());(root/'coupled-landing-restart-family.json').write_text(json.dumps(report,indent=2)+'\n')
for r in reports:
 print(r['phase'],'unsupported',sum(bool(v['unsupported'])for v in r['restarts']))
 for v in r['restarts']:
  if v['start_tenths']%5==0:print(v['start_tenths'],v['max_y'],v['max_pitch'],v['errors'][-1])
