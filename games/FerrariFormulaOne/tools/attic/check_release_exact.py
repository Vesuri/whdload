from pathlib import Path
import json,hashlib
r=Path(__file__).resolve().parents[1];results={}
for kind in ('state','frame'):
 base=r/f'tmp/step5/c4-q03-release-{kind}-production-a1200-fast-normal-8m' if kind=='frame' else r/'tmp/step5/c4-q03-release-state-accepted-030-50-normal'
 if not (base/'result.json').exists():continue
 reference=json.loads((base/'result.json').read_text());cases=[]
 for folder in sorted((r/'tmp/step5').glob(f'c4-q03-release-{kind}-production-*')):
  if kind=='state' and 'a1200-fast' in folder.name:continue
  if folder.name.endswith('a1200-fast-normal'):continue
  if not (folder/'result.json').exists():continue
  report=json.loads((folder/'result.json').read_text())
  if report.get('status')!='captured':continue
  assert report['error']==0
  if kind=='state':
   base=r/('tmp/step5/c4-q03-release-state-accepted-'+('030-50' if '-030-50-' in folder.name else '040-25')+'-normal')
   if not (base/'records.bin').exists():continue
   reference_state=json.loads((base/'result.json').read_text());assert reference_state['status']=='captured' and reference_state['error']==0 and reference_state['steps']==100
   assert report['steps']==100
   blocks=json.loads((base/'blocks.json').read_text());assert json.loads((folder/'blocks.json').read_text())==blocks
   a=(base/'records.bin').read_bytes();b=(folder/'records.bin').read_bytes();width=sum(x['bytes'] for x in blocks);assert len(a)==len(b)==100*width
   failures=[]
   for step in range(100):
    at=step*width
    for block in blocks:
     n=block['bytes']
     if a[at:at+n]!=b[at:at+n]:failures.append(dict(step=step+1,block=block['name']))
     at+=n
   private=json.loads((base/'private.json').read_text())==json.loads((folder/'private.json').read_text())
   exact=not failures and private
   cases.append(dict(name=folder.name,passed=exact,private_exact=private,failures=failures))
  else:
   exact=reference['frames']==report['frames'];cases.append(dict(name=folder.name,passed=exact,frames=len(report['frames'])))
 results[kind]=dict(reference=('same-layout accepted 030 and 040 references; 040/060 production records compared in full without additional pointer normalization' if kind=='state' else base.name),status='passed' if len(cases)==(9 if kind=='state' else 10) and all(x['passed'] for x in cases) else 'incomplete-or-failed',cases=cases)
(r/'manifest/release-exact.json').write_text(json.dumps(results,indent=2)+'\n')
for k,v in results.items():print(k,v['status'],[(x['name'],x['passed']) for x in v['cases']])
