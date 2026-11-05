"""Compare live phase state with pristine native-engine incremental oracle."""
from pathlib import Path
import sys,json
exec(Path('tools/check_native_phase_incremental.py').read_text().split('results=[];native_checks=0')[0])
try:
 for name in sys.argv[1:]:
  root=Path('tmp/prof')/name
  init=json.loads((root/'initialization.json').read_text());data=json.loads((root/'motion.json').read_text())
  x=Incremental((0,0,1));age=0;checks=[]
  for row in data['rows']:
   if row['kind']!='STEP' or row['consumed']==0:continue
   if not row['phase_valid']:
    assert not checks and row['phase_calls']==0 and row['velocity']==0 and row['x8']==init['position'][0],row
    age=row['consumed'];continue
   assert row['mask']==15 and row['road']==255 and row['fall_velocity']==0 and row['heading']==360 and row['y8']==0 and row['z8']==init['position'][2],row
   target=row['consumed'];n=target-age
   assert n==row['interval'],(age,row)
   throttle=init['new_throttle'] if age>=init['consumed_before'] else 0
   expected=x.advance(n,throttle);age=target
   actual=(F(row['phase_current_v'],65536),F(row['phase_current_r'],65536),row['gear'],F((row['x8']-init['position'][0])*65536+row['position_fraction_x']+row['position_carry_x']*512,65536))
   good=actual==expected and row['phase']==x.phase and row['phase_valid']==1
   checks.append(dict(field=row['field'],age=age,actual=encode(actual),expected=encode(expected),passed=good))
  report=dict(passed=bool(checks) and all(c['passed'] for c in checks),checks=len(checks),results=checks,scope='Live straight automatic drive against pristine-engine oracle, including exact phase Q16 scalars, gear and position. No general handling or FPS acceptance.')
  (root/'phase-motion.json').write_text(json.dumps(report,indent=2)+'\n')
  print(name,report['passed'],len(checks),[c for c in checks if not c['passed']][:3])
  assert report['passed']
finally:ok(u.uc_close(h))
