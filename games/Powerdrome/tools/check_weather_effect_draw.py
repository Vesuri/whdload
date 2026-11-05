#!/usr/bin/env python3
"""Verify owned effect draws install/replay visual RNG and restore the outer seed.

This checks observed draws, not logical-generation arithmetic, visual pixels, or
whole-game timing. Initial/final partial draws are reported explicitly.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
from report_weather import advance_seed
from weather_effect_state import NAMES, snapshot, parse_values


def check(root):
    first=snapshot(root)
    config=json.loads((root/'configuration.json').read_text())
    before=None;stage=None;completed=0;replays=Counter()
    if first['drawing']:
        assert int(config['ANCHOR'],0)==0x112f0
        before=first;stage='body'
        assert before['visible']>0 and before['rng']==before['visual_seed']
    events=[(int(f),int(off,16),parse_values(values)) for f,off,values in re.findall(
        r'^PDWEFX_EVENT (-?\d+) (0x[0-9a-f]+) (.+)$',
        (root/'swaps-gdb.txt').read_text(),re.M)]
    assert events, 'Missing experimental effect observations'
    assert all(a[0]<=b[0] for a,b in zip(events,events[1:]))
    for field,off,s in events:
        if off==0x112f0:
            assert before is None, 'Previous effect did not restore its seed'
            assert s['drawing']==1 and s['visible']>0, 'Observed native fallback instead of owned effect'
            assert s['rng']==s['visual_seed'], 'Draw did not install published visual seed'
            before=s;stage='body'
        elif off==0x112f4:
            assert stage=='body' and before is not None, 'Missing draw-entry observation'
            assert all(s[k]==before[k] for k in NAMES), 'Effect helper changed logical publication/ownership'
            assert all(s[k]==before[k] for k in ('lifetime','delay','enabled','transition','palette'))
            assert s['rng']==advance_seed(before['visual_seed'],4), 'Wrong native visual RNG advance'
            stage='restore'
        elif off==0x112fa:
            assert stage=='restore' and before is not None, 'Missing draw-exit observation'
            assert s['drawing']==0 and s['rng']==before['saved_seed'], 'Outer RNG was not restored'
            assert all(s[k]==before[k] for k in NAMES if k!='drawing')
            assert all(s[k]==before[k] for k in ('lifetime','delay','enabled','transition'))
            assert s['palette']==0xffff
            replays[(s['clock'],s['visual_seed'],s['visible'])]+=1
            completed+=1;before=None;stage=None
    last=snapshot(root,True)
    assert completed>0, 'No complete owned effect draws'
    if before is None:
        assert last['drawing']==0, 'Unobserved draw owns the final seed'
    else:
        assert last['drawing']==1, 'Unobserved end of partial draw'
        assert last['saved_seed']==before['saved_seed'] and last['visual_seed']==before['visual_seed']
    repeated=sum(n-1 for n in replays.values())
    print(f'{root.name}: {completed} complete owned draws; four RNG advances per draw; outer seed/lifetime restored and publication unchanged')
    print(f'  {repeated} repeated draws of the same logical visual state; final partial draw={stage or "none"}')
    print('  Draw ownership only; logical generation, cleanup, pixels and full weather timing require separate checks.')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('capture',type=Path)
    check(p.parse_args().capture)
