from pathlib import Path
import json,struct
r=Path(__file__).resolve().parents[1];root=r/'tmp/step5';blocks=json.loads((r/'manifest/step4-measurements.json').read_text())['semantic_blocks'];out={'scope':'real VBL producer, unmodified native integrator, matched completed demo loops','runs':{},'comparisons':{}}
for profile in ('a500','a1200','a1200-fast'):
 for mode in ('off','control','slow','logic'):
  name=profile+'-vbl-'+mode;p=root/name
  if not (p/'result.json').exists():continue
  result=json.loads((p/'result.json').read_text())
  if result.get('status')!='complete':continue
  checks=[];points={}
  for label in ('update120','anchor','loop125','loop150','loop175','loop225'):
   b=(p/(label+'.bin')).read_bytes();t=struct.unpack('>14I',(p/(label+'-time.bin')).read_bytes());native=struct.unpack_from('>H',b,0x24ad2)[0]
   check=(not any(t)) if mode=='off' else ((t[0]&65535)==(native-result['native_base'])%65536 and (t[1]<<32|t[2])==t[0]*710510 and t[3:5]==(0,0))
   checks.append(check);points[label]={'native_field':native,'context':t,'clock_correct':check,'state':{k['name']:b[int(k['address'],16):int(k['address'],16)+k['bytes']].hex() for k in blocks}}
  fields=(points['loop225']['native_field']-points['loop125']['native_field'])%65536
  out['runs'][name]={'clock_correct':all(checks),'native_base':result['native_base'],'fields_per_100_updates':fields,'ms_per_update':fields/(3546895/71051)*10,'points':points};print(name,'clock correct',all(checks))
 for mode in ('control','slow','logic'):
  a=profile+'-vbl-off';b=profile+'-vbl-'+mode
  if a not in out['runs'] or b not in out['runs']:continue
  diffs={t:[k for k,v in point['state'].items() if v!=out['runs'][a]['points'][t]['state'][k]] for t,point in out['runs'][b]['points'].items()}
  out['comparisons'][a+' vs '+b]={'mismatches':diffs,'exact':not any(diffs.values())};print(b,'state exact',not any(diffs.values()))
(r/'manifest/step5-vbl-validation.json').write_text(json.dumps(out,indent=2)+'\n')
assert all(d['clock_correct'] for d in out['runs'].values())
assert all(d['exact'] for d in out['comparisons'].values())
