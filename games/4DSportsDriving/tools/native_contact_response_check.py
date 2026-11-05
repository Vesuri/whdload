#!/usr/bin/env python3
"""Check reusable contact reference against captured native instruction stages."""
import collections
import hashlib
import json
from fractions import Fraction
from pathlib import Path
from native_contact_response import resolve, vec, word, MovementBudget

p=Path('tmp/prof')
reports={}
for name in ('penetration-release20-source','penetration-landing20','penetration-course20'):
    path=p/name/'penetration.json'
    rows=json.loads(path.read_text())['rows']; groups={}
    for r in rows:
        stages=groups.setdefault((r['tick'],r['wheel']),{})
        assert r['stage'] not in stages, 'Repeated stage requires separate event grouping'
        stages[r['stage']]=r
    refs=json.loads((p/'first-release20/takeoff-plane.json').read_text())['rows']
    refs={(r['tick'],r['wheel']):r for r in refs if r['event']=='SELECT'}
    results=[]
    for key,stages in groups.items():
        r=dict(stages['ROTATED']);entry=stages['ENTER'];done=stages['DONE']
        if 'origin_x' not in r:
            ref=refs[key];assert vec(entry,'new')==vec(ref,'world')
            for a in 'xyz':
                r['origin_'+a]=word(ref['base_'+a]+ref['node_'+a]);r['normal_'+a]=ref['normal_'+a]
        result=resolve(vec(r,'old'),vec(r,'new'),r,r['distance'],r['velocity'],r['velocity'],r.get('impact_flags',0))
        assert result['position']==vec(stages['RESOLVED'],'new')==vec(done,'new'),(name,key,result,done)
        assert result['velocity']==done['velocity'],(name,key,'velocity')
        assert result['stored_clearance']==done['clearance'],(name,key,'stored clearance')
        if 'impact_flags' in r:assert result['impact_flags']==done['impact_flags'],(name,key,'impact flags')
        if result['branch']=='backoff64':
            assert 'REQUERY' not in stages and 'PUSH_VECTOR' not in stages
            assert result['backoff']==vec(stages['RESOLVED'],'resolved')
        else:
            q=stages['REQUERY']
            assert result['before_push']==vec(q,'new')
            assert result['tangent']==vec(q,'resolved')
            if result['branch']=='crossing':
                assert result['intersection']==vec(q,'correction')
                assert (result['total'],result['rest'])==(q['ratio_total'],q['ratio_rest'])
            if 'PUSH_VECTOR' in stages:assert result['push']==vec(stages['PUSH_VECTOR'],'correction')
            else:assert result['push']==[0,0,0]
        results.append(dict(tick=key[0],wheel=key[1],**result))
    reports[name]=dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest(),count=len(results),branches=dict(collections.Counter(r['branch'] for r in results)),results=results)

# Splitting time must neither duplicate distance nor lose integer remainders.
# These are accounting checks, not an assertion that collision response itself
# composes across arbitrary subdivisions.
ledger_cases=0
for distance in (0,1,63,64,951,2304,3357,32767):
    for parts in (1,2,3,5,7,14,50,127):
        budget=MovementBudget(distance);spans=[budget.consume_to(Fraction(i,parts)) for i in range(1,parts+1)]
        assert sum(s['forward_distance'] for s in spans)==distance
        assert spans[0]['start']==0 and spans[-1]['end']==1
        assert all(a['end']==b['start'] for a,b in zip(spans,spans[1:]))
        for invalid in (0,Fraction(1,2),1,Fraction(101,100)):
            before=(budget.cursor,budget.delivered)
            try:budget.consume_to(invalid)
            except ValueError:pass
            else:raise AssertionError('Overlapping/out-of-range span accepted')
            assert before==(budget.cursor,budget.delivered)
        ledger_cases+=1
result=dict(captures=reports,ledger_cases=ledger_cases,scope='Native straight-direction response stage equality; captures overlap, so totals are not independent contacts. Backoff64 skips requery and residual push. Ledger conserves issued distance but does not establish a fractional collision law. General heading, flat retry, crash5, hard crash and coupled integration remain open.')
(p/'native-contact-response-check.json').write_text(json.dumps(result,indent=2)+'\n')
for name,r in reports.items():print(name,r['count'],r['branches'])
print('Movement ledgers:',ledger_cases)
