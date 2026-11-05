#!/usr/bin/env python3
"""Analyze bounded residual corrections; no runtime contact law is changed."""
import hashlib,json
from pathlib import Path
from native_contact_response import plane,rotate,vec
P=Path(__file__).resolve().parents[1]/'tmp/prof'

def dot_raw(r,v):
 normal=[0,8192,0] if r['plane']<4 else vec(r,'normal')
 return sum((x-64*o)*n for x,o,n in zip(v,vec(r,'origin'),normal))

def candidates(r,before,limit):
 matrix=[r[f'matrix{i}'] for i in range(9)]
 out=[]
 for amount in range(limit+1):
  push=rotate([0,amount,0],matrix);point=[a+b for a,b in zip(before,push)]
  out.append(dict(amount=amount,push=push,position=point,native_clearance=plane(r,point),raw_dot=dot_raw(r,point)))
 return out

report={}
for name in ('takeoff-early-contact50','penetration-course20'):
 path=P/name/'penetration.json';data=json.loads(path.read_text());events={}
 for r in data['rows']:
  group=events.setdefault((r['tick'],r['wheel']),{})
  assert r['stage'] not in group
  group[r['stage']]=r
 rows=[]
 for (tick,w),stages in events.items():
  if 'PUSH_VECTOR' not in stages:continue
  geometry=stages['ROTATED'];query=stages['REQUERY'];before=vec(query,'new')
  limit=-plane(geometry,before)*64;assert 0<limit<=4096
  values=candidates(geometry,before,limit)
  assert values[-1]['push']==vec(stages['PUSH_VECTOR'],'correction')
  assert values[-1]['position']==vec(stages['RESOLVED'],'new')
  minimal_query=next((v for v in values if v['native_clearance']>=0),None)
  minimal_both=next((v for v in values if v['native_clearance']>=0 and v['raw_dot']>=0),None)
  rows.append(dict(tick=tick,wheel=w,plane=geometry['plane'],native_magnitude=limit,before=values[0],native=values[-1],query_only=minimal_query,query_and_unrounded=minimal_both))
 report[name]=dict(trace_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),pushes=len(rows),rows=rows)
result=dict(captures=report,scope='Exhaustive integer distances along the original rotated normal ray, bounded by the original correction. Two DIFFERENT hypotheses are reported: clear the quantized native query only, or additionally clear the unrounded normal plane. Neither is native semantics nor a validated50Hz replacement. No arbitrary penetration tolerance or fitted coefficient is added. Cases lacking a solution within native distance are reported as unsupported; no fallback is silently accepted.')
(P/'contact-push-reference.json').write_text(json.dumps(result,indent=2)+'\n')
for name,r in report.items():
 print(name,'pushes',r['pushes'],'both_supported',sum(v['query_and_unrounded'] is not None for v in r['rows']))
 for v in r['rows'][:3]:print(v['tick'],v['wheel'],v['native_magnitude'],'query',v['query_only']['amount'] if v['query_only'] else None,'both',v['query_and_unrounded']['amount'] if v['query_and_unrounded'] else None)
