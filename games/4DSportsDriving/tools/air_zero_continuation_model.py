"""Offline hypothesis: a coarse zero cell does not stop a falling wheel above its plane.

Resting/initial-zero-velocity wheels retain the exact current response. Only an
already nonzero downward velocity can continue through coarse clearance zero
when raw normal depth stays positive. Gravity formula is unchanged; negative
coarse penetration still uses native response. No new history, reference kick,
threshold tuning, contact delay or rendered interpolation is introduced.
"""
from contact_body_predictor import body,wheel as baseline,trunc
from native_contact_response import plane,resolve,word
from supported_plane_model import dot

def wheel(r):
    if r['velocity']<=0 and r['velocity_fraction']==0:return baseline(r)
    if r['correction']:return baseline(r)
    old=[r['old_world_'+a]for a in 'xyz'];new=[r['world_'+a]for a in 'xyz']
    geo={k:r[k]for k in ('plane','plane_flags','normal_x','normal_y','normal_z',*('matrix'+str(i)for i in range(9)))}
    origin=[word(r['base_'+a]+r['node_'+a])for a in 'xyz'];normal=[r['normal_'+a]for a in 'xyz'];geo.update(dict(zip(('origin_x','origin_y','origin_z'),origin)))
    q=plane(geo,new);assert q==r['clearance'];depth=lambda p:dot(p,origin,normal)
    v=r['velocity'];vf=r['velocity_fraction'];pf=r['position_fraction'];ef=r['extension_fraction'];down=0
    continued=q==0 and depth(new)>0;applied=q>0 or continued
    if applied:
        a=21 if r['wheel']<2 else 15
        down,pf=divmod(10*v+2*vf+7*a+pf,25);dv,vf=divmod(2*a+vf,5);v=word(v+dv);new[1]-=down;q=plane(geo,new)
    sc=q
    if q<0:
        ratio=down if applied else trunc(10*v+2*vf,25);out=resolve(old,new,geo,r['distance'],ratio,v,r['impact_flags']);new=out['position'];q=out['stored_clearance'];branch=out['branch']
    elif q==0 and depth(new)>0:
        branch='air';sc=(depth(new)+8192*64-1)//(8192*64);continued=True
    else:branch='zero'if q==0 else'air'
    if branch!='air':v=vf=pf=ef=0
    return dict(position=new,clearance=q,suspension_clearance=sc,velocity=v,vf=vf,pf=pf,ef=ef,branch=branch,applied_gravity=applied,down=down,continued_zero=continued)

def solve(entry,build,rows,state):return body(entry,build,rows,wheel_solver=wheel)
