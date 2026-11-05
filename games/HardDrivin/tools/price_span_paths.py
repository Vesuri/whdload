"""Price solid span boundary candidates from actual native operands before coding."""
import sys,json,collections
from pathlib import Path
import numpy as np
import barto_mmap as barto
out=Path(sys.argv[1]);meta=json.loads((out/'metadata.json').read_text());base=meta['layout']['code_base'];t=barto.load(out/'trace.bin');total=0;cost=collections.Counter();patterns=collections.Counter();counts=collections.Counter()
for f in t.fields:
 assert (f.insn_end-f.insn_off)%76==0
 a=np.frombuffer(t.data,dtype='<u4',count=(f.insn_end-f.insn_off)//4,offset=f.insn_off).reshape(-1,19);pc=a[:,0].astype(np.int64)-base;c=0xffffffff-a[:,1];total+=int(c.sum())
 for name,lo,hi in [('single',0x33b6,0x33d8),('left',0x33e0,0x3404),('right',0x34b0,0x34d2),('interior',0x3410,0x34b0)]:
  cost[name]+=int(c[(pc>=lo)&(pc<hi)].sum());counts[name]+=int(np.count_nonzero(pc==lo))
 for row in a[pc==0x337c]:patterns[tuple(int(row[i]) for i in [5,7,8,9])]+=1
eligible=sum(v for k,v in patterns.items() if all(p in [0,0xffffffff] for p in k))
r=dict(total_cycles=total,cycles=dict(cost),shares_percent={k:100*v/total for k,v in cost.items()},calls=dict(counts),solid_calls=sum(patterns.values()),uniform_calls=eligible,patterns=[dict(planes=[hex(x) for x in k],calls=v) for k,v in patterns.most_common()]);(out/'span-census.json').write_text(json.dumps(r,indent=2)+'\n');print(out.name,{k:v for k,v in r.items() if k!='patterns'},r['patterns'][:10])
