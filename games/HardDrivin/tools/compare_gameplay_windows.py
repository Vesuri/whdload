"""Compare the frozen windows without treating different trajectories as equal work."""
import argparse,json,math,struct
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('off');p.add_argument('on');a=p.parse_args();root=Path(__file__).resolve().parents[1]/'tmp/prof';names=[a.off,a.on];paths=[root/n for n in names]
assert (paths[0]/'slave.slave').read_bytes()==(paths[1]/'slave.slave').read_bytes()
reports=[json.loads((x/'baseline.json').read_text()) for x in paths];result={}
for name,r in zip(names,reports):
 fields={x['field']:x for x in r['per_field']};result[name]={}
 for w,v in r['windows'].items():
  lo,hi=v['first'],v['end'];rows=[fields[f] for f in range(lo,hi)];extra={}
  for kind in ['crash','replay']:
   start=None;intervals=[]
   for row in rows:
    active=int(row[kind],16)!=0
    if active and start is None:start=row['field']
    elif not active and start is not None:intervals.append([start,row['field']]);start=None
   if start is not None:intervals.append([start,hi])
   extra[kind+'_intervals']=intervals;extra[kind+'_fields']=sum(b-a for a,b in intervals)
  result[name][w]=dict(v,**extra,start_pose=list(struct.unpack('>3h',bytes.fromhex(rows[0]['pose'])[6:])),end_pose=list(struct.unpack('>3h',bytes.fromhex(rows[-1]['pose'])[6:])))
result['comparison']={}
for w in reports[0]['windows']:
 old,new=[r['windows'][w] for r in reports];assert old['seconds']==new['seconds']
 result['comparison'][w]=dict(fps_change_percent=100*(new['fps']/old['fps']-1),required_swaps=math.ceil(old['swaps']*.97),observed_swaps=new['swaps'],literal_performance_gate=new['swaps']>=old['swaps']*.97)
result['scope']='Same compiled slave and field-indexed input tape. Different trajectories and event workloads; not an isolated physics-cost comparison or handling acceptance.'
(paths[1]/'window-comparison.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
