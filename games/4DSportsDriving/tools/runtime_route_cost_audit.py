#!/usr/bin/env python3
"""Reproduce native route choice from read-only captures and resource bytes."""
from pathlib import Path
import json,struct,re,hashlib
root=Path(__file__).resolve().parents[1];p=root/'tmp/runtime-route-read';m=json.loads((p/'start/anchor.json').read_text());a=m['data_base']+0x7ffe-m['memory_base']
r=(root/'tmp/game/4DSportsDriving_v1.2_1461/4DSportsDriving/data/opp6.res').read_bytes();n=int.from_bytes(r[4:6],'big');header=6+8*n
resources={r[6+4*i:10+4*i].decode():struct.unpack_from('>I',r,6+4*n+4*i)[0] for i in range(n)}
assert resources['sped']-resources['path']==186 and resources['winn']-resources['sped']==16
rows={}
for label in ('first','second'):
 fast=(p/(label+'-resource.bin')).read_bytes();chip=(p/(label+'-chip.bin')).read_bytes();log=(p/(label+'-load.log')).read_text();a5=int(re.search(r'^a5\s+0x([0-9a-f]+)',log,re.M)[1],16)
 speed,path,base=struct.unpack_from('>III',fast,a5-0xf26-m['memory_base'])
 assert chip[base:base+len(r)]==r
 assert (path,speed)==(base+header+resources['path'],base+header+resources['sped'])
 reads=[tuple(map(int,z)) for z in re.findall(r'^COST (\d+) (\d+) (\d+) (\d+)',(p/(label+'-costs.log')).read_text(),re.M)]
 assert reads and all(ptr==speed and chip[ptr+index]==value for _,index,ptr,value in reads)
 def block(off,count):
  address=struct.unpack_from('>I',fast,a+off)[0]-m['memory_base'];return fast[address:address+count]
 primary=struct.unpack('>901h',block(-0x17ac,1802));secondary=struct.unpack('>901h',block(-0x17a8,1802));tiles=block(-0x176c,901)
 def choose(costs):
  stack=[(0,[],0)];candidates=[];sequence=[]
  while stack:
   i,route,total=stack.pop();assert 0<=i<901
   nxt=primary[i];valid=nxt==0;terminal=nxt in (0,-1) or i in route
   route=route+[i];total+=costs[tiles[i]]+1;sequence.append((i,tiles[i],costs[tiles[i]]))
   if terminal:
    if valid:candidates.append((total,route))
    continue
   if secondary[i]!=-1:stack.append((secondary[i],route,total))
   stack.append((nxt,route,total))
   assert len(sequence)<5000
  best=min(candidates,key=lambda x:x[0]);return best,candidates,sequence
 best,candidates,sequence=choose(chip[speed:speed+256])
 assert sequence==[(i,index,value) for i,index,_,value in reads]
 after=(p/(label+'-route.bin')).read_bytes();off=struct.unpack_from('>I',after,a-0x17a4)[0]-m['memory_base'];words=list(struct.unpack_from('>901H',after,off));expected=best[1]+[0,0,1]
 assert words[:len(expected)]==expected,(label,words[:len(expected)],expected)
 corrected,_,_=choose(chip[path:path+186])
 rows[label]={'resource_base':base,'resource_bytes':len(r),'speed_table':speed,'path_table':path,'cost_reads':len(reads),'outside_speed_table':sum(index>=16 for _,index,_,_ in reads),'outside_resource':sum(ptr+index>=base+len(r) for _,index,ptr,_ in reads),'max_piece_id':max(index for _,index,_,_ in reads),'route_costs':[(cost,len(route),route[:12]) for cost,route in candidates],'chosen_route':best[1],'correct_path_table_route':corrected[1],'all_native_reads_and_output_reproduced':True}
assert rows['first']['chosen_route']!=rows['second']['chosen_route']
assert rows['first']['correct_path_table_route']==rows['second']['correct_path_table_route']
report={'resource_sha256':hashlib.sha256(r).hexdigest(),'resource_layout':{'header':header,'path_bytes':186,'speed_bytes':16},'runs':rows,'conclusion':'Original native route selection uses sped instead of path. Identical resources at different allocations produce different out-of-resource cost reads; exact native read sequence, candidate costs and chosen route reproduced for both loads. Correct table predicts same route for both; no production fix yet.'}
(p/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:{key:value for key,value in v.items() if key not in ('chosen_route','correct_path_table_route')} for k,v in rows.items()},indent=2))
