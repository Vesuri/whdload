#!/usr/bin/env python3
"""Attribute local rate differences to wheel displacement and suspension lift."""
import json
from copy import deepcopy
from pathlib import Path
from coupled_vehicle_core import seed,advance,summarize
from native_contact_response import rotate
root=Path('tmp/prof')
b,read,param=seed(root/'natural-crest20')
for t in range(2,262):b,_=advance(b,20,read,param)
initial=deepcopy(b);traces={}
for hz in (20,50):
    b=deepcopy(initial)
    if hz==50:
        for o in (0xc6,0xcb):b['car'][o]=(5*b['car'][o]+1)//2
    rows=[]
    for i in range(1,hz//10+1):
        before=summarize(b);b,rec=advance(b,hz,read,param)
        c=rec['contact'];e=c['entry'];out=c['output'];wheels=[]
        for w,(s,end,su) in enumerate(zip(c['selected'],out['wheels'],out['suspensions'])):
            old=[s['old_world_'+a] for a in 'xyz'];new=[s['world_'+a] for a in 'xyz']
            restore=rotate([0,384+e[13+w],0],e[4:13]);lift=rotate([0,384+su['returned'],0],e[4:13])
            start=[x+y for x,y in zip(old,restore)];final=[x+y for x,y in zip(end['position'],lift)]
            wheels.append(dict(wheel=w,pre_clearance=s['clearance'],post_gravity_clearance=end['suspension_clearance'],branch=end['branch'],gravity=end['down'],velocity_before=e[21+w],velocity_after=end['velocity'],extension_before=e[13+w],extension_after=su['extension'],suspension_return=su['returned'],translation=[n-o for o,n in zip(old,new)],response=[n-o for o,n in zip(new,end['position'])],lift_change=[n-o for o,n in zip(restore,lift)],basis_change=[n-o for o,n in zip(start,final)]))
        rows.append(dict(ms=i*1000//hz,before=before,after=summarize(b),distance=rec['engine']['distance'],wheels=wheels))
    traces[str(hz)]=rows
report=dict(seed_tick=261,seed_time=13.05,traces=traces,scope='Read-only offline baseline diagnostic from identical native20 seed; no modified physics or acceptance claim.')
(root/'coupled-landing-attribution.json').write_text(json.dumps(report,indent=2)+'\n')
for hz,rows in traces.items():
    print('HZ',hz)
    for r in rows:
        print(r['ms'],'pitch',r['before']['pitch'],'->',r['after']['pitch'],'distance',r['distance'])
        for w in (0,2):
            q=r['wheels'][w]
            print({k:q[k] for k in ('wheel','pre_clearance','post_gravity_clearance','branch','gravity','velocity_before','extension_before','extension_after','suspension_return','response','lift_change','basis_change')})
