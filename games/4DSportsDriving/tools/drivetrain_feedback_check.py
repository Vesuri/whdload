#!/usr/bin/env python3
"""Verify observed rate conversion, contact sync and distance before modeling feedback."""
import json,collections
from pathlib import Path
from native_contact_response import word,trunc
cap=Path('tmp/prof/drivetrain-feedback-d9');data=json.loads((cap/'drivetrain.json').read_text());r=data['records'];cases=[];branches=collections.Counter();changes=collections.Counter()
for ac,ap,sy,en,di,de,bo in zip(*(r[k] for k in ('ACCEL','APPLIED','SYNC','ENGINE_END','DIST','DIST_END','BODY'))):
    t=ac[0];assert all(v[0]==t for v in (ap,sy,en,di,de,bo))
    nominal=ac[2];scaled=trunc(2*nominal+ac[3],5);speed=ac[1]
    if scaled>=0:
        pred=(speed+scaled)&65535
        if speed>=32768 and (pred<32768 or pred>62720):pred=62720
    else:pred=max(0,speed+scaled)
    assert pred==ap[1],('acceleration',t,pred,ap[1])
    before=ap[2:];after=sy[1:];predicted=before.copy()
    if before[7]:
        if abs(word(before[3]-ap[1]))>5120:
            expected=(before[2]+before[3])//2;branch='contact_blend'
        else:expected=ap[1];branch='contact_copy'
        predicted[2]=predicted[3]=expected
    else:predicted[2]=ap[1];branch='free_speed_only'
    assert predicted==after,('sync',t,predicted,after)
    q=(di[5]*1408)//15360;distance,carry=divmod(2*q+di[1],5)
    assert de[1:]==[distance,carry],('distance',t,de,distance,carry)
    branches[branch]+=1
    for label,a,b in [('engine_post_sync',after,en[1:]),('engine_to_distance',en[1:],di[2:]),('distance_to_body',di[2:],bo[1:])]:
        if a[3]!=b[3]:changes[label]+=1
    cases.append(dict(tick=t,branch=branch,nominal_acceleration=nominal,scaled_acceleration=scaled,
        old_speed=before[2],old_target=before[3],applied_speed=ap[1],synchronized_speed=after[2],synchronized_target=after[3],engine_end_target=en[4],distance_target=di[5],body_target=bo[4],distance=distance,slope_force=bo[1],contact_flag=before[7]))
out=dict(steps=len(cases),branches=dict(branches),target_changes=dict(changes),matching_full_states=data['matching_full_states'],rows=cases,scope='Exact observed local stage transitions. Acceleration input, contact flags, RPM/gear and post-contact speed remain observed; this is not a full drivetrain recurrence.')
(cap/'drivetrain-check.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k not in ('rows','scope')},indent=2))
