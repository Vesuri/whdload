#!/usr/bin/env python3
"""Native-compatible straight-direction contact response reference.

Independently traced full-tangent, crossing and backoff64 branches are supported.
Callers supply a SINGLE movement span, not a repeatedly reused full tick.
No clock, game memory or filesystem output is mutated by resolve().
"""
import struct
from pathlib import Path
from fractions import Fraction
raw=(Path(__file__).resolve().parents[1]/'tmp/game/4DSportsDriving_v1.2_1461/4DSportsDriving/data/stunts').read_bytes()
data=0x3a1dc+0x7ffe
angles=raw[data-0x386c:data-0x386c+257]
sines=struct.unpack_from('>257h',raw,data-0x376a)
def atan_native(x,y):
 octant=(4 if x<0 else 0)+(2 if y<0 else 0);x,y=abs(x),abs(y)
 if x==y:
  if not x:return 0
  angle=128
 else:
  if x>y:x,y=y,x;octant+=1
  quotient=(x<<16)//y;angle=angles[(quotient>>8)+((quotient>>7)&1)]
 return (angle,256-angle,512-angle,256+angle,-angle,angle-256,angle-512,-256-angle)[octant]
def sine(a):
 a&=1023
 return sines[a] if a<=256 else sines[512-a] if a<=512 else -sines[a-512] if a<=768 else -sines[1024-a]
def length2(x,y):
 a=abs(atan_native(x,y))
 if a>=256:a=512-a
 return (abs(y)<<14)//sine(a+256) if a<=128 else (abs(x)<<14)//sine(a)
def length3(v):return length2(v[1],length2(v[0],v[2]))
def word(x):return (x+32768)%65536-32768
def trunc(x,d):return (abs(x)//abs(d))*(1 if x*d>=0 else -1)
def vec(r,prefix):return [r[prefix+'_'+a] for a in 'xyz']
def rotate(v,m):return [word(sum(v[j]*m[3*j+i] for j in range(3))//16384) for i in range(3)]
def classify(r):
 old,new=r['old_plane_y'],r['new_plane_y'];deep=not r['plane_flags'] and old<-12 and new<-12
 if deep and new<=-24:return 'retry_flat'
 if new==0:return 'backoff64'
 if old>0 and new<0:return 'crossing'
 return 'full_tangent'
def plane(r,v):
 d=[word(word(x>>6)-o) for x,o in zip(v,vec(r,'origin'))]
 return d[1] if r['plane']<4 else word(trunc(sum(x*n for x,n in zip(d,vec(r,'normal'))),8192))

class UnsupportedContact(ValueError):pass

def resolve(old,new,geometry,forward_distance,downward_displacement,impact_velocity,impact_flags=0,*,coherent_clearance=False):
    old=list(old);new=list(new);r=dict(geometry)
    if any(type(x) is not int for x in old+new):raise UnsupportedContact('Native coordinate conversion must be explicit')
    if not 0<=forward_distance<=32767:raise UnsupportedContact('Forward distance outside supported signed-word range')
    if impact_velocity>0x5aeb:raise UnsupportedContact('Hard-crash event unvalidated')
    for prefix,v in [('old',old),('new',new)]:
        for a,x in zip('xyz',v):r[prefix+'_'+a]=x
    if plane(r,new)>=0:raise UnsupportedContact('Response requires negative candidate clearance')
    m=[r[f'matrix{i}'] for i in range(9)];inverse=[m[3*j+i] for i in range(3) for j in range(3)]
    for prefix,v in [('old_plane',old),('new_plane',new)]:
        local=[word(word(x>>6)-o) for x,o in zip(v,vec(r,'origin'))]
        for a,x in zip('xyz',rotate(local,inverse)):r[prefix+'_'+a]=x
    if coherent_clearance:
        r['old_plane_y']=plane(r,old);r['new_plane_y']=plane(r,new)
    if not r['plane_flags'] and r['old_plane_y']<-12 and -24<r['new_plane_y']<-12:
        raise UnsupportedContact('Native crash-reason5 path unvalidated')
    branch=classify(r)
    if branch=='backoff64':
        # CE3E..CE98 subtracts a surface-aligned 64-unit vector from the
        # candidate, then bypasses requery/push and enters impact handling.
        backoff=rotate([0,0,64],m)
        final=[a-b for a,b in zip(new,backoff)]
        return dict(branch=branch,backoff=backoff,position=final,
                    recomputed_clearance=plane(r,final),stored_clearance=plane(r,new),
                    velocity=0,impact_flags=impact_flags | (32 if impact_velocity>250 else 0))
    if branch not in ('full_tangent','crossing'):raise UnsupportedContact(branch)
    intersection=None;total=None;rest=None
    if branch=='full_tangent':projected=forward_distance;straight=[0,0,0]
    else:
        ov=vec(r,'old_plane');nv=vec(r,'new_plane')
        ov=[ov[0],ov[2],word(-ov[1])];nv=[nv[0],nv[2],word(-nv[1])]
        numerator=word(-ov[2]);denominator=word(nv[2]-ov[2])
        if denominator<0:numerator=(numerator&65535)>>1;denominator=(denominator&65535)>>1
        if denominator<=0:raise UnsupportedContact('Invalid intersection denominator')
        intersection=[word(ov[i]+trunc(word(nv[i]-ov[i])*numerator,denominator)) for i in (0,1)]+[0]
        projected=length3([word((b-a)*64) for a,b in zip(intersection,nv)])
        total=word(downward_displacement+forward_distance);rest=word(total-projected)
        if total<=0 or not 0<=rest<=total:raise UnsupportedContact('Nonphysical span ratio or signed-word overflow')
        straight=[word(trunc((b-a)*rest,total)) for a,b in zip(old,new)]
    tangent=rotate([0,0,projected],m)
    candidate=[a+b+c for a,b,c in zip(old,straight,tangent)]
    residual=plane(r,candidate)
    push=rotate([0,word(-residual*64),0],m) if residual<0 else [0,0,0]
    final=[a+b for a,b in zip(candidate,push)]
    return dict(branch=branch,intersection=intersection,total=total,rest=rest,projected_distance=projected,
                straight=straight,tangent=tangent,before_push=candidate,push=push,position=final,
                recomputed_clearance=plane(r,final),stored_clearance=residual,velocity=0,
                impact_flags=impact_flags | (32 if impact_velocity>250 else 0))

class MovementBudget:
    """Exact step-time ledger and telescoping integer forward-distance budget.

    Issuing a span consumes that time once. A response cannot issue it again.
    This does not decide where contact/surface events should split the step.
    """
    def __init__(self,distance):
        if type(distance) is not int or distance<0:raise ValueError('Nonnegative integer distance required')
        self.distance=distance;self.cursor=Fraction(0);self.delivered=0
    def consume_to(self,end):
        end=Fraction(end)
        if not self.cursor<end<=1:raise ValueError('Time span overlaps or exceeds the current step')
        cumulative=(self.distance*end.numerator)//end.denominator
        span=dict(start=self.cursor,end=end,forward_distance=cumulative-self.delivered)
        self.cursor=end;self.delivered=cumulative
        return span
