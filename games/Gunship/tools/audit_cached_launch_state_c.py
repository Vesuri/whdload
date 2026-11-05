from pathlib import Path
from functools import lru_cache
import os,re,struct,json,sys
l=Path(os.environ['LISTING']).read_text(encoding='latin1')
@lru_cache(None)
def s(n):return int(re.search(r'^([0-9A-F]{8}) '+n+'$',l,re.M)[1],16)
x,y=[Path(v) for v in sys.argv[1:3]];j=json.loads((Path(os.environ.get('REPORT_DIR',str(y)))/'launch-comparison.json').read_text());rows=[];epochs=[json.loads((p/'input-events.json').read_text())['epoch'] for p in [x,y]]
for r in j['worlds']:
 w=r['world'];assert all(not v for k,v in r['differences'].items() if k!='actors'),r
 h=[(p/f'world-{w}/h0.bin').read_bytes() for p in [x,y]]
 for off in r['differences']['actors']:
  address=0xc6a0+off
  if 0xc724<=address<=0xc729:
   slot=address-0xc724
   assert all(not (b[0xc6d6+slot]&1) for b in h),(w,'active animation countdown',slot)
  else:assert address==0xc732,(w,hex(address))
 fields=[]
 for p,e in zip([x,y],epochs):
  a=(p/f'world-{w}/arena.bin').read_bytes();clock=s('RT_CLOCK');hist=s('RT_HISTORY');sched=s('RT_SCHEDULER');rate=int.from_bytes(a[clock+22:clock+24],'big')
  last,total,ticks,dropped=struct.unpack_from('>4I',a,clock)
  assert rate in [50,60] and last-e==total==(w*rate+2)//3 and ticks==w and dropped==0,(p,w,last,total,ticks,dropped,e)
  assert struct.unpack_from('>II',a,hist+8)==(0,0)
  assert int.from_bytes(a[sched+22:sched+24],'big')==0
  assert int.from_bytes(a[sched+36:sched+40],'big')==w-1
  fields.append(total)
 assert fields[0]==fields[1]
 assert h[0][0xc6d5]==h[1][0xc6d5]==max(64-w,0),(w,'lifetime')
 rows.append(w)
report=dict(worlds=rows,authoritative_state_equal=True,actor_exceptions='Only inactive animation countdowns and native drawing scratch C732 differ',clock_deadlines_exact=True,no_history_or_clock_loss=True,rocket_release_world=64 if 64 in rows else None)
(Path(os.environ.get('REPORT_DIR',str(y)))/'cached-state-audit.json').write_text(json.dumps(report,indent=2)+'\n');print({**report,'worlds':len(rows)})
