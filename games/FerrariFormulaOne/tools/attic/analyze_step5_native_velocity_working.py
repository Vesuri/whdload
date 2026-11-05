from pathlib import Path
import json,struct,hashlib
r=Path(__file__).resolve().parents[1];b=r/'tmp/build/step5-native-velocity-working';cases=json.loads((b/'cases.json').read_text());report={'scope':'Seeded native working velocity writer groups; not full fine physics or event flow','profiles':{}}
seed=b''.join(struct.pack('>IIhh',256+c*257,(200<<16)+512+c*513,c-4,4-c) for c in range(8))
arrays=bytes(16)+struct.pack('>8h',*([200]*8))
for profile in ('a1200','a1200-fast'):
 paths=[r/'tmp/step5'/('native-velocity-working-'+profile+'-'+v) for v in ('control','bridge')]
 if not all((p/'result.json').exists() for p in paths):continue
 results=[json.loads((p/'result.json').read_text()) for p in paths]
 if not all(d.get('status')=='complete' and d.get('slave_sha256')==hashlib.sha256((b/(v+'.slave')).read_bytes()).hexdigest() for d,v in zip(results,('control','bridge'))):continue
 data=[(p/'results.bin').read_bytes() for p in paths];assert all(len(d)==56*144 for d in data)
 checks=[]
 for i,c in enumerate(cases):
  car=c['car'];op=c['operation'];old,new=[d[i*144:(i+1)*144] for d in data];expected=bytearray(seed);native=bytearray(arrays);work=[0,200]
  if op in ('zero_a','zero_b','projection'):
   work=[17,23] if op=='projection' else [0,0]
   expected[car*12:car*12+12]=struct.pack('>ii',*(x<<16 for x in work))+bytes(4)
  elif op.startswith('clamp'):
   work[1]=int(op[5:]);expected[car*12+4:car*12+8]=struct.pack('>i',work[1]<<16);expected[car*12+10:car*12+12]=bytes(2)
  else:
   value=7 if op=='impulse_a' else -9
   native[car*2:car*2+2]=struct.pack('>h',value)
   expected[car*12:car*12+2]=struct.pack('>h',value)
  index=i%7;counts=(car*3+min(index+1,3),car*2+max(0,min(index-2,2)),car*2+max(0,index-4))
  checks.append(dict(c,control_seed_exact=old[:96]==seed,native_expected=old[96:132]==native+struct.pack('>hh',*work) and new[96:132]==old[96:132],ownership_exact=new[:96]==expected,counts_exact=struct.unpack_from('>3I',new,132)==counts))
 passed=all(all(v for k,v in c.items() if k not in ('car','operation')) for c in checks) and results[1]['probe']=={'error':0,'velocity_installed':1,'velocity_work_resets':24,'velocity_clamps':16,'velocity_impulses':16}
 report['profiles'][profile]={'passed':passed,'cases':checks,'probe':results[1]['probe']};print(profile,'passed' if passed else 'FAILED',[c for c in checks if not all(c[k] for k in ('control_seed_exact','native_expected','ownership_exact','counts_exact'))][:4])
report['status']='passed' if len(report['profiles'])==2 and all(x['passed'] for x in report['profiles'].values()) else 'incomplete_or_failed'
(r/'manifest/step5-native-velocity-working-validation.json').write_text(json.dumps(report,indent=2)+'\n')
