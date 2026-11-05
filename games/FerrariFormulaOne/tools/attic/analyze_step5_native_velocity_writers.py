from pathlib import Path
import json,struct,hashlib
r=Path(__file__).resolve().parents[1];b=r/'tmp/build/step5-native-velocity-writers';cases=json.loads((b/'cases.json').read_text());report={'scope':'Seeded native cold velocity writer groups; not complete initialization/modal transitions','profiles':{}}
seed=b''.join(struct.pack('>IIhh',256+c*257,(200<<16)+512+c*513,c-4,4-c) for c in range(8))
arrays=bytes(16)+struct.pack('>8h',*([200]*8))
for profile in ('a1200','a1200-fast'):
 paths=[r/'tmp/step5'/('native-velocity-writers-'+profile+'-'+v) for v in ('control','bridge')]
 if not all((p/'result.json').exists() for p in paths):continue
 results=[json.loads((p/'result.json').read_text()) for p in paths]
 if not all(d.get('status')=='complete' and d.get('slave_sha256')==hashlib.sha256((b/(v+'.slave')).read_bytes()).hexdigest() for d,v in zip(results,('control','bridge'))):continue
 data=[(p/'results.bin').read_bytes() for p in paths];assert all(len(d)==40*132 for d in data)
 checks=[]
 for i,c in enumerate(cases):
  car=c['car'];op=c['operation'];old,new=[d[i*132:(i+1)*132] for d in data];expected=bytearray(seed);native=bytearray(arrays)
  axes=(0,1) if op=='zero_both' else (0,) if op.startswith('zero_x') else (1,)
  for axis in axes:
   value=200 if op=='set_z200' else 0
   expected[car*12+axis*4:car*12+axis*4+4]=struct.pack('>i',value<<16)
   expected[car*12+8+axis*2:car*12+10+axis*2]=bytes(2)
   native[axis*16+car*2:axis*16+car*2+2]=struct.pack('>h',value)
  checks.append(dict(c,control_seed_exact=old[:96]==seed,native_expected=old[96:128]==native and new[96:128]==native,ownership_exact=new[:96]==expected,hook_count=struct.unpack_from('>I',new,128)[0]==car*6+(1,2,3,4,6)[i%5]))
 passed=all(all(v for k,v in c.items() if k not in ('car','operation')) for c in checks) and results[1]['probe']=={'error':0,'velocity_installed':1,'velocity_cold_writes':48}
 report['profiles'][profile]={'passed':passed,'cases':checks,'probe':results[1]['probe']};print(profile,'passed' if passed else 'FAILED',[c for c in checks if not all(c[k] for k in ('control_seed_exact','native_expected','ownership_exact','hook_count'))][:4])
report['status']='passed' if len(report['profiles'])==2 and all(x['passed'] for x in report['profiles'].values()) else 'incomplete_or_failed'
(r/'manifest/step5-native-velocity-writers-validation.json').write_text(json.dumps(report,indent=2)+'\n')
