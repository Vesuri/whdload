#!/usr/bin/env python3
"""Read isolated native terrain-friction regression results from an exact build."""
import argparse
import json
import re
import struct
from pathlib import Path


def read(folder, listing):
    folder, listing = Path(folder), Path(listing)
    root = folder
    while not (root/'slave.slave').exists():
        assert root != root.parent, 'retained slave missing'
        root = root.parent
    assert (root/'slave.slave').read_bytes() == listing.with_suffix('.slave').read_bytes()
    symbols = dict((name, int(offset, 16)) for name, offset in re.findall(
        r'^(s60_entry|s60_friction_results)\s+00:([0-9A-F]+)',
        listing.read_text(encoding='latin1'), re.M))
    assert set(symbols) == {'s60_entry', 's60_friction_results'}
    meta = {k: int(v, 0) for k, v in re.findall(
        r'^(code|base)=(\S+)', (folder/'anchor.txt').read_text(), re.M)}
    memory = (folder/'code.bin').read_bytes()
    code = meta['code']-meta['base']
    assert memory[code+0x2af6:code+0x2af8] == bytes.fromhex('4ef9')
    entry = struct.unpack_from('>I', memory, code+0x2af8)[0]-meta['base']
    assert memory[entry+4:entry+8] == b'S760'
    assert struct.unpack_from('>H', memory, entry+50)[0] >= 29
    at = entry-symbols['s60_entry']+symbols['s60_friction_results']
    assert memory[at:at+4] == b'TF60'
    checked, errors = struct.unpack_from('>II', memory, at+4)
    return dict(checked=checked, mismatches=errors,
                scope='Native damping fragment on private signed velocities: 24 start ticks, 108 observations each, contact gaps, rendering, inactive behavior and unsigned tick rollover. Not a full encounter.')


def validate(result):
    assert result['checked'] == 2592 and result['mismatches'] == 0, result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--listing', type=Path, required=True)
    args = parser.parse_args()
    result = read(args.capture, args.listing)
    print(json.dumps(result, indent=2))
    validate(result)
