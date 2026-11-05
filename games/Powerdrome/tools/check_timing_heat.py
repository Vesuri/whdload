#!/usr/bin/env python3
"""Check isolated boost RNG arithmetic and matched-seed engine histories."""
import argparse
from pathlib import Path
import re
import struct
from coverage_status import fixture


def heat_state(path):
    data=path.read_bytes()
    positions=[m.start() for m in re.finditer(b'PDHEAT02',data)
               if struct.unpack_from('>H',data,m.start()+8)[0]==1]
    assert len(positions)==1, 'Expected one isolated heat RNG state'
    return struct.unpack_from('>HH2xI',data,positions[0]+10)


p=argparse.ArgumentParser(description=__doc__)
p.add_argument('captures',type=Path,nargs='+')
p.add_argument('--compare-engine',action='store_true')
a=p.parse_args();sequences=[];histories=[];seeds=[]
for root in a.captures:
    initial,seed,calls=heat_state(root/'code.bin')
    seeds.append(initial)
    epoch=fixture(root/'code.bin')['epoch']*4
    log=(root/'swaps-gdb.txt').read_text()
    rows=[]
    for offset,values in re.findall(r'^PDHEAT_EVENT -?\d+ (0x[0-9a-f]+) (.+)$',log,re.M):
        clock,count,observed,result,left,right=map(int,values.split())
        seed=(seed*0x7ab7+1)&65535
        expected=((seed&32767)*10)>>15
        calls+=1
        assert count==calls and observed==seed and result==expected,(root.name,count,calls,observed,seed,result,expected)
        assert int(offset,16)==(0xcfec if calls%2 else 0xcff8), 'Expected left then right heat draws'
        rows.append((clock-epoch,seed,result))
    final_initial,final_seed,final_calls=heat_state(root/'final-code.bin')
    assert final_initial==initial and final_seed==seed and final_calls==calls, 'Unobserved RNG call or reset'
    assert len(rows)>=20, 'Insufficient boost coverage'
    sequences.append(rows)
    engines=[]
    for values in re.findall(r'^PDENGINE_EVENT -?\d+ 0xdffc (.+)$',log,re.M):
        values=list(map(int,values.split()))
        if values[2]:
            # clock, cooling phase, temperatures, damage, target and engine state.
            engines.append((values[0]-epoch,values[1]%4,*values[8:13]))
    assert len(engines)>=50
    histories.append(engines)
    print(f'{root.name}: {len(rows)} consecutive boost draws match native RNG arithmetic; seed {initial}; no missed draws')
if len(sequences)>1:
    assert len(set(seeds))==1, 'Cross-CPU comparison requires identical initial heat seeds'
    errors=[]
    length=min(map(len,sequences))
    for capture,rows in zip(a.captures[1:],sequences[1:]):
        mismatch=next(((i,x,y) for i,(x,y) in enumerate(zip(sequences[0][:length],rows[:length])) if x!=y),None)
        if mismatch:errors.append(f'{capture.name}: heat consumption mismatch (index, reference, actual): {mismatch}')
    if not errors:print(f'{length} common boost draws match across captures, including logical timestamps')
    if a.compare_engine:
        length=min(map(len,histories));engine_errors=[]
        for capture,rows in zip(a.captures[1:],histories[1:]):
            mismatch=next(((i,x,y) for i,(x,y) in enumerate(zip(histories[0][:length],rows[:length])) if x!=y),None)
            if mismatch:engine_errors.append(f'{capture.name}: engine state mismatch (index, reference, actual): {mismatch}')
        if not engine_errors:print(f'{length} common logical engine temperature/damage/target/propulsion states match exactly')
        errors+=engine_errors
    assert not errors, '\n'.join(errors)
