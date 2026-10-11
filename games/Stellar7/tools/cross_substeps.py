#!/usr/bin/env python3
"""Expose every mapped difference at an equal native-update boundary.

Internal integrator records contain rate-dependent clocks and remainders and
are reported separately. No difference is silently accepted or normalized.
A result with differences still requires a source-based explanation.
"""
import argparse
import json
from pathlib import Path
import sim60_state
import simulation_state

INTERNAL = frozenset(('hud_clock','knockback_phase','pickup_integrator','shake_phase',
                     'terrain_clock','terrain_friction_clock','fractional_motion',
                     'fractional_stars','tick_phase','jump_integrator','power_phases',
                     'player_cooldowns'))

def compare(reference, candidate):
    clocks = [sim60_state.read(p) for p in (reference,candidate)]
    a,b = clocks
    assert a['substeps'] == 12, 'Reference must be N12'
    assert a['ticks'] % 12 == b['ticks'] % b['substeps'] == 0, 'Not native-update boundaries'
    assert a['ticks']//12 == b['ticks']//b['substeps'], 'Different game-time boundaries'
    assert a.get('session') == b.get('session'), 'Different sessions'
    states = [simulation_state.snapshot(p,True,True) for p in (reference,candidate)]
    parts = {}
    for name,keys in [('integrators',INTERNAL),('projection_scratch',{'projection_scratch'})]:
        pairs=[{k:v for k,v in s.items() if k in keys} for s in states]
        parts[name]=list(simulation_state.differences(*pairs))
    gameplay=[{k:v for k,v in s.items() if k not in INTERNAL and k!='projection_scratch'} for s in states]
    parts['gameplay']=list(simulation_state.differences(*gameplay))
    return dict(native_update=a['ticks']//12,reference_substeps=12,candidate_substeps=b['substeps'],
                differences=parts,explanations_required=any(parts.values()),
                scope='Mapped state only; no cross-rate divergence is automatically accepted.')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference',type=Path)
    parser.add_argument('candidate',type=Path)
    args=parser.parse_args()
    print(json.dumps(compare(args.reference,args.candidate),indent=2))
