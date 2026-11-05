#!/usr/bin/env python3
"""Attribute first-jump pitch to the measured front/rear release ages."""
import json,math
from fractions import Fraction as F
from pathlib import Path
p=Path('tmp/prof');release=json.loads((p/'first-release-model.json').read_text());r={}
for hz in (20,50):
 w=release[str(hz)]['wheels'];at=lambda i:next(x for x in w[i]['rows'] if x['tick']==round(11.4*hz))
 front=F(at(0)['velocity']);rear=F(at(2)['velocity']);r[str(hz)]=dict(front_velocity=str(front),rear_velocity=str(rear),differential=str(front-rear))
 # With no reset after release, observed velocity is exactly acceleration * age.
 for i,acc in ((0,21),(2,15)):
  row=at(i);age=F(row['tick']-w[i]['first_gravity_tick']+1,hz)
  assert F(row['velocity'])==20*acc*age
velocity_gap=F(r['20']['differential'])-F(r['50']['differential']);assert velocity_gap==F(36,5)
# Restrict geometry comparison to common window with fully extended wheels.
lo,hi=F(116,10),F(12);geometric={}
for hz in (20,50):
 d=json.loads((p/f'first-air-pitch{hz}'/'tilt-baseline-model.json').read_text())['rows'];raw=json.loads((p/f'first-air-pitch{hz}'/'tilt-baseline.json').read_text())['records'];built={b[0]:b for b in raw['BUILT']}
 subset=[m for m in d if lo<F(m['tick'],hz)<=hi]
 assert all(built[m['tick']][5:9]==[384]*4 for m in subset)
 geometric[str(hz)]=sum(m['pitch_change'] for m in subset)
def axis(v):return [-(v[8]+v[11]-v[2]-v[5]),v[7]+v[10]-v[1]-v[4]]
def angle(v):return math.atan2(v[0],v[1])*512/math.pi-256
raw=json.loads((p/'first-air-pitch50/tilt-baseline.json').read_text())['records'];corrections=[]
axis_change=2*F(2,5)*velocity_gap
for row in raw['PITCH']:
 if not lo<F(row[0],50)<=hi:continue
 a=axis(row[10:22]);corrections.append(dict(tick=row[0],local_angle_change=angle([a[0],a[1]+float(axis_change)])-angle(a)))
actual_gap=geometric['50']-geometric['20'];local=sum(x['local_angle_change'] for x in corrections)
result=dict(equal_time_velocity=r,front_minus_rear_gap=str(velocity_gap),window_seconds=[float(lo),float(hi)],geometry=geometric,geometric_gap=actual_gap,local_corrected_axis_change=str(axis_change),local_angle_sum=local,residual_after_local_correction=actual_gap+local,rows=corrections,scope='No runtime correction. For recorded fully extended poses, adding the measured differential velocity gap to wheel displacements accounts for most geometry disagreement. Altered poses would feed back into later geometry, so this is an attribution, not a validated closed-loop prediction. A fixed7.2 velocity or pitch bias must not be installed; derive contact-event timing instead.')
(p/'first-release-pitch-attribution.json').write_text(json.dumps(result,indent=2)+'\n');print({k:v for k,v in result.items() if k not in ('rows','scope')})
