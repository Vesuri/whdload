"""Offline crossing-only movement-budget diagnostic; native force/suspension.

Resolve the frozen start/end segment at its first negative native-query interval, then consume only remaining forward distance on the tangent.
This does not yet locate a ballistic event or unify support/force ownership.
"""
from fractions import Fraction as F
from contact_body_predictor import body,wheel
from native_contact_response import rotate,plane,word,UnsupportedContact
from crest_terrain_query import query
from supported_plane_model import geometry
from native_query_path import traverse,point_events

def solve(entry,build,rows,state):
    def response(row):
        out=wheel(row)
        if out['branch']!='crossing':return out
        old=[row['old_world_'+a] for a in 'xyz']
        end=[row['world_'+a] for a in 'xyz'];end[1]-=out['down']
        m=[row['matrix'+str(i)] for i in range(9)]
        origin=[64*word(row['base_'+a]+row['node_'+a]) for a in 'xyz']
        spans=traverse(old,end,state['cached'][row['wheel']])
        hits=[(a,b,key) for a,b,key in spans if key[4]<0]
        if not hits:raise UnsupportedContact('No negative native-query interval')
        fraction,stop,key=hits[0];remaining=1-fraction
        if any(t<fraction and k[4]<0 for t,k in point_events(old,end,state['cached'][row['wheel']])):
            raise UnsupportedContact('Earlier isolated negative boundary event')
        assert 0<=fraction<1 and fraction+remaining==1
        mid=(fraction+stop)/2
        point=[int((F(a)+(b-a)*mid)//64)*64 for a,b in zip(old,end)]
        hit=query(point,state['cached'][row['wheel']])
        if geometry(hit)!=geometry(row):raise UnsupportedContact('First hit differs from endpoint terrain')
        straight=[F(b-a)*fraction for a,b in zip(old,end)]
        tangent=[F(row['distance'])*remaining*v/16384 for v in m[6:9]]
        intersection=[F(a)+b for a,b in zip(old,straight)]
        exact_end=[a+b for a,b in zip(intersection,tangent)]
        redirected=traverse(intersection,exact_end,state['cached'][row['wheel']])
        if any(k[:4]!=key[:4] for a,b,k in redirected):raise UnsupportedContact('Redirected span changes terrain face')
        before=[int(v//1) for v in exact_end]
        fresh=query(before,state['cached'][row['wheel']])
        if geometry(fresh)!=geometry(row):raise UnsupportedContact('Crossing budget changed terrain face')
        q=fresh['clearance'];push=rotate([0,word(-q*64),0],m) if q<0 else [0,0,0]
        final=[a+b for a,b in zip(before,push)]
        endpoint=query(final,state['cached'][row['wheel']])
        if geometry(endpoint)!=geometry(row):raise UnsupportedContact('Crossing normal push changed terrain face')
        out.update(position=final,clearance=q,branch='query_budget_crossing',crossing_fraction=str(fraction),remaining_forward=str(F(row['distance'])*remaining),crossing_push=push,native_position=out['position'])
        return out
    return body(entry,build,rows,wheel_solver=response)
