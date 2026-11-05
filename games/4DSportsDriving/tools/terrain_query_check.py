#!/usr/bin/env python3
"""Validate centre-lane selector including actual cached-coordinate conditions."""
import collections,hashlib,json
from pathlib import Path
from crest_surface_selector_check import select,word,read,a4
from native_contact_response import plane
ROOT=Path(__file__).resolve().parents[1]
cap=ROOT/'tmp/prof/terrain-query-d9-verified'
def main():
 data=json.loads((cap/'terrain-query.json').read_text());records=data['records']
 prior=json.loads((ROOT/'tmp/prof/contact-prediction-d9/prediction.json').read_text())['records']
 entries={r[0]:r for r in prior['ENTRY']}
 failures=[];barriers=collections.Counter();flags=collections.Counter();different_cache=0;nodes={};cache_x_range=[];barrier_events=[]
 for i,(before,after) in enumerate(zip(records['QUERY_IN'],records['QUERY_OUT'])):
  tick,wheel,*coords=before;assert after[:2]==[tick,wheel]
  new,old=coords[:3],coords[3:]
  entry=entries[tick];assert new==[word(v>>6) for v in entry[57+3*wheel:60+3*wheel]]
  rebuilt=[word(v>>6) for v in entry[45+3*wheel:48+3*wheel]]
  different_cache+=old!=rebuilt
  s=select([v*64 for v in new]);orientation=s['orientation']
  lx,lz=word(new[0]-s['base_x']),word(new[2]-s['base_z'])
  ox,oz=word(old[0]-s['base_x']),word(old[2]-s['base_z'])
  if orientation==512:lx,lz,ox,oz=map(lambda v:word(-v),(lx,lz,ox,oz))
  assert abs(ox)<120 and abs(lx)<120,(tick,wheel,ox,lx)
  cache_x_range.append(ox)
  barrier=-1;plane_flags=1
  if s['kind']==16:
   if lz>0:plane_flags=0
   elif oz>=0:barrier=102
  surface=read(a4-0x5b0c+20*s['track']+15,'b')+1
  surface=max(surface,1)
  expected=[s['plane'],s['base_x'],s['base_y'],s['base_z'],barrier,-1000,-12,plane_flags,surface]
  if expected!=after[2:11]:failures.append(dict(tick=tick,wheel=wheel,predicted=expected,actual=after[2:11]))
  barriers[barrier]+=1;flags[plane_flags]+=1
  plane_id=s['plane'];node=after[11:];assert len(node)==17
  if plane_id in nodes:assert nodes[plane_id]==node,(plane_id,tick)
  else:nodes[plane_id]=node
  geometry=dict(plane=plane_id)
  for j,axis in enumerate('xyz'):
   geometry['origin_'+axis]=word(s['base_'+axis]+node[2+j])
   geometry['normal_'+axis]=node[5+j]
  clearance=plane(geometry,[v*64 for v in new])
  actual_select=prior['SELECT'][i]
  assert clearance==actual_select['clearance'],(tick,wheel,clearance,actual_select['clearance'])
  if barrier>=0:
   response=-1000<clearance<-12
   barrier_events.append(dict(tick=tick,wheel=wheel,barrier=barrier,clearance=clearance,response=response))
 report=dict(queries=len(records['QUERY_IN']),matching_full_states=data['matching_full_states'],
  different_cached_vs_rebuilt= different_cache,cached_local_x_range=[min(cache_x_range),max(cache_x_range)],
  barrier_events=barrier_events,barriers=dict(barriers),plane_flags=dict(flags),constant_nodes=nodes,failures=failures,
  trace_sha256=hashlib.sha256((cap/'terrain-query.json').read_bytes()).hexdigest(),
  scope='Read-only centre-lane native selector including real cached XYZ and barrier/flag conditions. Nodes observed constant per independently selected plane, not independently decoded from game assets. Changed-motion validation still required.')
 (ROOT/'tmp/prof/terrain-query-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));assert not failures
if __name__=='__main__':main()
