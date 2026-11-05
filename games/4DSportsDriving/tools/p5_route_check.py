import json,struct,re,sys,hashlib
from pathlib import Path
p=Path(sys.argv[1]);m=json.loads((p/'anchor.json').read_text());b=(p/'memory.bin').read_bytes();a=m['data_base']+0x7ffe-m['memory_base'];s={n:int(v,16) for n,v in re.findall(r'^(\w+)\s+00:([0-9A-Fa-f]+)\s*$',(p/'slave.lst').read_text(encoding='latin1'),re.M)};base=m['slave_base']-m['memory_base']
rate=struct.unpack_from('>H',b,a-0x15fa)[0];prepared=struct.unpack_from('>I',b,base+s['sim_opponent_route_prepared'])[0];costs=b[base+s['sim_opponent_route_costs']:base+s['sim_opponent_route_costs']+256]
if rate!=50:
 assert prepared==0 and not any(costs)
 report=dict(rate=rate,prepared=prepared,private_table_untouched=True)
else:
 assert prepared>0 and costs[:16]==b[a+0x210:a+0x220] and not any(costs[16:])
 def block(off,count):
  ptr=struct.unpack_from('>I',b,a+off)[0]-m['memory_base'];assert 0<=ptr<len(b)-count;return b[ptr:ptr+count]
 primary=struct.unpack('>901h',block(-0x17ac,1802));secondary=struct.unpack('>901h',block(-0x17a8,1802));tiles=block(-0x176c,901)
 stack=[(0,[],0)];candidates=[];reads=[]
 while stack:
  i,route,total=stack.pop();assert 0<=i<901
  nxt=primary[i];valid=nxt==0;terminal=nxt in (0,-1) or i in route
  route=route+[i];total+=costs[tiles[i]]+1;reads.append(tiles[i])
  if terminal:
   if valid:candidates.append((total,route))
   continue
  if secondary[i]!=-1:stack.append((secondary[i],route,total))
  stack.append((nxt,route,total));assert len(reads)<5000
 best=min(candidates,key=lambda x:x[0]);expected=best[1]+[0,0,1];actual=list(struct.unpack('>901H',block(-0x17a4,1802)));assert actual[:len(expected)]==expected,(best,actual[:len(expected)])
 report=dict(rate=rate,opponent=b[a-0x174a],prepared=prepared,cost_table_sha256=hashlib.sha256(costs).hexdigest(),defined_cost_bytes=16,zero_initialized_bytes=240,cost_reads=len(reads),formerly_out_of_bounds_reads=sum(i>=16 for i in reads),route=expected,candidate_costs=[x[0] for x in candidates],route_matches_model=True)
(p/'route-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
