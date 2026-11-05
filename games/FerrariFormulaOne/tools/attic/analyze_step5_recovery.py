from pathlib import Path
import json,struct,sys
version=sys.argv[1] if len(sys.argv)>1 else "v3"
r=Path(__file__).resolve().parents[1];root=r/'tmp/step5';blocks=json.loads((r/'manifest/step4-measurements.json').read_text())['semantic_blocks'];out={'scope':'synthetic status -8 at update126, native recovery ownership, not real contact handling or adapted physics','runs':{},'comparisons':{}}
for profile in ('a500','a1200','a1200-fast'):
 for mode in ('control','broken','fixed'):
  name=profile+'-recovery-'+version+'-'+mode;p=root/name
  if not (p/'result.json').exists():continue
  result=json.loads((p/'result.json').read_text())
  if result.get('status')!='complete':continue
  points={}
  for tick in (125,126,127,128,129,130,131,132):
   b=(p/f'loop{tick}.bin').read_bytes()
   points[str(tick)]={'status':struct.unpack_from('>h',b,0x2268e)[0],'state':{k['name']:b[int(k['address'],16):int(k['address'],16)+k['bytes']].hex() for k in blocks}}
  out['runs'][name]={'points':points};print(name,[p['status'] for p in points.values()])
 for mode in ('broken','fixed'):
  a=profile+'-recovery-'+version+'-control';b=profile+'-recovery-'+version+'-'+mode
  if a not in out['runs'] or b not in out['runs']:continue
  diffs={t:[k for k,v in point['state'].items() if v!=out['runs'][a]['points'][t]['state'][k]] for t,point in out['runs'][b]['points'].items()}
  exact=not any(diffs.values());out['comparisons'][a+' vs '+b]={'mismatches':diffs,'exact':exact,'expected_exact':mode=='fixed'};print(b,'state exact',exact)
(r/('manifest/step5-recovery-'+version+'-validation.json')).write_text(json.dumps(out,indent=2)+'\n')
assert all(d['exact']==d['expected_exact'] for d in out['comparisons'].values())
