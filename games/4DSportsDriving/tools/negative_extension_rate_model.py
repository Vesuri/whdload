"""Offline test of negative suspension relaxation scaling; no runtime change.
Keep native wheel projection, zero-clearance return and body correction formula.
Scale only requested negative-branch extension delta by2/5, retaining fifths.
Control uses5/5 and must exactly reproduce the current trajectory.
"""
from unittest.mock import patch
import contact_body_predictor as model
from native_contact_response import word
original=model.suspension

def solve_with(entry,build,rows,state,control=False,preserve_return=False):
 fractions=state.setdefault('negative_extension_fifths',[0]*4);index=[0]
 def suspension(extension,bias,clearance,ef,bf):
  w=index[0];index[0]+=1;out=original(extension,bias,clearance,ef,bf)
  if out['branch_clearance']<0:
   requested=word(out['extension']-extension)
   numerator=(5 if control else 2)*requested+fractions[w]
   delta=model.trunc(numerator,5);fractions[w]=numerator-5*delta
   out['extension']=max(-384,word(extension+delta))
   if not preserve_return:out['returned']=word(extension+word(word(extension-out['extension'])+out['branch_clearance']))
   if out['extension']==-384:fractions[w]=0
  else:fractions[w]=0
  return out
 with patch.object(model,'suspension',suspension):return model.body(entry,build,rows)
def solve(entry,build,rows,state):return solve_with(entry,build,rows,state)
def control(entry,build,rows,state):return solve_with(entry,build,rows,state,True)

def stored_only(entry,build,rows,state):return solve_with(entry,build,rows,state,preserve_return=True)
