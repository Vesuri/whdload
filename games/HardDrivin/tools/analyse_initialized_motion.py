"""Compare held-input live drivetrain states with an independent one-field model."""
import json,sys
from pathlib import Path
from drivetrain_model import advance
for name in sys.argv[1:]:
 out=Path('tmp/prof')/name
 init=json.loads((out/'initialization.json').read_text())
 assert init.get('valid') is True
 d=json.loads((out/'motion.json').read_text())
 rows=[r for r in d['rows'] if r['kind']=='STEP' and r['field']>=init['field']]
 assert rows
 assert rows[0]['consumed']-init['consumed_before']==init['initial_interval']
 assert all(b['serial']==a['serial']+1 and b['consumed']-a['consumed']==b['interval'] for a,b in zip(rows,rows[1:]))
 s=dict(velocity=0,velocity_carry=0,rpm=init['rpm'],rpm_carry=0,rpm_last=init['rpm'],rpm_gear=1,gear=1,throttle=init["new_throttle"])
 age=0;checks=[];position=init["position"][0]*65536;previous_projection=0
 for r in rows:
  assert r['throttle']==init['new_throttle'] and r['buttons']==0 and r['y8']==0 and r['z8']==200224 and r['heading']==360 and r['mask']==15 and r['road']==255 and not r['braking'] and not r['fall_velocity']
  target=r['consumed']-init['consumed_before'];assert target>=age
  while age<target:
   s,_=advance(s,1);age+=1
   v,c=s['velocity'],s['velocity_carry'];native=3*v//2
   neighbor=3*(v+(1 if c>=0 else -1))//2
   projection=native*65536+(neighbor-native)*abs(c)*8192
   position+=(9*projection-7*previous_projection)//16
   previous_projection=projection
  checks.append(dict(field=r['field'],consumed_age=age,interval=r['interval'],actual_eighths=r['velocity']*8+r['velocity_carry'],expected_eighths=s['velocity']*8+s['velocity_carry'],actual_gear=r['gear'],expected_gear=s['gear'],actual_x_q16=r['x8']*65536+r['position_carry_x']*512+r['position_fraction_x'],expected_x_q16=position))
 bad=[r for r in checks if r['actual_eighths']!=r['expected_eighths'] or r['actual_gear']!=r['expected_gear'] or r['actual_x_q16']!=r['expected_x_q16']]
 result=dict(passed=not bad,scope='Flat automatic drivetrain from verified stationary initial state and held initialized throttle. One-field independent force/RPM/gear recurrence plus native adjacent-vector interpolation and position extension. No collision or general-trajectory claim.',checked=len(checks),mismatches=len(bad),first_mismatch=bad[:1],checks=checks)
 (out/'initialized-motion.json').write_text(json.dumps(result,indent=2)+'\n')
 print(name,'checked',len(checks),'mismatches',len(bad),'first',bad[:1],'last',checks[-1],flush=True)
 assert result['passed'], 'Independent initialized motion comparison failed'
