"""Offline isolated analytic residual push; native contact branches unchanged.
Only full-tangent/crossing residual projection uses unrounded world depth.
Gravity activation, intersection, suspension and body reconstruction remain50Hz.
"""
from native_contact_response import plane,resolve as native_resolve,word,UnsupportedContact
from contact_body_predictor import body,trunc
from supported_plane_model import project,geometry,dot
from crest_terrain_query import query

def resolve(old,new,geo,distance,down,velocity,flags):
 out=native_resolve(old,new,geo,distance,down,velocity,flags)
 if out['branch'] not in ('full_tangent','crossing'):return out
 before=out['before_push'];origin=[geo['origin_'+a]for a in 'xyz'];normal=[geo['normal_'+a]for a in 'xyz'];depth=dot(before,origin,normal)
 final=project(before,origin,normal)[0] if depth<0 else before.copy()
 out['native_push']=out['push'];out['push']=[x-y for x,y in zip(final,before)];out['position']=final
 return out

def wheel(r):
    if r['correction']!=0:raise UnsupportedContact('Roof correction domain not supported')
    old=[r['old_world_'+a] for a in 'xyz'];new=[r['world_'+a] for a in 'xyz']
    geo={k:r[k] for k in ('plane','plane_flags','normal_x','normal_y','normal_z',*('matrix'+str(i) for i in range(9)))}
    geo.update({'origin_'+a:word(r['base_'+a]+r['node_'+a]) for a in 'xyz'})
    q=plane(geo,new);assert q==r['clearance']
    v=r['velocity'];vf=r['velocity_fraction'];pf=r['position_fraction'];ef=r['extension_fraction']
    applied=q>0;down=0
    if applied:
        a=21 if r['wheel']<2 else 15
        down,pf=divmod(10*v+2*vf+7*a+pf,25)
        dv,vf=divmod(2*a+vf,5);v=word(v+dv);new[1]-=down
        q=plane(geo,new)
    suspension_clearance=q
    if q<0:
        ratio=down if applied else trunc(10*v+2*vf,25)
        out=resolve(old,new,geo,r['distance'],ratio,v,r['impact_flags'])
        new=out['position'];q=out['stored_clearance'];branch=out['branch']
    else:branch='zero' if q==0 else 'air'
    if branch!='air':v=vf=pf=ef=0
    return dict(position=new,clearance=q,suspension_clearance=suspension_clearance,velocity=v,vf=vf,pf=pf,ef=ef,branch=branch,applied_gravity=applied,down=down)

def solve(entry,build,rows,state):
 def checked(r):
  out=wheel(r)
  if geometry(query(out['position'],state['cached'][r['wheel']]))!=geometry(r):raise UnsupportedContact('Fine push crossed selected face')
  return out
 return body(entry,build,rows,wheel_solver=checked)
