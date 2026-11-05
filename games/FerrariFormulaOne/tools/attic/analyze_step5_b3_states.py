from pathlib import Path
import json,struct
r=Path(__file__).resolve().parents[1];blocks=json.loads((r/'manifest/step4-measurements.json').read_text())['semantic_blocks']+[{'name':'gear','address':'0x6bf84','bytes':4},{'name':'instrument_phase','address':'0x6c942','bytes':6},{'name':'instrument_rates','address':'0x66c88','bytes':4},{'name':'flag_counter','address':'0x66be0','bytes':2}]
report={'scope':'101 exact checkpoints per arm, including all 20 native opponent pulses; native-instruction control restores the pre-conversion car code for opponents and the same converted player path. Player trajectory and all native semantic blocks must agree; no masks relaxed.','profiles':{}}
for profile in ('a1200','a1200-fast'):
 paths=[r/f'tmp/step5/{profile}-b3-v4-matrix-{v}-fine' for v in ('verify','control-lean','lean')]
 if not all((p/'result.json').exists() for p in paths):continue
 failures=[]
 for tick in range(125,226):
  data=[(p/f'loop{tick}.bin').read_bytes() for p in paths]
  for i in (1,2):
   for b in blocks:
    a=int(b['address'],16);n=b['bytes']
    if data[0][a:a+n]!=data[i][a:a+n]:failures.append(dict(tick=tick,arm=i,block=b['name'],first_difference=next(j for j in range(n) if data[0][a+j]!=data[i][a+j])))
 fractional={}
 for n in ('velocity_shadow','speed_shadow','position_shadow','heading_shadow','steering_shadow','wear_remainders','fuel_remainders'):
  raw=[(p/(n+'.bin')).read_bytes() for p in paths];fractional[n]=raw[0]==raw[1]==raw[2]
 result=dict(passed=not failures and all(fractional.values()),failures=failures,checkpoints=101,native_pulses=20,fractional_exact=fractional)
 report['profiles'][profile]=result;print(profile,result)
report['status']='passed' if len(report['profiles'])==2 and all(x['passed'] for x in report['profiles'].values()) else 'incomplete_or_failed'
(r/'manifest/step5-b3-state-validation.json').write_text(json.dumps(report,indent=2)+'\n')
