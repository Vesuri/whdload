#!/usr/bin/env python3
"""Locate release-state divergence using matched native approach restarts.
Each restart is an offline independent experiment, not a runtime reset scheme.
Gravity/reset timestamps cover only the continuation, not history before seed.
"""
from pathlib import Path
from copy import deepcopy
import json,hashlib
from coupled_vehicle_core import seed,advance,summarize
from native_contact_response import UnsupportedContact
root=Path('tmp/prof');reports=[]
for phase in ('nominal','minus64','plus64'):
 cap=root/('natural-crest20'if phase=='nominal'else'phase-'+phase+'-native20');b,read,param=seed(cap);states={}
 ref={v['tick']:v for v in json.loads((cap/'bridge.json').read_text())['rows']};native_steps=0
 while b['contact']['entry'][0]<=232:
  tick=b['contact']['entry'][0];b,_=advance(b,20,read,param);v=summarize(b)
  assert v['position']+[v['pitch'],v['speed']]==[ref[tick][k]for k in ('x','y','z','pitch','speed')]
  native_steps+=1
  if tick>=180 and tick%2==0:states[tick]=deepcopy(b)
 target=states[232];te=target['contact']['entry'];rows=[]
 for start in range(180,232,2):
  b=deepcopy(states[start]);b['contact']['entry'][0]=start*5//2+1
  for o in (0xc6,0xcb):b['car'][o]=(5*b['car'][o]+1)//2
  reset=[None]*4;first_after_reset=[None]*4;trace=[];failure=None
  try:
   while b['contact']['entry'][0]<=580:
    tick=b['contact']['entry'][0];b,rec=advance(b,50,read,param);out=rec['contact']['output']
    for w,wheel in enumerate(out['wheels']):
     if wheel['branch']!='air':reset[w]=tick;first_after_reset[w]=None
     elif wheel['applied_gravity'] and first_after_reset[w]is None:first_after_reset[w]=tick
    if tick>=550:
     trace.append(dict(tick=tick,state=summarize(b),pre_clearances=[v['clearance']for v in rec['contact']['selected']],post_clearances=[v['suspension_clearance']for v in out['wheels']],planes=[v['plane']for v in rec['contact']['selected']],branches=[v['branch']for v in out['wheels']],velocities_fifths=[5*b['contact']['entry'][21+w]+b['contact']['entry'][25+w]for w in range(4)]))
  except UnsupportedContact as e:failure=dict(tick=tick,reason=str(e))
  row=dict(native_start_tick=start,start_time_tenths=start//2,trace=trace,unsupported=failure)
  if not failure:
   e=b['contact']['entry'];x,y=summarize(target),summarize(b)
   row.update(endpoint=y,error=dict(position=[v-u for u,v in zip(x['position'],y['position'])],**{k:y[k]-x[k]for k in ('pitch','speed','target')}),velocity_error_fifths=[5*(e[21+w]-te[21+w])+e[25+w]for w in range(4)],last_reset_ticks=reset,first_gravity_after_last_reset=first_after_reset)
  rows.append(row)
 reports.append(dict(phase=phase,native_steps_exact=native_steps,native_release_state=summarize(target),native_release_velocity=te[21:25],restarts=rows))
report=dict(scope=__doc__,cases=reports,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
(root/'coupled-approach-restart-family.json').write_text(json.dumps(report,indent=2)+'\n')
for phase in reports:
 print(phase['phase'],'unsupported',sum(bool(v['unsupported'])for v in phase['restarts']))
 for v in phase['restarts']:
  if v['native_start_tick']in (180,190,200,210,220,222,224,226,228,230):print(v['start_time_tenths'],v.get('error'),v.get('velocity_error_fifths'),v.get('first_gravity_after_last_reset'))
