"""Offline hypothesis: geometric first-contact rebound, time-scaled sustained return.

Current50Hz zero-clearance retraction is a128-unit geometric correction. Retain
it on acquisition of support. If the immediately preceding resolved wheel was
also supported, treat the continuing return as128/50ms with exact fifths.
Separation resets this history; no20Hz scheduling, future/reference input or
render interpolation. This is a screened hypothesis, not accepted physics.
"""
from unittest.mock import patch
import contact_body_predictor as model
from native_contact_response import word
original=model.suspension

def solve(entry,build,rows,state):
    previous=state.get('impact_return_support',[False]*4)
    fraction=state.get('impact_return_fraction',[0]*4)
    wheels=[];support=[];fractions=[];index=[0];changed=[]
    def wheel(row):
        result=model.wheel(row);wheels.append(result);return result
    def suspension(extension,bias,clearance,ef,bf):
        w=index[0];index[0]+=1;out=original(extension,bias,clearance,ef,bf)
        supported=wheels[w]['branch']!='air';support.append(supported)
        carry=0;before=dict(out)
        if supported and previous[w] and out['branch_clearance']==0:
            cap,carry=divmod(256+fraction[w],5);target=out['bias']
            if extension>target:
                out['extension']=max(target,word(extension-cap))
                out['returned']=word(extension+word(extension-out['extension']))
            elif extension<target:
                out['extension']=min(target,word(extension+cap));out['returned']=extension
            if out['extension']==target:carry=0
        fractions.append(carry);changed.append(before!=out)
        return out
    with patch.object(model,'suspension',suspension):out=model.body(entry,build,rows,wheel_solver=wheel)
    assert index[0]==4
    state['impact_return_support']=support;state['impact_return_fraction']=fractions
    out['impact_return_changed']=changed
    return out
