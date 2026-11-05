#!/usr/bin/env python3
"""Offline controlled comparison; externally prescribed canonical distance."""
import json,struct,collections
from pathlib import Path
from copy import deepcopy
from contact_step import step
from anchored_support_model import solve_resting as solve
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
supported=[w for out in records for w in out['wheels'] if w['branch']=='anchored_support']
acquisitions=collections.Counter(w['acquisition_endpoint_clearance'] for out in records for w in out['wheels'] if 'acquisition_endpoint_clearance' in w)
report=dict(native_contact_endpoint_queries=dict(acquisitions),require_resting_acquisition=True,support_nonzero=sum(any(w['constraint_delta']) for w in supported),support_native_query_counts=dict(collections.Counter(w['native_query_after_projection'] for w in supported)),support_max_residual=max(w['analytic_residual'] for w in supported),branches=dict(branches),errors_at_13s=errors,limits={k:criteria['envelope'][k] for k in errors},records=records,
 scope='Experimental acquired-depth projection of remembered same-surface zero-gravity contact; native responses retained elsewhere. Canonical forward distances externally supplied, no drivetrain/controller simulation or live candidate validation. No handling acceptance.')
(root/'resting-anchor-probe.json').write_text(json.dumps(report,indent=2)+'\n');print({k:v for k,v in report.items() if k not in ('records','scope')})
