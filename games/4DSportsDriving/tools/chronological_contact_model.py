"""Offline chronological native-cell force/first-impact wheel experiment.

Within a step, gravity evolves only in positive cells and resets at zero.
First penetration consumes the remaining forward span on the contacted tangent.
Multiple-face supported motion and boundary chatter are explicit exclusions.
Floating event roots are a diagnostic, not a runtime implementation.
"""
import math
from contact_interval_general import roots
from contact_body_predictor import body
from native_contact_response import rotate,word,UnsupportedContact
from crest_terrain_query import query
from native_query_path import traverse
from supported_plane_model import geometry

def advance(row,cached):
    if row['correction']:raise UnsupportedContact('Roof correction')
    old=[row['old_world_'+a] for a in 'xyz'];delta=[row['world_'+a]-v for a,v in zip('xyz',old)]
    if delta[0] or delta[2]<=0:raise UnsupportedContact('Requires stationary X, increasing Z')
    pos=list(map(float,old));pos[1]-=row['position_fraction']/25;cells=[math.floor(v/64) for v in pos]
    v=row['velocity']+row['velocity_fraction']/5;acc=21 if row['wheel']<2 else 15
    h=.4;t=0.;events=[];zero_events=0;down=0.;impact=None
    for _ in range(1024):
        q=query([64*c for c in cells],cached);c=q['clearance']
        if c<0:impact=q;break
        if c==0:v=0.
        if t>=1-1e-12:break
        air=c>0;a=-acc*h*h/2 if air else 0.;b=delta[1]-h*(v+acc/2) if air else delta[1]
        z_dt=((cells[2]+1)*64-pos[2])/delta[2]
        if z_dt<=0:raise UnsupportedContact('Invalid Z ownership')
        dt=min(z_dt,1-t);direction=0;boundary=None
        for sign,target in ((-1,64*cells[1]),(1,64*(cells[1]+1))):
            for tau in roots(a,b,pos[1]-target):
                if -1e-12<=tau<=dt+1e-12 and sign*(b+2*a*tau)>1e-10:
                    tau=max(0.,tau)
                    if tau<=dt:dt=tau;direction=sign;boundary=target
        zero_events=zero_events+1 if dt<1e-12 else 0
        if zero_events>4:raise UnsupportedContact(('Contact boundary chatter',row['tick'],row['wheel'],pos,c))
        fall=h*dt*v+acc*(h*dt)*(h*dt+1)/2 if air else 0.
        pos[1]+=delta[1]*dt-fall;pos[2]+=delta[2]*dt;down+=fall
        if air:v+=acc*h*dt
        t+=dt
        if direction:pos[1]=float(boundary);cells[1]+=direction
        if abs(dt-z_dt)<1e-10:cells[2]+=1;pos[2]=float(64*cells[2])
        events.append(dict(time=t,clearance=c,plane=q['plane'],velocity=v,position=pos.copy()))
    else:raise UnsupportedContact('Event budget exhausted')
    if impact is not None:
        remaining=1-t;m=[impact['matrix'+str(i)] for i in range(9)]
        exact=[x+row['distance']*remaining*d/16384 for x,d in zip(pos,m[6:9])]
        end=[math.floor(x) for x in exact]
        spans=traverse(pos,exact,cached)
        surface=tuple(impact[k] for k in ('plane','base_x','base_y','base_z'))
        if any(key[:4]!=surface for a,b,key in spans):raise UnsupportedContact('Supported path crosses terrain face')
        q=query(end,cached)
        if geometry(q)!=geometry(impact):raise UnsupportedContact('Supported remainder crosses terrain face')
        # A collision correction does not spend forward distance/time.
        c=q['clearance'];push=rotate([0,word(-c*64),0],m) if c<0 else [0,0,0]
        end=[x+d for x,d in zip(end,push)]
        if geometry(query(end,cached))!=geometry(impact):raise UnsupportedContact('Normal push crosses terrain face')
        return dict(position=end,clearance=c,suspension_clearance=c,velocity=0,vf=0,pf=0,ef=0,branch='chronological_contact',applied_gravity=down>0,down=down,event_time=t,events=events)
    assert abs(t-1)<1e-9
    end=[math.floor(x+1e-9) for x in pos];end[1]=math.ceil(pos[1]-1e-9)
    pf=25*(end[1]-pos[1]);c=query(end,cached)['clearance']
    # Retain full host precision for this diagnostic; no ABI representability claim.
    if c<0:raise UnsupportedContact('Rounded air endpoint penetrates')
    velocity=math.floor(v);vf=(v-velocity)*5
    if c==0:velocity=vf=pf=0
    return dict(position=end,clearance=c,suspension_clearance=c,velocity=velocity,vf=vf,pf=pf if c>0 else 0,ef=row['extension_fraction'] if c>0 else 0,branch='air' if c>0 else 'zero',applied_gravity=down>0,down=down,events=events)

def solve(entry,build,rows,state):
    return body(entry,build,rows,wheel_solver=lambda row:advance(row,state['cached'][row['wheel']]))
