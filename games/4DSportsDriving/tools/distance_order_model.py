#!/usr/bin/env python3
"""Exact trapezoidal/right-endpoint decomposition of the flat approach traces."""
from pathlib import Path
from fractions import Fraction as F
import json
root=Path('tmp/prof');result={};K=F(11,6)
for hz in (20,50):
 d=json.loads((root/f'crest-distance{hz}/distance-order.json').read_text());rows=[r for r in d['rows'] if r['tick']>hz//10]
 assert len(rows)==93*hz//10 and not d['old_new_mismatch'] and not d['applied_mismatch']
 assert all(r['old_target']==r['old_local_speed']==r['saved_old_target']==r['distance_old_target'] for r in rows)
 assert all(r['position'][:2]==[493824,512] for r in rows)
 assert all(a['distance_speed']==b['old_local_speed'] for a,b in zip(rows,rows[1:]))
 distance=sum(r['distance'] for r in rows);start=rows[0]['position'][2]-rows[0]['distance'];end=rows[-1]['position'][2];assert end-start==distance
 trapezoid=K/F(hz)*sum(F(r['old_local_speed']+r['distance_speed'],2) for r in rows)
 endpoint_bias=K/F(2*hz)*(rows[-1]['distance_speed']-rows[0]['old_local_speed'])
 ideal_right=K/F(hz)*sum(r['distance_speed'] for r in rows);assert trapezoid+endpoint_bias==ideal_right
 quantization=ideal_right-distance
 result[str(hz)]=dict(updates=len(rows),start_z=start,end_z=end,distance=distance,start_speed=rows[0]['old_local_speed'],end_speed=rows[-1]['distance_speed'],trapezoid=trapezoid,endpoint_bias=endpoint_bias,quantization=quantization)
a,b=result['20'],result['50'];parts=dict(initial_position=a['start_z']-b['start_z'],speed_curve_area=a['trapezoid']-b['trapezoid'],endpoint_order=a['endpoint_bias']-b['endpoint_bias'],quantization=b['quantization']-a['quantization'])
assert sum(parts.values())==a['end_z']-b['end_z']
correction=F(11,400)*(b['end_speed']-b['start_speed'])
result['difference']=dict(parts=parts,total=a['end_z']-b['end_z'],reference20_order_correction_on_observed50_speeds=correction,remaining_after_that_correction=a['end_z']-b['end_z']-correction)
result['scope']='Read-only algebra on the observed straight grounded approach. The proposed11/400*delta-speed correction retains native20 semi-implicit ordering, not evidence for closed-loop terrain, clamped stops, gear/contact impulses or airborne paths.'
def encode(v):
 if isinstance(v,F):return dict(exact=str(v),value=float(v))
 raise TypeError(type(v))
(root/'crest-distance-order-model.json').write_text(json.dumps(result,default=encode,indent=2)+'\n');print(json.dumps(result['difference'],default=encode,indent=2))
