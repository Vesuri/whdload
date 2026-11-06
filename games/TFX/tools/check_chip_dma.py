import sys,struct,collections,json
from pathlib import Path
import replay_flight
from amigaxdev import barto
root=Path(sys.argv[1]);out=[]
for p in sorted(root.glob('swap-*.trace')):
 t=barto.load(p);counts=collections.Counter();bounds={}
 for f in t.fields:
  assert f.dma_size==58
  for off in range(0,len(f.dma),58):
   ty=struct.unpack_from('<h',f.dma,off+29)[0]
   if ty not in (3,4,5,6,7):continue
   addr=struct.unpack_from('<I',f.dma,off+12)[0]
   if addr==0xffffffff:continue
   assert addr<0x200000,(p,ty,hex(addr))
   counts[ty]+=1;bounds[ty]=[min(bounds.get(ty,[addr,addr])[0],addr),max(bounds.get(ty,[addr,addr])[1],addr)]
 out.append(dict(trace=p.name,counts=dict(counts),bounds=bounds));print(p.name,dict(counts))
(root/'dma-checks.json').write_text(json.dumps(out,indent=2))
