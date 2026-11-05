#!/usr/bin/env python3
"""Full-state checks for fresh file load, playback, and native later-slot seek."""
import json,struct,hashlib
from pathlib import Path
src=Path('tmp/runtime-later-checkpoint');dst=Path('tmp/runtime-later-load')
def sem(root,name):
 m=json.loads((root/'start/anchor.json').read_text());a=m['data_base']+0x7ffe-m['memory_base'];b=(root/(name+'.bin')).read_bytes();v=b[a-0xa80:a-0x620]+b[a+0x228:a+0x22e]
 for tag,n in [(b'4DA4PHYS',152),(b'4DTSTATE',32),(b'4DAUXPHY',192),(b'4DCAM050',8)]:
  p=b.index(tag)+12;assert struct.unpack_from('>H',b,p-2)[0]==n;v+=b[p:p+n]
 assert len(v)==1510;return v
load=lambda n:json.loads((dst/(n+'.json')).read_text())
f=(src/'a4test.rpl').read_bytes();assert (dst/'game/data/a4test.rpl').read_bytes()==f
assert (src/'start/slave.slave').read_bytes()==(dst/'start/slave.slave').read_bytes()
s=load('loaded');assert (s['consumer'],s['imported'],s['recorded_length'],s['active_rate'],s['mode'],s['replay_pause'])==(0,0,1651,50,2,1)
matches=[]
for phase,ticks in [('play',(1500,1550,1600)),('seek',(1550,1600))]:
 for t in ticks:
  x,y=sem(src,'live-'+str(t)),sem(dst,phase+'-'+str(t));assert x==y,(phase,t,[i for i,(a,b) in enumerate(zip(x,y)) if a!=b]);matches.append(dict(phase=phase,tick=t,equal_bytes=1510,sha256=hashlib.sha256(x).hexdigest()))
assert 'RESTORED 1500' in (dst/'seek.log').read_text()
assert sem(dst,'seek-restored')==sem(src,'live-1500')
e=load('seek-end');assert 1600<=e['consumer']<1651 and e['consumer']==e['imported'] and e['replay_pause']==1
assert e['perf_failure']==e['sim_schedule_overflow']==0
report=dict(runtime_sha256=hashlib.sha256((dst/'start/slave.slave').read_bytes()).hexdigest(),file_sha256=hashlib.sha256(f).hexdigest(),input_count=1651,restored_checkpoint=1500,restored_bytes=1510,matches=matches,seek_end=e['consumer'],guest_memory_modified=False,scope='Physical NoWriteCache save; fresh-process native file chooser load; native double playback; native backward seek restores slot1 and reconstructs subsequent inputs. Read-only breakpoints release native Return at seek entry. Solo original car/track; WARP correctness, not capacity or broad handling validation.')
(dst/'validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
