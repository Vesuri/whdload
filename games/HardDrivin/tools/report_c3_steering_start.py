"""Read-only capture diagnosis; this is not a passing C3 acceptance check."""
from pathlib import Path
import json
reports=[]
for suffix in ['a500','slow','020','040']:
 name='c3-current-steer-'+suffix
 rows=[r for r in json.loads((Path('tmp/prof')/name/'motion.json').read_text())['rows'] if r['kind']=='INTEGRATED']
 moving=next(r for r in rows if r['velocity']>0)
 start=moving['consumed']-moving['interval'];turn_start=moving['consumed']
 errors=[r['consumed'] for r in rows if r['heading']!=360+max(0,r['consumed']-turn_start)//2]
 assert not errors,(name,errors)
 changes=[];old=None
 for r in rows:
  state=(r['road'],r['gear'])
  if state!=old:
   changes.append({k:r[k] for k in ['consumed','interval','heading','road','gear','rpm','velocity','x8','z8']});old=state
 reports.append(dict(name=name,checked_returns=len(rows),throttle_response_start=start,first_moving_frame_end=turn_start,steering_delay_after_throttle_fields=turn_start-start,heading_formula='360 + floor(max(0, consumed - first_moving_frame_end) / 2)',heading_mismatches=errors,road_gear_transitions=changes))
report=dict(acceptance_passed=False,profiles=reports,scope='Current-source held-steering startup diagnosis. Every completed heading matches rate 4/8 after one complete moving render interval has been skipped by native B3B2. CDB2 calls orientation before CDB6 engine/position. Slow profiles upshift before road-state loss; fast profiles lose road state below automatic upshift threshold. The delay is proved; causal attribution of all later trajectory differences still requires a correction/controlled experiment. No C3 waiver.')
Path('tmp/c3-steering-start.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
