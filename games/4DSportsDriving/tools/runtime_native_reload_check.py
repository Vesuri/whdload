#!/usr/bin/env python3
"""Compare native-menu fresh-process reload with its original live recording."""
import json,struct,hashlib
from pathlib import Path
src=Path('tmp/runtime-save-nowritecache');dst=Path('tmp/runtime-load-native-rpl')
def semantic(root,name):
 m=json.loads((root/'start/anchor.json').read_text());a=m['data_base']+0x7ffe-m['memory_base'];b=(root/(name+'.bin')).read_bytes();out=b[a-0xa80:a-0x620]+b[a+0x228:a+0x22e]
 for marker,n in [(b'4DA4PHYS',152),(b'4DTSTATE',32),(b'4DAUXPHY',192),(b'4DCAM050',8)]:
  p=b.index(marker)+12;assert struct.unpack_from('>H',b,p-2)[0]==n;out+=b[p:p+n]
 assert len(out)==1510;return out
load=lambda n:json.loads((dst/(n+'.json')).read_text())
fileinfo=json.loads((src/'file-validation.json').read_text());count=fileinfo['input_count'];s=load('loaded');assert (s['consumer'],s['imported'],s['recorded_length'],s['active_rate'],s['mode'])==(0,0,count,50,2)
matches=[]
for label,t in [('loaded-a',200),('loaded-a',400),('loaded-b',600)]:
 x,y=semantic(src,'live-'+str(t)),semantic(dst,label+'-'+str(t));diff=[i for i,(a,b)in enumerate(zip(x,y))if a!=b];assert not diff,(t,diff)
 matches.append(dict(tick=t,equal_bytes=1510,sha256=hashlib.sha256(x).hexdigest()))
x,y=load('loaded-b-window-end'),load('end-held');assert y['sim_clock_fields']-x['sim_clock_fields']==250
assert x['consumer']==y['consumer']==x['imported']==y['imported']==count
assert x['sim_schedule_ticks']==y['sim_schedule_ticks'] and y['replay_pause']==1
assert semantic(dst,'loaded-b-window-end')==semantic(dst,'end-held')
for label in ('loaded-a','loaded-b'):
 d=load(label+'-window');a,b=d['start'],d['end'];assert b['sim_clock_fields']-a['sim_clock_fields']==250;assert [z[1]for z in d['bodies']]==list(range(a['consumer']+1,b['consumer']+1));assert b['perf_failure']==b['sim_schedule_overflow']==0
assert load('loaded-a-window')['published']==500
assert (src/'start/slave.slave').read_bytes()==(dst/'start/slave.slave').read_bytes()
report=dict(runtime_sha256=hashlib.sha256((dst/'start/slave.slave').read_bytes()).hexdigest(),saved_file=fileinfo,matches=matches,loaded_end=count,end_held_fields=250,scope='Native Save Replay filename editor and physical disk write with NoWriteCache, followed by fresh-process native Load Replay file-list selection. Native double playback; no guest RAM writes or fixtures. Same car/track solo FULL C2=1. Default cache flush, errors/overwrite prompts, nonzero checkpoint files and broader presentation/handling/hardware gates remain separate.')
(dst/'validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
