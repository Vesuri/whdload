#!/usr/bin/env python3
"""Same native20 initial states,100ms at10/20/50Hz, genuine independent feedback.

Remaining timers are converted to equal physical time (ceil(rate*n/20)). Future
native10 cooldown literal5/10/30 remains original, despite its different physical
duration; gear shift duration uses rate+rate/2. This is a diagnostic, not a new
acceptance envelope, runtime mode switch, reference substitution or interpolation.
"""
import json
from copy import deepcopy
from pathlib import Path
from coupled_vehicle_core import seed,advance,summarize
root=Path('tmp/prof');b,read,param=seed(root/'natural-crest20');states={1:deepcopy(b)}
for t in range(2,321):
    b,_=advance(b,20,read,param);states[t]=deepcopy(b)
rows=[]
for tick in range(1,319):
    outcomes={}
    for hz in (10,20,50):
        b=deepcopy(states[tick])
        for o in (0xc6,0xcb):b['car'][o]=(hz*b['car'][o]+19)//20
        for _ in range(hz//10):b,_=advance(b,hz,read,param)
        outcomes[str(hz)]=summarize(b)
        if hz==20:assert b==states[tick+2]
    errors={};native=outcomes['20']
    for hz in ('10','50'):
        s=outcomes[hz]
        errors[hz]={k:s[k]-native[k] for k in ('pitch','speed','target','rpm')}
        errors[hz]['position']=[x-y for x,y in zip(s['position'],native['position'])]
    rows.append(dict(seed_tick=tick,outcomes=outcomes,errors=errors))
summary={hz:dict(cases=len(rows),max_y=max(abs(r['errors'][hz]['position'][1]) for r in rows),max_z=max(abs(r['errors'][hz]['position'][2]) for r in rows),max_pitch=max(abs(r['errors'][hz]['pitch']) for r in rows),max_speed=max(abs(r['errors'][hz]['speed']) for r in rows)) for hz in ('10','50')}
report=dict(scope=__doc__,summary=summary,rows=rows)
(root/'coupled-three-rate-comparison.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(summary,indent=2))
for tick in (261,310):print(json.dumps(rows[tick-1]))
