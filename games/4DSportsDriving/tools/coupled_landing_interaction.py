#!/usr/bin/env python3
"""Factorial diagnostic of landing direction feedback and suspension rebound.
Both rates receive the same ablations. These trajectories are not candidates or
acceptance references. Unsupported altered contacts are reported, never clamped.
"""
import json,sys
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import contact_body_predictor as model50
import native20_contact_model as model20
from coupled_vehicle_core import seed,advance,summarize
from native_contact_response import sine,UnsupportedContact
r=Path('tmp/prof');phase=sys.argv[1] if len(sys.argv)>1 else 'nominal';assert phase in ('nominal','minus64','plus64')
cap='natural-crest20' if phase=='nominal' else 'phase-'+phase+'-native20'
b,read,param=seed(r/cap);states={1:deepcopy(b)}
bridge={v['tick']:v for v in json.loads((r/cap/'bridge.json').read_text())['rows']}
for t in range(2,321):
    b,_=advance(b,20,read,param);states[t]=deepcopy(b);v=summarize(b)
    assert v['position']+[v['pitch'],v['speed']]==[bridge[t][k] for k in ('x','y','z','pitch','speed')]
reference=json.loads((r/'coupled-three-rate-comparison.json').read_text())['rows']
rows=[];unsupported=[]
for tick in range(1,319):
    pitch=states[tick]['contact']['entry'][2];sn,cs=sine(pitch),sine(pitch+256);matrix=[16384,0,0,0,cs,-sn,0,sn,cs]
    cases={}
    for frozen,no_return in ((False,False),(True,False),(False,True),(True,True)):
        label=f'direction{int(frozen)}-return{int(no_return)}';outcomes={};changed={}
        for hz in (20,50):
            b=deepcopy(states[tick]);module=model20 if hz==20 else model50;original=module.suspension;count=[0]
            for o in (0xc6,0xcb):b['car'][o]=(hz*b['car'][o]+19)//20
            def suspension(extension,bias,clearance,ef,bf):
                s=original(extension,bias,clearance,ef,bf)
                if no_return and s['branch_clearance']==0:
                    count[0]+=int(s['extension']!=extension or s['returned']!=extension)
                    s.update(extension=extension,returned=extension)
                return s
            try:
                with patch.object(module,'suspension',suspension):
                    for i in range(hz//10):b,_=advance(b,hz,read,param,movement_matrix=matrix if frozen else None)
            except UnsupportedContact as e:
                unsupported.append(dict(tick=tick,case=label,hz=hz,substep=i+1,reason=str(e)));break
            assert module.suspension is original
            outcomes[str(hz)]=summarize(b);changed[str(hz)]=count[0]
            if not frozen and not no_return:
                if hz==20:assert b==states[tick+2]
                if phase=='nominal':assert outcomes[str(hz)]==reference[tick-1]['outcomes'][str(hz)]
        if len(outcomes)!=2:continue
        x,y=outcomes['20'],outcomes['50']
        cases[label]=dict(outcomes=outcomes,changed_returns=changed,errors=dict(position=[v-u for u,v in zip(x['position'],y['position'])],**{k:y[k]-x[k] for k in ('pitch','speed','target','rpm')}))
    rows.append(dict(tick=tick,cases=cases))
summary={}
for label in ('direction0-return0','direction1-return0','direction0-return1','direction1-return1'):
    valid=[v['cases'][label]['errors'] for v in rows if label in v['cases']]
    summary[label]=dict(cases=len(valid),max_y=max(abs(v['position'][1]) for v in valid),max_z=max(abs(v['position'][2]) for v in valid),max_pitch=max(abs(v['pitch']) for v in valid),max_speed=max(abs(v['speed']) for v in valid))
report=dict(scope=__doc__,phase=phase,summary=summary,unsupported=unsupported,rows=rows)
(r/('coupled-landing-interaction'+('' if phase=='nominal' else '-'+phase)+'.json')).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(summary=summary,unsupported=unsupported),indent=2))
for tick in (261,310):print(json.dumps(dict(tick=tick,errors={k:v['errors'] for k,v in rows[tick-1]['cases'].items()})))
