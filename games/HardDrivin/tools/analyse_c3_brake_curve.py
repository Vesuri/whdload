from pathlib import Path
import json,sys
exec(Path('tools/check_native_phase_incremental.py').read_text().split('results=[];native_checks=0')[0])
results=[]
try:
 for name in sys.argv[1:]:
  p=Path('tmp/prof')/name;data=json.loads((p/'motion.json').read_text());rows=data['rows']
  seed=next(r for r in rows if r['kind']=='INPUT' and r['phase_valid'] and r['throttle']==0 and r['braking'] and r['velocity']>100)
  x=Incremental((0,0,seed['gear']));x.anchor=tuple(F(seed[k],65536) for k in ['phase_anchor_v','phase_anchor_r']);x.v=F(seed['phase_current_v'],65536);x.r=F(seed['phase_current_r'],65536);x.phase=seed['phase']
  origin=F(seed['x8'])+F(seed['position_fraction_x'],65536)+F(seed['position_carry_x'],128)
  age=seed['consumed']-seed['interval'];curve={age:(x.v,x.position)};checks=0;end=None
  for row in rows:
   if row['kind']!='INTEGRATED' or row['consumed']<=age:continue
   if row['consumed']<seed['consumed']:continue
   assert row['throttle']==0 and row['heading']==360 and row['road']==255 and row['mask']==15 and row['y8']==0 and row['z8']==200224
   while age<row['consumed']:
    x.advance(1,0,255);age+=1;curve[age]=(x.v,x.position)
   actual=(F(row['phase_current_v'],65536),F(row['phase_current_r'],65536),row['gear'],F(row['x8'])+F(row['position_fraction_x'],65536)+F(row['position_carry_x'],128))
   expected=(x.v,x.r,x.gear,origin+x.position)
   assert actual==expected,(name,row['field'],actual,expected)
   checks+=1
   if x.v==0:end=age;break
  assert end is not None
  times=sorted(curve);cross=next((a,b) for a,b in zip(times,times[1:]) if curve[a][0]>=100>curve[b][0]);a,b=cross
  q=(curve[a][0]-100)/(curve[a][0]-curve[b][0]);cross_time=F(a)+q;cross_position=curve[a][1]+q*(curve[b][1]-curve[a][1]);stop=next(t for t in times if curve[t][0]==0)
  result=dict(name=name,checked_returns=checks,seed_consumed_field=seed['consumed']-seed['interval'],speed100_crossing_fields=[a,b],speed100_time=str(cross_time),stop_consumed_field=stop,stop_time_from_speed100=float(stop-cross_time),distance_world_from_speed100=float((curve[stop][1]-cross_position)/8),crossing_position_bracket_world=[float((curve[stop][1]-curve[z][1])/8) for z in [b,a]],max_capture_interval=max(r['interval'] for r in rows if r['kind']=='INPUT'),scope='Zero-throttle straight braking. Full fractional V/R/gear/X matches independent one-field native recurrence from an observed pre-braking seed above100. Subfield100 crossing interpolates adjacent one-field reference samples; retain its bracket.')
  result['curve']=[dict(field=t,velocity=str(v),position=str(pos)) for t,(v,pos) in sorted(curve.items())]
  (p/'brake-curve.json').write_text(json.dumps(result,indent=2)+'\n');results.append(result);print({k:v for k,v in result.items() if k!='curve'},flush=True)
 Path('tmp/c3-brake-curves.json').write_text(json.dumps(results,indent=2)+'\n')
finally:ok(u.uc_close(h))
