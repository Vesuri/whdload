"""Offline candidate: preserve native positive-clearance geometric extension.

Original $10226..$10296 uses identical clearance-sized corrections at10/20Hz.
Only this operation is changed from the current50Hz model; zero/negative return,
bias decay, wheel gravity/contact, pitch and drivetrain retain their semantics.
This hypothesis is not accepted physics and is never selected by runtime builds.
"""
from unittest.mock import patch
import contact_body_predictor as model
from native_contact_response import word
original=model.suspension

def suspension(extension,bias,clearance,ef,bf):
    result=original(extension,bias,clearance,ef,bf)
    if result['branch_clearance']>0:
        result['extension']=min(384,word(extension+min(clearance,192)))
        result['ef']=0
    return result

def solve(entry,build,rows,state):
    with patch.object(model,'suspension',suspension):
        return model.body(entry,build,rows)
