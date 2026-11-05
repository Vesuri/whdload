from pathlib import Path
import json,hashlib
r=Path(__file__).resolve().parents[1];b=r/'tmp/build/step5-selection';blocks=json.loads((r/'manifest/step4-measurements.json').read_text())['semantic_blocks'];report={'scope':'S0 startup candidate selection and passive-observer native state comparison at matched demo loops. No scheduler enabled; cycle-profile and enabled-mode acceptance remain separate gates.','profiles':{}}
for profile in ('a500','a500-fast','a1200','a1200-fast'):
 entries={};states={}
 for mode,custom in (('control',0),('fine',0),('fine',1)):
  key=f'{mode}-c2{custom}';p=r/'tmp/step5'/f'{profile}-selection-{key}';d=json.loads((p/'result.json').read_text());slave=b/(mode+('020' if profile.startswith('a1200') else '')+'.slave')
  assert d['status']=='passed' and d['slave_sha256']==hashlib.sha256(slave.read_bytes()).hexdigest()
  entries[key]=d;states[key]={t:(p/f'loop{t}.bin').read_bytes() for t in (125,150,175)}
 mismatches=[]
 for key in ('fine-c20','fine-c21'):
  for t in (125,150,175):
   for block in blocks:
    a=int(block['address'],16);z=block['bytes']
    if states[key][t][a:a+z]!=states['control-c20'][t][a:a+z]:mismatches.append(dict(variant=key,loop=t,block=block['name']))
 report['profiles'][profile]={'passed':not mismatches,'mismatches':mismatches,'captures':entries}
 print(profile,'passed' if not mismatches else 'failed',mismatches,flush=True)
report['status']='passed' if all(x['passed'] for x in report['profiles'].values()) else 'failed'
(r/'manifest/step5-selection-validation.json').write_text(json.dumps(report,indent=2)+'\n')
assert report['status']=='passed'
