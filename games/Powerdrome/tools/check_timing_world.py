#!/usr/bin/env python3
"""Verify coupled control/movement/world epochs and compare completed world states."""
import argparse
import json
from pathlib import Path
import re
import struct
from coverage_status import fixture
from timing_report import input_state


def state(path):
    data=path.read_bytes()
    hits=[m.start() for m in re.finditer(b'PDWORLD1',data)
          if struct.unpack_from('>I',data,m.start()+20)[0]]
    assert len(hits)==1
    pos=hits[0]
    return dict(active=struct.unpack_from('>H',data,pos+8)[0],
                ticks=struct.unpack_from('>I',data,pos+20)[0])

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('captures',type=Path,nargs='+')
a=p.parse_args();histories=[]
for root in a.captures:
    initial=state(root/'code.bin');final=state(root/'final-code.bin')
    assert not initial['active'], 'Anchor must be outside an unfinished world update'
    epoch=fixture(root/'code.bin')['epoch']*4
    log=(root/'swaps-gdb.txt').read_text();start=None;rows=[];steps=[]
    for offset,values in re.findall(r'^PDWORLD_EVENT -?\d+ (0x[0-9a-f]+) (.+)$',log,re.M):
        v=list(map(int,values.split()));off=int(offset,16)
        assert v[0]==1, 'World body ran outside an active logical update'
        if off==0xccee:
            assert start is None, 'World movement repeated before completing collisions/opponents'
            start=v
        elif off==0xcde2:
            assert start and v[1:3]==start[1:3] and v[3]==18
        elif off==0xcedc:
            assert start and v[1:3]==start[1:3] and v[3]==18
            steps.append(v[2]);rows.append((v[1]-epoch,*v[3:]));start=None
    assert len(rows)>=50
    assert steps==list(range(initial['ticks']+1,initial['ticks']+1+len(steps)))
    assert all(y[0]-x[0]==18 for x,y in zip(rows,rows[1:])), 'World epochs were lost or duplicated'
    assert 0<=final['ticks']-initial['ticks']-len(rows)<=1, 'Unobserved complete world updates'
    # Opponent movement must not inherit an interval sampled by an incident flash.
    opponents=[list(map(int,v.split())) for v in re.findall(r'^PDTIME_EVENT -?\d+ 0xd56c (.+)$',log,re.M)]
    probes=json.loads((root/'configuration.json').read_text()).get('COVERAGE_PROBES') or ''
    if '0xd56c' in probes:assert opponents, 'Requested opponent probes were never reached'
    assert all(v[2]==18 for v in opponents), 'Opponent movement used a presentation delta'
    initial_input=input_state(root/'code.bin');final_input=input_state(root/'final-code.bin')
    controls=(final_input['clock']-initial_input['clock'])&0xffffffff
    assert 0<=(final['ticks']-initial['ticks'])*18-controls<=18, 'World/control accounting diverged'
    histories.append(rows)
    print(f'{root.name}: {len(rows)} consecutive 90-ms control/movement/collision/opponent epochs; {len(opponents)} opponent delta reads checked')
if len(histories)>1:
    length=min(map(len,histories))
    for root,rows in zip(a.captures[1:],histories[1:]):
        mismatch=next(((i,x,y) for i,(x,y) in enumerate(zip(histories[0][:length],rows[:length])) if x!=y),None)
        assert mismatch is None,(root.name,'World state mismatch (index, reference, actual)',mismatch)
    print(f'{length} common world states match: speed, segment, position, damage, temperatures and sampled RNG state')
