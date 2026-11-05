#!/usr/bin/env python3
"""Verify native Countach replay loading after a Ferrari race; read-only evidence."""
import hashlib,json
from pathlib import Path
src=Path('tmp/runtime-later-checkpoint');dst=Path('tmp/runtime-resource-load')
def memory(root,name):
 b=(root/(name+'.bin')).read_bytes();m=json.loads((root/'start/anchor.json').read_text());return b,m['data_base']+0x7ffe-m['memory_base']
def semantic(root,name):
 b,a=memory(root,name);v=b[a-0xa80:a-0x620]+b[a+0x228:a+0x22e]
 for tag,n in [(b'4DA4PHYS',152),(b'4DTSTATE',32),(b'4DAUXPHY',192),(b'4DCAM050',8)]:
  p=b.index(tag)+12;v+=b[p:p+n]
 assert len(v)==1510
 return v
before,a=memory(dst,'ferrari-live');loaded,a=memory(dst,'loaded')
f=(src/'a4test.rpl').read_bytes();assert (dst/'game/data/a4test.rpl').read_bytes()==f
assert before[a-0x1750:a-0x174c]==b'fgto'
assert loaded[a-0x1750:a-0x1736]==f[36:62]
assert loaded[a-0x1750:a-0x174c]==b'coun'
s=json.loads((dst/'loaded.json').read_text())
assert (s['consumer'],s['imported'],s['recorded_length'],s['active_rate'],s['mode'],s['replay_pause'])==(0,0,1651,50,2,1)
matches=[]
for t in (1500,1550,1600):
 x,y=semantic(src,'live-'+str(t)),semantic(dst,'play-'+str(t));assert x==y,t
 matches.append(dict(tick=t,bytes=1510,sha256=hashlib.sha256(x).hexdigest()))
e=json.loads((dst/'record-end.json').read_text());assert e['perf_failure']==e['sim_schedule_overflow']==0
report=dict(runtime_sha256=hashlib.sha256((dst/'start/slave.slave').read_bytes()).hexdigest(),file_sha256=hashlib.sha256(f).hexdigest(),prior_car='fgto',loaded_car='coun',matches=matches,guest_memory_modified=False,scope='Native car selector Ferrari GTO race, native file chooser Countach replay load, native double playback. Exact semantic playback in this solo stock-track case; does not prove every graphical resource or car combination. Red car panel illustration also appears with unmodified v1.2 and active Countach (original-replay-panel/validation.json); not evidence of a resource regression. No capacity claim.')
(dst/'validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
