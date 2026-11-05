#!/usr/bin/env python3
"""Attribute native shallow-contact endpoint change to tangent and residual push.
Read-only diagnostic on matched-state transition rows; not a candidate force.
"""
import json
from pathlib import Path
from native_contact_response import resolve,word,trunc
from fine_residual_push_model import resolve as fine
r=Path('tmp/prof');source=json.loads((r/'coupled-second-transition-probe.json').read_text());out=[]
for case in source['cases']:
 for hz,rows in case['paths'].items():
  for row in rows:
   if row['ms']>14100:continue
   for s,w in zip(row['selected'],row['output']['wheels']):
    if w['branch'] not in ('full_tangent','crossing'):continue
    old=[s['old_world_'+a]for a in 'xyz'];proposed=[s['world_'+a]for a in 'xyz'];new=proposed.copy();new[1]-=w['down']
    # The inspected shallow-contact transitions have no incoming gravity.
    assert not w['applied_gravity'] and s['velocity']==s['velocity_fraction']==0
    geo={k:s[k]for k in ('plane','plane_flags','normal_x','normal_y','normal_z',*('matrix'+str(i)for i in range(9)),*('origin_'+a for a in 'xyz'))}
    n=resolve(old,new,geo,s['distance'],0,0,s['impact_flags']);f=fine(old,new,geo,s['distance'],0,0,s['impact_flags'])
    assert n['position']==w['position']
    out.append(dict(phase=case['phase'],hz=int(hz),ms=row['ms'],wheel=s['wheel'],branch=n['branch'],tangent_delta_from_proposal=[x-y for x,y in zip(n['before_push'],proposed)],native_push=n['push'],fine_push=f['push'],endpoint_difference=[x-y for x,y in zip(f['position'],n['position'])],native_residual=n['stored_clearance'],suspension=row['output']['suspensions'][s['wheel']]))
(r/'contact-push-attribution.json').write_text(json.dumps(dict(scope=__doc__,rows=out),indent=2)+'\n')
for v in out:
 if v['wheel']in(0,2):print(v)
