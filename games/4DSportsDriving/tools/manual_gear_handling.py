#!/usr/bin/env python3
"""Freeze native manual-shift handling metrics, then compare a50Hz fixture."""
import argparse,json,struct,hashlib
from pathlib import Path
from simulation_fixture import read_fixture

def read(path):
 p=Path(path);m=json.loads((p/'anchor.json').read_text());b=(p/'memory.bin').read_bytes();aa=m['data_base']+0x7ffe-m['memory_base'];hz=m['active_simulation_word'];n=m['simulation_tick'];ptr=struct.unpack_from('>I',b,aa-0x1770)[0]-m['memory_base']
 assert b[aa-0x174b]==0,'Replay header must describe manual transmission'
 expected=bytes((1 if t<3*hz else 0 if t<4*hz else 2)|(16 if t==hz//2 else 32 if t==2*hz else 0) for t in range(n))
 assert b[ptr:ptr+n]==expected,'Recorded controls differ from the schedule'
 rows=[]
 for t,h,s in read_fixture(p):
  assert h==hz and s[0x21e]==0
  x,y,z=struct.unpack_from('>iii',s,0x152)
  rows.append(dict(time=t/h,x=x,y=y,z=z,speed=struct.unpack_from('>H',s,0x17c)[0],gear=s[0x210],busy=s[0x21c],delay=s[0x21d],current=list(struct.unpack_from('>HHH',s,0x186)[::2]),target=list(struct.unpack_from('>HH',s,0x18c)),crash=s[0x21b]))
 assert len(rows)==64 and [r['time'] for r in rows]==[t/10 for t in range(64)]
 assert all(r['x']==rows[0]['x'] and r['y']==512 and r['crash']==0 for r in rows)
 changes=[];last=None
 for r in rows:
  if r['gear']!=last:changes.append(r);last=r['gear']
 assert [r['gear'] for r in changes]==[1,2,1]
 settled=[]
 for c in changes[1:]:
  r=next(r for r in rows if r['time']>=c['time'] and r['gear']==c['gear'] and r['busy']==0)
  assert r['current']==r['target'];settled.append(r)
 assert settled[0]['target']==[34,12] and settled[1]['target']==[22,42]
 def at(t):return next(r for r in rows if r['time']==t)
 stop=next(r for r in rows if r['time']>4 and r['speed']==0)
 metrics=dict(upshift_settled_sample=settled[0]['time'],downshift_settled_sample=settled[1]['time'],speed_at_3s=at(3)['speed'],coast_speed_loss=at(3)['speed']-at(4)['speed'],braking_distance=stop['z']-at(4)['z'],stop_time_sample=stop['time'])
 return dict(metrics=metrics,rows=rows,sha256=hashlib.sha256((p/'slave.slave').read_bytes()).hexdigest())
p=argparse.ArgumentParser();p.add_argument('native10');p.add_argument('native20');p.add_argument('criteria');p.add_argument('--candidate');a=p.parse_args();l,r=read(a.native10),read(a.native20);path=Path(a.criteria)
if not a.candidate:
 assert not path.exists()
 limits={k:max(abs(l['metrics'][k]-v),0.1 if 'sample' in k else 1) for k,v in r['metrics'].items()}
 result=dict(native10=l,native20=r,limits=limits,rationale='Per-metric native10/20 difference, one-unit floor,0.1s sample-resolution floor for timing. Exact manual-header/input sequence and1->2->1 completed target positions required; flat/straight/crash-free. Fixed before candidate50.')
 path.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(limits,indent=2))
else:
 c=read(a.candidate);criteria=json.loads(path.read_text());assert criteria['native10']==l and criteria['native20']==r
 checks={k:dict(reference=v,actual=c['metrics'][k],tolerance=criteria['limits'][k],passed=abs(c['metrics'][k]-v)<=criteria['limits'][k]+1e-8) for k,v in r['metrics'].items()}
 result=dict(candidate=c,checks=checks,passed=all(r['passed'] for r in checks.values()),criteria_sha256=hashlib.sha256(path.read_bytes()).hexdigest());(Path(a.candidate)/'manual-handling.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(checks,indent=2));raise SystemExit(0 if result['passed'] else 1)
