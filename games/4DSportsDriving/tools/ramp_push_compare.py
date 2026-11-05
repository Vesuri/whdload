#!/usr/bin/env python3
"""Check live supported-ramp response and minimal-query search results."""
import hashlib,json
from pathlib import Path
from native_contact_response import resolve,vec,plane,rotate
P=Path(__file__).resolve().parents[1]/'tmp/prof';report={}
for name,minimal in (('ramp-push-reference50',False),('ramp-push-minimum50',True)):
 p=P/name;rows=json.loads((p/'penetration.json').read_text())['rows'];groups={}
 for r in rows:
  group=groups.setdefault((r['tick'],r['wheel']),{});assert r['stage'] not in group;group[r['stage']]=r
 checks=[]
 for (tick,w),s in groups.items():
  r=s['ROTATED'];assert r['velocity']==0
  native=resolve(vec(r,'old'),vec(r,'new'),r,r['distance'],0,0,r['impact_flags'])
  predicted=native['position'];push=native.get('push');amount=None
  if minimal and push is not None and any(push):
   before=native['before_push'];limit=-plane(r,before)*64;m=[r[f'matrix{i}'] for i in range(9)]
   assert r['plane']>=4 and 0<limit<=512
   for n in range(1,limit+1):
    v=rotate([0,n,0],m);point=[a+b for a,b in zip(before,v)]
    if plane(r,point)>=0:predicted=point;push=v;amount=n;break
   assert amount is not None
  assert predicted==vec(s['DONE'],'new'),(name,tick,w,predicted,s['DONE'])
  assert native['velocity']==s['DONE']['velocity'] and native['stored_clearance']==s['DONE']['clearance']
  assert native['impact_flags']==s['DONE']['impact_flags']
  if 'PUSH_VECTOR' in s:assert push==vec(s['PUSH_VECTOR'],'correction')
  checks.append(dict(tick=tick,wheel=w,branch=native['branch'],push=push,minimum_magnitude=amount))
 totals=[sum((c['push'] or [0,0,0])[i] for c in checks) for i in range(3)]
 report[name]=dict(slave_sha256=hashlib.sha256((p/'slave.slave').read_bytes()).hexdigest(),trace_sha256=hashlib.sha256((p/'penetration.json').read_bytes()).hexdigest(),contacts=len(checks),pushes=sum(c['push'] is not None and any(c['push']) for c in checks),sum_push=totals,checks=checks)
result=dict(captures=report,scope='Live same-interval supported-ramp contact responses. All recorded falling velocities zero. Original response or bounded exhaustive native-query minimum independently reproduces final XYZ, velocity, stored clearance and impact flags. Push sums are per-wheel geometric corrections, not body displacement. Increased contact frequency is observed; full-course causal contribution is not isolated by this trace alone.')
(P/'ramp-push-comparison.json').write_text(json.dumps(result,indent=2)+'\n')
for n,r in report.items():print(n,r['contacts'],r['pushes'],r['sum_push'])
