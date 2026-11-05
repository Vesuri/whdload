"""Offline crossing-only movement-budget diagnostic; native force/suspension.

Resolve the frozen start/end segment at its exact surface-matrix plane
intersection, then consume only remaining forward distance on the tangent.
This does not yet locate a ballistic event or unify support/force ownership.
"""
from fractions import Fraction as F
from contact_body_predictor import body,wheel
from native_contact_response import rotate,plane,word,UnsupportedContact
from crest_terrain_query import query
from supported_plane_model import geometry

def solve(entry,build,rows,state):
    def response(row):
        out=wheel(row)
        if out['branch']!='crossing':return out
        old=[row['old_world_'+a] for a in 'xyz']
        end=[row['world_'+a] for a in 'xyz'];end[1]-=out['down']
        m=[row['matrix'+str(i)] for i in range(9)]
        origin=[64*word(row['base_'+a]+row['node_'+a]) for a in 'xyz']
        # Native collision transforms world into the surface frame. Its Y row
        # is original matrix row1; query normals are separately quantized.
        heights=[sum((x-o)*n for x,o,n in zip(v,origin,m[3:6])) for v in (old,end)]
        if not heights[0]>0>heights[1]:raise UnsupportedContact(('No strict continuous crossing',row['tick'],row['wheel'],heights))
        fraction=F(heights[0],heights[0]-heights[1]);remaining=1-fraction
        straight=[F(b-a)*fraction for a,b in zip(old,end)]
        tangent=[F(row['distance'])*remaining*v/16384 for v in m[6:9]]
        before=[int((F(a)+b+c)//1) for a,b,c in zip(old,straight,tangent)]
        fresh=query(before,state['cached'][row['wheel']])
        if geometry(fresh)!=geometry(row):raise UnsupportedContact('Crossing budget changed terrain face')
        q=fresh['clearance'];push=rotate([0,word(-q*64),0],m) if q<0 else [0,0,0]
        final=[a+b for a,b in zip(before,push)]
        endpoint=query(final,state['cached'][row['wheel']])
        if geometry(endpoint)!=geometry(row):raise UnsupportedContact('Crossing normal push changed terrain face')
        out.update(position=final,clearance=q,branch='budget_crossing',crossing_fraction=str(fraction),remaining_forward=str(F(row['distance'])*remaining),crossing_push=push,native_position=out['position'])
        return out
    return body(entry,build,rows,wheel_solver=response)
