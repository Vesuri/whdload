#!/usr/bin/env python3
"""Estimate crest crossing time from adjacent measured wheel positions."""
import json
from fractions import Fraction as F
from pathlib import Path
p=Path('tmp/prof');report={}
for hz in (20,50):
 d=json.loads((p/f'first-release{hz}'/'takeoff-plane.json').read_text());wheels=[]
 for w in range(4):
  rows=[r for r in d['rows'] if r['wheel']==w and r['event']=='SELECT'];i=next(i for i,r in enumerate(rows) if r['plane']==14);a,b=rows[i-1:i+1]
  assert a['plane']==12 and b['tick']==a['tick']+1
  ay=a['base_y']+a['node_y'];by=b['base_y']+b['node_y'];az=a['base_z']+a['node_z'];bz=b['base_z']+b['node_z']
  assert ay==by and a['normal_y']==b['normal_y'] and a['normal_z']==-b['normal_z'] and a['normal_x']==b['normal_x']==0
  # The two measured planes intersect at their common height and midpoint Z.
  crest=32*(az+bz);assert crest==655360 and a['world_z']<crest<b['world_z']
  fraction=F(crest-a['world_z'],b['world_z']-a['world_z']);t=(F(a['tick'])+fraction)/hz
  wheels.append(dict(wheel=w,estimated_crossing_seconds=float(t),exact_linear_estimate=str(t),sampled_release_seconds=b['tick']/hz,previous_sample_seconds=a['tick']/hz,crest_z=crest))
 report[str(hz)]=dict(wheels=wheels,estimated_front_rear_separation=wheels[2]['estimated_crossing_seconds']-wheels[0]['estimated_crossing_seconds'],sampled_front_rear_separation=wheels[2]['sampled_release_seconds']-wheels[0]['sampled_release_seconds'])
report['scope']='Read-only linear estimate between adjacent proposed wheel positions, using the analytically derived intersection of observed planes12/14. No render interpolation or guest state change. Substep trajectory curvature and collision solver scheduling are not measured by this estimate. It does not justify forcing50Hz events onto the20Hz clock.'
(p/'first-release-event-time.json').write_text(json.dumps(report,indent=2)+'\n')
for hz in ('20','50'):print(hz,report[hz])
