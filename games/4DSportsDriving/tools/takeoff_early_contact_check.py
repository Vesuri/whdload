#!/usr/bin/env python3
"""Reproduce the early supported front-wheel penetration response exactly."""
import hashlib,json
from pathlib import Path
from native_contact_response import resolve,vec
P=Path(__file__).resolve().parents[1]/'tmp/prof'
p=P/'takeoff-early-contact50';d=json.loads((p/'penetration.json').read_text());events={}
for r in d['rows']:events.setdefault((r['tick'],r['wheel']),{})[r['stage']]=r
results=[]
for (tick,w),stages in events.items():
 r=stages['ROTATED'];done=stages['DONE'];assert r['velocity']==0
 predicted=resolve(vec(r,'old'),vec(r,'new'),r,r['distance'],0,0,r['impact_flags'])
 assert predicted['position']==vec(done,'new')
 assert predicted['before_push']==vec(stages['REQUERY'],'new')
 assert predicted['push']==vec(stages['PUSH_VECTOR'],'correction')
 assert predicted['velocity']==done['velocity'] and predicted['stored_clearance']==done['clearance']
 assert predicted['impact_flags']==done['impact_flags']
 results.append(dict(tick=tick,wheel=w,initial=vec(stages['ENTER'],'new'),**predicted))
assert len(results)==2 and all(r['tick']==3 and r['branch']=='full_tangent' and r['push']==[0,58,-26] for r in results)
geometry=json.loads((P/'takeoff-early-tilt50/tilt-baseline-model.json').read_text())
tilt=next(r for r in geometry['rows'] if r['tick']==3)
assert tilt['old_pitch']==67 and tilt['final_pitch_observed']==70
out=dict(slave_sha256=hashlib.sha256((p/'slave.slave').read_bytes()).hexdigest(),responses=results,tilt=tilt,scope='Two independent replays of the same saved slave: penetration instructions and pitch geometry. Existing native response reference reproduces both front-wheel branches, tangent motion, residual push, final positions, velocity and flags exactly. No gravity applied in these responses. The normal-query floor reports-1 while rotated planeY remains+1; native response then pushes one64-unit normal quantum. Native20 need not sample the same coordinate cell. This explains a mechanism, not a validated replacement contact law.')
(P/'takeoff-early-contact-check.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
