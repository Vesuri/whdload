#!/usr/bin/env python3
"""Prospective response gate for an isolated common-time grass-step diagnostic."""
import argparse,hashlib,json,struct
from pathlib import Path
from simulation_fixture import read_fixture

def read(root):
 root=Path(root); rows=[]
 for t,h,b in read_fixture(root):
  rows.append(dict(time=t/h,y=struct.unpack_from('>i',b,0x156)[0],pitch=struct.unpack_from('>h',b,0x16c)[0],roll=struct.unpack_from('>h',b,0x16e)[0],extension=list(struct.unpack_from('>4h',b,0x1a6)),surface=list(b[0x214:0x218]),crash=b[0x21b]))
 assert len(rows)==64 and [r['time'] for r in rows]==[i/5 for i in range(64)]
 at={r['time']:r for r in rows}
 metrics=dict(rise_at_12_0=at[12.0]['y']-at[11.6]['y'],raised_plateau_drift=at[12.0]['y']-at[11.8]['y'],fall_by_12_2=at[12.2]['y']-at[12.0]['y'],settled_drift=at[12.6]['y']-at[12.4]['y'])
 # Original flat contact: floor((bodyY-384)/64)-ground=0, only while
 # level and unextended. This is a geometry-derived interval, not a fitted
 # cross-rate error allowance. Samples are safely beyond transition edges.
 checks={}
 for time,ground in ((12.0,1),(12.4,0),(12.6,0)):
  r=at[time];lo=64*ground+384;hi=lo+63
  checks[str(time)]=dict(y=r['y'],interval=[lo,hi],passed=lo<=r['y']<=hi and r['pitch']==r['roll']==0 and r['extension']==[0]*4 and r['surface']==[4]*4)
 return dict(metrics=metrics,rows=rows,contact_checks=checks,crash_free=all(not r['crash'] for r in rows),sha256=hashlib.sha256((root/'slave.slave').read_bytes()).hexdigest())
p=argparse.ArgumentParser();p.add_argument('native10');p.add_argument('native20');p.add_argument('criteria');p.add_argument('--candidate');a=p.parse_args()
l,r=read(a.native10),read(a.native20);path=Path(a.criteria)
if not a.candidate:
 assert not path.exists()
 assert all(x['crash_free'] and all(c['passed'] for c in x['contact_checks'].values()) for x in (l,r))
 limits={k:max(abs(l['metrics'][k]-v),1) for k,v in r['metrics'].items()}
 result=dict(native10=l,native20=r,limits=limits,rationale='Controlled grass step only; fixed derived zero-distance intervals for level/unextended four-wheel contact. Compare relative rise, plateau drift, fall and settled drift against paired native disagreement (one-unit floor). Require crash-free outcome. Does not retroactively pass the natural spin raw-height criteria.')
 path.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(native10=l['metrics'],native20=r['metrics'],limits=limits),indent=2))
else:
 rules=json.loads(path.read_text());assert rules['native10']==l and rules['native20']==r;c=read(a.candidate)
 checks={k:dict(reference=v,actual=c['metrics'][k],limit=rules['limits'][k],passed=abs(c['metrics'][k]-v)<=rules['limits'][k]) for k,v in r['metrics'].items()}
 passed=c['crash_free'] and all(v['passed'] for v in c['contact_checks'].values()) and all(v['passed'] for v in checks.values())
 result=dict(passed=passed,candidate=c,checks=checks,criteria_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
 (Path(a.candidate)/'grass-step-response.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));raise SystemExit(0 if passed else 1)
