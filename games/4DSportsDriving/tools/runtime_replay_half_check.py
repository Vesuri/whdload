#!/usr/bin/env python3
"""Verify explicitly selected half-speed runtime replay (not a UI test)."""
import json,struct,hashlib
from pathlib import Path
r=Path('tmp/replay-half-runtime-67');m=json.loads((r/'start/anchor.json').read_text());a=m['data_base']+0x7ffe-m['memory_base']
read=lambda n:(r/(n+'.bin')).read_bytes()
b,c=read('selector-before'),read('selector-after');assert [i for i,(x,y) in enumerate(zip(b,c)) if x!=y]==[a+0x3d];assert (b[a+0x3d],c[a+0x3d])==(0,2)
def semantic(b):
    parts=[b[a-0xa80:a-0x620],b[a+0x228:a+0x22e]]
    for marker,n in [(b'4DA4PHYS',152),(b'4DTSTATE',32),(b'4DAUXPHY',192),(b'4DCAM050',8)]:
        p=b.index(marker)+12;assert struct.unpack_from('>H',b,p-2)[0]==n;parts.append(b[p:p+n])
    out=b''.join(parts);assert len(out)==1510;return out
windows=[];previous=None
for label in ('half-a','half-b'):
    d=json.loads((r/(label+'-window.json')).read_text());x,y=d['start'],d['end']
    assert y['sim_clock_fields']-x['sim_clock_fields']==250
    assert y['sim_schedule_ticks']-x['sim_schedule_ticks']==125
    assert [v[1] for v in d['bodies']]==list(range(x['consumer']+1,y['consumer']+1))
    assert len(d['bodies'])==125
    for st in (x,y):
        assert st['replay_speed']==2 and st['mode']==2 and st['replay_pause']==0
        assert st['active_rate']==st['recorded_rate']==50
        assert st['perf_failure']==st['sim_schedule_overflow']==0
    if previous is not None:assert previous==x
    previous=y;windows.append(dict(fields=250,published=125,completed=125,first_tick=x['consumer']+1,last_tick=y['consumer']))
live=semantic(read('live-200'));replay=semantic(read('half-b-200'));assert live==replay
report=dict(runtime_sha256=hashlib.sha256((r/'start/slave.slave').read_bytes()).hexdigest(),windows=windows,equal_tick=200,equal_bytes=1510,state_sha256=hashlib.sha256(live).hexdigest(),diagnostic_changed_bytes=1,scope='Current ordinary runtime FULL solo C2=1 private040/PAL WARP1. Native record/rewind/play; debugger changed only speed byte0->2. Not half-speed UI, hardware capacity, disk replay, or handling acceptance.')
(r/'validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
