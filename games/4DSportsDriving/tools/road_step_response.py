#!/usr/bin/env python3
"""Matched-initial-clearance, common-time road-drop diagnostic."""
import argparse,hashlib,json,struct
from pathlib import Path
from simulation_fixture import read_fixture

def read(root):
 root=Path(root);meta=json.loads((root/'anchor.json').read_text());hz=meta['active_simulation_word'];blob=(root/'memory.bin').read_bytes();q=blob.index(b'4DRDSTEP')
 version,reserved,calls,low,first,last=struct.unpack_from('>HHIIHH',blob,q+8)
 assert version==1 and low==8*(3*hz//5) and first==hz+1 and last==8*hz//5,(hz,low,first,last)
 rows=[]
 for tick,rate,b in read_fixture(root):
  assert rate==hz
  if tick==rate:
   assert b[0x466+8:0x466+48]==bytes(40)
   assert b[0x466+134:0x466+136]==bytes(2)
   assert b[0x466+144:0x466+148]==bytes(4)
  rows.append(dict(time=tick/rate,y=struct.unpack_from('>i',b,0x156)[0],pitch=struct.unpack_from('>h',b,0x16c)[0],roll=struct.unpack_from('>h',b,0x16e)[0],velocity=list(struct.unpack_from('>4h',b,0x19e)),extension=list(struct.unpack_from('>4h',b,0x1a6)),wheel_y=list(struct.unpack_from('>12h',b,0x1c6))[1::3],surface=list(b[0x214:0x218]),crash=b[0x21b]))
 assert len(rows)==21 and [r['time'] for r in rows]==[i/10 for i in range(21)]
 at={r['time']:r for r in rows}
 initial=at[1.0];assert initial['y']==512 and initial['pitch']==initial['roll']==0 and initial['velocity']==initial['extension']==[0]*4 and initial['wheel_y']==[2]*4 and initial['surface']==[1]*4
 metrics=dict(fall_at_1_1=at[1.1]['y']-initial['y'],low_plateau_drift=at[1.5]['y']-at[1.2]['y'],rise_at_1_8=at[1.8]['y']-at[1.5]['y'],high_plateau_drift=at[2.0]['y']-at[1.8]['y'])
 contact={}
 for time,ground in ((1.2,1),(1.5,1),(1.8,2),(2.0,2)):
  r=at[time];lo=64*ground+384
  contact[str(time)]=dict(y=r['y'],interval=[lo,lo+63],passed=lo<=r['y']<=lo+63 and r['pitch']==r['roll']==0 and r['velocity']==r['extension']==[0]*4 and r['wheel_y']==[ground]*4 and r['surface']==[1]*4)
 return dict(rows=rows,metrics=metrics,contact_checks=contact,crash_free=all(not r['crash'] for r in rows),forcing=dict(calls=calls,low_calls=low,first_tick=first,last_tick=last),sha256=hashlib.sha256((root/'slave.slave').read_bytes()).hexdigest())
p=argparse.ArgumentParser();p.add_argument('native10');p.add_argument('native20');p.add_argument('criteria');p.add_argument('--candidate');a=p.parse_args();l,r=read(a.native10),read(a.native20);path=Path(a.criteria)
if not a.candidate:
 assert not path.exists()
 assert all(v['crash_free'] and all(x['passed'] for x in v['contact_checks'].values()) for v in (l,r))
 limits={k:max(abs(l['metrics'][k]-v),1) for k,v in r['metrics'].items()}
 result=dict(native10=l,native20=r,limits=limits,rationale='Matched level/unextended pre-drop bodyY512, four wheelY2 and zero velocities. Exact live forced-step call counts. Contact intervals derive from original floor((bodyY-384)/64)-ground. Per-metric native10/20 disagreement with one-unit floor. Controlled fixture only, not natural-terrain acceptance.')
 path.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(native10=l['metrics'],native20=r['metrics'],limits=limits),indent=2))
else:
 rules=json.loads(path.read_text());assert rules['native10']==l and rules['native20']==r;c=read(a.candidate)
 checks={k:dict(reference=v,actual=c['metrics'][k],limit=rules['limits'][k],passed=abs(c['metrics'][k]-v)<=rules['limits'][k]) for k,v in r['metrics'].items()}
 passed=c['crash_free'] and all(v['passed'] for v in c['contact_checks'].values()) and all(v['passed'] for v in checks.values())
 result=dict(passed=passed,candidate=c,checks=checks,criteria_sha256=hashlib.sha256(path.read_bytes()).hexdigest());(Path(a.candidate)/'road-step-response.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(passed=passed,checks=checks,contact=c['contact_checks']),indent=2));raise SystemExit(0 if passed else 1)
