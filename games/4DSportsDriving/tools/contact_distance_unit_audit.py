#!/usr/bin/env python3
"""Audit distance/velocity units in the exact scoped 50Hz contact recurrence."""
import json,hashlib
from pathlib import Path
from unittest.mock import patch
import contact_body_predictor as model
from coupled_vehicle_core import seed,advance,summarize
from collections import Counter
root=Path('tmp/prof');cases=[];native_resolve=model.resolve
for phase in ('nominal','minus64','plus64'):
 cap=root/('crest-d9e7903'if phase=='nominal'else'phase-'+phase+'-d9')
 bundle,read,param=seed(cap);baseline=json.loads((root/('coupled-course-baseline'+(''if phase=='nominal'else'-'+phase)+'.json')).read_text())['rows'];events=[];tick=[0]
 def resolve(old,new,geo,forward,down,velocity,flags):
  out=native_resolve(old,new,geo,forward,down,velocity,flags)
  events.append(dict(tick=tick[0],branch=out['branch'],forward_raw_per_step=forward,down_raw_per_step=down,velocity_raw_per_native_step=velocity,total=out.get('total'),rest=out.get('rest'),projected=out.get('projected_distance')))
  if out['branch']=='crossing':assert out['total']==((forward+down+32768)%65536)-32768
  return out
 with patch.object(model,'resolve',resolve):
  for expected in baseline:
   tick[0]=bundle['contact']['entry'][0];bundle,rec=advance(bundle,50,read,param);s=summarize(bundle)
   assert s['position']+[s['pitch'],s['speed']]==[expected[k]for k in ('x','y','z','pitch','speed')]
   for selected,w in zip(rec['contact']['selected'],rec['contact']['output']['wheels']):
    if w['applied_gravity']:
     a=21 if selected['wheel']<2 else 15
     assert w['down']==(10*selected['velocity']+2*selected['velocity_fraction']+7*a+selected['position_fraction'])//25
 cases.append(dict(phase=phase,exact_trajectory_steps=len(baseline),branches=dict(Counter(e['branch']for e in events)),takeoff_events=[e for e in events if 550<=e['tick']<=565],crossing_events=[e for e in events if e['branch']=='crossing']))
report=dict(scope=__doc__,cases=cases,interpretation='Forward distance and downward displacement use the same20ms span; impact velocity retains native20 reference units for native thresholds. Crossing ratio is the only consumer of the summed distances in this scoped resolver. No candidate or runtime mutation.',source_sha256=hashlib.sha256(Path('../../4/4DSportsDriving/usr/source/simulation_a4000.s').read_bytes()).hexdigest())
(root/'contact-distance-unit-audit.json').write_text(json.dumps(report,indent=2)+'\n')
for c in cases:print(c['phase'],c['exact_trajectory_steps'],c['branches'],'takeoff',Counter(e['branch']for e in c['takeoff_events']),'crossings',len(c['crossing_events']))
