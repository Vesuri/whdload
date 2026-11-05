from pathlib import Path
import json,struct,hashlib
r=Path(__file__).resolve().parents[1];b=r/'tmp/build/step5-native-heading-writers';cases=json.loads((b/'cases.json').read_text())
report={'scope':'Seeded native instruction groups for two coupled heading zeroes, two cold resets and one relative-to-world assignment; not full modal transitions','profiles':{}}
def u32(v):return struct.pack('>I',v&0xffffffff)
seed=b''.join(struct.pack('>ihih',c*12345-50000,c-4,c*45678+90000,4-c) for c in range(8))
arrays=b''.join(u32(c*12345-50000) for c in range(8))+b''.join(u32(c*45678+90000) for c in range(8))
for profile in ('a1200','a1200-fast'):
 paths=[r/'tmp/step5'/('native-heading-writers-'+profile+'-'+v) for v in ('control','heading')]
 if not all((p/'result.json').exists() for p in paths):continue
 results=[json.loads((p/'result.json').read_text()) for p in paths]
 if not all(d.get('status')=='complete' and d.get('slave_sha256')==hashlib.sha256((b/(v+'.slave')).read_bytes()).hexdigest() for d,v in zip(results,('control','heading'))):continue
 data=[(p/'results.bin').read_bytes() for p in paths];assert all(len(d)==len(cases)*168 for d in data)
 checks=[]
 for i,case in enumerate(cases):
  car=case['car'];op=case['operation'];old,new=[d[i*168:(i+1)*168] for d in data]
  relative=car*12345-50000;world=car*45678+90000;rr=car-4;wr=4-car
  expected_shadow=bytearray(seed);expected_arrays=bytearray(arrays);native_work=u32(relative)+u32(world);fine_work=native_work
  if op.startswith('zero_'):
   total=wr-rr;q=(abs(total)//5)*(1 if total>=0 else -1);rem=total-q*5
   expected_shadow[car*12:car*12+12]=u32(0)+struct.pack('>h',0)+u32(world-relative+q)+struct.pack('>h',rem)
   native_work=u32(0)+u32(world-relative);fine_work=u32(0)+u32(world-relative+q)
  elif op.startswith('cold_zero_'):
   expected_shadow[car*12:car*12+6]=bytes(6);expected_arrays[car*4:car*4+4]=bytes(4)
  else:
   newworld=relative+0x12345000
   expected_shadow[car*12+6:car*12+12]=u32(newworld)+struct.pack('>h',rr)
   expected_arrays[32+car*4:36+car*4]=u32(newworld)
  checks.append(dict(case,control_exact=old==seed+expected_arrays+native_work,heading_exact=new==expected_shadow+expected_arrays+fine_work))
 probe=results[1]['probe'];passed=all(c['control_exact'] and c['heading_exact'] for c in checks) and probe=={'error':0,'heading_installed':1,'heading_zeroes':16,'heading_resets':16,'heading_assignments':8}
 report['profiles'][profile]={'passed':passed,'probe':probe,'cases':checks};print(profile,'passed' if passed else 'FAILED',json.dumps([c for c in checks if not c['control_exact'] or not c['heading_exact']]),flush=True)
report['status']='passed' if len(report['profiles'])==2 and all(p['passed'] for p in report['profiles'].values()) else 'incomplete_or_failed'
(r/'manifest/step5-native-heading-writers-validation.json').write_text(json.dumps(report,indent=2)+'\n')
