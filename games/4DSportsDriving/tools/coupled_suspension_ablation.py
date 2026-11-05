#!/usr/bin/env python3
"""Diagnostic only: remove zero-clearance return at both rates, not a candidate.

Both paths start at the same original state. Ablation removes the same physical
operation in both models; terrain/contact/body/drivetrain feedback remains live.
Differences between runs include feedback and must not be summed as independent
error contributions. Neither altered trajectory is a native acceptance reference.
"""
import json
from pathlib import Path
from copy import deepcopy
from unittest.mock import patch
import contact_body_predictor as model50
import native20_contact_model as model20
from coupled_vehicle_core import seed,advance,summarize
root=Path('tmp/prof');b,read,param=seed(root/'natural-crest20');seeds={}
for tick in range(2,311):
    b,_=advance(b,20,read,param)
    if tick in (261,310):seeds[tick]=deepcopy(b)
reports=[]
for tick,initial in seeds.items():
    for mode in ('baseline','no-zero-return'):
        traces={};counts={}
        for hz in (20,50):
            b=deepcopy(initial)
            if hz==50:
                for o in (0xc6,0xcb):b['car'][o]=(5*b['car'][o]+1)//2
            module=model20 if hz==20 else model50;original=module.suspension;changed=[0]
            def suspension(extension,bias,clearance,ef,bf):
                s=original(extension,bias,clearance,ef,bf)
                if mode=='no-zero-return' and s['branch_clearance']==0:
                    if s['extension']!=extension or s['returned']!=extension:changed[0]+=1
                    s.update(extension=extension,returned=extension)
                return s
            rows=[]
            with patch.object(module,'suspension',suspension):
                for i in range(1,hz//2+1):
                    b,record=advance(b,hz,read,param)
                    rows.append(dict(ms=i*1000//hz,**summarize(b),extensions=b['contact']['entry'][13:17]))
            assert module.suspension is original
            traces[str(hz)]=rows;counts[str(hz)]=changed[0]
        common=[]
        for tenth in range(1,6):
            a=traces['20'][2*tenth-1];b=traces['50'][5*tenth-1]
            common.append(dict(ms=100*tenth,position_error=[y-x for x,y in zip(a['position'],b['position'])],**{k+'_error':b[k]-a[k] for k in ('pitch','speed','target','rpm')}))
        reports.append(dict(seed_tick=tick,mode=mode,changed_wheel_returns=counts,common=common,traces=traces))
# Baseline must exactly reproduce the independently retained landing report.
reference=json.loads((root/'coupled-landing-events.json').read_text())
for r in reports:
    if r['mode']!='baseline':continue
    ref=next(v for v in reference['cases'] if v['seed_tick']==r['seed_tick'])
    for hz in ('20','50'):
        for actual,expected in zip(r['traces'][hz],ref['traces'][hz]):
            for key in ('position','pitch','speed','target','rpm','gear','clutch','flags'):
                assert actual[key]==expected[key],(r['seed_tick'],hz,actual['ms'],key)
(root/'coupled-suspension-ablation.json').write_text(json.dumps(dict(scope=__doc__,cases=reports),indent=2)+'\n')
for r in reports:print(json.dumps({k:v for k,v in r.items() if k!='traces'}))
