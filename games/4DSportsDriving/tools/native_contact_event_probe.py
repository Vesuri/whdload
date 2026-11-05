#!/usr/bin/env python3
"""First-contact response experiment under prescribed zero-gravity motion.

This is not a wheel solver: force activation is frozen out. The response turns
the unspent forward budget onto the contacted surface, then applies the native
integer normal correction at the endpoint. Terrain changes during the response
are rejected, not silently assigned to the old face.
"""
import json, collections
from fractions import Fraction as F
from pathlib import Path
from native_motion_budget import MotionBudget
from native_query_path import traverse
from native_contact_response import rotate
from crest_terrain_query import query

def surface(q):
    return tuple(q[k] for k in ('plane','base_x','base_y','base_z'))
class Unsupported(ValueError):pass

def respond(old,distance,direction,cached,pieces=1):
    target=[F(x)+F(distance*d,16384) for x,d in zip(old,direction)]
    spans=traverse(old,target,cached)
    hits=[(a,b,k) for a,b,k in spans if k[4]<0]
    if not hits:return None
    start,end,key=hits[0]
    midpoint=(start+end)/2
    sample=[int((F(x)+(y-x)*midpoint)//64)*64 for x,y in zip(old,target)]
    hit=query(sample,cached)
    tangent=tuple(hit['matrix'+str(i)] for i in (6,7,8))
    ledger=MotionBudget(distance)
    def advance(a,b,d):
        if a==b:return
        for i in range(1,pieces+1):ledger.advance(a+(b-a)*F(i,pieces),d)
    advance(F(0),start,direction)
    contact_exact=[F(x)+v for x,v in zip(old,ledger.exact_world)]
    remaining_end=[x+F(distance,16384)*(1-start)*d for x,d in zip(contact_exact,tangent)]
    # Check the actual redirected path, not the original endpoint surface.
    redirected=traverse(contact_exact,remaining_end,cached)
    if any(k[:4]!=key[:4] for a,b,k in redirected):
        raise Unsupported('Remaining tangent movement crosses a terrain face')
    advance(start,F(1),tangent)
    candidate=[x+d for x,d in zip(old,ledger.displacement)]
    q=query(candidate,cached)
    if surface(q)!=surface(hit):raise Unsupported('Rounded endpoint changes face')
    matrix=[hit['matrix'+str(i)] for i in range(9)]
    push=rotate([0,-q['clearance']*64,0],matrix) if q['clearance']<0 else [0,0,0]
    ledger.push(push)
    final=[x+d for x,d in zip(old,ledger.displacement)]
    fresh=query(final,cached)
    if surface(fresh)!=surface(hit):raise Unsupported('Normal correction changes face')
    assert ledger.remaining_distance==0 and sum(s['distance'] for s in ledger.spans)==distance
    return dict(time=str(start),position=final,push=push,clearance=fresh['clearance'],
                tangent_budget=str(distance*(1-start)),remainder=[str(v) for v in ledger.remainder])

def main():
    import struct
    from contact_body_predictor import wheel as wheel50
    from native20_contact_model import wheel as wheel20
    root=Path('tmp/prof');reports=[]
    for rate,name in ((20,'native20-contact-model'),(50,'contact-prediction-d9')):
        cap=root/name;r=json.loads((cap/'prediction.json').read_text())['records']
        meta=json.loads((cap/'anchor.json').read_text());memory=(cap/'memory.bin').read_bytes()
        car=meta['data_base']+0x7ffe-0x92e-meta['memory_base']
        entries={e[0]:e for e in r['ENTRY']};first=min(entries)
        finals={(v[0],v[1]):v[2:5] for v in r['FINAL']}
        stats=collections.Counter();rows=[]
        for row in r['SELECT']:
            if row['velocity'] or row['velocity_fraction'] or row['correction'] or row['clearance']>0:continue
            t,w=row['tick'],row['wheel'];old=[row['old_world_'+a] for a in 'xyz']
            cached=list(struct.unpack_from('>3h',memory,car+0x74+6*w)) if t==first else [v>>6 for v in finals[t-1,w]]
            direction=entries[t][10:13]
            stats['eligible_prescribed_zero_gravity_paths']+=1
            try:
                result=respond(old,row['distance'],direction,cached)
                if result is None:
                    stats['no_negative_interval']+=1;continue
                for parts in (2,5):assert respond(old,row['distance'],direction,cached,parts)==result
            except Unsupported as exc:
                stats[str(exc)]+=1;continue
            native=(wheel20 if rate==20 else wheel50)(row)
            delta=[x-y for x,y in zip(result['position'],native['position'])]
            stats['resolved']+=1;stats['subdivision_checks']+=2
            stats['changed_native_endpoint']+=any(delta)
            stats['negative_after_response']+=result['clearance']<0
            stats['positive_after_response']+=result['clearance']>0
            stats['nonzero_contact_time']+=F(result['time'])>0
            rows.append(dict(tick=t,wheel=w,native_branch=native['branch'],delta=delta,**result))
        reports.append(dict(rate=rate,counts=dict(stats),rows=rows))
    report=dict(rates=reports,scope='Frozen zero-gravity first-contact response only. Initial source rows have zero gravity velocity and nonpositive endpoint query. Not a recurrent trajectory or a complete force/contact solver; response may leave positive clearance and does not yet acquire support.')
    (root/'native-contact-event-probe.json').write_text(json.dumps(report,indent=2)+'\n')
    for r in reports:print(r['rate'],r['counts'])
if __name__=='__main__':main()
