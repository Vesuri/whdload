#!/usr/bin/env python3
"""Validate extended recurrence, then compare an offline crossing-budget candidate.

Distances and roof/impact inputs remain externally prescribed. This is not a
full vehicle simulation and cannot establish handling acceptance.
"""
import json,struct,sys
from pathlib import Path
from copy import deepcopy
from contact_step import step
from crossing_budget_model import solve
cap=Path(sys.argv[1]);root=Path('tmp/prof')
r=json.loads((cap/'prediction.json').read_text())['records']
meta=json.loads((cap/'anchor.json').read_text());mem=(cap/'memory.bin').read_bytes()
car=meta['data_base']+0x7ffe-0x92e-meta['memory_base']
canonical={v['tick']:v for v in json.loads((root/(sys.argv[2] if len(sys.argv)>2 else 'crest-d9e7903')/'bridge.json').read_text())['rows']}
native={v['tick']:v for v in json.loads((root/(sys.argv[3] if len(sys.argv)>3 else 'natural-crest20')/'bridge.json').read_text())['rows']}
start=meta['simulation_tick']
initial=dict(entry=r['ENTRY'][0].copy(),position=[canonical[start][a] for a in ('x','y','z')],cached=[list(struct.unpack_from('>3h',mem,car+0x74+6*w)) for w in range(4)])
selected={(v['tick'],v['wheel']):v for v in r['SELECT']}
actualbody={v[0]:v[1:] for v in r['BODY']}
state=deepcopy(initial);count=0;geometry_fields=0
for e in r['ENTRY']:
    t=e[0]
    state,rec=step(state,50,selected[t,0]['distance'],[selected[t,w]['correction'] for w in range(4)],[selected[t,w]['impact_flags'] for w in range(4)])
    assert rec['entry']==e,('entry',t)
    for w,row in enumerate(rec['selected']):
        for key in row.keys() & selected[t,w].keys():
            assert row[key]==selected[t,w][key],('query',t,w,key,row[key],selected[t,w][key])
            geometry_fields+=1
    out=rec['output']
    assert out['position']+[0,out['pitch'],0,out['pitch_carry']]+out['centroid_carries']==actualbody[t],('body',t)
    count+=1
state=deepcopy(initial);records=[];common=[]
for e in r['ENTRY']:
    t=e[0]
    state,rec=step(state,50,selected[t,0]['distance'],[selected[t,w]['correction'] for w in range(4)],[selected[t,w]['impact_flags'] for w in range(4)],body_solver=solve)
    out=rec['output'];records.append(out)
    if t%10==0:
        ref=native[t*2//5]
        common.append(dict(tick=t,seconds=t/50,errors=dict(y=out['position'][1]-ref['y'],z=out['position'][2]-ref['z'],pitch=out['pitch']-ref['pitch'])))
criteria=json.loads((root/'natural-crest-criteria.json').read_text())
maxima={key:max(common,key=lambda v:abs(v['errors'][key])) for key in ('y','z','pitch')}
report=dict(canonical_steps_exact=count,canonical_entry_fields=count*69,canonical_selected_fields=geometry_fields,range=[start+1,r['ENTRY'][-1][0]],maxima=maxima,limits={k:criteria['envelope'][k] for k in maxima},common=common,records=records,scope=__doc__)
(cap/'crossing-budget-comparison.json').write_text(json.dumps(report,indent=2,default=str)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('common','records','scope')},indent=2))
