#!/usr/bin/env python3
"""Verify the contact-to-engine inputs from independent wheel/body predictions."""
import json,struct
from pathlib import Path
from contact_body_predictor import wheel
from native_contact_response import rotate
root=Path('tmp/prof');cap=root/'drivetrain-feedback-inputs-d9';eng=json.loads((cap/'drivetrain.json').read_text())['records'];r=json.loads((root/'contact-prediction-d9-long/prediction.json').read_text())['records']
entries={e[0]:e for e in r['ENTRY']};selected={(v['tick'],v['wheel']):v for v in r['SELECT']};bridge={v['tick']:v for v in json.loads((root/'crest-d9e7903/bridge.json').read_text())['rows']}
rows=[];flags_pred={}
for t in range(451,801):
    ends=[wheel(selected[t,w]) for w in range(4)]
    # CC14 checks post-gravity/pre-response clearance, not SELECT clearance.
    flags=[int(v['suspension_clearance']<=12) for v in ends]
    assert flags==[bridge[t]['w'+str(w)] for w in range(4)],('flags',t,flags)
    flags_pred[t]=flags
for pre,body in zip(eng['PRE_ENGINE'],eng['BODY']):
    t=pre[0];car=struct.pack('>104H',*pre[4:]);prior=flags_pred[t-1] if t>451 else [bridge[450]['w'+str(w)] for w in range(4)]
    rear=sum(bool(v) for v in prior[2:]);all_wheels=sum(bool(v) for v in prior)
    assert car[0xc0]==rear and car[0xc1]==all_wheels,('counts',t,car[0xc0:0xc2],rear,all_wheels)
    slope=-rotate([0,0,130],entries[t][4:13])[1]
    assert slope==body[1],('slope',t,slope,body[1])
    rows.append(dict(tick=t,pre_engine_driven_contacts=rear,pre_engine_all_contacts=all_wheels,body_slope=slope,body_wheel_flags=flags_pred[t]))
report=dict(steps=len(rows),wheel_flags_exact=4*len(rows),rear_counts_exact=len(rows),all_counts_exact=len(rows),slope_force_exact=len(rows),rows=rows,scope='Original straight-road geometry: post-gravity clearance<=12 gives surface1 contact flag; rear pair feeds next engine update. Terrain identities other than road1 and arbitrary collision modes not covered. Only initial contact flags borrowed; subsequent counts independently predicted.')
(cap/'contact-inputs-check.json').write_text(json.dumps(report,indent=2)+'\n');print({k:v for k,v in report.items() if k not in ('rows','scope')})
