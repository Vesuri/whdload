"""Offline coherent acquired-depth boundary for support and airborne recontact.

Acquire native contact depth on a new face. On the same face use that boundary
for gravity activation, suspension clearance and final normal projection; retain
it during separation until the selected face changes. Native acquisition on a
new face remains unchanged. No reference impulses or extra time/distance budget.
General steering, crash side effects and edge-crossing projection are not covered.
"""
from contact_body_predictor import body,wheel as baseline
from supported_plane_model import geometry,dot
from anchored_support_model import project
from native_contact_response import word,UnsupportedContact
from crest_terrain_query import query

def solve(entry,build,rows,state):
    memory=state.setdefault('acquired_boundary',[None]*4)
    def wheel(r):
        w=r['wheel'];key=geometry(r);origin=[word(r['base_'+a]+r['node_'+a])for a in 'xyz'];normal=[r['normal_'+a]for a in 'xyz'];active=memory[w]
        if r['correction']:raise UnsupportedContact('Roof correction not covered')
        if active is None or active['surface']!=key:
            out=baseline(r);memory[w]=None
            if out['branch']!='air':
                if geometry(query(out['position'],state['cached'][w]))!=key:raise UnsupportedContact('Acquisition changed face')
                memory[w]=dict(surface=key,target=dot(out['position'],origin,normal))
            return out
        new=[r['world_'+a]for a in 'xyz'];target=active['target'];depth=lambda p:dot(p,origin,normal)-target
        v=r['velocity'];vf=r['velocity_fraction'];pf=r['position_fraction'];ef=r['extension_fraction'];down=0
        applied=depth(new)>0
        if applied:
            a=21 if w<2 else 15
            down,pf=divmod(10*v+2*vf+7*a+pf,25);dv,vf=divmod(2*a+vf,5);v=word(v+dv);new[1]-=down
        d=depth(new)
        if d<=0:
            if v>0x5aeb:raise UnsupportedContact('Hard impact not covered')
            new,residual=project(new,origin,normal,target)
            if geometry(query(new,state['cached'][w]))!=key:raise UnsupportedContact('Projection changed selected face')
            q=0;branch='acquired_boundary';v=vf=pf=ef=0
        else:q=(d+8192*64-1)//(8192*64);branch='air'
        return dict(position=new,clearance=q,suspension_clearance=q,velocity=v,vf=vf,pf=pf,ef=ef,branch=branch,applied_gravity=applied,down=down)
    return body(entry,build,rows,wheel_solver=wheel)
