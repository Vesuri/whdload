#!/usr/bin/env python3
"""Verify native opponent replay loading after an active solo race; read-only evidence."""
import hashlib,json
from pathlib import Path
src=Path('tmp/runtime-opponent-watch');dst=Path('tmp/runtime-opponent-stack-fixed')
def memory(root,name):
 b=(root/(name+'.bin')).read_bytes();m=json.loads((root/'start/anchor.json').read_text());return b,m['data_base']+0x7ffe-m['memory_base']
def semantic(root,name):
 b,a=memory(root,name);v=b[a-0xa80:a-0x620]+b[a+0x228:a+0x22e]
 for tag,n in [(b'4DA4PHYS',152),(b'4DTSTATE',32),(b'4DAUXPHY',192),(b'4DCAM050',8)]:
  p=b.index(tag)+12;v+=b[p:p+n]
 assert len(v)==1510
 return v
before,a=memory(dst,'solo-moving');loaded,a=memory(dst,'loaded')
f=(src/'a4test.rpl').read_bytes();assert (dst/'game/data/a4test.rpl').read_bytes()==f
assert before[a-0x174a]==0
assert loaded[a-0x174a]==6
prior=json.loads((dst/'solo-moving.json').read_text());assert prior['mode']==0 and prior['started']==1 and prior['player']['speed']>0
assert loaded[a-0x1750:a-0x1736]==f[36:62]
assert loaded[a-0x1750:a-0x174c]==b'coun'
s=json.loads((dst/'loaded.json').read_text())
assert (s['consumer'],s['imported'],s['recorded_length'],s['active_rate'],s['mode'],s['replay_pause'])==(0,0,1653,50,2,1)
matches=[]
for t in (1500,1550,1600):
 x,y=semantic(src,'live-'+str(t)),semantic(dst,'play-'+str(t));assert x==y,t
 matches.append(dict(tick=t,bytes=1510,sha256=hashlib.sha256(x).hexdigest()))
e=json.loads((dst/'record-end.json').read_text());assert e['perf_failure']==e['sim_schedule_overflow']==0
report=dict(runtime_sha256=hashlib.sha256((dst/'start/slave.slave').read_bytes()).hexdigest(),file_sha256=hashlib.sha256(f).hexdigest(),prior_opponent=0,loaded_opponent=6,matches=matches,guest_memory_modified=False,scope='Native moving solo50 race; physical ABI9 Countach/Skid Vicious replay loaded through native file chooser; double playback. Exact semantic state compared against the recorded opponent race. This verifies opponent addition, not general resources, capacity or physics handling. Earlier allocator transition fault remains unresolved.')
(dst/'validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
