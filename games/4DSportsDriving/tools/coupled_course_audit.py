#!/usr/bin/env python3
"""Partial original handling gates for fully recurrent straight-course models."""
import json,hashlib
from pathlib import Path
root=Path('tmp/prof');criteria_path=root/'natural-crest-criteria.json';c=json.loads(criteria_path.read_text());native={r['tick']:r for r in json.loads((root/'natural-crest20/bridge.json').read_text())['rows']};reports=[]
for mode in ('baseline','chronological','support-release','query-crossing','native-extension','fine-contact'):
    p=root/('coupled-course-'+mode+'.json');d=json.loads(p.read_text());r=d['rows'];assert [v['tick'] for v in r]==list(range(6,801))
    flights=[];block=[]
    for v in r:
        if not any(v['flags']):block.append(v['tick'])
        elif block:flights.append(block);block=[]
    assert not block,'Unfinished flight'
    metrics={ 'final_'+k:r[-1][k] for k in ('x','y','z','pitch','speed')}
    metrics.update(peak_height=max(v['y'] for v in r),minimum_pitch=min(v['pitch'] for v in r),maximum_pitch=max(v['pitch'] for v in r),airborne_time=sum(map(len,flights))/50)
    for i,seq in enumerate(flights):metrics['takeoff_'+str(i)]=seq[0]/50;metrics['landing_'+str(i)]=(seq[-1]+1)/50
    checks={k:dict(actual=v,reference=c['native20']['metrics'][k],limit=c['limits'][k],passed=abs(v-c['native20']['metrics'][k])<=c['limits'][k]+1e-8) for k,v in metrics.items() if k in c['limits']}
    for k in ('x','y','z','pitch','speed'):
        err=max(abs(v[k]-native[v['tick']*2//5][k]) for v in r if v['tick']>=450 and v['tick']%10==0)
        checks['common_'+k]=dict(actual=err,limit=c['envelope'][k],passed=err<=c['envelope'][k])
    checks['two_flights']=dict(actual=len(flights),passed=len(flights)==2)
    reports.append(dict(mode=mode,checks=checks,failures=[k for k,v in checks.items() if not v['passed']],input_sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
report=dict(criteria_sha256=hashlib.sha256(criteria_path.read_bytes()).hexdigest(),cases=reports,scope='Offline feedback model, ticks6..800, held throttle stock straight course. Partial physical gates; excludes collision/crash side effects, rendering, arbitrary steering/terrain, replay and capacity. No acceptance claim.')
(root/'coupled-course-audit.json').write_text(json.dumps(report,indent=2)+'\n');print([(v['mode'],v['failures']) for v in reports])
