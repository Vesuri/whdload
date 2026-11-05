#!/usr/bin/env python3
"""Exact table-based forward-vector quadrature attribution on recorded air motion."""
from pathlib import Path
from fractions import Fraction as F
import json,struct
p=Path('tmp/prof');b=Path('tmp/game/4DSportsDriving_v1.2_1461/4DSportsDriving/data/stunts').read_bytes();table=struct.unpack_from('>257h',b,0x3a1dc+0x7ffe-0x376a)
def sine(a):
 a&=1023
 return table[a] if a<=256 else table[512-a] if a<=512 else -table[a-512] if a<=768 else -table[1024-a]
result={}
for hz,drive,body,motion in [(20,'order-air-distance20','natural-crest20','order-takeoff20'),(50,'distance-order-trace50','distance-order-crest50','order-takeoff50')]:
 rows=json.loads((p/drive/'distance-order.json').read_text())['rows']; dist={r['tick']:r for r in rows}
 states={r['tick']:r for r in json.loads((p/body/'bridge.json').read_text())['rows']}
 observed=json.loads((p/motion/'landing-motion-check.json').read_text())['rows'];checked=0
 for r in observed:
  if r['tick'] not in dist:continue
  d=dist[r['tick']]['distance'];pitch=r['angles'][1]
  predicted=[0,d*sine(pitch)//16384,d*sine(pitch+256)//16384]
  assert predicted==r['translation'],(hz,r['tick'],predicted,r['translation']);checked+=1
 subset=[r for r in rows if F(143,10)<F(r['tick'],hz)<=F(153,10)]
 assert len(subset)==hz
 assert all(not any(states[r['tick']][f'w{i}'] for i in range(4)) for r in subset)
 assert all(states[r['tick']]['heading']==states[r['tick']]['roll']==0 for r in subset)
 assert all(r['position']==[states[r['tick']][k] for k in ('x','y','z')] for r in subset)
 left=trap=quant=F(0);first=subset[0]['tick'];last=subset[-1]['tick'];correction=F(0)
 for r in subset:
  old=states[r['tick']-1]['pitch'];new=states[r['tick']]['pitch'];d=r['distance']
  a=F(d*sine(old),16384);z=F(d*sine(new),16384)
  left+=a;trap+=(a+z)/2;quant+=a-(a.numerator//a.denominator)
  correction+=F(3,4)*(a-z)
 result[str(hz)]=dict(updates=len(subset),live_translation_checks=checked,distance_speeds=sorted(set(r['distance_speed'] for r in subset)),start_pitch=states[first-1]['pitch'],end_pitch=states[last]['pitch'],forward_y=left-quant,trapezoid=trap,left_endpoint_bias=left-trap,projection_floor_loss=quant,observed_body_rise=states[last]['y']-states[first-1]['y'],proposed_reference20_order_correction=correction if hz==50 else None)
a,c=result['20'],result['50'];parts=dict(pitch_speed_curve=a['trapezoid']-c['trapezoid'],endpoint_order=a['left_endpoint_bias']-c['left_endpoint_bias'],projection_floor=c['projection_floor_loss']-a['projection_floor_loss']);assert sum(parts.values())==a['forward_y']-c['forward_y']
result['difference']=dict(parts=parts,forward_y=a['forward_y']-c['forward_y'],body_rise=a['observed_body_rise']-c['observed_body_rise'])
result['scope']='Recorded-trajectory quadrature attribution, not a live correction. Q14 table formula independently matches the observed 6 native20 and30 A4000 forward translations. All body states match independent bridge captures. Proposed orientation coupling needs a causal, contact-consistent vector derivation; no runtime patch or acceptance claim.'
def enc(x):
 if isinstance(x,F):return dict(exact=str(x),value=float(x))
 raise TypeError(type(x))
(p/'pitch-distance-order-model.json').write_text(json.dumps(result,default=enc,indent=2)+'\n');print(json.dumps(result,default=enc,indent=2))
