from pathlib import Path
from functools import lru_cache
import json,re,sys
r=Path(sys.argv[1]);l=Path(sys.argv[2]).read_text(encoding='latin1')
@lru_cache(None)
def sy(n):return int(re.search(r'^([0-9A-F]{8}) '+n+'$',l,re.M)[1],16)
frames=json.loads((r/'frames.json').read_text());byworld={}
for f in frames:byworld.setdefault(f['world'],f)
rows=[]
for f in frames:
 nxt=byworld.get(f['world']+1)
 if not nxt:continue
 d=r/f"frame-{f['frame']:03d}";a=(d/'arena.bin').read_bytes();h=(d/'h0.bin').read_bytes();n=(r/f"frame-{nxt['frame']:03d}"/'h0.bin').read_bytes();rf=sy('RT_FORECAST')
 mask=int.from_bytes(a[rf+sy('RF_PRESENT_SAFE'):rf+sy('RF_PRESENT_SAFE')+2],'big')
 for slot in range(6):
  if not mask&(1<<slot) or h[0xc6d6+slot]&0x98!=0x80:continue
  predicted=[int.from_bytes(a[rf+sy('RF_ACTOR_NEXT')+12*axis+2*slot:rf+sy('RF_ACTOR_NEXT')+12*axis+2*slot+2],'big') for axis in range(3)]
  actual=[int.from_bytes(n[0xc6a0+12*axis+2*slot:0xc6a0+12*axis+2*slot+2],'big') for axis in range(3)]
  delta=[((x-y+32768)&65535)-32768 for x,y in zip(predicted,actual)]
  rows.append(dict(frame=f['frame'],world=f['world'],slot=slot,predicted=predicted,actual=actual,delta=delta))
report=dict(run=r.name,comparisons=len(rows),exact=sum(not any(x['delta']) for x in rows),mismatches=[x for x in rows if any(x['delta'])],rows=rows)
(r/'live-forecast-endpoint-audit.json').write_text(json.dumps(report,indent=2)+'\n');print({k:v for k,v in report.items() if k!='rows'})
