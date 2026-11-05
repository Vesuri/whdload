#!/usr/bin/env python3
"""Event-driven reference for monotone wheel contact across continuousZ planes.

Gravity feeds back into Y-cell crossing times. Native zero contact resets
velocity without moving the wheel. Negative clearance is returned to the
caller as unsupported penetration; it is never silently clamped.
"""
import json,math
from pathlib import Path
H=.4
class Unsupported(Exception):pass

def word(v):return (v+32768)%65536-32768
def cell_clearance(r,cells):
    d=[word(word(c)-r['base_'+a]-r['node_'+a]) for a,c in zip('xyz',cells)]
    if r['plane']<4:return d[1]
    n=sum(v*r['normal_'+a] for a,v in zip('xyz',d))
    return word((abs(n)//8192)*(1 if n>=0 else -1))
def parameters(r):
    old=[float(r['old_world_'+a]) for a in 'xyz'];delta=[r['world_'+a]-r['old_world_'+a] for a in 'xyz']
    if delta[0]!=0 or delta[1]<=0 or delta[2]<=0:raise Unsupported('Requires stationaryX/increasingY/increasingZ')
    return old,delta,r['velocity']+r['velocity_fraction']/5,21 if r['wheel']<2 else 15

def surface_switch(r,previous):
    if previous is None:return None
    def coefficients(q):
        if q['plane']<4:return 0.,float(64*(q['base_y']+q['node_y']))
        if q['normal_x']!=0 or q['normal_y']<=0:raise Unsupported('NonverticalZ crest requires general topology')
        slope=-q['normal_z']/q['normal_y']
        return slope,64*(q['base_y']+q['node_y'])-slope*64*(q['base_z']+q['node_z'])
    a,b=coefficients(previous);c,d=coefficients(r)
    if (a,b)==(c,d):return None
    if a==c:raise Unsupported('Discontinuous parallel surfaces')
    z=(d-b)/(a-c);t=(z-r['old_world_z'])/(r['world_z']-r['old_world_z'])
    if not 0<t<1:raise Unsupported('Plane change has no crease within segment')
    return t

def event_integrate(r,previous=None,*,defer_penetration=False,step_h=H):
    # Experimental deferred mode treats interior nonpositive cells as support
    # for gravity only. It does NOT geometrically resolve or clamp them. Its
    # caller must explicitly handle the final candidate once, using the whole
    # step's original movement. Default mode still rejects all penetration.
    pos,delta,v,acc=parameters(r);cells=[math.floor(x/64) for x in pos];t=0.;down=0.;events=[];switch=surface_switch(r,previous)
    for _ in range(256):
        active=previous if switch is not None and t<switch-1e-12 else r
        c=cell_clearance(active,cells)
        if c<0 and not defer_penetration:raise Unsupported(f'Penetration at time fraction {t:.12f}')
        if c<=0:
            if v>250:raise Unsupported('Native impact event requires handling')
            v=0.
        remaining=1-t
        if remaining<1e-12:break
        airborne=c>0
        if airborne and delta[1]-step_h*(v+acc/2)-acc*step_h*step_h*remaining<=0:raise Unsupported('NonmonotoneY needs additional turning events')
        def fall(dt):return step_h*dt*v+acc*(step_h*dt)*(step_h*dt+1)/2 if airborne else 0.
        z_dt=((cells[2]+1)*64-pos[2])/delta[2]
        assert z_dt>0,(t,z_dt,pos,cells)
        plane_dt=switch-t if switch is not None and t<switch-1e-12 else remaining
        dt=min(z_dt,remaining,plane_dt);next_y=(cells[1]+1)*64;y_event=False
        if pos[1]+delta[1]*dt-fall(dt)>=next_y:
            lo,hi=0.,dt
            for _ in range(60):
                mid=(lo+hi)/2
                if pos[1]+delta[1]*mid-fall(mid)<next_y:lo=mid
                else:hi=mid
            dt=(lo+hi)/2;y_event=True
        assert dt>0
        d=fall(dt);pos[1]+=delta[1]*dt-d;pos[2]+=delta[2]*dt;down+=d
        if airborne:v+=acc*step_h*dt
        t+=dt
        if y_event:pos[1]=float(next_y);cells[1]+=1
        if abs(dt-z_dt)<1e-10:cells[2]+=1;pos[2]=float(64*cells[2])
        events.append(dict(time=t,clearance=c,plane=active["plane"],velocity=v,downward=down,y=pos[1],z=pos[2]))
    else:raise Unsupported('Event budget exhausted')
    return dict(velocity=v,downward=down,position=pos,events=events,surface_switch_fraction=switch)

def sampled_integrate(r,n,previous=None,*,defer_penetration=False,step_h=H):
    """Independent uniform-time, midpoint-predicate convergence check."""
    pos,delta,v,acc=parameters(r);down=0.;dt=1/n;h=step_h*dt;switch=surface_switch(r,previous)
    for i in range(n):
        midpoint=[pos[i]+delta[i]*dt/2 for i in range(3)]
        active=previous if switch is not None and (i+.5)/n<switch else r
        c=cell_clearance(active,[math.floor(x/64) for x in midpoint])
        if c<0 and not defer_penetration:raise Unsupported('Sampled penetration')
        if c<=0:
            if v>250:raise Unsupported('Native impact event requires handling')
            v=0.;d=0.
        else:d=h*v+acc*h*(h+1)/2;v+=acc*h
        pos[1]+=delta[1]*dt-d;pos[2]+=delta[2]*dt;down+=d
    end_clearance=cell_clearance(r,[math.floor(x/64) for x in pos])
    if end_clearance==0 or (defer_penetration and end_clearance<0):v=0.
    return dict(velocity=v,downward=down,position=pos)

def main():
    p=Path('tmp/prof');eligible=json.loads((p/'contact-cell-segments.json').read_text())['captures'];report={}
    for name,rows in eligible.items():
        live=json.loads((p/name/'takeoff-plane.json').read_text())['rows'];selected={(r['tick'],r['wheel']):r for r in live if r['event']=='SELECT'};results=[]
        rows=[r for r in live if r['event']=='SELECT' and (r['tick']-1,r['wheel']) in selected and r['correction']==0]
        for row in rows:
            r=selected[row['tick'],row['wheel']];item=dict(tick=r['tick'],wheel=r['wheel'])
            try:
                previous=selected[r['tick']-1,r['wheel']];result=event_integrate(r,previous);item.update(result);item['supported']=True
                # Left/right wheels are identical here: avoid redundant expensive
                # convergence runs while retaining all event-driven outputs.
                if r['wheel'] in (0,2):
                    item['sampled']={str(n):sampled_integrate(r,n,previous) for n in (1000,4000,16000)}
                    last=item['sampled']['16000'];item['fine_error']={k:abs(last[k]-result[k]) for k in ('velocity','downward')}
            except Unsupported as e:item.update(supported=False,reason=str(e))
            results.append(item)
        report[name]=results
    result=dict(captures=report,scope='Gravity-coupled position/velocity reference on recorded per-step forward displacement, supporting a derived continuousZ crease between two measured planes. Supports stationaryX/increasingY/increasingZ, zero/positive clearance and low-impact contact. Penetration, general polygon topology, retry ownership, reconstruction/suspension feedback between ticks, integer carry/replay ABI and general driving are not implemented. Floating numerical reference, not68000 runtime code.')
    (p/'coupled-contact-reference.json').write_text(json.dumps(result,indent=2)+'\n')
    for name,rows in report.items():
        good=[r for r in rows if r['supported']];checked=[r for r in good if 'fine_error' in r]
        print(name,'supported',len(good),'of',len(rows),'convergence cases',len(checked),'max fine errors',{k:max((r['fine_error'][k] for r in checked),default=0) for k in ('velocity','downward')})
        for r in rows:
            if name=='release-second-step50' and (r['tick'],r['wheel']) in ((702,2),(704,0),(705,0),(706,2),(707,2)):print({k:v for k,v in r.items() if k not in ('events','sampled')})
if __name__=='__main__':main()
