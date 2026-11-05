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


def check(folder, activation, refresh=None):
    clock = scheduler(folder)
    n = clock['substeps']
    state = snapshot(folder)
    elapsed = clock['ticks'] - activation
    if elapsed < 1:
        raise ValueError('Capture must follow fixture activation')
    native = struct.unpack('>7H', bytes.fromhex(state['power_timers']))
    actual = [native[i] for i in (0, 1, 4, 5, 6)]
    elapsed_by_power = [elapsed]*5
    if refresh is not None and clock['ticks'] > refresh:
        if refresh <= activation:
            raise ValueError('Refresh must follow activation')
        elapsed_by_power[-1] = clock['ticks']-refresh
    expected = [max(0, initial-age//n)
                for initial,age in zip((900,500,500,500,200),elapsed_by_power)]
    phase = list(struct.unpack('>10H', bytes.fromhex(state['power_phases'])))
    expected_phase = [item for value,age in zip(expected,elapsed_by_power)
                      for item in ((n-age % n) if value else n, value)]
    clone = int(40*n <= elapsed < 900*n)
    errors = []
    if actual != expected:
        errors.append(f'timers: {actual} != {expected}')
    if phase != expected_phase:
        errors.append(f'phases: {phase} != {expected_phase}')
    if state['clone_active'] != clone:
        errors.append(f'clone active: {state["clone_active"]} != {clone}')
    return dict(tick_substeps=n, tick=clock['ticks'], elapsed_ticks=elapsed, timers=actual,
                phases=phase, clone_active=state['clone_active'], errors=errors)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('captures', nargs='+')
    parser.add_argument('--activation', type=int, default=1205)
    parser.add_argument('--refresh', type=int, help='tick at which the fixture reactivates speed power')
    args = parser.parse_args()
    ok = True
    for folder in args.captures:
        result = check(folder, args.activation, args.refresh)
        print(folder, json.dumps(result))
        ok &= not result['errors']
    raise SystemExit(0 if ok else 1)
