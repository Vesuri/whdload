#!/usr/bin/env python3
"""Check observed native weather mutations and report measured transition cadence.

Missing event families remain explicit. This report alone does not establish a
complete episode, A500 calibration acceptance, or corrected timing equivalence.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
from weather_state import FIELDS, PROBES, parse_values

# Before/after instruction boundaries, expected mutated field(s).
PAIRS = {
    0xe1d4: (0xe1ca, 'forecast_deadline', lambda b: (b['d7']+5000)&0xffffffff),
    0xe242: (0xe23c, 'd0', lambda b: (b['d0']+b['clock'])&0xffffffff),
    0xe246: (0xe242, 'active_deadline', lambda b: b['d0']),
    0xbd36: (0xbd32, 'transition', lambda b: (b['transition']-1)&0xffff),
    0xbd4c: (0xbd48, 'transition', lambda b: (b['transition']+1)&0xffff),
    0x112f0: (0x112e6, 'effect_lifetime', lambda b: (b['effect_lifetime']-1)&0xffff),
    0x112fa: (0x112f4, 'palette_active', lambda b: 0xffff),
    0xbd1a: (0xbd16, 'effect_delay', lambda b: b['d0']&0xffff),
}


def report(root):
    events=[]
    for field,off,values in re.findall(r'^PDWEATHER_EVENT (-?\d+) (0x[0-9a-f]+) (.+)$',
                                      (root/'swaps-gdb.txt').read_text(),re.M):
        off=int(off,16)
        assert off in PROBES, 'Unknown weather probe'
        state=parse_values(values)
        for name,_,_,width in FIELDS:
            assert 0<=state[name]<1<<(width*8), (name,'out of range')
        events.append((int(field),off,state))
    assert events, 'No runtime weather observations'
    assert all(a[0]<=b[0] for a,b in zip(events,events[1:])), 'Observation order changed'
    alignment={s['vbl']-field for field,_,s in events}
    assert len(alignment)==1, 'Guest/debugger field alignment changed'
    pending={};counts=Counter();transitions=[]
    starts={v[0] for v in PAIRS.values()} | {0xe278}
    for field,off,s in events:
        if off in starts: pending[off]=(field,s)
        if off in PAIRS:
            before,key,expected=PAIRS[off]
            if before not in pending: continue # capture may begin inside a mutation
            oldfield,b=pending.pop(before)
            assert s[key]==expected(b),(hex(off),key,b[key],s[key],expected(b))
            if off in (0xbd36,0xbd4c):
                assert b['loop']&15==0, 'Native fade escaped its 16-counter gate'
                assert (0<b['transition']<0x8000) if off==0xbd36 else (b['transition']>=0x8000)
                transitions.append(dict(field=oldfield,vbl=b['vbl'],clock=b['clock'],
                                        loop=b['loop'],before=b['transition'],after=s['transition']))
            if off==0x112f0: assert b['effect_lifetime']>0
            counts[f'{before:x}->{off:x}']+=1
        if off==0xe294 and 0xe278 in pending:
            pending.pop(0xe278)
            assert (s['transition'],s['active_deadline'],s['forecast_deadline'],s['effects_enabled'])==(0xfff1,0xffffffff,0xffffffff,0)
            counts['e278->e294']+=1
    probes=Counter(off for _,off,_ in events)
    return dict(capture=root.name,scope='Observed native mutations only; missing families are not passes',
                events=len(events),guest_field_offset=alignment.pop(),
                probe_counts={f'{off:x}':probes[off] for off in PROBES},
                checked_pairs=dict(counts),transition_steps=transitions,
                unpaired_before_boundaries=[f'{off:x}' for off in sorted(pending)])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('capture',type=Path)
    print(json.dumps(report(p.parse_args().capture),indent=2))
