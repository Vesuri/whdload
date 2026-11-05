from pathlib import Path
from fractions import Fraction as F
import json,math
root=Path('tmp/prof');names=['c3-current-brake-'+x for x in ['a500','slow','020','040']]
reports=[json.loads((root/n/'brake-curve.json').read_text()) for n in names]
frame=max(r['interval'] for r in json.loads((root/names[0]/'motion.json').read_text())['rows'] if r['kind']=='INPUT')
curves=[];rates=[]
for n,d in zip(names,reports):
 c={r['field']:(F(r['velocity']),F(r['position'])) for r in d['curve']};start=F(d['speed100_time']);end=max(c)
 def at(t,c=c,end=end):
  t=min(t,F(end));a=math.floor(t);b=math.ceil(t);f=t-a
  return tuple(c[a][i]+f*(c[b][i]-c[a][i]) for i in range(2))
 origin=at(start)[1];curves.append([(at(start+t)[0],(at(start+t)[1]-origin)/8) for t in range(165)])
 rows=[r for r in json.loads((root/n/'motion.json').read_text())['rows'] if r['kind']=='INTEGRATED' and F(d['speed100_crossing_fields'][1])<=r['consumed']<=d['stop_consumed_field']]
 rate_v=rate_x=F(0)
 for a,b in zip(rows,rows[1:]):
  dt=b['consumed']-a['consumed'];assert dt>0
  rate_v=max(rate_v,abs(F(b['phase_current_v']-a['phase_current_v'],65536*dt)))
  def pos(r):return F(r['x8'])+F(r['position_fraction_x'],65536)+F(r['position_carry_x'],128)
  rate_x=max(rate_x,abs((pos(b)-pos(a))/(8*dt)))
 rates.append(dict(name=n,max_recorded_velocity_change_per_field=float(rate_v),max_recorded_world_distance_per_field=float(rate_x)))
max_v=max(d['max_recorded_velocity_change_per_field'] for d in rates);max_x=max(d['max_recorded_world_distance_per_field'] for d in rates)
spreads=[max(float(c[t][i]) for c in curves)-min(float(c[t][i]) for c in curves) for i in [0,1] for t in range(165)]
vspread=max(spreads[:165]);xspread=max(spreads[165:])
time_range=[min(d['stop_time_from_speed100'] for d in reports),max(d['stop_time_from_speed100'] for d in reports)]
# Retain a complete one-field uncertainty at each speed-100 crossing rather
# than presenting the subfield interpolation as an exact observed instant.
time_uncertain=[min(d['stop_consumed_field']-d['speed100_crossing_fields'][1] for d in reports),max(d['stop_consumed_field']-d['speed100_crossing_fields'][0] for d in reports)]
distance_uncertain=[min(d['crossing_position_bracket_world'][0] for d in reports),max(d['crossing_position_bracket_world'][1] for d in reports)]
report=dict(passed=vspread+2*max_v<=frame*max_v and xspread+2*max_x<=frame*max_x and time_uncertain[1]-time_uncertain[0]<=frame,ordinary_a500_frame_bound_fields=frame,recorded_rates=rates,velocity_bound=frame*max_v,distance_bound_world=frame*max_x,max_equal_elapsed_velocity_spread=vspread,max_equal_elapsed_distance_spread_world=xspread,crossing_phase_uncertainty_fields_per_run=1,stop_time_range_fields=time_range,conservative_stop_time_range_fields=time_uncertain,conservative_stop_distance_range_world=distance_uncertain,profiles=[{k:v for k,v in d.items() if k!='curve'} for d in reports],scope='C3 straight zero-throttle braking component only. Compare 0..164 elapsed fields after descending speed100. Native one-field curves have been checked against all complete captured returns. Bounds use one measured ordinary A500 frame (not the larger slowed frame) times maximum recorded rates, with crossing uncertainty charged against that allowance. Does not pass steering, lap/checkpoint timing, or overall C3.')
Path('tmp/c3-brake-comparison.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['profiles','recorded_rates']},indent=2));assert report['passed']
