#!/usr/bin/env python3
"""Check per-tick native death/quit dispatch and preserved periodic counters."""
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
    code = meta['code'] - meta['base']
    assert memory[code+0x2af6:code+0x2af8] == bytes.fromhex('4ef9')
    entry = struct.unpack_from('>I', memory, code+0x2af8)[0] - meta['base']
    assert memory[entry+4:entry+8] == b'S760'
    version, n = sim60_state.decode_version(struct.unpack_from('>H', memory, entry+50)[0])
    assert version >= 16
    offset = struct.unpack_from('>H', memory, entry+98)[0]
    assert offset, 'POST_TEST fixture is absent'
    assert memory[entry+offset:entry+offset+4] == b'U760'
    result = dict(zip(('death_cases', 'quit_cases', 'periodic_substeps', 'errors'),
                    struct.unpack_from('>4H', memory, entry+offset+4)))
    result['tick_substeps'] = n
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('captures', nargs='+')
    args = parser.parse_args()
    ok = True
    for folder in args.captures:
        result = read(folder)
        print(folder, json.dumps(result, sort_keys=True))
        ok &= result == dict(tick_substeps=result['tick_substeps'], death_cases=4*result['tick_substeps'], quit_cases=2*result['tick_substeps'],
                             periodic_substeps=64*result['tick_substeps'], errors=0)
    raise SystemExit(0 if ok else 1)
