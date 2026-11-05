#!/usr/bin/env python3
"""Freeze controlled drop bounds from native modes before candidate runs."""
import argparse,json,struct,hashlib
from pathlib import Path
from simulation_fixture import read_fixture

def read(path):
 p=Path(path);m=json.loads((p/'anchor.json').read_text());hz=m['active_simulation_word'];mem=(p/'memory.bin').read_bytes();a4=m['data_base']+0x7ffe-m['memory_base'];hist=struct.unpack_from('>I',mem,a4-0x1770)[0]-m['memory_base'];assert mem[hist:hist+2*hz+1]==bytes(1 if t<hz or t>=2*hz else 5 if 2*t<3*hz else 9 for t in range(2*hz+1))
 rows=[]
 for t,h,b in read_fixture(p):
  assert h==hz
  rows.append(dict(time=t/hz,position=list(struct.unpack_from('>iii',b,0x152)),angles=list(struct.unpack_from('>hhh',b,0x16a)),extension=list(struct.unpack_from('>4h',b,0x1a6)),surfaces=list(b[0x214:0x218]),crash=b[0x21b]))
 assert len(rows)==21 and [r['time'] for r in rows]==[i/10 for i in range(21)]
 assert rows[0]['position']==[493824,1536,347008]
 # Initial cached contact is inherited; only inspect actual later samples.
 airborne=[r for r in rows[1:] if not any(r['surfaces'])];assert airborne
 contact=next(r for r in rows[1:] if any(r['surfaces']));ground=next(r for r in rows[1:] if all(r['surfaces']))
 metrics=dict(first_contact=contact['time'],full_contact=ground['time'],minimum_height=min(r['position'][1] for r in rows),final_y=rows[-1]['position'][1],final_pitch=rows[-1]['angles'][1],final_roll=rows[-1]['angles'][2],tail_height_range=max(r['position'][1] for r in rows if r['time']>=1.5)-min(r['position'][1] for r in rows if r['time']>=1.5))
 return dict(rows=rows,metrics=metrics,crash_free=all(r['crash']==0 for r in rows),ends_grounded=all(rows[-1]['surfaces']),slave_sha256=m['slave_sha256'])
def errors(a,b):
 return {k:max(abs(x['position'][i]-y['position'][i]) for x,y in zip(a['rows'],b['rows'])) for i,k in enumerate(('x','y','z'))}
p=argparse.ArgumentParser();p.add_argument('native10');p.add_argument('native20');p.add_argument('criteria');p.add_argument('--candidate');a=p.parse_args();l,r=read(a.native10),read(a.native20);f=Path(a.criteria)
if not a.candidate:
 assert not f.exists() and all(d[k] for d in (l,r) for k in ('crash_free','ends_grounded'))
 limits={k:max(abs(l['metrics'][k]-v),.1 if k.endswith('contact') else 1) for k,v in r['metrics'].items()};envelope={k:max(v,1) for k,v in errors(l,r).items()}
 d=dict(native10=l,native20=r,limits=limits,envelope=envelope,rationale='Original1024-unit body-only drop diagnostic (cached wheels unchanged), standard throttle/right/left controls, same native-derived pointwise XYZ and endpoint/contact bounds; freeze before experimental50 capture.')
 f.write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(dict(limits=limits,envelope=envelope),indent=2))
else:
 d=json.loads(f.read_text());assert d['native10']==l and d['native20']==r;c=read(a.candidate)
 checks={k:abs(c['metrics'][k]-v)<=d['limits'][k]+1e-8 for k,v in r['metrics'].items()};checks.update({f'common_{k}':v<=d['envelope'][k] for k,v in errors(c,r).items()});checks.update({k:c[k] for k in ('crash_free','ends_grounded')});out=dict(candidate=c,checks=checks,errors=errors(c,r),passed=all(checks.values()),criteria_sha256=hashlib.sha256(f.read_bytes()).hexdigest());(Path(a.candidate)/'return-drop.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2));raise SystemExit(0 if out['passed'] else 1)
