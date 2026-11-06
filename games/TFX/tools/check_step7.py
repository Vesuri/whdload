#!/usr/bin/env python3
"""Check retained step 7 fixture evidence without starting an emulator."""
import json,hashlib,struct
from pathlib import Path
root=Path(__file__).resolve().parents[1]/'tmp/step7'
r={}
for cpu in ['040','030','060']:
 cases=json.loads((root/f'sort-pass-{cpu}/results.json').read_text())
 assert len(cases)==13 and all(c['passed'] for c in cases)
 for c in cases:
  d=(root/f'sort-pass-{cpu}'/f"{c['mode']}-{c['count']}-{c['pattern']}.bin").read_bytes()
  assert d[4:6]==b'\0\0'
  if c['mode']=='draw':assert struct.unpack_from('>HH',d)==(c['count'],347)
 r['sort-'+cpu]=len(cases)
base=json.loads((root/'sort-baseline-coherent/results.json').read_text())
assert len(base)==4 and all(not x['guard'] and not x['permutation'] for x in base)
for name,expected in [('fire-control-before',[1,2,1]),('fire-sort-only-before-checked',[2,2,1])]+[(f'fire-after-{cpu}',[1,1,1]) for cpu in ['040','030','060']]+[('fire-original-040',[1,1,1])]:
 d=root/name;events=json.loads((d/'events.json').read_text());done=[e for e in events if e['kind']=='launch-done']
 assert len(done)==len([e for e in events if e['kind']=='launch'])
 assert len({e['missile'] for e in done})==len(done)
 counts=[sum(lo<=e['swap']<=hi for e in done) for lo,hi in [(5,7),(15,17),(25,27)]]
 assert counts==expected and sum(counts)==len(done),(name,counts)
 assert (d/'fire-hook.bin').read_bytes()[:2]==bytes.fromhex('13f9' if 'before' in name else '6024')
 r[name]=counts
for name in ['sort-window','sort-window-same-seed','final-window']:
 d=json.loads((root/name/'counts.json').read_text());assert d['window']==[2,252] and d['publications']==57
 r[name]=d['publications']
for name in ['counts.json','after.png']+[f'end-hunk{i}.bin' for i in range(3)]:
 assert (root/'sort-window'/name).read_bytes()==(root/'sort-window-same-seed'/name).read_bytes()
r['sort_repeat_events_image_hunks_equal']=True
r['final_repeat']={name:(root/'final-window'/name).read_bytes()==(root/'final-window-repeat'/name).read_bytes() for name in ['counts.json','after.png']+[f'end-hunk{i}.bin' for i in range(3)]}
assert r['final_repeat']['counts.json']
r['correctness_cases_passed']=True
for backend in ['regression','regression-shared']:
 reg=json.loads((root/backend/'summary.json').read_text())
 assert set(reg)=={'020','030','040','060'}
 assert all(x['screenshots_identical'] for x in reg.values())
 r[backend]=dict(results=reg,state_gate_passed=all(x['raw_identical'] if cpu in ['040','060'] else x['clock_relative_identical'] for cpu,x in reg.items()))
(root/'validation.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
