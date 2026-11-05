"""Compare live changing-input phase integration with pristine native engine."""
from pathlib import Path
import sys,json
exec(Path('tools/check_native_phase_incremental.py').read_text().split('results=[];native_checks=0')[0])
try:
 for name in sys.argv[1:]:
  root=Path('tmp/prof')/name;data=json.loads((root/'motion.json').read_text())
  x=None;pending=None;checks=[];backward=[];inputs=[];start=None
  for row in data['rows']:
   if row['kind']=='INPUT':
    assert pending is None,row
    if row['interval']==0:
     assert x is None and row['velocity']==0 and row['phase_calls']==0,row
     continue
    assert row['mask']==15 and row['road']==255 and row['fall_velocity']==0 and row['heading']==360 and row['skid']==row['turning']==row['pitch']==row['roll']==0,row
    assert row['automatic']==1
    if x is None:
     assert row['velocity']==row['rpm']==0 and row['gear']==1 and row['phase_calls']==0,row
     x=Incremental((0,0,1));start=row['x8']*65536+row['position_fraction_x']+row['position_carry_x']*512
    pending=row;inputs.append((row['throttle'],row['braking']))
   elif row['kind']=='STEP' and pending is not None:
    before=pending;pending=None
    old_position=x.position
    expected=x.advance(before['interval'],before['throttle'],before['braking'])
    actual=(F(row['phase_current_v'],65536),F(row['phase_current_r'],65536),row['gear'],F(row['x8']*65536+row['position_fraction_x']+row['position_carry_x']*512-start,65536))
    assert row['velocity']==int(actual[0]) and row['rpm']==int(actual[1]),row
    good=actual==expected and row['phase']==x.phase and row['phase_valid']==1
    checks.append(dict(field=row['field'],interval=before['interval'],throttle=before['throttle'],brake=before['braking'],actual=encode(actual),expected=encode(expected),passed=good))
    if actual[3]<old_position:backward.append(encode(old_position-actual[3]))
  assert checks and any(b for t,b in inputs) and len(set(inputs))>1
  report=dict(passed=all(c['passed'] for c in checks),checks=len(checks),input_transitions=sum(a!=b for a,b in zip(inputs,inputs[1:])),backward=backward,final=checks[-1],results=checks,scope='Actual controls-driven throttle/braking, flat full-contact automatic fixed-heading. Every complete active frame checked against pristine native engine. Trailing incomplete frame omitted; no mode-transition or FPS claim.')
  (root/'phase-inputs.json').write_text(json.dumps(report,indent=2)+'\n')
  print(name,{k:v for k,v in report.items() if k not in ['results','scope']},'mismatches',[c for c in checks if not c['passed']][:2],flush=True)
  assert report['passed']
finally:ok(u.uc_close(h))
