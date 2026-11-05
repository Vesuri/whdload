#!/usr/bin/env python3
"""Experimental continuous support with native-calibrated release state.

Support follows the actual query normal with the issued arc-distance budget.
Air follows the existing modified constant-gravity flow. Topology is restricted
explicitly to two continuous nonvertical Z planes and increasing forward motion.
"""
import math
from contact_interval_general import roots
from coupled_contact_reference import Unsupported,word,H

def plane(r):
    origin=[64*word(r['base_'+a]+r['node_'+a]) for a in 'xyz']
    n=[r['normal_'+a] for a in 'xyz'] if r['plane']>=4 else [0,8192,0]
    if n[0]!=0 or n[1]<=0:raise Unsupported('Requires nonvertical straight-Z plane')
    norm=math.hypot(n[1],n[2]);slope=-n[2]/n[1]
    return dict(origin=origin,normal=n,norm=norm,slope=slope,intercept=origin[1]-slope*origin[2])

def integrate(r,previous=None,step_h=H):
    old=[float(r['old_world_'+a]) for a in 'xyz'];delta=[r['world_'+a]-r['old_world_'+a] for a in 'xyz']
    if delta[0]!=0 or delta[2]<=0 or r['distance']<=0:raise Unsupported('Requires straight forward issued motion')
    current=plane(r);before=plane(previous) if previous else current;crease=None
    if (before['slope'],before['intercept'])!=(current['slope'],current['intercept']):
        if before['slope']==current['slope']:raise Unsupported('Discontinuous parallel surfaces')
        crease=(current['intercept']-before['intercept'])/(before['slope']-current['slope'])
        if not old[2]<crease<r['world_z']:raise Unsupported('Plane seam outside observed movement')
    pos=old[:];v=r['velocity']+r['velocity_fraction']/5;acc=21 if r['wheel']<2 else 15
    t=0.;events=[];projections=[];switched=crease is None
    for _ in range(32):
        surface=current if switched else before;n=surface['normal'];norm=surface['norm'];o=surface['origin']
        clearance=sum((x-y)*z for x,y,z in zip(pos,o,n))/norm
        # Existing free-flow state has normal speed proportional to
        # dy - h*(v+a/2). Inelastic contact cancels THAT speed, not v alone.
        contact_v=(n[1]*delta[1]+n[2]*delta[2])/(n[1]*step_h)-acc/2
        if clearance < -1e-8:
            if v>250:raise Unsupported('High-impact initial penetration')
            correction=[-clearance*z/norm for z in n];pos=[x+y for x,y in zip(pos,correction)];v=min(v,contact_v)
            projections.append(dict(time=t,vector=correction));clearance=0.
        a=-.5*n[1]*acc*step_h*step_h/norm
        b=(n[1]*(delta[1]-step_h*(v+acc/2))+n[2]*delta[2])/norm
        supported=clearance<=1e-8 and b<=1e-8
        dt=1-t;impact=False;switch=False
        if dt<1e-12:break
        if supported:
            v=contact_v;motion=[0.,-n[2]*r['distance']/norm,n[1]*r['distance']/norm]
            if not switched:
                seam_dt=(crease-pos[2])/motion[2]
                if seam_dt < -1e-10:raise Unsupported('Projection crossed surface seam')
                if seam_dt<=dt:dt=max(0.,seam_dt);switch=True
            pos=[x+y*dt for x,y in zip(pos,motion)]
        else:
            if not switched:
                seam_dt=(crease-pos[2])/delta[2]
                if seam_dt < -1e-10:raise Unsupported('Air starts beyond surface seam')
                if seam_dt<=dt:dt=max(0.,seam_dt);switch=True
            contacts=[tau for tau in roots(a,b,clearance) if tau>1e-10 and tau<=dt and b+2*a*tau<0]
            if contacts:dt=min(contacts);impact=True;switch=False
            fall=step_h*dt*v+acc*(step_h*dt)*(step_h*dt+1)/2
            pos=[pos[0],pos[1]+delta[1]*dt-fall,pos[2]+delta[2]*dt];v+=acc*step_h*dt
        t+=dt
        events.append(dict(time=t,duration=dt,supported=supported,impact=impact,switch=switch,position=pos[:],velocity=v))
        if impact:
            if v>250:raise Unsupported('High-impact event requires general response')
            v=contact_v
        if switch:
            switched=True
            if supported:
                # Native contact clears its gravity accumulator. The temporary
                # normal constraint reaction belongs to geometric support, not
                # to the persistent native gravity state on the released span.
                v=0.
                events[-1]['release_gravity_reset']=True
        if dt<1e-12 and not switch:raise Unsupported('Non-progressing contact event')
    else:
        error=Unsupported('Contact event budget exhausted');error.events=events;error.position=pos;error.velocity=v;raise error
    if abs(t-1)>1e-9:raise Unsupported('Incomplete time budget')
    n=current['normal'];o=current['origin'];q=sum((x-y)*z for x,y,z in zip(pos,o,n))/8192/64
    if q < -1e-8:raise Unsupported('Endpoint remains penetrating')
    is_support=bool(events[-1]['supported'] or events[-1]['impact'])
    return dict(position=pos,velocity=0. if is_support else v,supported=is_support,clearance_units=q,events=events,projections=projections,
                time_sum=sum(e['duration'] for e in events))
