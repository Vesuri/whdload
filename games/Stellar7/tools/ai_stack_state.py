#!/usr/bin/env python3
"""Check native stack-byte dependence and the SIM60 AI decision correction."""
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
    offset = struct.unpack_from('>H', memory, entry+68)[0]
    assert offset, 'AI_STACK_TEST fixture is absent'
    at = entry+offset
    signature = memory[at:at+4]
    assert signature in (b'U760', b'U761')
    count = struct.unpack_from('>H', memory, at+4)[0]
    result = dict(completed=count, native_decisions=list(memory[at+6:at+8]))
    if signature == b'U761':
        expected, rng_errors = struct.unpack_from('>2H', memory, at+10)
        result.update(corrected_decisions=list(memory[at+8:at+10]),
                      expected_decision=expected, rng_errors=rng_errors)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('captures', nargs='+')
    parser.add_argument('--native-only', action='store_true', help='inspect the original two-case reproduction')
    args = parser.parse_args()
    ok = True
    for folder in args.captures:
        result = read(folder)
        print(folder, json.dumps(result))
        ok &= result['native_decisions'] == [5, 3]
        if args.native_only:
            ok &= result['completed'] >= 2
        else:
            ok &= result['completed'] == 4 and result.get('rng_errors') == 0
            ok &= result.get('corrected_decisions') == [result.get('expected_decision')]*2
    raise SystemExit(0 if ok else 1)
