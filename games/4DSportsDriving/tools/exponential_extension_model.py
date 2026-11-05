"""Offline native20-derived unsaturated suspension decay at50Hz.
Fixed-body gap retention63/64 per50ms gives coefficient
64*(1-(63/64)^(2/5)), roundedQ16=26338, versus linear2/5.
Keep saturated speed192*2/5 and existing cap384. Extra fractions are model-only.
A linear control checks that changing fraction representation is neutral.
"""
from unittest.mock import patch
import contact_body_predictor as model
from native_contact_response import word
original=model.suspension
DEN=5*65536

def solve_with(entry,build,rows,state,linear=False):
 fractions=state.setdefault('exponential_extension',[entry[33+w]*65536 for w in range(4)]);idx=[0]
 def suspension(extension,bias,clearance,ef,bf):
  w=idx[0];idx[0]+=1;out=original(extension,bias,clearance,ef,bf)
  if out['branch_clearance']>0:
   numerator=min(clearance*(2*65536 if linear else 5*26338),192*2*65536)
   step,fractions[w]=divmod(numerator+fractions[w],DEN)
   out['extension']=min(384,word(extension+step));out['ef']=0
   if out['extension']==384:fractions[w]=0
  else:fractions[w]=0
  return out
 with patch.object(model,'suspension',suspension):return model.body(entry,build,rows)
def solve(entry,build,rows,state):return solve_with(entry,build,rows,state)
def control(entry,build,rows,state):return solve_with(entry,build,rows,state,True)
