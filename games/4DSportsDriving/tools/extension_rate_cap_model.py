"""Offline geometric extension with a time-scaled movement cap.

Close the available positive clearance directly, up to192*20/50 per update.
Carry fifths only while cap-limited; discard unused capacity when the gap closes
or the384 extension bound is reached. Other suspension/contact laws unchanged.
Native10/20 share their original192 cap, so this is an A2500-derived hypothesis,
not an assertion that both original modes implement one continuous rate law.
"""
from unittest.mock import patch
import contact_body_predictor as model
from native_contact_response import word
original=model.suspension

def suspension(extension,bias,clearance,ef,bf):
 out=original(extension,bias,clearance,ef,bf)
 if out['branch_clearance']>0:
  cap,f=divmod(384+ef,5);step=min(clearance,cap)
  out['extension']=min(384,word(extension+step))
  out['ef']=f if clearance>cap and out['extension']<384 else 0
 return out

def solve(entry,build,rows,state):
 with patch.object(model,'suspension',suspension):return model.body(entry,build,rows)
