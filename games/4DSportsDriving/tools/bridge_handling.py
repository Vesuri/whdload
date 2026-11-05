#!/usr/bin/env python3
"""Prospective native-derived bounds for the stock-grid crest jump course."""
import argparse,json,hashlib,struct,re
from pathlib import Path
from simulation_fixture import read_fixture

def read(path):
 p=Path(path);d=json.loads((p/'bridge.json').read_text());hz=d['rate'];rows=d['rows'];m=json.loads((p/'anchor.json').read_text())
 assert d['first']==m['simulation_tick']+1 and 2<=d['first']<=hz//5 and d['end']==16*hz
 assert [r['tick'] for r in rows]==list(range(d['first'],16*hz+1))
 assert m['opponent']==0
 initial=read_fixture(p)[0];assert initial[:2]==(0,hz) and struct.unpack_from('>iii',initial[2],0x152)==(493824,512,347008)
 lookup={r['tick']:r for r in rows};matched=[]
 for t,rate,b in read_fixture(p,'bridge-end.bin'):
  if t in lookup:
   r=lookup[t];assert (r['x'],r['y'],r['z'])==struct.unpack_from('>iii',b,0x152)
   assert (r['heading'],r['pitch'],r['roll'])==struct.unpack_from('>hhh',b,0x16a)
   assert r['speed']==struct.unpack_from('>H',b,0x17c)[0]
   assert [r[f'w{i}'] for i in range(4)]==list(b[0x214:0x218]) and r['crash']==b[0x21b]
   matched.append(t)
 assert len(matched)==63
 intervals=[]
 for r in rows:
  if not any(r[f'w{i}'] for i in range(4)):
   if not intervals or intervals[-1][-1]!=r['tick']-1:intervals.append([])
   intervals[-1].append(r['tick'])
 assert intervals and intervals[-1][-1]<16*hz
 metrics={f'final_{k}':rows[-1][k] for k in ('x','y','z','heading','pitch','roll','speed','slip','spin')}
 metrics.update(peak_height=max(r['y'] for r in rows),minimum_pitch=min(r['pitch'] for r in rows),maximum_pitch=max(r['pitch'] for r in rows),airborne_time=sum(map(len,intervals))/hz)
 for i,seq in enumerate(intervals):
  metrics[f'takeoff_{i}']=seq[0]/hz;metrics[f'landing_{i}']=(seq[-1]+1)/hz
 common={r['tick']*5//hz:r for r in rows if r['tick']*5%hz==0 and r['tick']>=9*hz}
 return dict(rate=hz,metrics=metrics,intervals=len(intervals),common=common,crash_free=all(r['crash']==0 for r in rows),ends_grounded=all(rows[-1][f'w{i}'] for i in range(4)),aligned_samples=len(matched),slave_sha256=d['slave_sha256'])
def errors(a,b):
 return {k:max(abs(a['common'][t][k]-r[k]) for t,r in b['common'].items()) for k in ('x','y','z','heading','pitch','roll','speed','slip','spin')}
p=argparse.ArgumentParser(description=__doc__);p.add_argument('native10');p.add_argument('native20');p.add_argument('criteria');p.add_argument('--candidate');a=p.parse_args()
l,r=read(a.native10),read(a.native20);f=Path(a.criteria)
if not a.candidate:
 assert not f.exists();assert l['intervals']==r['intervals'] and all(v[k] for v in (l,r) for k in ('crash_free','ends_grounded'))
 limits={k:max(abs(l['metrics'][k]-v),.1 if k.startswith(('takeoff','landing')) or k=='airborne_time' else 1) for k,v in r['metrics'].items()}
 envelope={k:max(v,1) for k,v in errors(l,r).items()}
 out=dict(native10=l,native20=r,limits=limits,envelope=envelope,rationale='Before A4000 capture: same stock-grid throttle-only16s course; compare each event time, total airborne duration, peak height, pitch extrema and final state against A2500 with native10/20 disagreement bounds, floor0.1s for event time and one raw unit otherwise. Compare common-time5Hz body-state samples9..16s with maximum native disagreement, floorone. Require same airborne interval count, crash-free trajectory, grounded endpoint. Per-update traces independently aligned with63 fixture samples.')
 f.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
else:
 c=json.loads(f.read_text());assert json.loads(json.dumps(l))==c['native10'] and json.loads(json.dumps(r))==c['native20'];v=read(a.candidate)
 checks={k:dict(actual=v['metrics'].get(k),reference=n,limit=c['limits'][k],passed=k in v['metrics'] and abs(v['metrics'][k]-n)<=c['limits'][k]+1e-8) for k,n in r['metrics'].items()}
 checks.update({f'common_{k}':dict(actual=n,limit=c['envelope'][k],passed=n<=c['envelope'][k]) for k,n in errors(v,r).items()})
 checks.update({k:dict(passed=v[k]) for k in ('crash_free','ends_grounded')});checks['airborne_intervals']=dict(actual=v['intervals'],reference=r['intervals'],passed=v['intervals']==r['intervals'])
 out=dict(candidate=v,checks=checks,passed=all(x['passed'] for x in checks.values()),criteria_sha256=hashlib.sha256(f.read_bytes()).hexdigest());(Path(a.candidate)/'bridge-handling.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(checks,indent=2));raise SystemExit(0 if out['passed'] else 1)
