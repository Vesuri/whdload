#!/usr/bin/env python3
"""Check path partition invariance and expose endpoint-missed contacts."""
import json,struct,collections
from fractions import Fraction as F
from pathlib import Path
from native_query_path import traverse,divided,point_events
from crest_terrain_query import query
root=Path('tmp/prof');reports=[]
for rate,name in ((20,'native20-contact-model'),(50,'contact-prediction-d9')):
 cap=root/name;r=json.loads((cap/'prediction.json').read_text())['records'];meta=json.loads((cap/'anchor.json').read_text());memory=(cap/'memory.bin').read_bytes();car=meta['data_base']+0x7ffe-0x92e-meta['memory_base']
 finals={(v[0],v[1]):v[2:5] for v in r['FINAL']};first=r['ENTRY'][0][0];rows=[];misses=[];isolated=[]
 for row in r['SELECT']:
  t,w=row['tick'],row['wheel'];old=[row['old_world_'+a] for a in 'xyz'];new=[row['world_'+a] for a in 'xyz']
  cached=list(struct.unpack_from('>3h',memory,car+0x74+6*w)) if t==first else [v>>6 for v in finals[t-1,w]]
  spans=traverse(old,new,cached)
  assert spans==divided(old,new,cached,2)==divided(old,new,cached,5),(rate,t,w)
  endpoint=query(new,cached);assert endpoint['clearance']==row['clearance'] and endpoint['plane']==row['plane']
  for at,key in point_events(old,new,cached):
   if at in (0,1):continue
   left=next(k for a,b,k in spans if a<at<=b)
   right=next(k for a,b,k in spans if a<=at<b)
   if key!=left and key!=right:
    isolated.append(dict(tick=t,wheel=w,time=str(at),point_clearance=key[4],left_clearance=left[4],right_clearance=right[4]))
  negative=sum(b-a for a,b,k in spans if k[4]<0);positive=sum(b-a for a,b,k in spans if k[4]>0)
  item=dict(tick=t,wheel=w,endpoint=row['clearance'],negative_fraction=str(negative),positive_fraction=str(positive),intervals=len(spans))
  if negative and row['clearance']>=0:
   item['spans']=[dict(start=str(a),end=str(b),plane=k[0],clearance=k[4]) for a,b,k in spans];misses.append(item)
  rows.append(item)
 reports.append(dict(rate=rate,paths=len(rows),partition_checks=2*len(rows),endpoint_missed_negative=len(misses),isolated_boundary_queries=isolated,max_intervals=max(x['intervals'] for x in rows),misses=misses,rows=rows))
synthetic_old=[493824,229*64+32,9728*64-32]
synthetic_new=[493824,229*64-32,9728*64+32]
synthetic_cached=[7716,230,9727]
synthetic_spans=traverse(synthetic_old,synthetic_new,synthetic_cached)
synthetic_points=point_events(synthetic_old,synthetic_new,synthetic_cached)
assert [(str(a),str(b),k[4]) for a,b,k in synthetic_spans]==[('0','1/2',2),('1/2','1',0)]
assert next(k[4] for t,k in synthetic_points if t==F(1,2))==1
report=dict(synthetic_simultaneous_crossing=dict(left_clearance=2,boundary_clearance=1,right_clearance=0),rates=reports,scope='Exact prescribed LINEAR pre-gravity translated paths, fixed cached coordinates. Fresh map queries and coordinate floors; identical event sequence under2/5 subdivisions. Does not integrate gravity, change body state, apply collisions, or establish a replacement contact law.')
(root/'native-query-path-check.json').write_text(json.dumps(report,indent=2)+'\n')
for r in reports:print({k:v for k,v in r.items() if k not in ('rows','misses','isolated_boundary_queries')},'isolated boundary queries',len(r['isolated_boundary_queries']))
