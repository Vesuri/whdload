#!/usr/bin/env python3
"""Compare C2 captured whole-tick state at common layout, never field-aligned races."""
import gzip
import json
from pathlib import Path
import sys

from machine_matrix import sha
from state_diff import SIZES, scratch

RANGES = {
    'all 26 complete car records': (1, 0x5d6, 26*0xc0),
    'view/source selection and synthetic camera': (1, 0x234, 0xe2),
    'gameplay RNG': (0, 0x3a7b0, 5),
    'shared RNG': (0, 0x257c4, 5),
    'pit phases': (0, 0x3a746, 8),
    'debris expiry': (0, 0x3a770, 4),
    'game clocks': (0, 0x3a77c, 12),
    'camera pose and spring': (0, 0x3a7f8, 0x30),
    'HUD requests, deadlines and blink state': (0, 0x3a6bc, 0x48),
    # +3A706/+3A708 are sound interpolation values, dependent on elapsed fields.
    'replay, view and HUD refresh flags': (0, 0x3a70a, 0x0a),
    'HUD dirty-mask snapshot': (0, 0x2dce2, 2),
    'instrument current and previous values': (0, 0x3a91c, 4),
    'text colours, cursor and control state': (2, 0x1f302, 0x1c),
    'HUD box reuse flag': (2, 0x231ea, 1),
}


def compare(left, right):
    paths = [scratch(left), scratch(right)]
    metadata = [json.loads((p/'meta.json').read_text()) for p in paths]
    for p, m in zip(paths, metadata):
        if (m['status'] != 'CAPTURED' or m['quit'] != 'OK'
                or m['tick_sha256'] != sha(p/'tick.bin.gz')
                or m['build']['slave_sha256'] != sha(p/'slave.bin')):
            raise ValueError('incomplete or changed capture')
    for key in ('build', 'runtime', 'setup', 'extra_args', 'route', 'replay', 'ticks',
                'game_inputs', 'hunk_bases'):
        if metadata[0][key] != metadata[1][key]:
            raise ValueError(f'unmatched {key}')
    if metadata[0].get('boundary', 'pacer') != metadata[1].get('boundary', 'pacer'):
        raise ValueError('unmatched snapshot boundary')
    snapshots = [gzip.decompress((p/'tick.bin.gz').read_bytes()) for p in paths]
    if any(len(s) != sum(SIZES) for s in snapshots):
        raise ValueError('incomplete tick snapshot')
    result = {}
    for name, (h, offset, size) in RANGES.items():
        start = sum(SIZES[:h])+offset
        a, b = (s[start:start+size] for s in snapshots)
        differences = [f'h{h}+{offset+i:05x}' for i, (x,y) in enumerate(zip(a,b)) if x != y]
        result[name] = dict(equal=not differences, differences=differences)
    picture = None
    if metadata[0].get('boundary', 'pacer') == 'publish':
        pictures = []
        for p, m in zip(paths, metadata):
            if m.get('paint_sha256') != sha(p/'paint.bin'):
                raise ValueError('changed publication bitmap')
            pictures.append((p/'paint.bin').read_bytes())
        if any(len(p) != 32000 for p in pictures):
            raise ValueError('incomplete publication bitmap')
        differences = sum(a != b for a, b in zip(*pictures))
        picture = dict(equal=not differences, differing_bytes=differences, size=32000)
    passed = all(r['equal'] for r in result.values()) and (picture is None or picture['equal'])
    return dict(status='PASS' if passed else 'FAIL',
                tick=metadata[0]['ticks'], ranges=result, picture=picture,
                note='Selected authoritative A3/A4 ranges, not a whole-program or performance gate.')


if __name__ == '__main__':
    result = compare(*sys.argv[1:3])
    if len(sys.argv) == 4:
        scratch(sys.argv[3]).write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
    sys.exit(0 if result['status'] == 'PASS' else 1)
