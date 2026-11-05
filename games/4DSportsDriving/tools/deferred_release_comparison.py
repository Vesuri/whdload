#!/usr/bin/env python3
"""Carry candidate wheel velocity over recorded native20 / experimental50 poses.

The pose path remains recorded, so this isolates release timing and does not
claim a resimulated car trajectory, pitch, suspension or handling acceptance.
"""
import json
from pathlib import Path
from coupled_contact_reference import event_integrate,sampled_integrate
from deferred_contact_reference import endpoint,distances
p=Path('tmp/prof');output={}
native_distance={};native_flags={}
for r in json.loads((p/'penetration-course20/penetration.json').read_text())['rows']:
    if r['stage']=='ENTER':
        native_distance[(r['tick'],r['wheel'])]=r['distance']
        native_flags[(r['tick'],r['wheel'])]={k:r[k] for k in ('plane_flags','impact_flags')}
for rate in (20,50):
    name=f'release-step{rate}';data=json.loads((p/name/'takeoff-plane.json').read_text())
    assert data['rate']==rate
    selected=[r for r in data['rows'] if r['event']=='SELECT']
    original_after={(r['tick'],r['wheel']):r for r in data['rows'] if r['event']=='AFTER'}
    original_end={(r['tick'],r['wheel']):r for r in data['rows'] if r['event'] in ('ZERO','PENETRATION_ZERO')}
    # These captures use the player only. Each wheel is initially supported.
    velocity={};previous={};results=[]
    for recorded in selected:
        r=dict(recorded);key=(r['tick'],r['wheel']);w=r['wheel']
        assert r['correction']==0
        if w not in velocity:
            assert r['velocity']==r['velocity_fraction']==0
            velocity[w]=0.
        r['velocity']=velocity[w];r['velocity_fraction']=0.
        prior=previous.get(w,r)
        model=event_integrate(r,prior,defer_penetration=True,step_h=20/rate)
        sampled=sampled_integrate(r,16000,prior,defer_penetration=True,step_h=20/rate)
        error={k:abs(model[k]-sampled[k]) for k in ('velocity','downward')}
        assert max(error.values())<.003,(rate,key,error)
        # Distance is only used if the final candidate needs native response.
        distance=distances[key[0]] if rate==50 else native_distance.get(key)
        final=endpoint(r,model,distance,native_flags.get(key) if rate==20 else None)
        velocity[w]=final['velocity'];previous[w]=recorded
        observed=original_after[key]
        actual=observed['velocity']+observed['velocity_fraction']/5
        if key in original_end:actual=0.
        results.append(dict(tick=key[0],wheel=w,time=key[0]/rate,velocity=velocity[w],observed_velocity=actual,
                            downward=model['downward'],endpoint_branch=final['branch'],fine_error=error))
    common=[]
    for t in (11.3,11.4,11.5):
        pair=[next(r for r in results if r['wheel']==w and r['tick']==round(t*rate)) for w in (0,2)]
        common.append(dict(time=t,front=pair[0]['velocity'],rear=pair[1]['velocity'],
                           differential=pair[0]['velocity']-pair[1]['velocity'],
                           observed_differential=pair[0]['observed_velocity']-pair[1]['observed_velocity']))
    output[str(rate)]=dict(rows=results,common=common)
    print(rate,*common,sep='\n')
report=dict(captures=output,scope='Candidate velocities chained, recorded wheel/body poses unchanged. Each within-step gravity calculation checked against16000 uniform subdivisions. Endpoint response uses actual recorded scalar movement when required. Fractional position carry across poses, changed geometry/suspension, pitch feedback, hard-impact/general terrain and runtime are not represented. Not a handling gate.')
(p/'deferred-release-comparison.json').write_text(json.dumps(report,indent=2)+'\n')
