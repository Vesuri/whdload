#!/usr/bin/env python3
"""Validate the native-reference projection omission guard fixture."""
import json
import re
import struct
import sys
from pathlib import Path


def read(folder):
    folder = Path(folder)
    meta = {k:int(v,0) for k,v in re.findall(r'^(code|base)=(\S+)', (folder/'anchor.txt').read_text(), re.M)}
    memory = (folder/'code.bin').read_bytes()
    code = meta['code']-meta['base']
    assert memory[code+0x2af6:code+0x2af8] == bytes.fromhex('4ef9')
    entry = struct.unpack_from('>I', memory, code+0x2af8)[0]-meta['base']
    assert memory[entry+4:entry+8] == b'S760'
    assert struct.unpack_from('>H', memory, entry+50)[0] >= 24
    offset = struct.unpack_from('>H', memory, entry+118)[0]
    assert offset, 'PROJECT_TEST fixture is absent'
    at = entry+offset
    signature = memory[at:at+4]
    assert signature in (b'J760', b'J761', b'J762')
    assert memory[code+0x12bfc:code+0x12c00] == bytes.fromhex('202b001a'), 'native callback boundary not restored'
    return dict(signature=signature.decode(), **dict(zip(('cases','failures','busy','first_failure'), struct.unpack_from('>4H',memory,at+4))))


if __name__ == '__main__':
    for folder in sys.argv[1:]:
        result = read(folder)
        print(folder, json.dumps(result, sort_keys=True))
        expected = 240 if result['signature'] == 'J762' else 192
        assert result['cases'] == expected and result['failures'] == result['busy'] == 0
        assert result['first_failure'] == 65535
