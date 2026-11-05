"""Offline two-stage contact/movement ordering hypothesis.
Predict the current20ms body response, discard it, correct translation with
3/4*D*(u_old-u_predicted), then freshly query/contact from the SAME initial
state. Only final physics result and issued-direction residue commit.
Q8 sine interpolation changes correction directions, not frame/input timing.
"""
from coupled_order_fraction_model import direction,evaluate
from contact_body_predictor import body

def solve_with(entry,build,rows,state,identity=False):
 prediction=body(entry,build,rows)
 old=direction(entry[2],entry[41]);new=direction(prediction['pitch'],prediction['pitch_carry'])
 carry=state.setdefault('explicit_order_carry',[0,0,0]);distance=rows[0]['distance']
 q=[divmod(carry[i]+(0 if identity else 3*distance*(old[i]-new[i])),16777216)for i in range(3)]
 out=evaluate(entry,build,rows,state,tuple(v[0]for v in q))
 state['explicit_order_carry']=[v[1]for v in q]
 return out

def solve(entry,build,rows,state):return solve_with(entry,build,rows,state)
def control(entry,build,rows,state):return solve_with(entry,build,rows,state,True)
