#!/usr/bin/env python3
import json,collections,hashlib
from pathlib import Path
from contact_body_predictor import body
P=Path('tmp/prof/contact-prediction-d9');data=json.loads((P/'prediction.json').read_text());r=data['records']
groups=lambda key:{(v[0],v[1]):v[2:] for v in r[key]}
build=groups('BUILD');final=groups('FINAL');sinputs=groups('SUSP_IN');soutputs=groups('SUSP_OUT')
selected={(v['tick'],v['wheel']):v for v in r['SELECT']};bodies={v[0]:v[1:] for v in r['BODY']}
checks=[];failures=[]
for entry in r['ENTRY']:
    t=entry[0]
    try:
        out=body(entry,[build[t,w] for w in range(4)],[selected[t,w] for w in range(4)])
        for w,(end,s) in enumerate(zip(out['wheels'],out['suspensions'])):
            expected=end['position']+[end[k] for k in ('clearance','velocity','vf','pf','ef')]
            assert final[t,w]==expected,('wheel',t,w,final[t,w],expected,end)
            sin=sinputs[t,w]
            assert sin==[end['suspension_clearance'],entry[13+w],entry[17+w],end['ef'],entry[37+w]],('suspension input',t,w,sin)
            predicted=[s[k] for k in ('returned','extension','bias','ef','bf')]
            assert soutputs[t,w]==predicted,('suspension',t,w,soutputs[t,w],predicted)
        expected=out['position']+[0,out['pitch'],0,out['pitch_carry']]+out['centroid_carries']
        assert bodies[t]==expected,('body',t,bodies[t],expected)
        checks.append(out)
    except Exception as e:
        failures.append(dict(tick=t,error=repr(e)));break
report=dict(trace_sha256=hashlib.sha256((P/'prediction.json').read_bytes()).hexdigest(),
    matching_full_baseline_states=data['matching_full_states'],
    changed_global_vs_suspension_clearances=sum(w['clearance']!=w['suspension_clearance'] for c in checks for w in c['wheels']),
    suspension_branches=dict(collections.Counter((s['branch_clearance']>0)-(s['branch_clearance']<0) for c in checks for s in c['suspensions'])),
    observed_nonzero_bias_inputs=sum(bool(x) for e in r['ENTRY'] for x in e[17:21]),
    checked_body_updates=len(checks),checked_wheels=4*len(checks),branches=dict(collections.Counter(w['branch'] for c in checks for w in c['wheels'])),failures=failures,rows=checks,
 scope='Predict current integer gravity/contact/suspension and body geometry from ENTRY/BUILD plus OBSERVED SELECT terrain descriptions. All pre-contact wheel states also equal ENTRY values. Does not yet predict terrain selection for a changed vector or define a changed integration law. No general yaw/roll, hard crash/impact flag proof, controller/drivetrain evolution, replay-state or capacity acceptance.')
Path('tmp/prof/contact-body-predictor-check.json').write_text(json.dumps(report,indent=2)+'\n')
print({k:v for k,v in report.items() if k not in ('rows','scope')})
if failures:raise SystemExit(1)
