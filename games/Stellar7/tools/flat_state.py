#!/usr/bin/env python3
"""Validate native movement comparisons, including the optional zero-speed shortcut."""
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
    assert struct.unpack_from('>H', memory, entry+50)[0] >= 22
    offset = struct.unpack_from('>H', memory, entry+114)[0]
    assert offset, 'FLAT_TEST fixture is absent'
    at = entry+offset
    signature = memory[at:at+4]
    assert signature in (b'F760', b'F761', b'F762')
    if signature in (b'F761', b'F762'):
        assert memory[code+0x86ae:code+0x86b0] == bytes.fromhex('4a40')
        sites = ((0x86cc, '4eba733e'), (0x8712, '4eba72f8'),
                 (0x875a, '4eba72b0'), (0x8786, '4eba7284'), (0x87ac, '4eba725e'))
        words = [memory[code+site:code+site+4] for site, _ in sites]
        assert words == [bytes.fromhex(op) for _, op in sites] or words == [bytes.fromhex('c1c14e71')]*5
        for site, op in ((0x86ea, '4eba7320'), (0x8730, '4eba72da')):
            assert memory[code+site:code+site+4] == bytes.fromhex(op)
    return dict(signature=signature.decode(), **dict(zip(('cases', 'errors'),
                    struct.unpack_from('>2H', memory, at+4))))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('captures', nargs='+')
    args = parser.parse_args()
    for folder in args.captures:
        result = read(folder)
        print(folder, json.dumps(result, sort_keys=True))
        assert result['cases'] == (480 if result['signature'] in ('F761', 'F762') else 384) and result['errors'] == 0
