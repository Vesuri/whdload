#!/usr/bin/env python3
"""Matched-native-state50Hz local pose sensitivity at11.1s; diagnostic, not tolerance fitting.
Only current body Y/Z positions shift by at most one raw unit. Cached prior wheel
positions, timers, speed and every physics field are unchanged. The centre-lane
query domain is enforced by the existing model. No altered states enter runtime.
"""
from pathlib import Path
from copy import deepcopy
import json
from coupled_vehicle_core import seed,advance,summarize
root=Path('tmp/prof');cases=[]
for phase in ('nominal','minus64','plus64'):
 cap=root/('natural-crest20'if phase=='nominal'else'phase-'+phase+'-native20');b,read,param=seed(cap);reference={v['tick']:v for v in json.loads((cap/'bridge.json').read_text())['rows']}
 while b['contact']['entry'][0]<=222:
  t=b['contact']['entry'][0];b,_=advance(b,20,read,param);v=summarize(b);assert v['position']+[v['pitch'],v['speed']]==[reference[t][k]for k in ('x','y','z','pitch','speed')]
 initial=deepcopy(b);initial['contact']['entry'][0]=556
 for o in (0xc6,0xcb):initial['car'][o]=(5*initial['car'][o]+1)//2
 runs=[];control={}
 for dy in (0,-1,1):
  for dz in (0,-1,1):
   b=deepcopy(initial);b['contact']['position'][1]+=dy;b['contact']['position'][2]+=dz;rows=[];release=None
   while b['contact']['entry'][0]<=650:
    t=b['contact']['entry'][0];b,rec=advance(b,50,read,param);v=summarize(b)
    if dy==dz==0:control[t]=dict(x=v['position'][0],y=v['position'][1],z=v['position'][2],pitch=v['pitch'],speed=v['speed'])
    ref=control[t]
    if dy==dz==0:assert v['position']+[v['pitch'],v['speed']]==[ref[k]for k in ('x','y','z','pitch','speed')]
    rows.append(dict(tick=t,error=dict(y=v['position'][1]-ref['y'],z=v['position'][2]-ref['z'],pitch=v['pitch']-ref['pitch'],speed=v['speed']-ref['speed']),branches=[w['branch']for w in rec['contact']['output']['wheels']]))
    if t==580:release=dict(state=v,velocity=b['contact']['entry'][21:25],velocity_fifths=[5*b['contact']['entry'][21+w]+b['contact']['entry'][25+w]for w in range(4)])
   runs.append(dict(delta_y=dy,delta_z=dz,release=release,errors=rows,max_errors={k:max(abs(v['error'][k])for v in rows)for k in ('y','z','pitch','speed')}))
 control_run=next(v for v in runs if v['delta_y']==v['delta_z']==0)
 for test in runs:
  assert [v['branches']for v in test['errors']]==[v['branches']for v in control_run['errors']]
  assert test['release']['velocity_fifths']==control_run['release']['velocity_fifths']
 cases.append(dict(phase=phase,initial=summarize(initial),runs=runs));print(phase)
 for v in runs:print(v['delta_y'],v['delta_z'],v['max_errors'],'release velocities',v['release']['velocity'])
(root/'matched50-position-sensitivity.json').write_text(json.dumps(dict(scope=__doc__,cases=cases),indent=2)+'\n')
