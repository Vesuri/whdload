#!/usr/bin/env python3
"""Exact stage accounting from the same car seed, including first update."""
import hashlib,json,struct
from pathlib import Path
from simulation_fixture import read_fixture
root=Path(__file__).resolve().parents[1]
seed=(root/'tmp/fixtures/matched-takeoff-abi9/car.bin').read_bytes()
start=list(struct.unpack_from('>iii',seed))
terms=('rebuild','translation','contact','suspension','centroid_rounding','post_centroid')
data={};proof={}
reference={r['tick']:r for r in json.loads((root/'tmp/prof/natural-crest20/bridge.json').read_text())['rows']}
for hz,count in ((20,13),(50,31)):
 cap=root/f'tmp/prof/takeoff-complete-ledger{hz}'
 samples=read_fixture(cap)
 assert samples[0][:2]==(0,hz) and samples[0][2][0x152:0x222]==seed
 assert not any(samples[0][2][0x466:0x466+152])
 d=json.loads((cap/'landing-motion-check.json').read_text())
 rows=d['rows'];assert [r['tick'] for r in rows]==list(range(1,count+1))
 assert rows[0]['initial_position']==start
 last=start
 for r in rows:
  assert r['initial_position']==last
  assert [sum(r[k][i] for k in terms) for i in range(3)]==r['total']
  assert [last[i]+r['total'][i] for i in range(3)]==r['final_position']
  last=r['final_position']
  if hz==20:
   assert last==[reference[222+r['tick']][k] for k in ('x','y','z')]
 data[hz]=rows
 proof[str(hz)]={'slave_sha256':hashlib.sha256((cap/'slave.slave').read_bytes()).hexdigest(),'updates':count,'all_steps_accounted':True}
result=[]
for n in range(1,7):
 elapsed=n/10; window={hz:data[hz][:hz*n//10] for hz in (20,50)}
 delta={k:[sum(r[k][i] for r in window[50])-sum(r[k][i] for r in window[20]) for i in range(3)] for k in terms}
 error=[window[50][-1]['final_position'][i]-window[20][-1]['final_position'][i] for i in range(3)]
 assert [sum(delta[k][i] for k in terms) for i in range(3)]==error
 result.append(dict(elapsed=elapsed,position_error=error,stage_difference=delta))
report=dict(seed_sha256=hashlib.sha256(seed).hexdigest(),proof=proof,native_exact_positions=13,rows=result,scope='Complete displacement accounting, not causal independence. Translation reflects current heading/pitch; contact includes gravity and collision response. Rebuild and suspension contain cancelling geometry. All positions in raw game units. Equal car seed with zero private fractions; native course reproduction checked. No acceptance tolerances changed.')
path=root/'tmp/prof/takeoff-complete-ledger.json';path.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
