from pathlib import Path
import json,struct,hashlib
r=Path(__file__).resolve().parents[1];b=r/'tmp/build/step5-native-heading-reset'
report={'scope':'Seeded native $69496 recovery heading reset ownership, all eight cars; not cold initialization or full modal coverage','profiles':{}}
for profile in ('a1200','a1200-fast'):
 paths=[r/'tmp/step5'/('native-heading-reset-'+profile+'-'+v) for v in ('control','heading')]
 if not all((p/'result.json').exists() for p in paths):continue
 results=[json.loads((p/'result.json').read_text()) for p in paths]
 if not all(d.get('status')=='complete' and d.get('slave_sha256')==hashlib.sha256((b/(v+'.slave')).read_bytes()).hexdigest() for d,v in zip(results,('control','heading'))):continue
 data=[(p/'results.bin').read_bytes() for p in paths];assert all(len(d)==8*324 for d in data)
 seed=b''.join(struct.pack('>ihih',c*12345-50000,c-4,c*45678+90000,4-c) for c in range(8))
 checks=[]
 for c in range(8):
  old,new=[d[c*324:(c+1)*324] for d in data]
  expected=bytearray(seed)
  for axis in range(2):
   native=new[248+axis*32+c*4:252+axis*32+c*4]
   expected[c*12+axis*6:c*12+axis*6+6]=native+b'\0\0'
  native_expected=bytearray(b''.join(struct.pack('>i',c*12345-50000) for c in range(8))+b''.join(struct.pack('>i',c*45678+90000) for c in range(8)))
  native_expected[c*4:c*4+4]=new[312:316]
  native_expected[32+c*4:36+c*4]=new[316:320]
  checks.append({'car':c,'control_shadow_seed_exact':old[152:248]==seed,'native_state_exact':old[248:320]==new[248:320] and new[248:312]==native_expected,'relative_reset_value':struct.unpack_from('>i',new,312)[0]==-262144,'heading_ownership_exact':new[152:248]==expected,'two_heading_resets_per_call':struct.unpack_from('>I',new,320)[0]==2*(c+1)})
 passed=all(all(v for k,v in c.items() if k!='car') for c in checks) and results[1]['probe']['error']==0 and results[1]['probe']['heading_installed']==1 and results[1]['probe']['heading_resets']==16
 report['profiles'][profile]={'passed':passed,'probe':results[1]['probe'],'cases':checks};print(profile,'passed' if passed else 'FAILED',json.dumps(checks),flush=True)
report['status']='passed' if len(report['profiles'])==2 and all(p['passed'] for p in report['profiles'].values()) else 'incomplete_or_failed'
(r/'manifest/step5-native-heading-reset-validation.json').write_text(json.dumps(report,indent=2)+'\n')
