"""Offline unilateral acquired-face tangent support hypothesis; no fitted trajectory data.

Only while the proposed endpoint is at/below the acquired normal depth, advance its endpoint along that same face by
this tick's forward distance, retaining fractional rotated motion. Native first
impact and face changes remain unchanged. Support cannot survive a face change;
roof/hard impact and response crossing a face are outside this experiment.
This is a candidate to screen, not a production contact law.
"""
from contact_body_predictor import body,wheel as baseline
from supported_plane_model import geometry,dot
from crest_terrain_query import query
from native_contact_response import UnsupportedContact,word

def solve(entry,build,rows,state):
 memory=state.setdefault('unilateral_tangent',[None]*4)
 def wheel(r):
  w=r['wheel'];key=geometry(r);active=memory[w];origin=[word(r['base_'+a]+r['node_'+a])for a in 'xyz'];normal=[r['normal_'+a]for a in 'xyz'];new=[r['world_'+a]for a in 'xyz']
  if r['correction']:raise UnsupportedContact('Roof correction not covered')
  if active is not None and active['surface']==key and r['velocity']==r['velocity_fraction']==0 and dot(new,origin,normal)<=active['target']:
   old=[r['old_world_'+a]for a in 'xyz'];delta=[]
   for i in range(3):
    d,c=divmod(r['distance']*r['matrix'+str(6+i)]+active['carry'][i],16384);delta.append(d);active['carry'][i]=c
   new=[x+d for x,d in zip(old,delta)]
   if geometry(query(new,state['cached'][w]))!=key:raise UnsupportedContact('Tangent support crossed selected face')
   return dict(position=new,clearance=0,suspension_clearance=0,velocity=0,vf=0,pf=0,ef=0,branch='tangent_support',applied_gravity=False,down=0)
  out=baseline(r);memory[w]=None
  if out['branch']!='air' and geometry(query(out['position'],state['cached'][w]))==key:memory[w]=dict(surface=key,carry=[0,0,0],target=dot(out['position'],origin,normal))
  return out
 return body(entry,build,rows,wheel_solver=wheel)
