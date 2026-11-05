#!/usr/bin/env python3
"""Cross-check first-jump live geometry and independently integrate wheel gravity."""
import json,math,struct
from pathlib import Path
p=Path('tmp/prof');result={}
def axis(v):return [-(v[8]+v[11]-v[2]-v[5]),v[7]+v[10]-v[1]-v[4]]
def angle(v):return math.atan2(v[0],v[1])*512/math.pi-256
for hz,reference in [(20,'natural-crest20'),(50,'distance-order-crest50')]:
 root=p/f'first-air-pitch{hz}';meta=json.loads((root/'anchor.json').read_text());mem=(root/'memory.bin').read_bytes();a=meta['data_base']+0x7ffe-meta['memory_base'];car=a-0x92e;priv=mem.index(b'4DA4PHYS')+12
 vel=list(struct.unpack_from('>4h',mem,car+0x4c));vf=[struct.unpack_from('>h',mem,priv+8+4*i)[0] for i in range(4)];pf=[struct.unpack_from('>h',mem,priv+10+4*i)[0] for i in range(4)]
 data=json.loads((root/'tilt-baseline.json').read_text())['records'];states={r['tick']:r for r in json.loads((p/reference/'bridge.json').read_text())['rows']};model=json.loads((root/'tilt-baseline-model.json').read_text())['rows'];checks=[]
 for b,pr,po,m in zip(data['BUILT'],data['PITCH'],data['PITCH_OUT'],model):
  tick=b[0];assert b[32:35]==[states[tick-1][k] for k in ('x','y','z')]
  assert b[3]==states[tick-1]['pitch'] and po[1]==states[tick]['pitch']
  assert not any(states[tick-1][f'w{i}'] for i in range(4))
  ds=[]
  for i,acc in enumerate((21,21,15,15)):
   if hz==20:vel[i]+=acc;ds.append(vel[i])
   else:
    step,pf[i]=divmod(10*vel[i]+2*vf[i]+7*acc+pf[i],25)
    dv,vf[i]=divmod(2*acc+vf[i],5);vel[i]+=dv;ds.append(step)
  if b[5:9]!=[384]*4:continue
  assert pr[1:10]==[16384,0,0,0,16384,0,0,0,16384]
  old=axis(b[18:30]);actual=axis(pr[10:22]);predicted=[old[0],old[1]+ds[0]+ds[1]-ds[2]-ds[3]]
  assert actual==predicted,(hz,tick,actual,predicted)
  checks.append(dict(tick=tick,old_pitch=b[3],new_pitch=po[1],geometric_delta=m['pitch_change'],raw_axis_gravity_delta=angle(actual)-angle(old),steps=ds))
 # Common physical window: (11.4,12.0], avoiding guard activation around level.
 common=[m for m in model if 11.4<m['tick']/hz<=12.0]
 before=states[round(11.4*hz)];after=states[12*hz]
 geometric=sum(m['pitch_change'] for m in common);observed=after['pitch']-before['pitch']
 result[str(hz)]=dict(trace_updates=len(model),exact_gravity_axes=len(checks),initial_velocity=struct.unpack_from('>4h',mem,car+0x4c),common_window=dict(start_pitch=before['pitch'],end_pitch=after['pitch'],observed_delta=observed,geometric_delta=geometric,rounding_and_gate_residual=observed-geometric,start_y=before['y'],end_y=after['y']),rows=checks)
a,c=result['20']['common_window'],result['50']['common_window'];result['pitch_gap_at_12s']=dict(initial=c['start_pitch']-a['start_pitch'],geometric=c['geometric_delta']-a['geometric_delta'],residual=c['rounding_and_gate_residual']-a['rounding_and_gate_residual'],final=c['end_pitch']-a['end_pitch'])
assert abs(sum(result['pitch_gap_at_12s'][k] for k in ('initial','geometric','residual'))-result['pitch_gap_at_12s']['final'])<1e-9
result['scope']='Observed trajectory attribution. Saved binary hashes in capture anchors. Every trace input position and output pitch matches independent bridge runs. Exact wheel-axis proof is restricted to fully extended suspension. Not a live corrected simulation.'
(p/'first-jump-attribution.json').write_text(json.dumps(result,indent=2)+'\n')
print({k:{q:v for q,v in r.items() if q!='rows'} if isinstance(r,dict) else r for k,r in result.items()})
