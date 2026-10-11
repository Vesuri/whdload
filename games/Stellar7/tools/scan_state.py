#!/usr/bin/env python3
"""Validate the native collision-scan twin and its synthetic boundary cases."""
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
    assert decode_version(struct.unpack_from('>H', memory, entry+50)[0])[0] >= 19
    offset = struct.unpack_from('>H', memory, entry+108)[0]
    assert offset, 'SCAN_TWIN fixture is absent'
    at = entry+offset
    assert memory[at:at+4] == b'L760'
    return dict(zip(('calls', 'mismatches', 'cases', 'failed_cases'),
                    struct.unpack_from('>2I2H', memory, at+4)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('captures', nargs='+')
    parser.add_argument('--flag-cases', action='store_true', help='expect SCAN_FLAG_TEST: 256 additional native byte-state cases')
    args = parser.parse_args()
    for folder in args.captures:
        result = read(folder)
        print(folder, json.dumps(result, sort_keys=True))
        expected = 324 if args.flag_cases else 68
        assert result['calls'] > expected and result['cases'] == expected
        assert result['mismatches'] == result['failed_cases'] == 0
