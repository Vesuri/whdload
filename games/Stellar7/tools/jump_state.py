#!/usr/bin/env python3
"""Check a direct native jump activation against the native height equation.

This verifies motion and landing, not inventory selection or arbitrary contacts.
"""
import argparse
import json
import struct
from pathlib import Path
import sim60_state
import simulation_state


def check(folder, activation):
    clock = sim60_state.read(folder)
    state = simulation_state.snapshot(folder)
    n, tick = clock['substeps'], clock['ticks']
    elapsed = tick-activation
    assert elapsed > 0 and clock['running']
    height = state['objects'][0]['position'][2]
    valid, last, velocity, remainder, reserved = struct.unpack(
        '>HhihH', bytes.fromhex(state['jump_integrator']))
    if elapsed < 45*n:
        assert valid == 1 and reserved == 0
        assert velocity == 220*n-10*elapsed
        published = (abs(velocity)//n)*(1 if velocity >= 0 else -1)
        assert last == published
        assert height*n*n+remainder == elapsed*(225*n-5*elapsed)
        assert abs(remainder) < n*n
        if elapsed % n == 0:
            k = elapsed//n
            assert height == 220*k-5*k*(k-1) and remainder == 0
    else:
        published = 0
        assert height == 0 and state['jump_integrator'] == bytes(12).hex()
    assert struct.unpack('>7h', bytes.fromhex(state['power_timers']))[2] == published
    return dict(substeps=n,tick=tick,elapsed=elapsed,height=height,
                native_boundary=elapsed % n == 0,velocity=published,remainder=remainder)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('captures',nargs='+',type=Path)
    parser.add_argument('--activation',type=int,required=True)
    args = parser.parse_args()
    print(json.dumps([check(p,args.activation) for p in args.captures],indent=2))
