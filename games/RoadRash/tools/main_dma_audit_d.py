import sys,json,struct,collections
from pathlib import Path
from drive import barto
trace=barto.load('tmp/c-actor-memory-audit/actor-dma.bin');by=collections.defaultdict(set);counts=collections.Counter()
for f in trace.fields:
 assert f.dma_size==58
 for i in range(0,len(f.dma),58):
  addr=struct.unpack_from('<I',f.dma,i+12)[0];kind=struct.unpack_from('<h',f.dma,i+29)[0]
  if 0x80000<=addr<0xc14f4 and kind not in [0,2]:by[kind].add(addr);counts[kind]+=1
def ranges(values):
 out=[]
 for x in sorted(values):
  if out and x<=out[-1][1]+2:out[-1][1]=max(out[-1][1],x)
  else:out.append([x,x])
 return [[hex(a),hex(b+2)] for a,b in out]
r=dict(fields=len(trace.fields),counts=dict(counts),ranges={k:ranges(v) for k,v in by.items()});Path('tmp/d-original-hunk/race-dma.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
