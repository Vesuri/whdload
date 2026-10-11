#!/usr/bin/env python3
"""Read native animation/explosion cadence, render-isolation and refresh checks."""
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
    offset = struct.unpack_from('>H', memory, entry+90)[0]
    assert offset, 'ANIMATION_TEST fixture is absent'
    at = entry+offset
    signature = memory[at:at+4].decode('ascii')
    assert signature in ('A760', 'A761', 'A762')
    completed, failed, refresh, independent = struct.unpack_from('>4H', memory, at+4)
    expected_cases = 8 if signature == "A762" else 4
    assert completed <= expected_cases
    cases = [dict(zip(('type', 'failed', 'animation_words', 'life_words'),
                     struct.unpack_from('>4H', memory, at+12+i*8)))
             for i in range(completed)]
    return dict(tick_substeps=sim60_state.read(folder)['substeps'], signature=signature, expected_cases=expected_cases, completed=completed, failed=failed, refresh_errors=refresh,
                independence_errors=independent if signature != "A760" else None, cases=cases)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('captures', nargs='+')
    args = parser.parse_args()
    ok = True
    for folder in args.captures:
        result = read(folder)
        print(folder, json.dumps(result, indent=2))
        ok &= result['completed'] == result['expected_cases'] and result['failed'] == 0 and result['refresh_errors'] == 0 and result['independence_errors'] in (None, 0)
        ok &= all(not c['failed'] for c in result['cases'])
    raise SystemExit(0 if ok else 1)
