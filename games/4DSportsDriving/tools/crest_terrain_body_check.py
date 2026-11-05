#!/usr/bin/env python3
"""Compose independently selected terrain with exact contact/body prediction."""
import json
from pathlib import Path
from crest_terrain_query import query,ROOT
from contact_body_predictor import body
cap=ROOT/'tmp/prof/contact-prediction-d9'
r=json.loads((cap/'prediction.json').read_text())['records']
t=json.loads((ROOT/'tmp/prof/terrain-query-d9-verified/terrain-query.json').read_text())['records']
inputs={(x[0],x[1]):x[5:8] for x in t['QUERY_IN']}
build={(x[0],x[1]):x[2:] for x in r['BUILD']}
selected={(x['tick'],x['wheel']):x for x in r['SELECT']}
actual={x[0]:x[1:] for x in r['BODY']}
final={(x[0],x[1]):x[2:] for x in r['FINAL']}
susp={(x[0],x[1]):x[2:] for x in r['SUSP_OUT']}
checks=0;fields=set()
for e in r['ENTRY']:
    tick=e[0];rows=[]
    for w in range(4):
        world=e[57+3*w:60+3*w]
        q=query(world,inputs[tick,w])
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
report=dict(body_updates=checks,wheels=4*checks,suspensions=4*checks,replaced_fields=sorted(fields),failures=[],
    scope='Actual track-map query and separately captured cached wheel positions feed contact/body predictor; all output checks exact. Static node records sourced from independently captured terrain queries. Original SELECT retains only dynamic/roof/distance/impact inputs. No altered-motion runtime or general-track acceptance.')
(ROOT/'tmp/prof/crest-terrain-body-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
