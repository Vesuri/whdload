from pathlib import Path
import json,struct,hashlib
r=Path(__file__).resolve().parents[1];b=r/'tmp/build/step5-native-contact';cases=json.loads((b/'cases.json').read_text());report={'scope':'Forced native car-contact ownership; full 100 ms physics otherwise unchanged; not fine-step contact dynamics acceptance','profiles':{}}
for profile in ('a1200','a1200-fast'):
 paths=[r/'tmp/step5'/('native-contact-'+profile+'-'+v) for v in ('control','bridge')]
 if not all((p/'result.json').exists() for p in paths):continue
 results=[json.loads((p/'result.json').read_text()) for p in paths]
 if not all(d.get('status')=='complete' and d['slave_sha256']==hashlib.sha256((b/(v+'.slave')).read_bytes()).hexdigest() for d,v in zip(results,('control','bridge'))):continue
 data=[(p/'results.bin').read_bytes() for p in paths];checks=[]
 for i,c in enumerate(cases):
  old,new=[x[i*148:(i+1)*148] for x in data]
  dst=c['first'] if c['front']==0 else c['second'];src=c['second'] if c['front']==0 else c['first']
  expected=bytearray(old[:96]);expected[dst*12+6:dst*12+8]=new[96+dst*2:98+dst*2];expected[dst*12+8:dst*12+12]=old[src*12+8:src*12+12]
  checks.append({'case':c,'native_state_exact':old[96:144]==new[96:144],'fraction_ownership_exact':new[:96]==expected,'exactly_one_contact':struct.unpack_from('>I',new,144)[0]==i+1})
 probe=results[1]['probe'];passed=all(all(c[k] for k in ('native_state_exact','fraction_ownership_exact','exactly_one_contact')) for c in checks) and probe['contact_first_count']==28 and probe['contact_second_count']==28
 report['profiles'][profile]={'passed':passed,'probe':probe,'cases':checks};print(profile,'passed' if passed else 'FAILED',probe,flush=True)
 if not passed:print('failed cases',json.dumps([c for c in checks if not all(c[k] for k in ('native_state_exact','fraction_ownership_exact','exactly_one_contact'))])[:3000])
report['status']='passed' if len(report['profiles'])==2 and all(d['passed'] for d in report['profiles'].values()) else 'incomplete_or_failed'
(r/'manifest/step5-native-contact-validation.json').write_text(json.dumps(report,indent=2)+'\n')
