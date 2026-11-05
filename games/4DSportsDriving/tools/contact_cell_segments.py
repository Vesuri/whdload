#!/usr/bin/env python3
"""Partition measured wheel segments at every native64-unit coordinate cell."""
from fractions import Fraction as F
from pathlib import Path
import json
p=Path('tmp/prof')
def w(x):return (x+32768)%65536-32768
def trunc(x,n):return (abs(x)//n)*(1 if x>=0 else -1)
def clearance(r,v):
 d=[w(w(x//64)-r['base_'+a]-r['node_'+a]) for a,x in zip('xyz',v)]
 return d[1] if r['plane']<4 else w(trunc(sum(x*r['normal_'+a] for a,x in zip('xyz',d)),8192))
def partition(r):
 old=[r['old_world_'+a] for a in 'xyz'];new=[r['world_'+a] for a in 'xyz'];cuts={F(0),F(1)}
 for a,b in zip(old,new):
  if a==b:continue
  for cell in range(min(a,b)//64,max(a,b)//64+2):
   t=F(64*cell-a,b-a)
   if 0<t<1:cuts.add(t)
 cuts=sorted(cuts);intervals=[]
 for left,right in zip(cuts,cuts[1:]):
  t=(left+right)/2;v=[F(a)+(b-a)*t for a,b in zip(old,new)];c=clearance(r,v)
  # Quantized coordinates must be constant throughout the open interval.
  for q in ((3*left+right)/4,(left+3*right)/4):
   assert [x//64 for x in v]==[(F(a)+(b-a)*q)//64 for a,b in zip(old,new)]
  intervals.append((left,right,c))
 assert clearance(r,list(map(F,new)))==r['clearance']
 return intervals
report={}
for name in ('release-step50','release-second-step50'):
 data=json.loads((p/name/'takeoff-plane.json').read_text());selected=[r for r in data['rows'] if r['event']=='SELECT'];previous={};out=[]
 for r in selected:
  same=r['wheel'] in previous and previous[r['wheel']]['plane']==r['plane'] and all(previous[r['wheel']][k]==r[k] for k in ('base_x','base_y','base_z','node_x','node_y','node_z','normal_x','normal_y','normal_z'))
  previous[r['wheel']]=r
  if not same or r['correction']!=0:continue
  intervals=partition(r);positive=sum((b-a for a,b,c in intervals if c>0),F(0));switches=sum((a[2]>0)!=(b[2]>0) for a,b in zip(intervals,intervals[1:]));tail=F(0)
  for a,b,c in reversed(intervals):
   if c<=0:break
   tail+=b-a
  out.append(dict(tick=r['tick'],wheel=r['wheel'],plane=r['plane'],endpoint_clearance=r['clearance'],cells=len(intervals),switches=switches,positive_fraction=str(positive),positive_ms=float(20*positive),final_positive_ms=float(20*tail),intervals=[dict(start=str(a),end=str(b),clearance=c) for a,b,c in intervals]))
 report[name]=out
result=dict(captures=report,scope='Exact partition of RECORDED linear segments under the selected native quantized plane predicate, restricted to unchanged plane coefficients and zero correction branch. Endpoint predictions match live clearances and each open cell interval is constant. No gravity/collision feedback, terrain polygon topology test, contact resolution, or runtime acceptance. Internal positive intervals occur even when the endpoint skips gravity; patching only positive endpoints would omit them.')
(p/'contact-cell-segments.json').write_text(json.dumps(result,indent=2)+'\n')
for name,rows in report.items():
 print(name,'segments',len(rows),'with repeated transitions',sum(r['switches']>1 for r in rows),'endpoint nonpositive but interior positive',sum(r['endpoint_clearance']<=0 and F(r['positive_fraction'])>0 for r in rows))
 for r in rows:
  if name=='release-second-step50' and r['wheel'] in (0,2) and r['tick']<=707:print({k:v for k,v in r.items() if k!='intervals'})
