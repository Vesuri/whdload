#!/usr/bin/env python3
"""Read phase-7 private counters and compare core state at equal elapsed fields."""
import json,struct,argparse
from pathlib import Path
from check_units import MARK
from timing_map import decode

def private(raw):
 at=raw.index(MARK)+len(MARK);at=(at+1)&~1
 names=['failures','assertions','first_failure','data','h4','active','epoch','fired','recovery_started','rng_count']
 r=dict(zip(names,struct.unpack_from('>10I',raw,at)))
 r['visual_seed']=struct.unpack_from('>H',raw,at+40)[0]
 n=min(r['rng_count'],256);r['rng_log']=[list(struct.unpack_from('>HH',raw,at+42+4*i)) for i in range(n)]
 return r

def compare(a,b):
 ma=json.loads((a/'capture.json').read_text());mb=json.loads((b/'capture.json').read_text())
 if ma.get('options',{}).get('C2') and mb.get('options',{}).get('C2'):
  from compare_simulation_demo import compare as enhanced_compare
  return enhanced_compare(a,b,require_rng=False)
 # Report measured differences; the original renderer coupling is a negative
 # control. Phase 8 must explicitly choose the intended equality requirements.
 aa=json.loads((a/'states/samples.json').read_text());bb=json.loads((b/'states/samples.json').read_text())
 for folder,states in [(a,aa),(b,bb)]:
  for i,state in enumerate(states):
   raw=(folder/'states'/f'{i:04d}.bin').read_bytes()
   state['saved_x']=int.from_bytes(raw[0x7ffe-22372:0x7ffe-22368],'big',signed=True)
 ea=private((a/'code.bin').read_bytes())['epoch'];eb=private((b/'code.bin').read_bytes())['epoch']
 assert ea and eb,'core comparison requires player-race anchors; inspect demo RNG logs separately'
 aa={s['vbl']-ea:s for s in aa};bb={s['vbl']-eb:s for s in bb}
 fields=sorted(aa.keys()&bb.keys());assert fields,'no common elapsed fields'
 keys=['saved_x','speed','pos','gear','clutch','rpm','x','road_left','road_right','traffic_x','traffic_lane_offsets','police_clock','police_stop','samples','sum_speed','steer','heading','yaw','event','chances','stage','score_total']
 first={k:next((i for i in fields if aa[i][k]!=bb[i][k]),None) for k in keys}
 pa=private((a/'end/code.bin').read_bytes());pb=private((b/'end/code.bin').read_bytes());n=min(pa['rng_count'],pb['rng_count'],256)
 return dict(common_fields=len(fields),first_difference=first,rng_prefix_length=n,rng_prefix_equal=pa['rng_log'][:n]==pb['rng_log'][:n],rng_counts=[pa['rng_count'],pb['rng_count']])
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('a',type=Path);p.add_argument('b',type=Path,nargs='?');p.add_argument('--expect-equal',action='store_true');a=p.parse_args()
 result=compare(a.a,a.b) if a.b else private((a.a/'end/code.bin').read_bytes());print(json.dumps(result,indent=2))
 if a.expect_equal:
  assert a.b is not None,'two captures required'
  assert all(v is None for v in result['first_difference'].values()),'core state differs at equal elapsed fields'
  if 'status' in result:assert result['status']=='PASS','enhanced state/RNG/effects differ'
