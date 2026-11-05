#!/usr/bin/env python3
"""Freeze forward direction for100ms at all rates; body rebuild stays recurrent.

Diagnostic only, not a proposed frozen-direction runtime or acceptance envelope.
All contact, engine, suspension, pitch and wheel caches still feed subsequent
steps. Comparing altered histories does not produce additive causal error terms.
"""
import json
from copy import deepcopy
from pathlib import Path
from coupled_vehicle_core import seed,advance,summarize
from native_contact_response import sine,UnsupportedContact
root=Path('tmp/prof');b,read,param=seed(root/'natural-crest20');states={1:deepcopy(b)}
for t in range(2,321):
    b,_=advance(b,20,read,param);states[t]=deepcopy(b)
ref=json.loads((root/'coupled-three-rate-comparison.json').read_text())['rows']
rows=[];unsupported=[]
for tick in range(1,319):
    pitch=states[tick]['contact']['entry'][2];sn,cs=sine(pitch),sine(pitch+256)
    matrix=[16384,0,0,0,cs,-sn,0,sn,cs]
    modes={}
    for mode in ('baseline','fixed-direction'):
        outcomes={}
        for hz in (10,20,50):
            b=deepcopy(states[tick])
            for o in (0xc6,0xcb):b['car'][o]=(hz*b['car'][o]+19)//20
            try:
                for substep in range(hz//10):b,record=advance(b,hz,read,param,movement_matrix=matrix if mode=='fixed-direction' else None)
            except UnsupportedContact as error:
                assert mode!='baseline'
                unsupported.append(dict(seed_tick=tick,mode=mode,hz=hz,substep=substep+1,error=str(error)))
                continue
            outcomes[str(hz)]=summarize(b)
            if mode=='baseline':assert outcomes[str(hz)]==ref[tick-1]['outcomes'][str(hz)]
        errors={}
        if '20' not in outcomes:
            modes[mode]=dict(outcomes=outcomes,errors=errors);continue
        native=outcomes['20']
        for hz in ('10','50'):
            if hz not in outcomes:continue
            s=outcomes[hz];errors[hz]={k:s[k]-native[k] for k in ('pitch','speed','target','rpm')}
            errors[hz]['position']=[x-y for x,y in zip(s['position'],native['position'])]
        modes[mode]=dict(outcomes=outcomes,errors=errors)
    rows.append(dict(seed_tick=tick,modes=modes))
summary={}
for mode in ('baseline','fixed-direction'):
    summary[mode]={}
    for hz in ('10','50'):
        selected=[r['modes'][mode]['errors'][hz] for r in rows if hz in r['modes'][mode]['errors']]
        summary[mode][hz]=dict(cases=len(selected),max_y=max(abs(r['position'][1]) for r in selected),max_z=max(abs(r['position'][2]) for r in selected),max_pitch=max(abs(r['pitch']) for r in selected),max_speed=max(abs(r['speed']) for r in selected))
(root/'coupled-direction-ablation.json').write_text(json.dumps(dict(scope=__doc__,summary=summary,unsupported=unsupported,rows=rows),indent=2)+'\n')
print(json.dumps(summary,indent=2));print("UNSUPPORTED",unsupported)
for tick in (261,310):print(json.dumps(rows[tick-1]))
