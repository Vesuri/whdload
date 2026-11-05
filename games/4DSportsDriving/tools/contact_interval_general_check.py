#!/usr/bin/env python3
"""Cross-check generalized events against earlier evidence and fine integration."""
import json,copy
from pathlib import Path
from contact_interval_general import event_integrate,sampled_integrate,Unsupported
from coupled_contact_reference import event_integrate as legacy
p=Path('tmp/prof');rows=json.loads((p/'crest-release-d9-50/takeoff-plane.json').read_text())['rows'];selected={(r['tick'],r['wheel']):r for r in rows if r['event']=='SELECT'};checks=[]
for (t,w),r in selected.items():
    prior=selected.get((t-1,w))
    if prior is None:continue
    a=legacy(r,prior,defer_penetration=True);b=event_integrate(r,prior,defer_penetration=True)
    assert max(abs(a[k]-b[k]) for k in ('velocity','downward'))<1e-8
    checks.append(dict(tick=t,wheel=w))
# Cases deliberately cover flat support, downward boundary arrival, a turning
# trajectory, and exact starting-boundary descent. High impact remains excluded.
cases=[]
for old_y,dy,v in ((0,0,0),(64,0,0),(70,0,20),(90,-50,0),(126,12,30),(140,-4,80),(200,4,0),(127,7,.5)):
    r={f'{prefix}{a}':value for prefix in ('base_','node_') for a,value in zip('xyz',(0,0,0))}
    r.update(plane=0,normal_x=0,normal_y=8192,normal_z=0,wheel=0,velocity=v,velocity_fraction=0,old_world_x=0,old_world_y=old_y,old_world_z=0,world_x=0,world_y=old_y+dy,world_z=200)
    exact=event_integrate(r,defer_penetration=True);fine=sampled_integrate(r,64000,defer_penetration=True)
    error={k:abs(exact[k]-fine[k]) for k in ('velocity','downward')}
    assert max(error.values())<.003,(r,exact,fine)
    cases.append(dict(old_y=old_y,dy=dy,velocity=v,result=exact,errors=error))
out=dict(legacy_cases=len(checks),new_cases=cases,scope='Straight increasing-Z reference only; endpoint geometry remains separate. Explicit unsupported boundary chatter/topology/high-impact states are not clamped or counted as passed.')
(p/'contact-interval-general-check.json').write_text(json.dumps(out,indent=2)+'\n');print('Legacy exact',len(checks),'new signed/flat cases',len(cases),'max errors',{k:max(r['errors'][k] for r in cases) for k in ('velocity','downward')})
