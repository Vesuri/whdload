#!/usr/bin/env python3
"""Reference gravity/reset flow on a prescribed quantized contact segment.

This is an integration primitive, NOT a coupled wheel/terrain solver. Geometry
is prescribed; gravity displacement is not fed back into cell-crossing times.
"""
from fractions import Fraction as F
import json
from pathlib import Path

def integrate(intervals,velocity,acceleration,duration=F(2,5)):
    """Compose native ordered-pair flow, resetting velocity at contact.

    Intervals are (start,end,clearance) in normalized segment time. Negative
    clearance requires the penetration solver and is deliberately unsupported.
    All contacts clear velocity; positive intervals accumulate displacement.
    """
    v=F(velocity);a=F(acceleration);down=F(0);cursor=F(0);resets=0
    for start,end,clearance in intervals:
        assert start==cursor and start<end<=1
        if clearance<0:raise ValueError('Penetration resolution required')
        if clearance==0:v=F(0);resets+=1
        else:
            h=duration*(end-start)
            down+=h*v+a*h*(h+1)/2
            v+=a*h
        cursor=end
    assert cursor==1
    return v,down,resets

def main():
    # Splitting a continuous flight must not change the integration.
    for v in (F(-7,5),F(0),F(106,5)):
        for a in (15,21):
            full=integrate([(F(0),F(1),1)],v,a)
            split=integrate([(F(0),F(1,7),1),(F(1,7),F(4,5),1),(F(4,5),F(1),1)],v,a)
            assert full==split
    assert integrate([(F(0),F(1),0)],F(99),21)==(0,0,1)
    v,d,n=integrate([(F(0),F(1,2),1),(F(1,2),F(3,4),0),(F(3,4),F(1),1)],F(0),21)
    assert v==F(21,10) and d==F(147,40) and n==1
    p=Path('tmp/prof');cells=json.loads((p/'contact-cell-segments.json').read_text())['captures'];report={}
    for name,rows in cells.items():
        live=json.loads((p/name/'takeoff-plane.json').read_text())['rows'];selected={(r['tick'],r['wheel']):r for r in live if r['event']=='SELECT'};after={(r['tick'],r['wheel']):r for r in live if r['event']=='AFTER'};results=[]
        for row in rows:
            key=row['tick'],row['wheel'];r=selected[key];intervals=[(F(c['start']),F(c['end']),c['clearance']) for c in row['intervals']]
            if any(c<0 for _,_,c in intervals):continue
            old=F(r['velocity'])+F(r['velocity_fraction'],5);acc=21 if r['wheel']<2 else 15
            v,d,n=integrate(intervals,old,acc);actual=after[key];observed=F(actual['velocity'])+F(actual['velocity_fraction'],5)
            results.append(dict(tick=key[0],wheel=key[1],old_velocity=str(old),reference_velocity=str(v),reference_downward=str(d),observed_velocity_after_gravity_stage=str(observed),reset_intervals=n,endpoint_clearance=row['endpoint_clearance']))
        report[name]=results
    result=dict(captures=report,scope='Prescribed-segment gravity/reset reference only. Negative-clearance intervals are excluded because they require native penetration resolution. Observed AFTER is before later contact-zeroing, so endpoint-zero velocity comparisons must account for that stage. No geometry feedback, displacement clamp, retry/topology, replay or runtime acceptance.')
    (p/'contact-interval-reference.json').write_text(json.dumps(result,indent=2)+'\n')
    for name,rows in report.items():
        print(name,'eligible segments',len(rows))
        for r in rows:
            if name=='release-second-step50' and (r['tick'],r['wheel']) in ((702,2),(704,0),(705,0),(706,2),(707,2)):print(r)
if __name__=='__main__':main()
