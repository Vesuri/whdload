#!/usr/bin/env python3
"""Predeclare per-metric envelopes from native10/20, then evaluate50 separately."""
import argparse,json,struct,hashlib
from pathlib import Path
from simulation_fixture import read_fixture

def read(path):
 rows=[]
 for tick,hz,b in read_fixture(path):
  x,y,z=struct.unpack_from('>iii',b,0x152)
  rows.append(dict(time=tick/hz,speed=struct.unpack_from('>H',b,0x17c)[0],x=x,y=y,z=z,crash=b[0x21b]))
 assert len(rows)==32 and [r['time'] for r in rows]==[n/5 for n in range(32)]
 assert all(r['x']==rows[0]['x'] and r['y']==512 and r['crash']==0 for r in rows),'not a flat, straight, crash-free test'
 def at(t):return next(r for r in rows if r['time']==t)
 stop=next(r for r in rows if r['time']>3 and r['speed']==0)
 metrics={'speed_at_2s':at(2)['speed'],'acceleration_distance':at(2)['z']-at(0)['z'],
 'coast_speed_loss':at(2)['speed']-at(3)['speed'],'coast_distance':at(3)['z']-at(2)['z'],
 'braking_distance':stop['z']-at(3)['z'],'stop_time_sample_upper_bound':stop['time']-3}
 return dict(rows=rows,metrics=metrics,sha256=hashlib.sha256((Path(path)/'slave.slave').read_bytes()).hexdigest())
p=argparse.ArgumentParser();p.add_argument('native10');p.add_argument('native20');p.add_argument('criteria');p.add_argument('--candidate');a=p.parse_args()
l,r=read(a.native10),read(a.native20)
path=Path(a.criteria)
if not a.candidate:
 assert not path.exists(),'Do not overwrite predeclared criteria'
 # Native step quantization: one speed unit / one position unit. Stop time is
 # sampled at0.2s and must allow that interval rather than false precision.
 floors={k:(0.2 if k=='stop_time_sample_upper_bound' else 1) for k in r['metrics']}
 limits={k:max(abs(l['metrics'][k]-v),floors[k]) for k,v in r['metrics'].items()}
 result=dict(native10=l,native20=r,absolute_tolerances=limits,
 rationale='Each metric permits no greater departure from A2500 than the native Normal/A2500 disagreement, with a one-unit floor (0.2s for sampled stop). Fixed before reading candidate50. Flat/straight/no-crash outcomes are mandatory. No aggregate percentage.')
 path.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ('absolute_tolerances','rationale')},indent=2))
else:
 criteria=json.loads(path.read_text());assert criteria['native10']==l and criteria['native20']==r
 c=read(a.candidate);checks={k:dict(reference=v,actual=c['metrics'][k],tolerance=criteria['absolute_tolerances'][k],passed=abs(c['metrics'][k]-v)<=criteria['absolute_tolerances'][k]+1e-9) for k,v in r['metrics'].items()}
 result=dict(candidate=c,checks=checks,passed=all(v['passed'] for v in checks.values()))
 (Path(a.candidate)/'handling.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(checks,indent=2))
 raise SystemExit(0 if result['passed'] else 1)
