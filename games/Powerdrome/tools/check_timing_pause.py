#!/usr/bin/env python3
"""Verify native pause excludes input/simulation time without losing the logical remainder."""
import argparse
import json
from pathlib import Path
import re
import struct
from timing_report import input_state, samples


def periodic(path):
    data=path.read_bytes()
    rows=[struct.unpack_from('>HH7IHH',data,m.start()+8) for m in re.finditer(b'PDTIME01',data)]
    rows=[r for r in rows if r[0]]
    assert len(rows)==1
    return dict(zip(('started','due','last','phase','loop','ticks','frames','controls','resources','control_left','resource_left'),rows[0]))

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('captures',type=Path,nargs='+')
a=p.parse_args()
for root in a.captures:
    config=json.loads((root/'configuration.json').read_text())
    assert 'CUSTOM5=8' in config['WHD_ARGS']
    initial=input_state(root/'code.bin');final=input_state(root/'final-code.bin')
    pause=final['pause']
    assert pause['active']==0 and pause['entries']==pause['exits']==1
    assert final['produced']==final['consumed']==5 and final['overflow']==0
    log=(root/'swaps-gdb.txt').read_text()
    starts=[int(v) for v in re.findall(r'^PDEVENT (-?\d+) 0xbe12$',log,re.M)]
    ends=[int(v) for v in re.findall(r'^PDEVENT (-?\d+) 0xbef2$',log,re.M)]
    assert len(starts)==len(ends)==1
    start,end=starts[0],ends[0]
    assert pause['fields']==end-start,(pause,start,end)
    for field,offset in re.findall(r'^PDEVENT (-?\d+) (0x[0-9a-f]+)$',log,re.M):
        if int(offset,16) in (0xd058,0xccee):
            assert not start<int(field)<end,'Gameplay ran during native pause'
    rows=samples(root)
    assert all(r['speed']==0 for r in rows if r['field']>=end),'Paused throttle leaked into resumed gameplay'
    before=periodic(root/'code.bin');after=periodic(root/'final-code.bin')
    elapsed=(after['last']-before['last'])&0xffffffff
    ticks,phase=divmod(elapsed+before['phase'],18)
    assert after['phase']==phase and after['ticks']-before['ticks']==ticks,'Logical debt or fractional time was lost'
    assert (final['clock']-initial['clock'])&0xffffffff==(after['controls']-before['controls'])*18,'Unfinished or misaccounted control updates at endpoint'
    print(f'{root.name}: {pause["fields"]} paused PAL fields excluded; five input events; no paused gameplay or leaked throttle; logical remainder retained')
