from pathlib import Path
import json
exec(Path('tools/check_native_phase_incremental.py').read_text().split('results=[];native_checks=0')[0])
results=[]
try:
 for label in ['a500','slow','020','040']:
  p=Path('tmp/prof')/('c3-final-straight-'+label);d=json.loads((p/'motion.json').read_text());init=json.loads((p/'initialization.json').read_text());start=init['consumed_before'];x=Incremental((0,0,1));age=0;checks=0
  for r in d['rows']:
   if r['kind']!='INTEGRATED' or r['consumed']<=start or r['consumed']>420:continue
   assert r['throttle']==22 and r['automatic']==1 and r['mask']==15 and r['road']==255 and r['heading']==360 and r['pitch']==r['roll']==r['fall_velocity']==r['skid']==0
   target=r['consumed']-start
   # Advance an independent one-field recurrence, regardless of machine frames.
   while age<target:x.advance(1,22);age+=1
   pos=F(r['x8'])+F(r['position_fraction_x'],65536)+F(r['position_carry_x'],128)
   assert (F(r['phase_current_v'],65536),F(r['phase_current_r'],65536),r['gear'],pos)==(x.v,x.r,x.gear,init['position'][0]+x.position),(label,age,r,x.v,x.r,x.position)
   checks+=1
  results.append(dict(profile=label,checks=checks,initial_consumed_field=start,initial_wall_field=init['field'],last_response_age=age,final_velocity=str(x.v),final_gear=x.gear))
 report=dict(passed=True,checks=sum(x['checks'] for x in results),results=results,scope='Full flat controlled-start trajectory to consumed field420. All machines match one-field pristine-engine phase recurrence in fractional speed, RPM, gear and absolute fractional X. Time is aligned only by the independently verified initial throttle publication; its measured startup delay is retained, not hidden.')
 Path('tmp/c3-final-straight-curve.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
finally:ok(u.uc_close(h))
