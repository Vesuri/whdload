from pathlib import Path
import json,struct,hashlib
r=Path(__file__).resolve().parents[1];b=r/'tmp/build/step5-native-velocity-contact';cases=json.loads((b/'cases.json').read_text());report={'scope':'Seeded native contact longitudinal fractional-velocity exchange; not full fine collision simulation','profiles':{}}
for profile in ('a1200','a1200-fast'):
 paths=[r/'tmp/step5'/('native-velocity-contact-'+profile+'-'+v) for v in ('control','bridge')]
 if not all((p/'result.json').exists() for p in paths):continue
 results=[json.loads((p/'result.json').read_text()) for p in paths]
 if not all(d.get('status')=='complete' and d.get('slave_sha256')==hashlib.sha256((b/(v+'.slave')).read_bytes()).hexdigest() for d,v in zip(results,('control','bridge'))):continue
 data=[(p/'results.bin').read_bytes() for p in paths];assert all(len(d)==56*148 for d in data)
 checks=[]
 for i,c in enumerate(cases):
  old,new=[d[i*148:(i+1)*148] for d in data];a=c['first'];z=c['second'];expected=bytearray(old[:96])
  for offset,size in ((4,4),(10,2)):
   expected[a*12+offset:a*12+offset+size]=old[z*12+offset:z*12+offset+size]
   expected[z*12+offset:z*12+offset+size]=old[a*12+offset:a*12+offset+size]
  seed=bytearray()
  for car in range(8):
   speed=120 if car==(a if c['front'] else z) else 100
   seed+=struct.pack('>IIhh',256+car*257,(speed<<16)+512+car*513,car-4,4-car)
  checks.append(dict(c,native_exact=old[96:144]==new[96:144],seed_exact=old[:96]==seed,exchange_exact=new[:96]==expected,one_exchange_per_call=struct.unpack_from('>I',new,144)[0]==i+1))
 passed=all(all(v for k,v in c.items() if k not in ('first','second','front')) for c in checks) and results[1]['probe']['error']==0
 report['profiles'][profile]={'passed':passed,'cases':checks,'probe':results[1]['probe']};print(profile,'passed' if passed else 'FAILED',[c for c in checks if not all(c[k] for k in ('native_exact','seed_exact','exchange_exact','one_exchange_per_call'))][:3])
report['status']='passed' if len(report['profiles'])==2 and all(x['passed'] for x in report['profiles'].values()) else 'incomplete_or_failed'
(r/'manifest/step5-native-velocity-contact-validation.json').write_text(json.dumps(report,indent=2)+'\n')
