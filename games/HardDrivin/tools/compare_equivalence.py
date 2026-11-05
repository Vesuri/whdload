from pathlib import Path
import json
root=Path(__file__).resolve().parents[1]/'tmp/prof'
a=root/'equivalence-original-fields-v4';b=root/'equivalence-rebuilt-fields-v4'
r={}
for kind in ('state','screen'):
 mismatches=[];offsets=set()
 for i in range(1001):
  x=(a/f'{kind}-{i:04d}.bin').read_bytes();y=(b/f'{kind}-{i:04d}.bin').read_bytes()
  assert len(x)==len(y)
  d=[p for p,(v,w) in enumerate(zip(x,y)) if v!=w]
  if d:mismatches.append(dict(field=i,count=len(d)))
  offsets.update(d)
 r[kind]=dict(mismatched_fields=mismatches,offsets=[hex(x) for x in sorted(offsets)])
(root/'equivalence-comparison.json').write_text(json.dumps(r,indent=2))
print(json.dumps({k:dict(mismatched_fields=len(v['mismatched_fields']),offsets=v['offsets'][:80]) for k,v in r.items()},indent=2))
