#!/usr/bin/env python3
"""Read the native-callback oracle for fixed-rate flying enemy motion.

The guest compares XYZ and bank on every substep and full actor/RNG state after each
of four N-tick intervals. Cases cover descent, climb, clamping, banking,
state timers, random decisions and contact-triggered retreat.
"""
import argparse
import json
import re
import struct
from pathlib import Path
import sim60_state


def read(folder):
    folder = Path(folder)
    meta = {k: int(v, 0) for k, v in re.findall(
        r'^(code|base)=(\S+)', (folder/'anchor.txt').read_text(), re.M)}
    memory = (folder/'code.bin').read_bytes()
    code = meta['code']-meta['base']
    assert memory[code+0x2af6:code+0x2af8] == bytes.fromhex('4ef9')
    entry = struct.unpack_from('>I', memory, code+0x2af8)[0]-meta['base']
    assert memory[entry+4:entry+8] == b'S760'
    _, n = sim60_state.decode_version(struct.unpack_from('>H', memory, entry+50)[0])
    offset = struct.unpack_from('>H', memory, entry+72)[0]
    assert offset, 'FLYING_TEST fixture is absent'
    at = entry+offset
    assert memory[at:at+4] == b'F760'
    completed, failed = struct.unpack_from('>2H', memory, at+4)
    assert completed <= 12
    cases = []
    for index in range(completed):
        kind, error, first, sixth, final = struct.unpack_from('>2H3i', memory, at+8+16*index)
        cases.append(dict(case=index, type=kind, failed=error,
                          first_tick_height=first, midpoint_tick=(n+1)//2, midpoint_tick_height=sixth, final_height=final))
    return dict(tick_substeps=n, completed=completed, failed=failed, cases=cases)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('captures', nargs='+')
    args = parser.parse_args()
    ok = True
    for folder in args.captures:
        result = read(folder)
        print(folder, json.dumps(result, indent=2))
        ok &= result['completed'] == 12 and result['failed'] == 0
        ok &= all(not c['failed'] for c in result['cases'])
    raise SystemExit(0 if ok else 1)
