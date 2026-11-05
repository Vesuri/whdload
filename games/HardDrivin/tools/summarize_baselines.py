"""Require full repeat equality; summarize matrix without assuming equal scenes."""
import collections,json
from pathlib import Path
from capture_demo import ROOT
from machine_profiles import PROFILES
from check_disabled import check
p=ROOT/'tmp/prof';result={}
for profile in PROFILES:
 a,b,d=[p/f's2-{profile}-{suffix}' for suffix in ['attract1','attract2','drive']]
 if not all((v/'baseline.json').exists() for v in [a,b,d]):continue
 x,y,z=[json.loads((v/'baseline.json').read_text()) for v in [a,b,d]];assert x==y,(profile,'fresh boots differ')
 assert check(a,['VERIFY_ATTRACT'])['passed'];assert check(d,['VERIFY_DRIVE'])['passed']
 row=dict(attract=x['windows']['attract'],**z['windows'],attract_repeat_samples=len(x['per_field']),repeat_identical=True,placement=json.loads((a/'placement.json').read_text()))
 for name,lo,hi in [('A',1,1251),('B',3000,5600)]:
  values=[v for v in z['per_field'] if lo<=v['field']<hi]
  row[name]['crash_fields']=sum(v['crash']!='00' for v in values);row[name]['replay_fields']=sum(v['replay']!='00' for v in values)
 result[profile]=row
(p/'step2-baselines.json').write_text(json.dumps(result,indent=2)+'\n')
for name,v in result.items():print(name,*(f'{v[k]["fps"]:.3f}' for k in ['attract','A','B']),v['repeat_identical'])
