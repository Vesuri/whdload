from pathlib import Path
import json,struct,hashlib
r=Path(__file__).resolve().parents[1];b=r/'tmp/build/step5-b3-contacts-v4';cases=json.loads((b/'cases.json').read_text());report={'scope':'112 native contact cases: every pair, both directions, pulse and non-pulse. Native control disables non-due opponent pairs. All native results exact; only player fractions may reset.','profiles':{}}
for profile in ('a1200','a1200-fast'):
 paths=[r/f'tmp/step5/b3-contacts-v4-{profile}-{v}' for v in ('control','candidate')]
 if not all((p/'result.json').exists() for p in paths):continue
 for p,v in zip(paths,('control','candidate')):
  d=json.loads((p/'result.json').read_text());assert d['status']=='complete' and d['slave_sha256']==hashlib.sha256((b/(v+'.slave')).read_bytes()).hexdigest()
 data=[(p/'results.bin').read_bytes() for p in paths];failures=[]
 for i,c in enumerate(cases):
  old,new=[x[i*304:(i+1)*304] for x in data];expected=bytearray(old[64:]);active=bool(c['pulse'] or c['first']==0)
  expected[96:98]=old[48:50]  # Native lateral impulse retains the player's fractional tail.
  dst=c['first'] if c['front']==0 else c['second']
  if active and dst==0:expected[6:12]=new[0:2]+bytes(4)
  if active and c['first']==0:
   expected[96+4:96+8]=new[32:34]+bytes(2);expected[96+10:96+12]=bytes(2)
   expected[192:198]=new[16:18]+bytes(4)
  if old[:64]!=new[:64] or new[64:]!=expected:failures.append(dict(index=i,case=c,native_exact=old[:64]==new[:64],shadow_exact=new[64:]==expected,actual=new.hex(),expected=(old[:64]+expected).hex()))
 report['profiles'][profile]=dict(passed=not failures,cases=len(cases),failures=failures);print(profile,'passed' if not failures else 'FAILED',len(failures),failures[:1])
report['status']='passed' if len(report['profiles'])==2 and all(x['passed'] for x in report['profiles'].values()) else 'incomplete_or_failed'
(r/'manifest/step5-b3-contact-validation.json').write_text(json.dumps(report,indent=2)+'\n')
