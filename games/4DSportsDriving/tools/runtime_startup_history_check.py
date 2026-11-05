#!/usr/bin/env python3
"""Verify fresh-start recording bounds and exact replay state after held Enter."""
import json,struct,hashlib
from pathlib import Path
r=Path('tmp/startup-history-fix');m=json.loads((r/'start/anchor.json').read_text());a=m['data_base']+0x7ffe-m['memory_base']
load=lambda n:json.loads((r/(n+'.json')).read_text())
raw=lambda n:(r/(n+'.bin')).read_bytes()
def semantic(b):
    out=b[a-0xa80:a-0x620]+b[a+0x228:a+0x22e]
    for marker,n in [(b'4DA4PHYS',152),(b'4DTSTATE',32),(b'4DAUXPHY',192),(b'4DCAM050',8)]:
        p=b.index(marker)+12;assert struct.unpack_from('>H',b,p-2)[0]==n;out+=b[p:p+n]
    assert len(out)==1510;return out
for name in ('active','record-end','replay-ready'):
    s=load(name);assert s['recorded_length']==s['imported']
s=load('replay-ready');assert s['consumer']==s['imported']==653
z=load('rewind-zero');assert z['consumer']==z['imported']==0 and z['recorded_length']==653
matches=[]
for label,t in [('double-a',200),('double-a',400),('double-b',600)]:
    x,y=semantic(raw('live-'+str(t))),semantic(raw(label+'-'+str(t)));assert x==y
    matches.append(dict(tick=t,bytes=1510,sha256=hashlib.sha256(x).hexdigest()))
x,y=load('double-b-window-end'),load('end-held');assert y['sim_clock_fields']-x['sim_clock_fields']==250
for st in (x,y):assert st['consumer']==st['imported']==st['recorded_length']==653 and st['replay_pause']==1
assert x['sim_schedule_ticks']==y['sim_schedule_ticks']
assert semantic(raw('double-b-window-end'))==semantic(raw('end-held'))
# Native end handling resets event/countdown fields; live Escape is a different
# lifecycle boundary. Equal-tick comparisons above use the same E5F8 checkpoint.
for name in ('active','record-end','rewind-zero','double-a-window-end','double-b-window-end','end-held'):
    st=load(name);assert st['perf_failure']==st['sim_schedule_overflow']==0
report=dict(runtime_sha256=hashlib.sha256((r/'start/slave.slave').read_bytes()).hexdigest(),recorded_end=653,matches=matches,unchanged_end_fields=250,end_equal_bytes=1510,scope='Ordinary runtime native held-Enter startup, recording, rewind and double playback. FULL solo C2=1 private040 PAL WARP1. No guest RAM writes. No new hardware capacity or handling claim.')
(r/'validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
