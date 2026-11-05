#!/usr/bin/env python3
"""Apply unchanged physical limits offline; do not claim unmodeled live checks."""
from p7_offline import OUT
import json,hashlib
from pathlib import Path
root=Path('tmp/prof');p=root/'natural-crest-criteria.json';ph=root/'native-contact-phase-criteria.json'
assert hashlib.sha256(p.read_bytes()).hexdigest()=='90570d37e39d7fbdf804bbc497959ffe30e60f51bbb60c3e938f041c1d3401db'
assert hashlib.sha256(ph.read_bytes()).hexdigest()=='74afe3d039870269ccf4d160434ec52f05fe195dfb8dc6c338a3aeca613d64ce'
c=json.loads(p.read_text());family=json.loads(ph.read_text());native={r['tick']:r for r in json.loads((root/'natural-crest20/bridge.json').read_text())['rows']}
cases=[]
for mode in ('control','distance','combined'):
 for phase in ('nominal','minus64','plus64'):
  rows=json.loads((OUT/f'{mode}-{phase}.json').read_text())['rows'];ix={r['tick']:r for r in rows};flights=[];block=[]
  for r in rows:
   if not any(r['flags']):block.append(r)
   elif block:flights.append(block);block=[]
  assert not block
  metrics={'final_'+k:rows[-1][k] for k in ('x','y','z','pitch','speed')}
  metrics.update(peak_height=max(r['y'] for r in rows),minimum_pitch=min(r['pitch'] for r in rows),maximum_pitch=max(r['pitch'] for r in rows),airborne_time=sum(map(len,flights))/50)
  for i,f in enumerate(flights):metrics['takeoff_'+str(i)]=f[0]['tick']/50;metrics['landing_'+str(i)]=(f[-1]['tick']+1)/50
  checks={k:dict(actual=v,reference=c['native20']['metrics'][k],limit=c['limits'][k],passed=abs(v-c['native20']['metrics'][k])<=c['limits'][k]+1e-8) for k,v in metrics.items() if k in c['limits']}
  for k in ('x','y','z','pitch','speed'):
   err=max(abs(v[k]-native[v['tick']*2//5][k]) for v in rows if v['tick']>=450 and v['tick']%10==0)
   checks['common_'+k]=dict(actual=err,limit=c['envelope'][k],passed=err<=c['envelope'][k])
  checks['two_flights']=dict(actual=len(flights),passed=len(flights)==2)
  fc=[]
  for t,bands in family['common_bands'].items():
   row=ix[int(t)*5]
   for k,band in bands.items():
    if k not in row:continue
    fc.append(dict(kind='common',time=int(t)/10,field=k,actual=row[k],**band,passed=band['low']<=row[k]<=band['high']))
  for i,(f,bands) in enumerate(zip(flights,family['flight_bands'])):
   vals=dict(takeoff=f[0]['tick']/50,landing=(f[-1]['tick']+1)/50,peak_height=max(v['y'] for v in f),minimum_pitch=min(v['pitch'] for v in f),maximum_pitch=max(v['pitch'] for v in f))
   for k,band in bands.items():
    v=vals[k];fc.append(dict(kind='flight',flight=i,field=k,actual=v,**band,passed=band['low']<=v+1e-8 and v-(.02 if k in ('takeoff','landing') else 0)<=band['high']+1e-8))
  result=dict(mode=mode,phase=phase,checks=checks,failures=[k for k,v in checks.items() if not v['passed']],phase_failures=[x for x in fc if not x['passed']],phase_check_count=len(fc))
  cases.append(result)
  print(mode,phase,'Y/pitch',checks['common_y']['actual'],checks['common_pitch']['actual'],'failed',result['failures'],'phase',len(result['phase_failures']))
(OUT/'audit.json').write_text(json.dumps(dict(cases=cases,criteria_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),phase_sha256=hashlib.sha256(ph.read_bytes()).hexdigest(),scope=__doc__),indent=2)+'\n')
