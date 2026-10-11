#!/usr/bin/env python3
"""Validate the native scalar-projection twin and its synthetic boundary cases."""
import argparse
import json
import re
import struct
from pathlib import Path
from sim60_state import decode_version


def read(folder):
    folder = Path(folder)
    meta = {k: int(v, 0) for k, v in re.findall(
        r'^(code|base)=(\S+)', (folder/'anchor.txt').read_text(), re.M)}
    memory = (folder/'code.bin').read_bytes()
    code = meta['code']-meta['base']
    assert memory[code+0x2af6:code+0x2af8] == bytes.fromhex('4ef9')
    entry = struct.unpack_from('>I', memory, code+0x2af8)[0]-meta['base']
    assert memory[entry+4:entry+8] == b'S760'
    assert decode_version(struct.unpack_from('>H', memory, entry+50)[0])[0] >= 20
    offset = struct.unpack_from('>H', memory, entry+110)[0]
    assert offset, 'RADIUS_TWIN fixture is absent'
    at = entry+offset
    signature = memory[at:at+4]
    assert signature in (b'V760', b'V761', b'V762')
    result = dict(signature=signature.decode(), **dict(zip(('calls', 'mismatches', 'cases', 'failed_cases'),
                    struct.unpack_from('>2I2H', memory, at+4))))
    if signature == b'V762' and result['mismatches']:
        result['first_mismatch'] = dict(zip(('radius', 'denominator', 'shift', 'native_d0', 'fast_d0', 'native_d1', 'fast_d1'), struct.unpack_from('>7I', memory, at+16)))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('captures', nargs='+')
    args = parser.parse_args()
    for folder in args.captures:
        result = read(folder)
        print(folder, json.dumps(result, sort_keys=True))
        expected = 128 if result['signature'] == 'V760' else 384
        assert result['calls'] > expected and result['cases'] == expected
        assert result['mismatches'] == result['failed_cases'] == 0
