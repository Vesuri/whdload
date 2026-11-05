import os
from pathlib import Path
from functools import lru_cache
import re,struct,json,sys
l=Path(os.environ.get('LISTING','tmp/build/combat.slave.lst')).read_text(encoding='latin1')
@lru_cache(None)
def s(n):return int(re.search(r'^([0-9A-F]{8}) '+n+'$',l,re.M)[1],16)
folders=[Path(x) for x in sys.argv[1:3]]
max_world=int(os.environ.get('MAX_WORLD','2147483647'))
def selected(p):return not p.name.startswith('world-') or int(p.name.split('-')[1])<=max_world
def history(f):
 m=json.loads((f/'input-events.json').read_text());records={};health=[]
 for p in list(f.glob('input-*-arena.bin'))+list(f.glob('world-*/arena.bin')):
  if not selected(p.parent):continue
  a=p.read_bytes();h=s('RT_HISTORY');q=s('RT_COMMANDS');clock=s('RT_CLOCK')
  values=struct.unpack_from('>II',a,h+8)+struct.unpack_from('>II',a,q+16)+(struct.unpack_from('>H',a,s('RT_SCHEDULER')+22)[0],)
  assert not any(values),(p,values)
  assert int.from_bytes(a[clock+12:clock+16],'big')==0,(p,'dropped clock fields')
  for i in range(128):
   r=a[h+20+40*i:h+60+40*i];field=int.from_bytes(r[:4],'big')-m['epoch']
   if field>0:
    v=r[4:32].hex();assert field not in records or records[field]==v
    records[field]=v
 return m['events'],records
x,y=[history(f) for f in folders];assert x[0]==y[0];common=sorted(x[1].keys()&y[1].keys());inputdiff=[k for k in common if x[1][k]!=y[1][k]]
worlds=sorted(int(p.name.split('-')[1]) for p in folders[0].glob('world-*') if p.is_dir() and selected(p));rows=[]
for w in worlds:
 states=[];details=[]
 for f in folders:
  d=f/f'world-{w}';h0=(d/'h0.bin').read_bytes();h4=(d/'h4.bin').read_bytes();h6=(d/'h6.bin').read_bytes();a=(d/'arena.bin').read_bytes()
  states.append(dict(player_objects=h6[0x3b88:0x3e5e],actors=h0[0xc6a0:0xc762],masks=h0[0xba08:0xba10],rng=h4[0x3cc:0x3d0],mission=(d/'mission.bin').read_bytes()[:0x94],alive=(d/'alive.bin').read_bytes(),generations=a[s('RT_ACTOR_GENERATIONS'):s('RT_ACTOR_GENERATIONS')+24],countermeasures=h6[0x42e8:0x42ea]))
  details.append(dict(mask=h0[0xba08:0xba0c].hex(),types=h0[0xc6d6:0xc6dc].hex(),lifetimes=h0[0xc6d0:0xc6d6].hex()))
 diffs={k:[i for i,(a,b) in enumerate(zip(states[0][k],states[1][k])) if a!=b] for k in states[0]}
 rows.append(dict(world=w,differences=diffs,slots=details))
result=dict(common_input_fields=len(common),different_input_fields=inputdiff,worlds=rows,scope='Raw actor differences retained, including field countdowns and rendering scratch; no blanket exclusion.')
(Path(os.environ.get('REPORT_DIR',str(folders[1])))/'launch-comparison.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
assert not inputdiff
assert all(not offsets for row in rows for k,offsets in row['differences'].items() if k!='actors')
