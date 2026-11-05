#!/usr/bin/env python3
"""Straight-Z fractional reference with exact upward/downward Y-cell events.

Geometric penetration resolution remains deferred to one native endpoint.
Boundary chatter, unsupported topology and high impacts remain explicit errors.
"""
import math
from coupled_contact_reference import cell_clearance,surface_switch,Unsupported,H

def parameters(r):
    old=[float(r['old_world_'+a]) for a in 'xyz']
    delta=[r['world_'+a]-r['old_world_'+a] for a in 'xyz']
    if delta[0]!=0 or delta[2]<=0:raise Unsupported('Requires stationary X and increasing Z')
    return old,delta,r['velocity']+r['velocity_fraction']/5,21 if r['wheel']<2 else 15

def roots(a,b,c):
    if abs(a)<1e-18:return [] if abs(b)<1e-18 else [-c/b]
    disc=b*b-4*a*c
    if disc<0:return []
    q=-.5*(b+math.copysign(math.sqrt(disc),b))
    return [-b/(2*a)] if q==0 else [q/a,c/q]

def event_integrate(r,previous=None,*,defer_penetration=False,step_h=H):
    pos,delta,v,acc=parameters(r);cells=[math.floor(x/64) for x in pos]
    t=0.;down=0.;events=[];switch=surface_switch(r,previous);zero_events=0
    for _ in range(1024):
        active=previous if switch is not None and t<switch-1e-12 else r
        c=cell_clearance(active,cells)
        if c<0 and not defer_penetration:raise Unsupported('Penetration requires endpoint ownership')
        if c<=0:
            if v>250:raise Unsupported('High-impact contact needs explicit handling')
            v=0.
        remaining=1-t
        if remaining<1e-12:break
        air=c>0;a=-acc*step_h*step_h/2 if air else 0.
        b=delta[1]-step_h*(v+acc/2) if air else delta[1]
        z_dt=((cells[2]+1)*64-pos[2])/delta[2]
        if z_dt<=0:raise Unsupported('Invalid Z-cell ownership')
        plane_dt=switch-t if switch is not None and t<switch-1e-12 else remaining
        dt=min(z_dt,plane_dt,remaining);direction=0;boundary=None
        for sign,target in ((-1,64*cells[1]),(1,64*(cells[1]+1))):
            for tau in roots(a,b,pos[1]-target):
                derivative=b+2*a*tau
                if tau>=-1e-12 and tau<=dt+1e-12 and sign*derivative>1e-10:
                    tau=max(0.,tau)
                    if tau<=dt:dt=tau;direction=sign;boundary=target
        zero_events=zero_events+1 if dt<1e-12 else 0
        if zero_events>4:raise Unsupported('Opposing cell vector fields: contact-boundary chatter requires a support law')
        fall=step_h*dt*v+acc*(step_h*dt)*(step_h*dt+1)/2 if air else 0.
        pos[1]+=delta[1]*dt-fall;pos[2]+=delta[2]*dt;down+=fall
        if air:v+=acc*step_h*dt
        t+=dt
        if direction:pos[1]=float(boundary);cells[1]+=direction
        if abs(dt-z_dt)<1e-10:cells[2]+=1;pos[2]=float(64*cells[2])
        events.append(dict(time=t,clearance=c,plane=active['plane'],velocity=v,downward=down,y=pos[1],z=pos[2],y_direction=direction))
    else:raise Unsupported('Event budget exhausted')
    return dict(velocity=v,downward=down,position=pos,events=events,surface_switch_fraction=switch)

def sampled_integrate(r,n,previous=None,*,defer_penetration=False,step_h=H):
    pos,delta,v,acc=parameters(r);down=0.;dt=1/n;h=step_h*dt;switch=surface_switch(r,previous)
    for i in range(n):
        midpoint=[pos[j]+delta[j]*dt/2 for j in range(3)]
        active=previous if switch is not None and (i+.5)/n<switch else r
        c=cell_clearance(active,[math.floor(x/64) for x in midpoint])
        if c<0 and not defer_penetration:raise Unsupported('Sampled penetration')
        if c<=0:
            if v>250:raise Unsupported('Sampled high-impact contact')
            v=0.;d=0.
        else:d=h*v+acc*h*(h+1)/2;v+=acc*h
        pos[1]+=delta[1]*dt-d;pos[2]+=delta[2]*dt;down+=d
    c=cell_clearance(r,[math.floor(x/64) for x in pos])
    if c==0 or (defer_penetration and c<0):v=0.
    return dict(velocity=v,downward=down,position=pos)
