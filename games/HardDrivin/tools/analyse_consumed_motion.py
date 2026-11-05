"""Separate constant-vector integration from wall-time publication sampling."""
import json,struct,sys
from fractions import Fraction
from pathlib import Path
FIELD_SECONDS=Fraction(142102,7093790)
START,END=360,420
for name in sys.argv[1:]:
 out=Path('tmp/prof')/name;data=json.loads((out/'motion.json').read_text())
 rows=[r for r in data['rows'] if r['kind']=='STEP' and START<=r['field']<=END]
 assert len(rows)>=2
 assert all(r['automatic']==1 and r['gear']>0 and r['velocity']>0 and r['throttle']==22 and r['buttons']==0 and not r['braking'] and r['y8']==0 and r['z8']==200224 and r['heading']==360 and r['fall_velocity']==0 and r['mask']==15 and r['road']==255 for r in rows),'not the qualified constant-throttle straight interval'
 assert all(r['velocity_last']==r['velocity'] for r in rows),'stale velocity companion'
 def projected(r):return r['projected_x']*65536+r['fraction_x']
 def position(r):return r['x8']*65536+r['position_carry_x']*512+r['position_fraction_x']
 pairs=[]
 for a,b in zip(rows,rows[1:]):
  elapsed=b['consumed']-a['consumed'];assert elapsed>=0 and elapsed==b['interval']
  assert b['serial']==a['serial']+1
  assert projected(a)==projected(b),'projection changes; constant-vector proof does not apply'
  expected=Fraction(projected(a)*elapsed,8);observed=position(b)-position(a)
  pairs.append(dict(first_field=a['field'],last_field=b['field'],consumed_fields=elapsed,expected_q16=str(expected),observed_q16=observed,error_q16=str(observed-expected)))
 elapsed=rows[-1]['consumed']-rows[0]['consumed'];assert elapsed>0
 displacement=Fraction(position(rows[-1])-position(rows[0]),65536*8)
 rate=displacement/(elapsed*FIELD_SECONDS)
 result=dict(passed=all(Fraction(x['error_q16'])==0 for x in pairs),profile=data['profile'],wall_window=[START,END],completed_return_fields=[rows[0]['field'],rows[-1]['field']],consumed_fields=elapsed,velocity_eighths=sorted({r['velocity']*8+r['velocity_carry'] for r in rows}),projection_q16=sorted({projected(r) for r in rows}),distance_world_exact=str(displacement),world_units_per_consumed_second=float(rate),world_units_per_observed_second=float(displacement/((rows[-1]['field']-rows[0]['field'])*FIELD_SECONDS)),publication_offsets=[min(r['field']-r['consumed'] for r in rows),max(r['field']-r['consumed'] for r in rows)],pairs=pairs,scope='Exact constant-vector position accounting against consumed fields, including both position carries. Not equal-wall-time trajectory or changing-force validation.')
 (out/'consumed-motion.json').write_text(json.dumps(result,indent=2)+'\n')
 print(name,{k:v for k,v in result.items() if k not in ['pairs','scope']});assert result['passed']
