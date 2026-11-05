#!/usr/bin/env python3
"""Independent equal-start/equal-time rate comparison with drivetrain feedback."""
import json,sys
from pathlib import Path
from copy import deepcopy
from coupled_vehicle_core import seed,advance,summarize
mode=sys.argv[1] if len(sys.argv)>1 else 'baseline';solver=None
if mode=='fine-contact':from fine_plane_contact_model import solve as solver
else:assert mode=='baseline'
root=Path('tmp/prof');initial,read,param=seed(root/'natural-crest20');b=initial;states={1:deepcopy(b)}
ref={r['tick']:r for r in json.loads((root/'natural-crest20/bridge.json').read_text())['rows']}
for t in range(2,321):
    b,_=advance(b,20,read,param);s=summarize(b)
    assert s['position']+[s['pitch'],s['speed']]==[ref[t][k] for k in ('x','y','z','pitch','speed')],('reference',t)
    states[t]=deepcopy(b)
rows=[]
for t in range(1,319):
    a=deepcopy(states[t]);b=deepcopy(a);before=deepcopy(a)
    # Remaining counters encode elapsed time, unlike gear actuator positions.
    for o in (0xc6,0xcb):b['car'][o]=(5*b['car'][o]+1)//2
    histories=[]
    for hz,value in ((20,a),(50,b)):
        history=[]
        for _ in range(hz//10):
            value,r=advance(value,hz,read,param,solver=solver if hz==50 else None);history.append(dict(**summarize(value),distance=r['engine']['distance'],wheel_branches=[w['branch'] for w in r['contact']['output']['wheels']]))
        histories.append((value,history))
    assert states[t]==before
    a,ha=histories[0];b,hb=histories[1]
    assert a==states[t+2],('native recurrence',t)
    sa,sb=summarize(a),summarize(b)
    error={k:sb[k]-sa[k] for k in ('pitch','speed','target','rpm')};error['position']=[y-x for x,y in zip(sa['position'],sb['position'])]
    rows.append(dict(seed_tick=t,seed_time=t/20,error=error,native=ha,a4000=hb))
summary=dict(cases=len(rows),max_abs_y=max(abs(r['error']['position'][1]) for r in rows),max_abs_z=max(abs(r['error']['position'][2]) for r in rows),max_abs_pitch=max(abs(r['error']['pitch']) for r in rows),max_abs_speed=max(abs(r['error']['speed']) for r in rows))
report=dict(mode=mode,summary=summary,rows=rows,scope='All318 native-seeded100ms windows,2x50ms vs5x20ms. Same physical/engine/gear start and held throttle; remaining timers converted with ceil(5*n/2). Actual contact/engine/distance feedback on both paths. Not a runtime candidate or arbitrary-car/terrain proof.')
(root/('coupled-equal-time'+('' if mode=='baseline' else '-'+mode)+'.json')).write_text(json.dumps(report,indent=2)+'\n');print(summary)
print('worst pitch seed',max(rows,key=lambda r:abs(r['error']['pitch']))['seed_tick'])
