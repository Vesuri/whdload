from pathlib import Path
import json,struct,hashlib
r=Path(__file__).resolve().parents[1];b=r/'tmp/build/step5-native-reset';cases=json.loads((b/'cases.json').read_text());report={'scope':'Native recovery routine reset ownership; not all clamp/teleport/save paths','profiles':{}}
for profile in ('a1200','a1200-fast'):
 paths=[r/'tmp/step5'/('native-reset-'+profile+'-'+v) for v in ('control','bridge')]
 if not all((p/'result.json').exists() for p in paths):continue
 results=[json.loads((p/'result.json').read_text()) for p in paths]
 if not all(d.get('status')=='complete' and d['slave_sha256']==hashlib.sha256((b/(v+'.slave')).read_bytes()).hexdigest() for d,v in zip(results,('control','bridge'))):continue
 data=[(p/'results.bin').read_bytes() for p in paths];checks=[]
 for i,c in enumerate(cases):
  old,new=[x[i*152:(i+1)*152] for x in data];dst=c['first'];expected=bytearray(old[:96])
  expected[dst*12:dst*12+6]=new[144:146]+bytes(4)
  expected[dst*12+6:dst*12+12]=new[146:148]+bytes(4)
  checks.append({'car':dst,'native_state_exact':old[96:148]==new[96:148],'reset_ownership_exact':new[:96]==expected,'two_resets_per_call':struct.unpack_from('>I',new,148)[0]==2*(i+1)})
 passed=all(all(c[k] for k in ('native_state_exact','reset_ownership_exact','two_resets_per_call')) for c in checks)
 report['profiles'][profile]={'passed':passed,'probe':results[1]['probe'],'cases':checks};print(profile,'passed' if passed else 'FAILED',json.dumps(checks),flush=True)
report['status']='passed' if len(report['profiles'])==2 and all(d['passed'] for d in report['profiles'].values()) else 'incomplete_or_failed'
(r/'manifest/step5-native-reset-validation.json').write_text(json.dumps(report,indent=2)+'\n')
