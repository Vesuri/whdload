#!/usr/bin/env python3
"""Validate the native sort-order twin and its synthetic boundary cases."""
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
    assert struct.unpack_from('>H', memory, entry+50)[0] >= 21
    offset = struct.unpack_from('>H', memory, entry+112)[0]
    assert offset, 'SORT_TWIN fixture is absent'
    at = entry+offset
    signature = memory[at:at+4]
    assert signature in (b'O760', b'O761')
    return dict(signature=signature.decode(), **dict(zip(('calls', 'cases'),
                    struct.unpack_from('>IH', memory, at+4))))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('captures', nargs='+')
    args = parser.parse_args()
    for folder in args.captures:
        result = read(folder)
        print(folder, json.dumps(result, sort_keys=True))
        expected = 64 if result['signature'] == 'O761' else 32
        assert result['calls'] > expected and result['cases'] == expected
