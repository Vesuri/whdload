from pathlib import Path
from functools import lru_cache
import re,json,sys
r=Path(sys.argv[1]);l=Path(sys.argv[2]).read_text(encoding='latin1')
@lru_cache(None)
def sy(n):return int(re.search(r'^([0-9A-F]{8}) '+n+'$',l,re.M)[1],16)
rate=60 if json.loads((r/'provenance.json').read_text()).get('ntsc')=='1' else 50
rows=[];frames=json.loads((r/'frames.json').read_text())
for f in frames:
 d=r/f"frame-{f['frame']:03d}";a=(d/'arena.bin').read_bytes();h=(d/'h0.bin').read_bytes();rf=sy('RT_FORECAST')
 def w(off):return int.from_bytes(a[off:off+2],'big')
 def q(off):return int.from_bytes(a[off:off+4],'big')
 v={n:q(rf+sy('RF_'+n)) for n in ('ATTEMPTS','ACCEPTED','REJECTED')}
 v.update(frame=f['frame'],world=f['world'],safe=w(rf+sy('RF_PRESENT_SAFE')),clock_dropped=q(sy('RT_CLOCK')+12),faults=[w(sy('RT_'+b)+sy(pre+'_FAULT')) for b,pre in [('CLOCK','TC'),('SCHEDULER','TS'),('HISTORY','TH'),('COMMANDS','CQ')]])
 v['history_lost']=q(sy('RT_HISTORY')+sy('TH_LOST'));v['history_discarded']=q(sy('RT_HISTORY')+sy('TH_DISCARDED'));v['command_lost']=q(sy('RT_COMMANDS')+sy('CQ_LOST'));v['command_discarded']=q(sy('RT_COMMANDS')+sy('CQ_DISCARDED'))
 assert not any(v[k] for k in ('history_lost','history_discarded','command_lost','command_discarded')),v
 assert not v['clock_dropped'] and not any(v['faults']),v
 assert v['ATTEMPTS']==v['ACCEPTED']+v['REJECTED'],v
 eligible=int.from_bytes(h[0xba08:0xba0a],'big')&int.from_bytes(h[0xba0c:0xba0e],'big')
 published=[]
 for slot in range(6):
  if eligible&(1<<slot) and h[0xc6d6+slot]&0x98==0x80 and v['safe']&(1<<slot):
   assert all(a[sy('RT_ACTOR_COORDS')+12*axis+2*slot:sy('RT_ACTOR_COORDS')+12*axis+2*slot+2]==a[rf+sy('RF_PRESENT_COORDS')+12*axis+2*slot:rf+sy('RF_PRESENT_COORDS')+12*axis+2*slot+2] for axis in range(3))
   published.append(slot)
 v['published_slots']=published;rows.append(v)
report=dict(frames=len(rows),first=rows[0],last=rows[-1],published_frames=sum(bool(x['published_slots']) for x in rows),sampled_faults=0,observed_draws_per_second=(len(frames)-1)*rate/(frames[-1]['native_field']-frames[0]['native_field']),rows=rows)
(r/'forecast-live-audit.json').write_text(json.dumps(report,indent=2)+'\n');print({k:v for k,v in report.items() if k!='rows'})
