#!/usr/bin/env python3
"""Read native damage-shake timing, RNG, impact refresh and menu-reset checks."""
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
    offset = struct.unpack_from('>H', memory, entry+96)[0]
    assert offset, 'SHAKE_TEST fixture is absent'
    at = entry+offset
    assert memory[at:at+4] == b'H760'
    completed, failed, refresh, reset = struct.unpack_from('>4H', memory, at+4)
    assert completed <= 4
    cases = [dict(case=i, failed=struct.unpack_from('>H', memory, at+12+i*2)[0])
             for i in range(completed)]
    return dict(tick_substeps=sim60_state.read(folder)['substeps'], completed=completed, failed=failed, refresh_errors=refresh,
                reset_errors=reset, cases=cases)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('captures', nargs='+')
    args = parser.parse_args()
    ok = True
    for folder in args.captures:
        result = read(folder)
        print(folder, json.dumps(result, indent=2))
        ok &= result['completed'] == 4 and result['failed'] == 0 and result['refresh_errors'] == 0 and result['reset_errors'] == 0
        ok &= all(not c['failed'] for c in result['cases'])
    raise SystemExit(0 if ok else 1)
