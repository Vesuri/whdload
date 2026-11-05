"""Exact cell-boundary traversal of a prescribed linear native wheel path.

Queries use current track data and fixed cached coordinates. This is geometry,
not a gravity/contact integrator; no response is deferred or applied here.
"""
from fractions import Fraction as F
from crest_terrain_query import query

def signature(q):return tuple(q[k] for k in ('plane','base_x','base_y','base_z','clearance','plane_flags','barrier','surface'))
def merge(spans):
    result=[]
    for a,b,key in spans:
        if result and result[-1][2]==key and result[-1][1]==a:result[-1]=(result[-1][0],b,key)
        else:result.append((a,b,key))
    return result

def boundaries(old,new):
    old=list(map(F,old));new=list(map(F,new));delta=[b-a for a,b in zip(old,new)];times={F(0),F(1)}
    for a,b,d in zip(old,new,delta):
        if not d:continue
        lo,hi=sorted((a,b))
        for cell in range(int(lo//64),int(hi//64)+2):
            t=(64*cell-a)/d
            if 0<t<1:times.add(t)
    return sorted(times)

def traverse(old,new,cached):
    old=list(map(F,old));new=list(map(F,new));delta=[b-a for a,b in zip(old,new)]
    times=boundaries(old,new);spans=[]
    for a,b in zip(times,times[1:]):
        mid=(a+b)/2
        point=[int((v+d*mid)//64)*64 for v,d in zip(old,delta)]
        spans.append((a,b,signature(query(point,cached))))
    assert sum(b-a for a,b,k in spans)==1
    return merge(spans)

def divided(old,new,cached,pieces):
    spans=[]
    for i in range(pieces):
        a=F(i,pieces);b=F(i+1,pieces)
        first=[F(x)+(y-x)*a for x,y in zip(old,new)];last=[F(x)+(y-x)*b for x,y in zip(old,new)]
        spans.extend((a+(b-a)*lo,a+(b-a)*hi,key) for lo,hi,key in traverse(first,last,cached))
    return merge(spans)

def point_events(old,new,cached):
    events=[]
    for t in boundaries(old,new):
        point=[int((F(x)+(y-x)*t)//64)*64 for x,y in zip(old,new)]
        events.append((t,signature(query(point,cached))))
    return events
