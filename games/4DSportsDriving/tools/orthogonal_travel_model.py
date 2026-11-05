"""Offline orthogonal contact travel; native contact classification retained.
Project the original tangent into the collision plane and normalize its length.
Only response travel changes; native residual-query/push, gravity, suspension
and body law remain. Fixed Q30 integer normalization avoids float trajectories.
"""
from math import isqrt
from native_contact_response import plane,resolve as native_resolve,word,UnsupportedContact,rotate
from contact_body_predictor import body,trunc
from supported_plane_model import geometry
from crest_terrain_query import query

def resolve(old,new,geo,distance,down,velocity,flags):
 out=native_resolve(old,new,geo,distance,down,velocity,flags)
 if out['branch'] not in ('full_tangent','crossing'):return out
 normal=[geo['normal_'+a]for a in 'xyz'];m=[geo['matrix'+str(i)]for i in range(9)];t=m[6:9]
 nn=sum(x*x for x in normal);nt=sum(x*y for x,y in zip(normal,t));v=[x*nn-y*nt for x,y in zip(t,normal)]
 assert sum(x*y for x,y in zip(v,normal))==0
 length=isqrt(sum(x*x for x in v)<<60);assert length
 tangent=[(out['projected_distance']*x*(1<<30))//length for x in v]
 candidate=[x+y+z for x,y,z in zip(old,out['straight'],tangent)]
 residual=plane(geo,candidate);push=rotate([0,word(-residual*64),0],m)if residual<0 else [0,0,0]
 out.update(tangent=tangent,before_push=candidate,push=push,position=[x+y for x,y in zip(candidate,push)],stored_clearance=residual)
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
