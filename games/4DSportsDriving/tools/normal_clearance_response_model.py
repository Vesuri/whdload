"""Offline use of the query normal for response-local Y and classification.
Keep matrix-local X/Z, tangent/push geometry, gravity, suspension and body law.
Only collision-local Y uses the same coarse plane function as penetration.
This removes contradictory negative-query/zero-local-Y backoff classification.
"""
from unittest.mock import patch
import contact_body_predictor as model
from native_contact_response import resolve

def solve_with(entry,build,rows,state,identity=False):
 def response(*args):return resolve(*args,coherent_clearance=not identity)
 with patch.object(model,'resolve',response):return model.body(entry,build,rows)
def solve(entry,build,rows,state):return solve_with(entry,build,rows,state)
def control(entry,build,rows,state):return solve_with(entry,build,rows,state,True)
