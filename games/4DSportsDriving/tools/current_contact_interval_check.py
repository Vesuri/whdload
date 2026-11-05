#!/usr/bin/env python3
"""Current-source coupled gravity/one-response hypothesis with explicit scope."""
import collections,hashlib,json,math
from pathlib import Path
from coupled_contact_reference import event_integrate,sampled_integrate,Unsupported
from deferred_contact_reference import endpoint
from native_contact_response import UnsupportedContact

root=Path('tmp/prof');cap=root/'crest-release-d9-50';source=cap/'takeoff-plane.json';trace=json.loads(source.read_text());groups={}
for row in trace['rows']:groups.setdefault((row['tick'],row['wheel']),[]).append(row)
selected={key:next(r for r in rows if r['event']=='SELECT') for key,rows in groups.items()}
results=[];native_checks=[]
for key,r in selected.items():
    events=groups[key];after=next(row for row in events if row['event']=='AFTER')
    # First verify the existing endpoint-response implementation using actual
    # recorded gravity displacement. This is separate from the new time law.
    down=r['world_y']-after['world_y']
    assert (r['world_x'],r['world_z'])==(after['world_x'],after['world_z'])
    native_result=dict(downward=down,velocity=after['velocity']+after['velocity_fraction']/5)
    native=endpoint(r,native_result,r['distance'],r)
    final=events[-1]
    assert native['position']==[final['world_'+a] for a in 'xyz'],(key,native,final)
    # At PENETRATION_ZERO the hook has not cleared velocity yet; all recorded
    # penetration examples here enter with zero, verified explicitly.
    expected_velocity=final['velocity']+final['velocity_fraction']/5
    assert abs(native['velocity']-expected_velocity)<1e-9,(key,native,final)
    native_checks.append(dict(tick=key[0],wheel=key[1],branch=native['branch']))
    prior=selected.get((r['tick']-1,r['wheel']))
    if prior is None or r['correction']!=0:continue
    item=dict(tick=key[0],wheel=key[1],observed_velocity=native['velocity'])
    try:
        result=event_integrate(r,prior,defer_penetration=True)
        resolved=endpoint(r,result,r['distance'],r)
        item.update(supported=True,velocity=result['velocity'],downward=result['downward'],endpoint=resolved,
                    negative_intervals=sum(e['clearance']<0 for e in result['events']))
        if r['wheel'] in (0,2):
            sampled=sampled_integrate(r,16000,prior,defer_penetration=True)
            errors={k:abs(sampled[k]-result[k]) for k in ('velocity','downward')}
            assert max(errors.values())<.002,(key,errors)
            item['fine_error']=errors
    except (Unsupported,UnsupportedContact) as error:item.update(supported=False,reason=str(error))
    results.append(item)
report=dict(trace_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),native_endpoint_checks=native_checks,rows=results,
 scope='Current-source independently initialized recorded steps. Native endpoint response first reproduced with observed gravity. Experimental interior nonpositive cells reset gravity but defer geometric correction to one endpoint using one whole-step movement budget. Negative-time support is a hypothesis, not a derived native fractional law. No chained body reconstruction, general topology, integer carry, runtime implementation or handling acceptance.')
(root/'current-contact-interval-check.json').write_text(json.dumps(report,indent=2)+'\n')
good=[r for r in results if r['supported']]
print('native endpoint checks',len(native_checks),'branches',dict(collections.Counter(r['branch'] for r in native_checks)))
print('coupled steps',len(good),'of',len(results),'negative cases',sum(r['negative_intervals']>0 for r in good),'endpoint branches',dict(collections.Counter(r['endpoint']['branch'] for r in good)))
print('unsupported',[(r['tick'],r['wheel'],r['reason']) for r in results if not r['supported']])
print('fine max',{k:max(r.get('fine_error',{}).get(k,0) for r in good) for k in ('velocity','downward')})
