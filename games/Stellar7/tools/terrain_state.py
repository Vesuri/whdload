#!/usr/bin/env python3
"""Read the native-reference terrain clock fixture and restored branch."""
import argparse
import json
import re
import struct
from pathlib import Path
import sim60_state


def read(folder):
    folder = Path(folder)
    meta = {k: int(v, 0) for k, v in re.findall(
        r'^(code|data|base)=(\S+)', (folder/'anchor.txt').read_text(), re.M)}
    memory = (folder/'code.bin').read_bytes()
    code = meta['code']-meta['base']
    assert memory[code+0x2af6:code+0x2af8] == bytes.fromhex('4ef9')
    entry = struct.unpack_from('>I', memory, code+0x2af8)[0]-meta['base']
    assert memory[entry+4:entry+8] == b'S760'
    assert sim60_state.decode_version(struct.unpack_from('>H', memory, entry+50)[0])[0] >= 25
    offset = struct.unpack_from('>H', memory, entry+124)[0]
    assert offset, 'TERRAIN_TEST fixture absent'
    at = entry+offset
    assert memory[at:at+4] == b'TR60'
    native = memory[at+18:at+26]
    assert native[:2] == bytes.fromhex('5379') and native[6:] == bytes.fromhex('4e75')
    assert struct.unpack_from('>I', native, 2)[0] == meta['data']+0x46c4
    assert memory[code+0x36f8:code+0x36fa] == bytes.fromhex('4eb9')
    assert memory[code+0x36fe:code+0x3702] == bytes.fromhex('600000a6')
    result = dict(zip(('cases', 'errors', 'substeps', 'inactive', 'resets', 'intermittent'),
                    struct.unpack_from('>2HI3H', memory, at+4)))
    result['tick_substeps'] = sim60_state.read(folder)['substeps']
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('captures', nargs='+')
    for folder in p.parse_args().captures:
        result = read(folder)
        print(folder, json.dumps(result, sort_keys=True))
        n = result['tick_substeps']
        assert result == dict(tick_substeps=n, cases=8*n, errors=0, substeps=24*n*n, inactive=4,
                              resets=8*n, intermittent=8)
