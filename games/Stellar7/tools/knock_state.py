#!/usr/bin/env python3
"""Check native knockback cadence and input interaction in SIM60."""
import argparse
import json
import re
import struct
from pathlib import Path


def read(folder):
    folder = Path(folder)
    meta = {k: int(v, 0) for k, v in re.findall(
        r'^(code|base)=(\S+)', (folder/'anchor.txt').read_text(), re.M)}
    memory = (folder/'code.bin').read_bytes()
    code = meta['code']-meta['base']
    assert memory[code+0x2af6:code+0x2af8] == bytes.fromhex('4ef9')
    entry = struct.unpack_from('>I', memory, code+0x2af8)[0]-meta['base']
    assert memory[entry+4:entry+8] == b'S760'
    offset = struct.unpack_from('>H', memory, entry+78)[0]
    assert offset, 'KNOCK_TEST fixture is absent'
    at = entry+offset
    assert memory[at:at+4] == b'K760'
    completed, errors, refresh_errors = struct.unpack_from('>3H', memory, at+4)
    return dict(completed=completed, errors=errors, refresh_errors=refresh_errors)


def check_play(folder, activation):
    """Validate the -160 KNOCK_PLAY route; additional impacts must be absent."""
    from sim60_state import read as scheduler
    from simulation_state import snapshot
    tick = scheduler(folder)['ticks']
    elapsed = tick - activation
    if elapsed < 1:
        raise ValueError('Capture must follow diagnostic activation')
    state = snapshot(folder)
    impulses = (-160, -80, -40, -20, -10, -5, -2, -1)
    period, substep = divmod(elapsed-1, 12)
    active = period < len(impulses)
    current = impulses[period] if active else -1
    pending = impulses[period+1] if period+1 < len(impulses) else 0
    remaining = 11-substep if active else 0
    expected = struct.pack('>3h', remaining, current, pending).hex()
    speed = struct.unpack_from('>h', bytes.fromhex(state['objects'][0]['motion']), 12)[0]
    errors = []
    if state['knockback_phase'] != expected:
        errors.append(f'phase: {state["knockback_phase"]} != {expected}')
    if state['knockback_pending'] != (pending & 65535):
        errors.append('pending impulse differs')
    if active and speed != current:
        errors.append(f'speed: {speed} != {current}')
    return dict(tick=tick, active=active, speed=speed, errors=errors)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('captures', nargs='+')
    parser.add_argument('--play', action='store_true', help='check the -160 KNOCK_PLAY route instead of the isolated oracle')
    parser.add_argument('--activation', type=int, default=1205)
    args = parser.parse_args()
    ok = True
    for folder in args.captures:
        result = check_play(folder, args.activation) if args.play else read(folder)
        print(folder, json.dumps(result))
        ok &= not result['errors'] if args.play else result == dict(completed=8, errors=0, refresh_errors=0)
    raise SystemExit(0 if ok else 1)
