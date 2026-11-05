"""Offline same-face shallow-resting wheel correction diagnostic.

For four uncompressed, unbiased, nonfalling wheels on the identical face, with
native clearance only-1 or0, replace unequal endpoint corrections by their
common centroid translation. Preserve its exact quarter-unit sum with carries.
Other contacts, gravity, suspension and body laws remain unchanged. This is a
restricted body/contact coherence hypothesis, not a production replacement.
"""
from copy import deepcopy
from contact_body_predictor import body,wheel
from supported_plane_model import geometry
from crest_terrain_query import query
from native_contact_response import UnsupportedContact

def solve(entry,build,rows,state):
 out=[wheel(r)for r in rows]
 eligible=(len({geometry(r)for r in rows})==1 and all(r['clearance']in(-1,0) and r['velocity']==r['velocity_fraction']==r['correction']==0 for r in rows) and not any(entry[13:21]) and any(r['clearance']==-1 for r in rows))
 if eligible:
  q=state.setdefault('coherent_quarters',[0,0,0]);common=[]
  for i,a in enumerate('xyz'):
   total=sum(o['position'][i]-r['world_'+a]for r,o in zip(rows,out));d,q[i]=divmod(total+q[i],4);common.append(d)
  for r,o in zip(rows,out):
   p=[r['world_'+a]+d for a,d in zip('xyz',common)]
   if geometry(query(p,state['cached'][r['wheel']]))!=geometry(r):raise UnsupportedContact('Coherent support crossed face')
   o['position']=p;o['branch']='coherent_shallow'
 else:state['coherent_quarters']=[0,0,0]
 return body(entry,build,rows,wheel_solver=lambda r:deepcopy(out[r['wheel']]))
