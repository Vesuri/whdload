#!/usr/bin/env python3
"""Offline controlled comparison; externally prescribed canonical distance."""
import json,struct,collections
from pathlib import Path
from copy import deepcopy
from contact_step import step
from endpoint_force_model import solve
root=Path('tmp/prof');cap=root/'contact-prediction-d9'
r=json.loads((cap/'prediction.json').read_text())['records'];meta=json.loads((cap/'anchor.json').read_text());mem=(cap/'memory.bin').read_bytes();car=meta['data_base']+0x7ffe-0x92e-meta['memory_base']
canonical={v['tick']:v for v in json.loads((root/'crest-d9e7903/bridge.json').read_text())['rows']};native={v['tick']:v for v in json.loads((root/'natural-crest20/bridge.json').read_text())['rows']}
state=dict(entry=r['ENTRY'][0].copy(),position=[canonical[450][a] for a in ('x','y','z')],cached=[list(struct.unpack_from('>3h',mem,car+0x74+6*w)) for w in range(4)])
selected={(v['tick'],v['wheel']):v for v in r['SELECT']};records=[];branches=collections.Counter()
for e in r['ENTRY']:
    t=e[0];distance=selected[t,0]['distance'];state,record=step(state,50,distance,body_solver=solve)
    out=record['output'];branches.update(x['branch'] for x in out['wheels']);records.append(out)
criteria=json.loads((root/'natural-crest-criteria.json').read_text());p=next(x for x in records if x['tick']==650);ref=native[260]
errors=dict(y=p['position'][1]-ref['y'],z=p['position'][2]-ref['z'],pitch=p['pitch']-ref['pitch'])
report=dict(activation_count=sum(w['force_activation_correction']!='0' for out in records for w in out['wheels']),branches=dict(branches),errors_at_13s=errors,limits={k:criteria['envelope'][k] for k in errors},records=records,
 scope='Offline endpoint-activation phase-average correction; prescribed canonical distances, no engine/controller feedback or runtime/capacity/replay validation. Native suspension/contact remains otherwise unchanged. No handling acceptance.')
(root/'endpoint-force-probe.json').write_text(json.dumps(report,indent=2,default=str)+'\n');print({k:v for k,v in report.items() if k not in ('records','scope')})
