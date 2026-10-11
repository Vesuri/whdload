#!/usr/bin/env python3
"""Check POWERS_FULL fixture deadlines and fractional phases at captured ticks.

This diagnostic activates five native-duration timers together, bypassing
inventory selection. It is not a general gameplay power-state validator.
"""
import argparse
import json
import struct
from sim60_state import read as scheduler
from simulation_state import snapshot


def check(folder, activation):
    clock = scheduler(folder)
    state = snapshot(folder)
    elapsed = clock['ticks'] - activation
    if elapsed < 1:
        raise ValueError('Capture must follow fixture activation')
    native = struct.unpack('>7H', bytes.fromhex(state['power_timers']))
    actual = [native[i] for i in (0, 1, 4, 5, 6)]
    expected = [max(0, initial-elapsed//12) for initial in (900, 500, 500, 500, 200)]
    phase = list(struct.unpack('>10H', bytes.fromhex(state['power_phases'])))
    expected_phase = [item for value in expected
                      for item in ((12-elapsed % 12) if value else 12, value)]
    clone = int(480 <= elapsed < 10800)
    errors = []
    if actual != expected:
        errors.append(f'timers: {actual} != {expected}')
    if phase != expected_phase:
        errors.append(f'phases: {phase} != {expected_phase}')
    if state['clone_active'] != clone:
        errors.append(f'clone active: {state["clone_active"]} != {clone}')
    return dict(tick=clock['ticks'], elapsed_ticks=elapsed, timers=actual,
                phases=phase, clone_active=state['clone_active'], errors=errors)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('captures', nargs='+')
    parser.add_argument('--activation', type=int, default=1205)
    args = parser.parse_args()
    ok = True
    for folder in args.captures:
        result = check(folder, args.activation)
        print(folder, json.dumps(result))
        ok &= not result['errors']
    raise SystemExit(0 if ok else 1)
