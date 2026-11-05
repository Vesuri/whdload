from pathlib import Path
import json
exec(Path('tools/check_native_phase_incremental.py').read_text().split('results=[];native_checks=0')[0])
try:
 summary=json.loads(Path('tmp/c3-final-straight-curve.json').read_text());assert summary['passed']
 x=Incremental((0,0,1));reference={0:(F(0),F(0))}
 for t in range(1,421):x.advance(1,22);reference[t]=(x.v,x.position/8)
 rates=[];frame=0
 for label in ['a500','slow','020','040']:
  rows=json.loads(Path('tmp/prof/c3-final-straight-'+label+'/motion.json').read_text())['rows']
  if label=='a500':frame=max(r['interval'] for r in rows if r['kind']=='INPUT')
  rows=[r for r in rows if r['kind']=='INTEGRATED' and r['consumed']<=420]
  for a,b in zip(rows,rows[1:]):
   dt=b['consumed']-a['consumed']
   def position(r):return F(r['x8'])+F(r['position_fraction_x']+512*r['position_carry_x'],65536)
   rates.append((F(abs(b['phase_current_v']-a['phase_current_v']),65536*dt),abs(position(b)-position(a))/(8*dt)))
 starts=[r['initial_consumed_field'] for r in summary['results']];spreads=[F(0),F(0)]
 for t in range(421):
  points=[reference[max(0,t-start)] for start in starts]
  for i in range(2):spreads[i]=max(spreads[i],max(p[i] for p in points)-min(p[i] for p in points))
 bounds=[frame*max(r[i] for r in rates) for i in range(2)]
 report=dict(passed=all(a<=b for a,b in zip(spreads,bounds)),ordinary_a500_frame_fields=frame,response_start_fields=starts,common_elapsed_range=[0,420],spread_velocity_world_distance=[float(v) for v in spreads],bounds_velocity_world_distance=[float(v) for v in bounds],scope='Full flat acceleration to settled plateau, absolute consumed simulation fields with observed throttle-publication offsets retained. Exact native one-field curve matches all343 active captured returns. Full550-field captures also have separate per-frame native-force/XYZ checks including later slope. This is not a displayed-pose or lap/checkpoint timing claim.')
 Path('tmp/c3-final-straight-comparison.json').write_text(json.dumps(report,indent=2)+'\n');print(report);assert report['passed']
finally:ok(u.uc_close(h))
