"""Offline implicit movement-order diagnostic, with fresh contact queries.
Leading left-endpoint native50ms vs20ms correction is3/4*D*(u_old-u_new).
Unlike the earlier airborne predictor, solve contact and corrected direction
self-consistently; reject discrete cycles/nonconvergence, never pick a fit.
This is a prospective modified-flow hypothesis, not a proven contact law.
"""
from copy import deepcopy
from native_contact_response import sine,UnsupportedContact
from crest_terrain_query import query
from contact_body_predictor import body

def solve_with(entry,build,rows,state,identity=False):
 carry=state.setdefault('order_direction_carry',[0,0,0]);distance=rows[0]['distance'];old=[0,sine(entry[2]),sine(entry[2]+256)]
 used=(0,0,0);seen=set();tries=[]
 for iteration in range(32):
  out=evaluate(entry,build,rows,state,used);new=[0,sine(out['pitch']),sine(out['pitch']+256)]
  q=[divmod(carry[i]+(0 if identity else 3*distance*(old[i]-new[i])),65536)for i in range(3)]
  requested=tuple(v[0]for v in q);tries.append(dict(used=used,requested=requested,pitch=out['pitch'],branches=[w['branch']for w in out['wheels']]))
  if requested==used:
   state['order_direction_carry']=[v[1]for v in q];state['order_iterations']=iteration+1;return out
  if requested in seen:raise UnsupportedContact('Movement/contact fixed-point cycle: '+repr(tries))
  seen.add(used);used=requested
 raise UnsupportedContact('Movement/contact fixed-point iteration limit: '+repr(tries))
def solve(entry,build,rows,state):return solve_with(entry,build,rows,state)
def control(entry,build,rows,state):return solve_with(entry,build,rows,state,True)

def evaluate(entry,build,rows,state,used):
 e=entry.copy();selected=deepcopy(rows)
 for w in range(4):
  new=[entry[57+3*w+i]+used[i]for i in range(3)];e[57+3*w:60+3*w]=new
  selected[w].update(query(new,state['cached'][w]));selected[w].update({'world_'+a:v for a,v in zip('xyz',new)})
 return body(e,build,selected)
