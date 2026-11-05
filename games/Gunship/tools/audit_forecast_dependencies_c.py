import os
from pathlib import Path
from functools import lru_cache
import re,struct,json,sys
p=Path(sys.argv[1]);l=Path(os.environ.get('LISTING','tmp/build/combat.slave.lst')).read_text(encoding='latin1')
@lru_cache(None)
def s(n):return int(re.search(r'^([0-9A-F]{8}) '+n+'$',l,re.M)[1],16)
worlds=sorted(int(d.name.split('-')[1]) for d in p.glob('world-*') if d.is_dir());checked=0;mismatches=[];captures=[];last=None;transitions=[]
for w in worlds:
 d=p/f'world-{w}';a=(d/'arena.bin').read_bytes();h=(d/'h0.bin').read_bytes();c=s('RT_ACTOR_PRESENT');g=a[s('RT_ACTOR_GENERATIONS'):s('RT_ACTOR_GENERATIONS')+24]
 assert a[c+s('AC_VALID'):c+s('AC_VALID')+2]==b'\0\1'
 assert int.from_bytes(a[c+s('AC_TICK'):c+s('AC_TICK')+4],'big')==w
 assert a[c+s('AC_GENERATIONS'):c+s('AC_GENERATIONS')+24]==g
 assert a[c+s('AC_CURRENT'):c+s('AC_CURRENT')+36]==h[0xc6a0:0xc6c4]
 mask=int.from_bytes(h[0xba08:0xba0a],'big');safe=int.from_bytes(a[c+s('AC_SAFE'):c+s('AC_SAFE')+2],'big')
 state=(mask,h[0xc6d6:0xc6dc].hex(),g.hex())
 if state!=last:transitions.append(dict(world=w,mask=mask,types=state[1],generations=state[2]));last=state
 if w+1 not in worlds:continue
 nxt=p/f'world-{w+1}';na=(nxt/'arena.bin').read_bytes();nh=(nxt/'h0.bin').read_bytes();ng=na[s('RT_ACTOR_GENERATIONS'):s('RT_ACTOR_GENERATIONS')+24];nm=int.from_bytes(nh[0xba08:0xba0a],'big')
 for slot in range(6):
  if not(safe&nm&(1<<slot)) or g[4*slot:4*slot+4]!=ng[4*slot:4*slot+4]:continue
  expected=[nh[0xc6a0+12*axis+slot*2:0xc6a2+12*axis+slot*2] for axis in range(3)]
  actual=[a[c+s('AC_NEXT')+12*axis+slot*2:c+s('AC_NEXT')+12*axis+slot*2+2] for axis in range(3)]
  if actual!=expected:mismatches.append(dict(world=w,slot=slot,predicted=[v.hex() for v in actual],native=[v.hex() for v in expected],selector_before=h[0xaa0a:0xaa16].hex(),selector_after=nh[0xaa0a:0xaa16].hex()))
  checked+=1
r=dict(mismatches=mismatches,world_captures=len(worlds),candidate_next_poses=checked,matching_next_poses=checked-len(mismatches),transitions=transitions,scope='Live post-world forecast cache, not a claim about rendered scanout.')
(p/'actor-forecast-dependency-audit.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
