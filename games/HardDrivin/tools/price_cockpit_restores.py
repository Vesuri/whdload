import sys,json,collections
from pathlib import Path
import numpy as np
import barto_mmap as barto
p=Path(sys.argv[1]);m=json.loads((p/'metadata.json').read_text());base=m['layout']['code_base'];t=barto.load(p/'trace.bin');starts=[0xea2e,0xea62,0xea86,0xeaaa,0xeace,0xeaf2,0xeb14];active={};cost=collections.Counter();count=collections.Counter();total=0
for f in t.fields:
 a=np.frombuffer(t.data,dtype='<u4',count=(f.insn_end-f.insn_off)//4,offset=f.insn_off).reshape(-1,19);pc=a[:,0].astype(np.int64)-base;c=0xffffffff-a[:,1];prefix=np.cumsum(c,dtype=np.uint64)
 for idx in np.flatnonzero(np.isin(pc,starts+[x+4 for x in starts])):
  at=int(pc[idx]);clock=total+int(prefix[idx])-int(c[idx])
  if at in starts:active[at]=clock
  elif at-4 in active:cost[at-4]+=clock-active.pop(at-4);count[at-4]+=1
 total+=int(c.sum())
r=dict(total_cycles=total,restores=[dict(callsite=hex(k),calls=count[k],cycles=v,share_percent=100*v/total) for k,v in cost.items()],non_large_gauge_upper_percent=100*sum(v for k,v in cost.items() if k not in [0xeace,0xeb14])/total);(p/'cockpit-price.json').write_text(json.dumps(r,indent=2)+'\n');print(p.name,r)
