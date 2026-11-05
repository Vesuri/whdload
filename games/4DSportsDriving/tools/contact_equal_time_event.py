#!/usr/bin/env python3
"""Resolve the supported-ramp differential without inventing a correction."""
import json
from fractions import Fraction
from pathlib import Path
from copy import deepcopy
from contact_step import step
root=Path('tmp/prof');r=json.loads((root/'native20-contact-model/prediction.json').read_text())['records']
entry=next(e for e in r['ENTRY'] if e[0]==222)
previous=next(v for v in json.loads((root/'natural-crest20/bridge.json').read_text())['rows'] if v['tick']==221)
final={(v[0],v[1]):v[2:5] for v in r['FINAL']};cached=[[v>>6 for v in final[221,w]] for w in range(4)]
seed=dict(entry=entry,position=[previous[k] for k in ('x','y','z')],cached=cached)
state=deepcopy(seed);rem=0;events=[]
for i in range(5):
 d,rem=divmod(2*2289+rem,5);state,record=step(state,50,d)
 for w,(row,end) in enumerate(zip(record['selected'],record['output']['wheels'])):
  if end['branch']!='full_tangent':continue
  raw={}
  for key,prefix in (('old','old_world'),('new','world')):
   v=[row[prefix+'_'+a] for a in 'xyz'];o=[row['origin_'+a] for a in 'xyz'];n=[row['normal_'+a] for a in 'xyz']
   raw[key]=sum((Fraction(x,64)-y)*z for x,y,z in zip(v,o,n))/8192
  events.append(dict(step=i+1,wheel=w,plane=row['plane'],clearance=row['clearance'],raw_clearances={k:str(v) for k,v in raw.items()},
   before=[row['world_'+a] for a in 'xyz'],after=end['position'],response_delta=[end['position'][j]-row['world_'+a] for j,a in enumerate('xyz')],
   body_pitch=record['output']['pitch'],body_pitch_carry=record['output']['pitch_carry']))
report=dict(seed_tick=222,total_ms=100,distance_per_native20=2289,events=events,
 scope='Exact same-state model attribution for a planar-ramp contact event. Raw clearance is analytic unrounded geometry, not substituted into the runtime query. No correction or claimed full-course cause.')
(root/'contact-equal-time-event.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
