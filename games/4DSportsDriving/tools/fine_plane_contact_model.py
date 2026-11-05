"""Offline geometric contact candidate using unrounded plane depth.

Native terrain selects the face, but gravity/support use raw world coordinates
instead of the native64-unit query cells. First linear-segment impact consumes
only the remaining forward distance. This is an endpoint-integrated hypothesis,
not a continuous ballistic solver or accepted runtime implementation. One face
per response is required; unsupported transitions are rejected explicitly.
"""
from fractions import Fraction
from native_contact_response import word,UnsupportedContact
from supported_plane_model import geometry,dot
from crest_terrain_query import query
from contact_body_predictor import body

def solve(entry,build,rows,state):
    def wheel(r):
        if r['correction']:raise UnsupportedContact('Roof correction')
        old=[r['old_world_'+a] for a in 'xyz'];new=[r['world_'+a] for a in 'xyz']
        origin=[word(r['base_'+a]+r['node_'+a]) for a in 'xyz'];normal=[r['normal_'+a] for a in 'xyz']
        if normal[1]<=0:raise UnsupportedContact('Non-upward plane')
        depth=lambda p:dot(p,origin,normal)
        v=r['velocity'];vf=r['velocity_fraction'];pf=r['position_fraction'];ef=r['extension_fraction']
        applied=depth(new)>0;down=0
        if applied:
            a=21 if r['wheel']<2 else 15
            down,pf=divmod(10*v+2*vf+7*a+pf,25)
            dv,vf=divmod(2*a+vf,5);v=word(v+dv);new[1]-=down
        before=depth(new)
        # Directed rounding removes the zero band only for nonzero raw depth.
        # Suspension still receives coarse plane units, with native limits.
        scale=8192*64
        clearance=(abs(before)+scale-1)//scale*(1 if before>0 else -1) if before else 0
        if before<=0:
            start=depth(old)
            fraction=Fraction(start,start-before) if start>0 else Fraction(0)
            m=[r['matrix'+str(i)] for i in range(9)]
            exact=[Fraction(x)+fraction*(y-x)+(1-fraction)*r['distance']*d/16384 for x,y,d in zip(old,new,m[6:9])]
            norm=sum(n*n for n in normal);penetration=depth(exact)
            if penetration<0:exact=[x-Fraction(penetration*n,norm) for x,n in zip(exact,normal)]
            final=[x.numerator//x.denominator for x in exact]
            residual=depth(final)
            if residual<0:final[1]+=(-residual+normal[1]-1)//normal[1]
            if geometry(query(final,state['cached'][r['wheel']]))!=geometry(r):raise UnsupportedContact('Response crosses selected terrain face')
            assert depth(final)>=0
            new=final;v=vf=pf=ef=0;branch='fine_contact'
        else:branch='air'
        return dict(position=new,clearance=clearance,suspension_clearance=clearance,velocity=v,vf=vf,pf=pf,ef=ef,branch=branch,applied_gravity=applied,down=down)
    return body(entry,build,rows,wheel_solver=wheel)
