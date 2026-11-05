#!/usr/bin/env python3
"""Compare same-build/same-period demos, including simulation-owned visual phases.
Renderer buffer acknowledgements and drawing snapshots are not gameplay state.
"""
import argparse,hashlib,json,struct
from pathlib import Path
from verify_state import private
KEYS='speed pos gear clutch rpm x road_left road_right traffic_x traffic_lane_offsets police_clock police_stop samples sum_speed steer heading yaw event chances stage score_total throttle ratio step_displacement road_turn heading_delta neutral_steer traffic_pos traffic_speed oncoming_pos oncoming_speed oncoming_x police_seen police_phase radar_flag gas_approach stage_end'.split()

def load(p):
 m=json.loads((p/'capture.json').read_text());s=json.loads((p/'states/samples.json').read_text())
 for i,x in enumerate(s):
  b=(p/f'states/{i:04d}.bin').read_bytes()
  x['background_phase']=b[0x7ffe-29280:0x7ffe-29262].hex()
  x['lamp_phase']=b[0x7ffe-27138]
  x['saved_x']=int.from_bytes(b[0x7ffe-22372:0x7ffe-22368],'big',signed=True)
 return m,{x['vbl']-x['epoch']:x for x in s}

def wind(p,m):
 chip=(p/'end/chip.bin').read_bytes();a=m['regions']['h4']+0x1f9a
 n=int.from_bytes(chip[a:a+2],'big');assert 0<=n<=30
 # Pointer identity is allocation dependent; compare each sprite against its
 # own game's initial/intermediate/final pointer tables, not raw addresses.
 ram=(p/'end/code.bin').read_bytes();a4=m['regions']['td-data']-m['base']+0x7ffe
 offsets=[-23266,-23270,-23258,-23262]+list(range(-23238,-23222,4))+list(range(-23254,-23238,4))
 pointers={int.from_bytes(ram[a4+x:a4+x+4],'big'):x for x in offsets}
 rows=[]
 for i in range(n):
  x,y,sprite,mask,phase=struct.unpack_from('>hhIIh',chip,a+2+14*i)
  assert sprite in pointers and mask in pointers,'unknown windscreen asset pointer'
  rows.append([x,y,pointers[sprite],pointers[mask],phase])
 return rows

def compare(a,b,require_rng=True):
 ma,aa=load(a);mb,bb=load(b)
 assert hashlib.sha256((a/'slave.slave').read_bytes()).digest()==hashlib.sha256((b/'slave.slave').read_bytes()).digest(),'different builds'
 assert {k:v for k,v in ma['options'].items() if k!='C4'}=={k:v for k,v in mb['options'].items() if k!='C4'} and ma['options']['C2']==1
 assert ma['options']['C4'] in (0,1) and mb['options']['C4'] in (0,1)
 assert {x['period'] for x in aa.values()}=={x['period'] for x in bb.values()}
 assert set(aa)==set(bb),'elapsed fields differ'
 keys=KEYS+['background_phase','lamp_phase']
 for key in keys:assert all(key in x for x in list(aa.values())+list(bb.values())),key
 first={k:next((i for i in sorted(aa) if aa[i][k]!=bb[i][k]),None) for k in keys}
 pa=private((a/'end/code.bin').read_bytes());pb=private((b/'end/code.bin').read_bytes())
 assert 0<=pa['rng_count']==pb['rng_count']<=256
 if require_rng:assert pa['rng_count']>0,'nonempty gameplay RNG evidence required'
 result=dict(fields=len(aa),first_difference=first,rng_equal=pa['rng_log']==pb['rng_log'],rng_log=pa['rng_log'],windscreen_equal=wind(a,ma)==wind(b,mb),windscreen=wind(a,ma),renderer_frames=[list(aa.values())[-1]['frames']-list(aa.values())[0]['frames'],list(bb.values())[-1]['frames']-list(bb.values())[0]['frames']])
 result['drawing_snapshots']={'saved_x_first_difference':next((i for i in sorted(aa) if aa[i]['saved_x']!=bb[i]['saved_x']),None)}
 result['status']='PASS' if all(x is None for x in first.values()) and result['rng_equal'] and result['windscreen_equal'] else 'FAIL'
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('a',type=Path);p.add_argument('b',type=Path);args=p.parse_args()
 r=compare(args.a,args.b);print(json.dumps(r,indent=2));assert r['status']=='PASS','simulation/phase comparison failed'
