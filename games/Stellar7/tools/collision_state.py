#!/usr/bin/env python3
"""Read VERIFY COLLISION_TEST results from an exact-tick capture.

Four isolated actor pairs exercise the native separation loop with speeds
0, 1, -1 and 12. Compare coordinates, bounce speed and iteration count with
native undo; the guest also checks restoration of fractional remainders.
Nonzero failures or watchdog use makes this command fail.
"""
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
    offset = struct.unpack_from('>H', memory, entry+64)[0]
    assert offset, 'COLLISION_TEST fixture is absent'
    at = entry+offset
    assert memory[at:at+4] == b'C760'
    completed, failed = struct.unpack_from('>2H', memory, at+4)
    assert completed <= 4, 'completion count exceeds the allocated four cases'
    cases = []
    for index in range(completed):
        pos = at+8+index*44
        speed, expected_calls, actual_calls, forced = struct.unpack_from('>h3H', memory, pos)
        expected_position = struct.unpack_from('>3i', memory, pos+8)
        actual_position = struct.unpack_from('>3i', memory, pos+20)
        expected_bounce, actual_bounce = struct.unpack_from('>2h', memory, pos+32)
        cases.append(dict(speed=speed, expected_calls=expected_calls,
                          actual_calls=actual_calls, watchdog=forced,
                          expected_position=expected_position, actual_position=actual_position,
                          expected_bounce=expected_bounce, actual_bounce=actual_bounce,
                          rollback_check=struct.unpack_from('>H',memory,pos+36)[0]))
    return dict(completed=completed, failed=failed, cases=cases)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('captures', nargs='+')
    args = parser.parse_args()
    ok = True
    for folder in args.captures:
        result = read(folder)
        print(folder, json.dumps(result, indent=2))
        ok &= result['completed'] == 4 and result['failed'] == 0
        ok &= all(not c['watchdog'] and c['rollback_check'] == 1 and c['expected_calls'] == c['actual_calls']
                  and c['expected_position'] == c['actual_position']
                  and c['expected_bounce'] == c['actual_bounce'] for c in result['cases'])
    raise SystemExit(0 if ok else 1)
