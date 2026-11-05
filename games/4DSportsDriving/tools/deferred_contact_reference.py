#!/usr/bin/env python3
"""Experimental gravity support intervals plus one native endpoint response.

This is an explicit alternative to applying geometric corrections at every
quantization-cell event. Negative interior cells reset gravity as support, but
no position correction occurs until the final candidate. This law is a
hypothesis, not inferred native substep behavior or an accepted runtime patch.
"""
import collections
import hashlib
import json
import math
from pathlib import Path
from coupled_contact_reference import event_integrate,sampled_integrate,Unsupported
from native_contact_response import resolve,plane,word,UnsupportedContact,MovementBudget

p=Path('tmp/prof')
distance_capture=p/'distance-order-trace50'
distances={r['tick']:r['distance'] for r in json.loads((distance_capture/'distance-order.json').read_text())['rows']}
distance_hash=json.loads((distance_capture/'anchor.json').read_text())['slave_sha256']
matrices={}
for r in json.loads((p/'penetration-course20/penetration.json').read_text())['rows']:
    if r['stage']!='ROTATED':continue
    key=(r['plane'],r['normal_x'],r['normal_y'],r['normal_z']);m=[r[f'matrix{i}'] for i in range(9)]
    assert key not in matrices or matrices[key]==m
    matrices[key]=m

def endpoint(r,result,distance,contact_flags=None):
    # This integer endpoint is diagnostic. Fractional carry across reconstructed
    # body poses is not implemented, so these are separately initialized steps.
    down=math.floor(result['downward'])
    old=[r['old_world_'+a] for a in 'xyz']
    new=[r['world_x'],r['world_y']-down,r['world_z']]
    geometry=dict(plane=r['plane'])
    for a in 'xyz':
        geometry['origin_'+a]=word(r['base_'+a]+r['node_'+a])
        geometry['normal_'+a]=r['normal_'+a]
    clearance=plane(geometry,new)
    if clearance>=0:
        return dict(branch='zero' if clearance==0 else 'air',position=new,clearance=clearance,
                    velocity=0 if clearance==0 else result['velocity'],response_count=0)
    if contact_flags is None:raise Unsupported('Endpoint penetration needs measured plane/impact flags')
    if distance is None:raise Unsupported('Endpoint penetration needs measured forward distance')
    geometry['plane_flags']=contact_flags['plane_flags']
    key=(r['plane'],r['normal_x'],r['normal_y'],r['normal_z'])
    if key not in matrices:raise Unsupported('No independently captured surface matrix')
    geometry.update({f'matrix{i}':x for i,x in enumerate(matrices[key])})
    # Exactly one full-step movement allocation. Interior events used no native
    # response and did not allocate this distance again.
    ledger=MovementBudget(distance);span=ledger.consume_to(1)
    response=resolve(old,new,geometry,span['forward_distance'],down,result['velocity'],contact_flags['impact_flags'])
    response['response_count']=1
    return response

def main():
    reports={}
    for name in ('release-step50','release-second-step50'):
        anchor=json.loads((p/name/'anchor.json').read_text());assert anchor['slave_sha256']==distance_hash
        path=p/name/'takeoff-plane.json';live=json.loads(path.read_text())['rows']
        selected={(r['tick'],r['wheel']):r for r in live if r['event']=='SELECT'};rows=[]
        for key,r in selected.items():
            prior=selected.get((r['tick']-1,r['wheel']))
            if prior is None or r['correction']!=0:continue
            out=dict(tick=r['tick'],wheel=r['wheel'])
            try:
                result=event_integrate(r,prior,defer_penetration=True)
                out.update(supported=True,velocity=result['velocity'],downward=result['downward'],
                           negative_intervals=sum(e['clearance']<0 for e in result['events']),
                           negative_time_fraction=sum(e['time']-(result['events'][i-1]['time'] if i else 0)
                                                      for i,e in enumerate(result['events']) if e['clearance']<0),
                           endpoint=endpoint(r,result,distances[r['tick']]))
                if r['wheel'] in (0,2):
                    out['sampled']={str(n):sampled_integrate(r,n,prior,defer_penetration=True) for n in (1000,4000,16000)}
                    out['fine_error']={k:abs(out['sampled']['16000'][k]-result[k]) for k in ('velocity','downward')}
                    assert max(out['fine_error'].values())<.002,(name,key,out['fine_error'])
            except (Unsupported,UnsupportedContact) as e:out.update(supported=False,reason=str(e))
            rows.append(out)
        reports[name]=dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest(),rows=rows)
    report=dict(captures=reports,slave_sha256=distance_hash,
                scope='Explicit deferred-contact hypothesis; negative interior intervals are support for gravity, geometric response happens once at endpoint. Independently initialized recorded trajectories, not chained wheel/body simulation. Monotone straight direction only. Integer carry and impact/lifecycle state, general polygon topology and fractional-time collision semantics remain open. Numerical convergence proves this chosen law only, not physical/native handling correctness.')
    (p/'deferred-contact-reference.json').write_text(json.dumps(report,indent=2)+'\n')
    for name,c in reports.items():
        good=[r for r in c['rows'] if r['supported']];checks=[r for r in good if 'fine_error' in r]
        print(name,'supported',len(good),'of',len(c['rows']),'interior negative cases',sum(r['negative_intervals']>0 for r in good),'endpoint branches',dict(collections.Counter(r['endpoint']['branch'] for r in good)))
        print('fine-error maxima',{k:max((r['fine_error'][k] for r in checks),default=0) for k in ('velocity','downward')})
        for r in good:
            if r['wheel'] in (0,2) and r['negative_intervals']:print({k:r[k] for k in ('tick','wheel','velocity','downward','negative_intervals','negative_time_fraction','endpoint')})
if __name__=='__main__':main()
