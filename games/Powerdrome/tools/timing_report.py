#!/usr/bin/env python3
"""Summarize read-only timing samples; displacement is observed travel, not a lap metric."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import re
import struct

NAMES = ('field clock loops delta speed resource segment x y z heading damage boost '
         'engine_left engine_right effect effect_delay weather impulse impulse_age '
         'buttons mouse_x mouse_y').split()
SIGNED = {'x', 'y', 'z', 'heading', 'mouse_x', 'mouse_y'}

def samples(root):
    rows=[]
    for line in re.findall(r'^PDTIME (.+)$', (root/'swaps-gdb.txt').read_text(), re.M):
        values=list(map(int,line.split()))
        assert len(values)==len(NAMES)
        row=dict(zip(NAMES,values))
        for key in SIGNED:
            row[key]=(row[key]^0x8000)-0x8000
        rows.append(row)
    assert len(rows)>=2, 'Missing TIMING_STATE=1 samples'
    return rows

def summarize(rows):
    seconds=(rows[-1]['field']-rows[0]['field'])/50
    distances=[math.sqrt(sum((b[k]-a[k])**2 for k in ('x','y','z'))) for a,b in zip(rows,rows[1:])]
    return dict(samples=len(rows),seconds=seconds,updates_per_second=(len(rows)-1)/seconds,
        delta_histogram=dict(sorted(Counter(r['delta'] for r in rows).items())),
        resource_used=rows[0]['resource']-rows[-1]['resource'],
        resource_per_second=(rows[0]['resource']-rows[-1]['resource'])/seconds,
        sampled_displacement=sum(distances),max_sample_displacement=max(distances),
        first=rows[0],last=rows[-1])

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('capture',type=Path)
    a=p.parse_args()
    rows=samples(a.capture)
    result={'configuration':json.loads((a.capture/'configuration.json').read_text()),
            'whole':summarize(rows)}
    for lo,hi in ((0,500),(500,1500)):
        part=[r for r in rows if lo<=r['field']<hi]
        if len(part)>1:result[f'fields_{lo}_{hi}']=summarize(part)
    blocks={}
    for label,filename in (('initial','code.bin'),('final','final-code.bin')):
        data=(a.capture/filename).read_bytes()
        positions=[m.start() for m in re.finditer(b'PDTIME01',data)]
        active=[pos for pos in positions if struct.unpack_from('>H',data,pos+8)[0]]
        if active:
            assert len(active)==1, 'Ambiguous initialized timing state'
            names=('started','due','last','phase','loop','ticks','frames','controls','resources','control_left','resource_left')
            blocks[label]=dict(zip(names,struct.unpack_from('>HH7IHH',data,active[0]+8)))
    if blocks:result['periodic']=blocks
    data=(a.capture/'final-code.bin').read_bytes()
    brake_blocks=[]
    for match in re.finditer(b'PDBRAK0[12]',data):
        pos=match.start()
        active,phase,steps=struct.unpack_from('>HII',data,pos+8)
        if steps:
            block=dict(active=active,phase=phase,steps=steps)
            if match.group().endswith(b'2'):
                block['pending']=struct.unpack_from('>I',data,pos+18)[0]
            brake_blocks.append(block)
    if brake_blocks:
        assert len(brake_blocks)==1,'Ambiguous brake diagnostics'
        result['braking']=brake_blocks[0]
    print(json.dumps(result,indent=2))
