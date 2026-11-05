#!/usr/bin/env python3
"""Compose independently selected terrain with exact contact/body prediction."""
import json,sys,collections
from pathlib import Path
from crest_terrain_query import query,ROOT
from contact_body_predictor import body
cap=Path(sys.argv[1]);data=json.loads((cap/'prediction.json').read_text());r=data['records']
inputs={(x[0],x[1]):x[2:] for x in r['CACHED']}
build={(x[0],x[1]):x[2:] for x in r['BUILD']}
selected={(x['tick'],x['wheel']):x for x in r['SELECT']}
actual={x[0]:x[1:] for x in r['BODY']}
final={(x[0],x[1]):x[2:] for x in r['FINAL']}
susp={(x[0],x[1]):x[2:] for x in r['SUSP_OUT']}
checks=0;fields=set();branches=collections.Counter();barriers=collections.Counter()
for e in r['ENTRY']:
    tick=e[0];rows=[]
    for w in range(4):
        world=e[57+3*w:60+3*w]
        q=query(world,inputs[tick,w]);barriers[q["barrier"]]+=1
        # Original row supplies the dynamic state/distance/roof/impact inputs.
        # All geometry and clearance are replaced by the actual map query.
        row=dict(selected[tick,w])
        for key,value in q.items():
            if key in row:assert row[key]==value,(tick,w,key,row[key],value)
            row[key]=value;fields.add(key)
        rows.append(row)
    out=body(e,[build[tick,w] for w in range(4)],rows)
    assert actual[tick]==out['position']+[0,out['pitch'],0,out['pitch_carry']]+out['centroid_carries']
    for w,(end,s) in enumerate(zip(out['wheels'],out['suspensions'])):
        assert final[tick,w]==end['position']+[end[k] for k in ('clearance','velocity','vf','pf','ef')]
        assert susp[tick,w]==[s[k] for k in ('returned','extension','bias','ef','bf')]
    checks+=1
    branches.update(w['branch'] for w in out['wheels'])
report=dict(shift=data["shift"],verified_writes=data["verified_writes"],matching_full_states=data["matching_full_states"],branches=dict(branches),barriers=dict(barriers),body_updates=checks,wheels=4*checks,suspensions=4*checks,replaced_fields=sorted(fields),failures=[],
    scope='Changed common-Z translation diagnostic. Actual map query with old canonical static node records and current cached coordinates feeds body model; native query/output fields used only for comparison. Dynamic/roof/distance/impact inputs are captured. This is no integration-law or general-track acceptance.')
(cap/'terrain-body-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
