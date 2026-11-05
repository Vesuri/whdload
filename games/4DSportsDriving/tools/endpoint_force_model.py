"""Experimental endpoint-force activation correction derived from step lengths.

The0.3*a term cancels the phase-average endpoint sampling bias between native
20Hz and50Hz. No position/velocity is copied from a reference run. Averages
are not a proof for deterministic contacts; this is an offline diagnostic.
"""
from fractions import Fraction
from contact_body_predictor import body,wheel

def corrected_wheel(row):
    r=dict(row);a=21 if r['wheel']<2 else 15
    activated=r['clearance']>0 and r['velocity']==r['velocity_fraction']==0
    if activated:
        r['velocity'],r['velocity_fraction']=divmod(Fraction(3*a,2),5)
    out=wheel(r);out['force_activation_correction']=str(Fraction(3*a,10)) if activated else '0'
    return out

def solve(entry,build,rows,state):return body(entry,build,rows,wheel_solver=corrected_wheel)
