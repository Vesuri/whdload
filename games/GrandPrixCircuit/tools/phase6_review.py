#!/usr/bin/env python3
"""Evaluate declared Phase 6 handling/event bounds on retained captures."""
import json,sys
from pathlib import Path
from phase3_decode import decode
root=Path(sys.argv[1]); mode=sys.argv[2]
def rows(name):
 p=root/name;m=json.loads((p/'metadata.json').read_text())
 rs=[decode(f.read_bytes(),m) for f in sorted((p/'state').glob('[0-9]*.bin'))]
 assert len({v['native_field'] for v in rs})==len(rs)
 return rs
def gears(rs):return [(v['native_field'],v['gear']) for i,v in enumerate(rs) if not i or v['gear']!=rs[i-1]['gear']]
result={}
if mode=='handling':
 a,b=rows('matrix-v5-p6'),rows('matrix-v5-p2')
 result['short']={'distance_error':abs(a[-1]['distance_q8']-b[-1]['distance_q8'])/256,'gear_fields':[gears(a),gears(b)],'clock_fields_equal':all(x['lap_ticks']==y['lap_ticks'] and x['race_tick_counter']==y['race_tick_counter'] for x,y in zip(a,b))}
 assert result['short']['distance_error']<=1
 assert gears(a)==gears(b) and result['short']['clock_fields_equal']
 assert all(v['condition']==320 for v in a+b)
 a,b=rows('matrix-v5-traffic-p6'),rows('matrix-v5-traffic-p2')
 initial=['segment','fraction','lateral','speed','gear','condition','rng','opponents','race_running']+[f'AI_{n}_{i}' for i in range(10) for n in ('segment','fraction','speed','lateral','cooldown','position_pointer')]
 assert all(a[0][k]==b[0][k] for k in initial)
 result['traffic']=[]
 for i in range(10):
  p,f,l=[f'AI_{n}_{i}' for n in ('segment','fraction','lateral')]
  err=max(abs((x[p]-y[p])*256+x[f]-y[f])/256 for x,y in zip(a,b))
  assert err<=11.84,(i,err)
  result['traffic'].append({'slot':i,'max_position_error':err,'lane_difference_fields':sum(x[l]!=y[l] for x,y in zip(a,b)),'final_lanes':[a[-1][l],b[-1][l]]})
 assert not json.loads((root/'matrix-v5-native-oracle.json').read_text())['differences']
elif mode=='events':
 for event in ('overheat','crash','spin','pause','neutral','pit','offroad'):
  names=[f'events-v5-{event}-{p}' for p in ('p6','p2')]
  a,b=map(rows,names);r={}
  if event in ('overheat','crash','spin','neutral'):
   sa,sb=[next(v for v in rs if v['native_field']>=180 and v['speed']==0) for rs in (a,b)]
   r={'stop_fields':[sa['native_field'],sb['native_field']],'stop_distance_error':abs(sa['distance_q8']-sb['distance_q8'])/256}
   assert abs(sa['native_field']-sb['native_field'])<=6 and r['stop_distance_error']<=1
  if event=='spin':
   r['spin_fields']=[sum(v['spin']!=0 for v in rs) for rs in (a,b)]
   assert r['spin_fields'][0]==r['spin_fields'][1] and r['spin_fields'][0]>0
  if event=='pause':
   paused=[[v['native_field'] for v in rs if v['pause']] for rs in (a,b)]
   assert paused[0]==paused[1] and len(paused[0])==60
   r={'pause_fields':[paused[0][0],paused[0][-1]],'count':len(paused[0])}
  if event=='pit':
   markers=[json.loads((root/n/'state/events.json').read_text()) for n in names]
   times=[json.loads((root/n/'state/pit-time.json').read_text()) for n in names]
   # Native service duration is the acceptance invariant. The unchanged
   # return path draws the race screen at $7240 before unpausing at $7250;
   # do not confuse that presentation latency with service/physics time.
   service=[[x for x in ms if x[1]!='7250'] for ms in markers]
   returns=[[int(x[0]) for x in ms if x[1]=='7250'] for ms in markers]
   assert service[0]==service[1] and {x[1] for x in service[0]}=={'5f62','61e2','66e8','66fc'}
   assert all(len(x)==1 for x in returns)
   resumed=[[v for v in rs if v['native_field']>ret[0]+1 and v['pause']==0] for rs,ret in zip((a,b),returns)]
   resume_keys=('active_fields','lap_ticks','race_tick_counter','condition','speed','gear','lateral','pit_eligible','race_running')
   assert min(map(len,resumed))>=200
   assert all(x[k]==y[k] for x,y in zip(*resumed) for k in resume_keys)
   assert times[0]==times[1] and int(times[0][0][1])==52
   for rs in (a,b):assert rs[-1]['pause']==0 and rs[-1]['pit_eligible']==0 and rs[-1]['condition']==240 and rs[-1]['race_running']==1
   assert a[-1]['lap_ticks']==b[-1]['lap_ticks']
   r={'native_markers':markers,'elapsed_fields_div_six':times[0],'final_condition':240,'resumed_clock':a[-1]['lap_ticks'],'return_field_delta':returns[1][0]-returns[0][0],'matched_active_time_samples':min(map(len,resumed)),'active_time_keys':resume_keys}
  if event=='offroad':
   r={'final_conditions':[a[-1]['condition'],b[-1]['condition']],'damage_markers':[sum(x[1]=='7fce' for x in json.loads((root/n/'state/events.json').read_text())) for n in names]}
   assert r['final_conditions']==[317,317] and r['damage_markers']==[3,3]
  result[event]=r
else:raise ValueError(mode)
result['pass']=True
(root/('final-'+mode+'.json')).write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
