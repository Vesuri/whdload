from pathlib import Path
from functools import lru_cache
import re,struct,json,sys
p=Path(sys.argv[1]);l=Path('tmp/build/reuse.slave.lst').read_text(encoding='latin1')
@lru_cache(None)
def s(n):return int(re.search(r'^([0-9A-F]{8}) '+n+'$',l,re.M)[1],16)
def u16(b,o):return struct.unpack_from('>H',b,o)[0]
def u32(b,o):return struct.unpack_from('>I',b,o)[0]
rows=[]
for d in sorted(p.glob('draw-*')):
 a=(d/'arena.bin').read_bytes();h=(d/'actors.bin').read_bytes();c=s('RT_ACTOR_PRESENT');clock=s('RT_CLOCK');tick=u32(a,clock+8);phase=u16(a,clock+20);rate=u16(a,clock+22);cp=u16(a,c+s('AC_PHASE'))
 assert u32(a,s('RT_ACTOR_GENERATIONS')+20)==2
 assert u32(a,c+s('AC_GENERATIONS')+20)==2 and u32(a,c+s('AC_TICK'))==tick
 assert u16(a,c+s('AC_SAFE'))&32
 assert (phase-cp)%3==0
 elapsed=(phase-cp)//3;interval=(rate-cp+2)//3;assert 0<=elapsed<interval
 expected=[];current=[];shown=[]
 for axis in range(3):
  off=axis*12+10;cur=u16(h,off);assert cur==u16(a,c+s('AC_CURRENT')+off)
  nxt=u16(a,c+s('AC_NEXT')+off);delta=((nxt-cur+32768)%65536)-32768
  want=(cur+delta*elapsed//interval)&65535;actual=u16(a,s('RT_ACTOR_COORDS')+off)
  assert actual==want,(d,tick,phase,axis,actual,want)
  assert u16(a,s('RT_PRESENT_SCENE')+12+off)==want
  current.append(cur);expected.append(want);shown.append(actual)
 rows.append(dict(tick=tick,phase=phase,elapsed_fields=elapsed,interval_fields=interval,committed=current,presented=shown,generation=2))
assert rows and any(r['committed']!=r['presented'] for r in rows)
r=dict(frames=len(rows),worlds=sorted(set(r['tick'] for r in rows)),rows=rows,scope='Inputs at original draw entry; no pixel/scanout claim.')
(p/'reuse-draw-comparison.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(frames=len(rows),worlds=r['worlds'],advanced_frames=sum(r['committed']!=r['presented'] for r in rows)),indent=2))
