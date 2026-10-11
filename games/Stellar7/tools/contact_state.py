#!/usr/bin/env python3
"""Check native contact effects and independent clocks in SIM60."""
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
    offset = struct.unpack_from('>H', memory, entry+80)[0]
    assert offset, 'CONTACT_TEST fixture is absent'
    at = entry+offset
    assert memory[at:at+4] == b'D762'
    completed, errors, clock_errors = struct.unpack_from('>3H', memory, at+4)
    sound_calls, active = struct.unpack_from('>2H', memory, at+10)
    return dict(tick_substeps=sim60_state.read(folder)['substeps'], completed=completed, errors=errors, clock_errors=clock_errors, sound_calls=sound_calls, active=active)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('captures', nargs='+')
    args = parser.parse_args()
    ok = True
    for folder in args.captures:
        result = read(folder)
        print(folder, json.dumps(result))
        ok &= all(result[k] == v for k,v in dict(completed=5, errors=0, clock_errors=0, sound_calls=3, active=0).items())
    raise SystemExit(0 if ok else 1)
