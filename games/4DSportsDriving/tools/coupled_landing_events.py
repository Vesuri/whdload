#!/usr/bin/env python3
"""Separate same-state landing event phase from persistent trajectory error."""
import json,struct
from pathlib import Path
from copy import deepcopy
from coupled_vehicle_core import seed,advance,summarize
root=Path('tmp/prof');b,read,param=seed(root/'natural-crest20');seeds={}
for t in range(2,311):
    b,_=advance(b,20,read,param)
    if t in (261,310):seeds[t]=deepcopy(b)
reports=[]
for tick,initial in seeds.items():
    traces={}
    for hz in (20,50):
        b=deepcopy(initial)
        if hz==50:
            for o in (0xc6,0xcb):b['car'][o]=(5*b['car'][o]+1)//2
        rows=[]
        for i in range(1,hz//2+1):
            before=summarize(b);b,record=advance(b,hz,read,param);after=summarize(b)
            rows.append(dict(elapsed=i/hz,**after,gear_changed=after['gear']!=before['gear'],target_changed=after['target']!=before['target'],nominal_acceleration=record['engine']['nominal_acceleration']))
        traces[str(hz)]=rows
    common=[]
    for tenth in range(1,6):
        a=traces['20'][2*tenth-1];b=traces['50'][5*tenth-1]
        common.append(dict(elapsed=tenth/10,position_error=[y-x for x,y in zip(a['position'],b['position'])],**{k+'_error':b[k]-a[k] for k in ('pitch','speed','target','rpm')}))
    events={hz:dict(first_rear_contact=next((r['elapsed'] for r in rows if any(r['flags'][2:])),None),first_target_change=next((r['elapsed'] for r in rows if r['target_changed']),None),first_gear_change=next((r['elapsed'] for r in rows if r['gear_changed']),None)) for hz,rows in traces.items()}
    reports.append(dict(seed_tick=tick,seed_time=tick/20,events=events,common=common,traces=traces))
report=dict(cases=reports,scope='Original native20 seed, held input and independent20/50 feedback over500ms. Time conversion of remaining counters as in coupled_equal_time. Describes event-order sensitivity, not acceptance or a proposed delay/retiming fix.')
(root/'coupled-landing-events.json').write_text(json.dumps(report,indent=2)+'\n')
for r in reports:print(json.dumps({k:v for k,v in r.items() if k!='traces'},indent=2))
