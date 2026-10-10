#!/usr/bin/env python3
"""Compare native departure geometry and A500-paced timing from read-only captures."""
import argparse
import json
from pathlib import Path
import re
from timing_report import samples, NAMES, SIGNED

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('reference',type=Path)
p.add_argument('captures',type=Path,nargs='+')
p.add_argument('--period-fields',type=int,default=5)
a=p.parse_args()
keys=('loops','speed','resource','segment','x','y','z','heading','damage')
reference=samples(a.reference)
assert len(reference)==9,'Reference must contain all nine native departure steps'
geometry=[[r[k] for k in keys] for r in reference]
for root in a.captures:
    config=json.loads((root/'configuration.json').read_text())
    assert config['ANCHOR']=='0x1020e' and config['SWAP_MARKER']=='0x102d0'
    rows=samples(root)
    assert [[r[k] for k in keys] for r in rows]==geometry,f'{root}: departure state sequence differs'
    text=(root/'swaps-gdb.txt').read_text()
    returns=[int(f) for f in re.findall(r'^PDEVENT (-?\d+) 0x10336$',text,re.M)]
    assert len(returns)==1,'Need one departure return probe'
    fields=[r['field'] for r in rows]+returns
    intervals=[b-a for a,b in zip(fields,fields[1:])]
    assert intervals==[a.period_fields]*9,f'{root}: unexpected step fields {intervals}'
    final=re.findall(r'^PDTIME_EVENT (-?\d+) 0x10336 (.+)$',text,re.M)
    if final:
        assert len(final)==1
        values=[int(final[0][0])]+list(map(int,final[0][1].split()))
        assert len(values)==len(NAMES)
        state=dict(zip(NAMES,values))
        for key in SIGNED:state[key]=(state[key]^0x8000)-0x8000
        assert state['speed']==90
        for key in ('x','y'):
            assert state[key]-rows[-1][key]==rows[-1][key]-rows[-2][key]
        assert state['z']-rows[-1]['z']==rows[-1]['z']-rows[-2]['z']+37
    print(f'{root.name}: nine identical native states; {a.period_fields*20} ms per step; {(fields[-1]-fields[0])*20} ms to return; final state '+('checked' if final else 'not sampled'))
