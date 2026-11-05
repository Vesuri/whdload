#!/usr/bin/env python3
"""Movement-accounting checks on recorded paths; not a contact simulation."""
import json, struct
from fractions import Fraction as F
from pathlib import Path
from native_motion_budget import MotionBudget
from native_query_path import traverse
from native_contact_response import rotate
from crest_terrain_query import query

def split_schedule(schedule, pieces):
    return [(a+(b-a)*F(i,pieces), a+(b-a)*F(i+1,pieces), d)
            for a,b,d in schedule for i in range(pieces)]

def run(distance,schedule):
    ledger=MotionBudget(distance)
    for a,b,d in schedule:
        assert a==ledger.cursor
        ledger.advance(b,d)
    assert ledger.cursor==1 and ledger.remaining_distance==0
    assert sum(s['distance'] for s in ledger.spans)==distance
    assert all(0<=r<1 for r in ledger.remainder)
    assert tuple(sum(s['movement'][i] for s in ledger.spans) for i in range(3))==ledger.displacement
    return ledger

root=Path('tmp/prof');reports=[]
for rate,name in ((20,'native20-contact-model'),(50,'contact-prediction-d9')):
    cap=root/name
    records=json.loads((cap/'prediction.json').read_text())['records']
    meta=json.loads((cap/'anchor.json').read_text());memory=(cap/'memory.bin').read_bytes()
    car=meta['data_base']+0x7ffe-0x92e-meta['memory_base']
    entries={e[0]:e for e in records['ENTRY']}
    finals={(v[0],v[1]):v[2:5] for v in records['FINAL']}
    first=min(entries)
    naive_errors=[];switching=0;max_loss=0;paths=0
    for row in records['SELECT']:
        t,w=row['tick'],row['wheel'];distance=row['distance']
        old=[row['old_world_'+a] for a in 'xyz'];new=[row['world_'+a] for a in 'xyz']
        cached=list(struct.unpack_from('>3h',memory,car+0x74+6*w)) if t==first else [v>>6 for v in finals[t-1,w]]
        intervals=traverse(old,new,cached)
        matrix=entries[t][4:13];direction=tuple(matrix[6:9])
        constant=[(a,b,direction) for a,b,key in intervals]
        ledger=run(distance,constant)
        assert ledger.displacement==tuple(rotate([0,0,distance],matrix))
        for pieces in (2,5):
            divided=run(distance,split_schedule(constant,pieces))
            assert (ledger.displacement,ledger.remainder)==(divided.displacement,divided.remainder)
        # Show the floor loss that independent interval projection would cause.
        naive=tuple(sum(int(((b-a)*distance*d)//16384) for a,b,_ in constant) for d in direction)
        error=tuple(a-b for a,b in zip(naive,ledger.displacement))
        if any(error):
            naive_errors.append(dict(tick=t,wheel=w,error=error,intervals=len(intervals)))
            max_loss=max(max_loss,max(abs(x) for x in error))
        # Prescribed surface directions test accounting through direction changes.
        # They are NOT asserted to be a physically valid contact response.
        schedule=[]
        for a,b,key in intervals:
            mid=(a+b)/2
            point=[int((F(x)+(y-x)*mid)//64)*64 for x,y in zip(old,new)]
            q=query(point,cached)
            schedule.append((a,b,tuple(q['matrix'+str(i)] for i in (6,7,8))))
        switching+=len(set(d for a,b,d in schedule))>1
        result=run(distance,schedule)
        expected=tuple(sum((b-a)*distance*d[i]/16384 for a,b,d in schedule) for i in range(3))
        assert tuple(result.exact_world)==expected
        for pieces in (2,5):
            divided=run(distance,split_schedule(schedule,pieces))
            assert (result.displacement,result.remainder)==(divided.displacement,divided.remainder)
        # Pushing between spans changes neither distance nor fractional motion.
        pushed=MotionBudget(distance)
        for a,b,d in schedule:
            pushed.advance(b,d)
            before=(pushed.cursor,pushed.remaining_distance,pushed.remainder)
            pushed.push((0,58,-26))
            assert before==(pushed.cursor,pushed.remaining_distance,pushed.remainder)
        assert pushed.displacement==tuple(v+len(schedule)*p for v,p in zip(result.displacement,(0,58,-26)))
        paths+=1
    reports.append(dict(rate=rate,paths=paths,subdivision_checks=paths*4,
                        prescribed_surface_direction_changes=switching,
                        independent_projection_wrong_paths=len(naive_errors),
                        max_independent_projection_loss=max_loss,examples=naive_errors[:6]))
# Native integer distance can be zero while a time interval is still valid.
zero=run(0,[(F(0),F(1,3),(0,0,16384)),(F(1,3),F(1),(0,-16384,0))])
assert zero.displacement==(0,0,0)
# Opposite signed travel cancels exactly, including its floor remainder.
cancel=run(1,[(F(0),F(1,2),(0,-1,1)),(F(1,2),F(1),(0,1,-1))])
assert cancel.displacement==(0,0,0) and cancel.remainder==(0,0,0)
# Invalid/overlapping events fail without consuming any state.
budget=MotionBudget(100);budget.advance(F(1,2),(0,0,16384))
for end,direction in [(F(1,2),(0,0,16384)),(F(1,3),(0,0,16384)),
                      (F(3,2),(0,0,16384)),(0.75,(0,0,16384)),
                      (F(3,4),(0,0,32768))]:
    before=(budget.cursor,budget.remaining_distance,budget.displacement,budget.remainder)
    try: budget.advance(end,direction)
    except (ValueError,TypeError): pass
    else: raise AssertionError('Accepted invalid event')
    assert before==(budget.cursor,budget.remaining_distance,budget.displacement,budget.remainder)
report=dict(rates=reports,scope='Exact movement ledger only. Recorded query intervals and prescribed directions; no gravity, physical response, new trajectory or runtime change.')
(root/'native-motion-budget-check.json').write_text(json.dumps(report,indent=2)+'\n')
for r in reports:print({k:v for k,v in r.items() if k!='examples'})
