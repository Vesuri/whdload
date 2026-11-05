from pathlib import Path
import json,struct,hashlib
r=Path(__file__).resolve().parents[1];b=r/'tmp/build/step5-native-position-writers';cases=json.loads((b/'cases.json').read_text());report={'scope':'Native instruction groups for five cold writers and snapshot/restore ownership; not complete modal/loading/save-file lifecycle','profiles':{}}
for profile in ('a1200','a1200-fast'):
 paths=[r/'tmp/step5'/('native-position-writers-'+profile+'-'+v) for v in ('control','bridge')]
 if not all((p/'result.json').exists() for p in paths):continue
 results=[json.loads((p/'result.json').read_text()) for p in paths]
 if not all(d.get('status')=='complete' and d['slave_sha256']==hashlib.sha256((b/(v+'.slave')).read_bytes()).hexdigest() for d,v in zip(results,('control','bridge'))):continue
 data=[(p/'results.bin').read_bytes() for p in paths];checks=[]
 for i,c in enumerate(cases):
  old,new=[x[i*192:(i+1)*192] for x in data];car=c['car'];op=c['operation']
  if op=='snapshot':
   shadow=bytearray(b''.join(struct.pack('>hHhhHh',10,256+j*257,j-4,100,512+j*513,j-4) for j in range(8)))
   saved=bytearray(struct.pack('>hHh',50,0x1234,2)*8)
   native_x=[10]*8;native_z=[100]*8;native_saved=[50]*8;native_saved[car]=100
   saved[car*6:car*6+6]=shadow[car*12+6:car*12+12]
  elif op=='restore':shadow[car*12+6:car*12+12]=saved[car*6:car*6+6]
  else:
   axis,value={'init_x_111':(0,111),'init_z_222':(1,222),'init_x_333':(0,333),'init_x_444':(0,444),'zero_z':(1,0)}[op]
   offset=car*12+axis*6;shadow[offset:offset+6]=struct.pack('>hHH',value,0,0)
   (native_z if axis else native_x)[car]=value
  checks.append({'case':c,'native_arrays_exact':old[144:]==new[144:],'native_arrays_expected':new[144:]==struct.pack('>24h',*(native_x+native_z+native_saved)),'shadow_exact':new[:96]==shadow,'saved_exact':new[96:144]==saved})
 probe=results[1]['probe'];passed=all(all(c[k] for k in ('native_arrays_exact','native_arrays_expected','shadow_exact','saved_exact')) for c in checks) and probe['bridge_array_resets']==40 and probe['bridge_snapshots']==8 and probe['bridge_restores']==8
 report['profiles'][profile]={'passed':passed,'probe':probe,'cases':checks};print(profile,'passed' if passed else 'FAILED',probe)
 if not passed:print('Failures:',json.dumps([c for c in checks if not all(c[k] for k in ('native_arrays_exact','native_arrays_expected','shadow_exact','saved_exact'))])[:3000])
report['status']='passed' if len(report['profiles'])==2 and all(d['passed'] for d in report['profiles'].values()) else 'incomplete_or_failed'
(r/'manifest/step5-native-position-writers-validation.json').write_text(json.dumps(report,indent=2)+'\n')
