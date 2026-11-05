"""Measure completion against native hunk-2 fields, not logical clock fields."""
from pathlib import Path
from functools import lru_cache
import os,re,json,sys
listing=Path(os.environ['LISTING']).read_text(encoding='latin1')
@lru_cache(None)
def s(n):return int(re.search(r'^([0-9A-F]{8}) '+n+'$',listing,re.M)[1],16)
for name in sys.argv[1:]:
 p=Path(name);rows=[]
 for d in sorted(p.glob('world-*'),key=lambda x:int(x.name.split('-')[1])):
  if not d.is_dir():continue
  w=int(d.name.split('-')[1]);a=(d/'arena.bin').read_bytes();h=(d/'h2.bin').read_bytes();q=s('RT_CLOCK');native=int.from_bytes(h[28:32],'big');logical=int.from_bytes(a[q:q+4],'big');rate=int.from_bytes(a[q+22:q+24],'big')
  rows.append(dict(world=w,native=native,logical=logical,completion_lag=(native-logical)&0xffffffff,rate=rate,rebases=int.from_bytes(a[q+16:q+20],'big')))
 assert len(rows)>1 and len({r['rate'] for r in rows})==1
 windows={}
 for width in [10,30,60]:
  v=[]
  for i in range(len(rows)-width):
   x,y=rows[i],rows[i+width];assert y['world']-x['world']==width
   elapsed=(y['native']-x['native'])&0xffffffff;assert elapsed>0
   v.append(width*rate/elapsed)
  if v:windows[str(width)]=dict(count=len(v),min_hz=min(v),max_hz=max(v))
 elapsed=(rows[-1]['native']-rows[0]['native'])&0xffffffff
 result=dict(rows=rows,native_fields=elapsed,observed_world_rate=(rows[-1]['world']-rows[0]['world'])*rate/elapsed,min_lag=min(x['completion_lag'] for x in rows),max_lag=max(x['completion_lag'] for x in rows),rebases_in_window=rows[-1]['rebases']-rows[0]['rebases'],rolling_windows=windows,scope='Actual native-field timestamps at world completion; finite-window evidence, no rate/latency acceptance implied.')
 (p/'actual-rate.json').write_text(json.dumps(result,indent=2)+'\n');print(name,{k:v for k,v in result.items() if k not in ['rows','scope']})
