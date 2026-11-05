"""Offline rate-scaled residual rounding bias. Analytic geometric correction is
unscaled; native-minus-analytic endpoint difference gets exact2/5 carry peraxis.
Native contact and push activation remain. This tests a numerical-bias hypothesis,
not an established continuous physical law; no fitted trajectory parameters.
"""
from native_contact_response import plane,resolve as native_resolve,word,UnsupportedContact
from contact_body_predictor import body,trunc
from supported_plane_model import project,geometry,dot
from crest_terrain_query import query

def resolve(old,new,geo,distance,down,velocity,flags,carry):
 out=native_resolve(old,new,geo,distance,down,velocity,flags)
 if out['branch'] not in ('full_tangent','crossing') or out['stored_clearance']>=0:return out
 before=out['before_push'];origin=[geo['origin_'+a]for a in 'xyz'];normal=[geo['normal_'+a]for a in 'xyz'];depth=dot(before,origin,normal)
 final=project(before,origin,normal)[0] if depth<0 else before.copy()
 native=out['position'].copy()
 for i in range(3):
  step,carry[i]=divmod(2*(native[i]-final[i])+carry[i],5);final[i]+=step
 out['native_push']=out['push'];out['push']=[x-y for x,y in zip(final,before)];out['position']=final
 return out

def wheel(r,carry):
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
        out=resolve(old,new,geo,r['distance'],ratio,v,r['impact_flags'],carry)
        new=out['position'];q=out['stored_clearance'];branch=out['branch']
    else:branch='zero' if q==0 else 'air'
    if branch=='air':carry[:]=[0,0,0]
    if branch!='air':v=vf=pf=ef=0
    return dict(position=new,clearance=q,suspension_clearance=suspension_clearance,velocity=v,vf=vf,pf=pf,ef=ef,branch=branch,applied_gravity=applied,down=down)

def solve(entry,build,rows,state):
 carries=state.setdefault('push_bias_carries',[[0,0,0]for _ in range(4)])
 def checked(r):
  out=wheel(r,carries[r['wheel']])
  if geometry(query(out['position'],state['cached'][r['wheel']]))!=geometry(r):raise UnsupportedContact('Fine push crossed selected face')
  return out
 return body(entry,build,rows,wheel_solver=checked)
