#!/usr/bin/env python3
"""Prospective native-baseline handling limits with an explicit coast rounding bound."""
import argparse,struct,json,hashlib
from pathlib import Path
from simulation_fixture import read_fixture
K=11/6  # Native forward speed-to-distance per second:1408/768.
def read(path,throttle):
 rows=[]
 anchor=json.loads((Path(path)/'anchor.json').read_text())
 memory=(Path(path)/'memory.bin').read_bytes();base=anchor['memory_base'];aa=anchor['data_base']+0x7ffe
 inputs=struct.unpack_from('>I',memory,aa-base-0x1770)[0]
 hz=anchor['active_simulation_word'];count=anchor['simulation_tick']
 actual=memory[inputs-base:inputs-base+count]
 expected=bytes(1 if t<throttle*hz else 0 if t<(throttle+1)*hz else 2 for t in range(count))
 assert actual==expected,'captured input stream differs from declared physical-time script'
 for t,h,b in read_fixture(path):
  x,y,z=struct.unpack_from('>iii',b,0x152)
  rows.append(dict(time=t/h,hz=h,x=x,y=y,z=z,speed=struct.unpack_from('>H',b,0x17c)[0],crash=b[0x21b]))
 assert len(rows)==48 and [r['time'] for r in rows]==[n/5 for n in range(48)]
 assert len({r['hz'] for r in rows})==1
 assert all(r['x']==rows[0]['x'] and r['y']==512 and r['crash']==0 for r in rows)
 def at(t):return next(r for r in rows if r['time']==t)
 start,end=at(throttle),at(throttle+1)
 stop=next(r for r in rows if r['time']>throttle+1 and r['speed']==0)
 metrics={'speed_at_release':start['speed'],'acceleration_distance':start['z']-at(0)['z'],'coast_speed_loss':start['speed']-end['speed'],'braking_distance':stop['z']-end['z'],'stop_time_sample_upper_bound':stop['time']-(throttle+1)}
 coast=[r for r in rows if throttle<=r['time']<=throttle+1]
 shape=max(abs(r['speed']-(start['speed']+(end['speed']-start['speed'])*(r['time']-throttle))) for r in coast)
 distance=end['z']-start['z'];ideal=K*(start['speed']+end['speed'])/2
 # Right-endpoint integration of a linear coast: rate-specific quadrature bias.
 quadrature=K*(end['speed']-start['speed'])/(2*start['hz'])
 residual=distance-ideal-quadrature
 return dict(metrics=metrics,coast_distance=distance,coast_linear_speed_deviation=shape,coast_rounding_residual=residual,rows=rows,sha256=hashlib.sha256((Path(path)/'slave.slave').read_bytes()).hexdigest())
p=argparse.ArgumentParser();p.add_argument('native10');p.add_argument('native20');p.add_argument('criteria');p.add_argument('--candidate');p.add_argument('--throttle',type=int,default=3);a=p.parse_args()
l,r=read(a.native10,a.throttle),read(a.native20,a.throttle);path=Path(a.criteria)
if not a.candidate:
 assert not path.exists()
 # Native per-step floor removes [0,hz) units over this one-second interval.
 # Permit speed quantization up to the measured linear-shape deviation.
 for b in (l,r):
  hz=b['rows'][0]['hz'];eps=K*b['coast_linear_speed_deviation']+1e-8
  assert -hz-eps<=b['coast_rounding_residual']<=eps,b
 limits={k:max(abs(l['metrics'][k]-v),0.2 if k=='stop_time_sample_upper_bound' else 1) for k,v in r['metrics'].items()}
 shape=max(l['coast_linear_speed_deviation'],r['coast_linear_speed_deviation'])+1
 result=dict(throttle_seconds=a.throttle,native10=l,native20=r,absolute_tolerances=limits,coast_linear_speed_deviation_limit=shape,coast_rounding_residual_limit=1+K*shape,
 rationale='Non-coast-distance limits are native10/20 disagreements with one-unit or0.2s floors. Coast speed loss retains its native limit. Native floor loss must be [0,hz) units. Candidate50 retains distance fractions so total position-rounding error is less than one; signed speed fractions add at most K times the permitted one-second linear-speed error. Subtract only the derived right-endpoint quadrature term. No aggregate percentage; straight/level/no-crash required.')
 path.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ('native10','native20')},indent=2))
else:
 criteria=json.loads(path.read_text());assert criteria['native10']==l and criteria['native20']==r and criteria['throttle_seconds']==a.throttle
 c=read(a.candidate,a.throttle);assert c['rows'][0]['hz']==50
 checks={k:dict(actual=c['metrics'][k],reference=v,tolerance=criteria['absolute_tolerances'][k],passed=abs(c['metrics'][k]-v)<=criteria['absolute_tolerances'][k]+1e-8) for k,v in r['metrics'].items()}
 for k,limit in [('coast_linear_speed_deviation',criteria['coast_linear_speed_deviation_limit']),('coast_rounding_residual',criteria['coast_rounding_residual_limit'])]:
  checks[k]=dict(actual=c[k],absolute_limit=limit,passed=abs(c[k])<=limit+1e-8)
 result=dict(candidate=c,checks=checks,passed=all(r['passed'] for r in checks.values()),criteria_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
 (Path(a.candidate)/'handling-rounding.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(checks,indent=2));raise SystemExit(0 if result['passed'] else 1)
