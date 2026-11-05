import json,sys,collections
from pathlib import Path
import numpy as np
import barto_mmap as barto
out=Path(sys.argv[1]);m=json.loads((out/'metadata.json').read_text());base=m['layout']['code_base'];t=barto.load(out/'trace.bin');total=0;cost=collections.Counter();cnt=collections.Counter();patterns=collections.Counter();bg=[];active={};detail=collections.defaultdict(list)
marks={0x3a28:('bg',1),0x3aaa:('bg',0),0xe9e2:('cockpit_restore',1),0xeb20:('cockpit_restore',0)}
for f in t.fields:
 a=np.frombuffer(t.data,dtype='<u4',count=(f.insn_end-f.insn_off)//4,offset=f.insn_off).reshape(-1,19);pc=a[:,0].astype(np.int64)-base;c=0xffffffff-a[:,1];prefix=np.cumsum(c,dtype=np.uint64)
 for name,l,h in [('background',0x3a28,0x3aac),('bgstores',0x3a84,0x3a98),('edges',0x2da2,0x2de6),('cockpit_setup',0xe9e2,0xeb22),('projection',0x2b74,0x2bde),('face',0x2bde,0x2c4c)]: cost[name]+=int(c[(pc>=l)&(pc<h)].sum())
 for idx in np.flatnonzero(np.isin(pc,list(marks))):
  key,begin=marks[int(pc[idx])];clock=total+int(prefix[idx])-int(c[idx])
  if begin:active[key]=clock
  elif key in active: detail[key].append(clock-active.pop(key)+int(c[idx]))
 for r in a[pc==0x3a76]: patterns[(int(r[4]),int(r[7]&65535)+1)]+=1
 total+=int(c.sum())
r=dict(total_cycles=total,direct_percent={k:100*v/total for k,v in cost.items()},inclusive={k:dict(calls=len(v),cycles=sum(v),share_percent=100*sum(v)/total,cycles_per_call=sum(v)/len(v)) for k,v in detail.items()},background_planes=[dict(pattern=hex(p),rows=n,calls=v) for (p,n),v in patterns.items()]);(out/'remaining-price.json').write_text(json.dumps(r,indent=2)+'\n');print(out.name,json.dumps(r))
