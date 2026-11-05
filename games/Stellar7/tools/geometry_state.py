#!/usr/bin/env python3
"""Read live fused enemy-geometry comparisons from an exact retained build."""
import argparse
import json
import re
import struct
from pathlib import Path
import sim60_state
import _amigaxdev  # noqa: F401 (finds amigaxdev)
from amigaxdev.patchlist import slave_code
from stellar7_report import locate


def read(folder, listing):
    folder, listing = Path(folder), Path(listing)
    n = sim60_state.read(folder)['substeps']
    root = folder
    while not (root/'slave.slave').exists():
        assert root != root.parent, 'retained slave missing'
        root = root.parent
    assert (root/'slave.slave').read_bytes() == listing.with_suffix('.slave').read_bytes()
    symbol = re.search(r'^s60_geometry_results\s+00:([0-9A-F]+)', listing.read_text(encoding='latin1'), re.M)
    assert symbol, 'geometry comparison fixture missing'
    meta = {k:int(v,0) for k,v in re.findall(r'^(code|base)=(\S+)', (folder/'anchor.txt').read_text(), re.M)}
    memory = (folder/'code.bin').read_bytes()
    body = slave_code(root/'slave.slave')
    base = locate(memory, body, meta['base'], header=32)
    assert base is not None
    offset = base-meta['base']+int(symbol[1],16)
    assert memory[offset:offset+4] == b'AG61'
    count, errors = struct.unpack_from('>II', memory, offset+4)
    cases_symbol = re.search(r'^s60_geometry_cases\s+00:([0-9A-F]+)', listing.read_text(encoding='latin1'), re.M)
    cases = struct.unpack_from('>H', memory, base-meta['base']+int(cases_symbol[1],16))[0] if cases_symbol else 0
    return dict(tick_substeps=n, comparisons=count, mismatches=errors, boundary_cases=cases,
                scope='Fifteen register outputs, CCR, actor distance and target heading; includes synthetic cases only when boundary_cases is nonzero. No performance claim.')


def validate(result):
    assert result['comparisons'] > 0 and result['mismatches'] == 0, result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--listing', type=Path, required=True)
    parser.add_argument('--boundaries', action='store_true', help='require all 128 synthetic coordinate cases')
    args = parser.parse_args()
    result = read(args.capture, args.listing)
    print(json.dumps(result, indent=2))
    validate(result)

    if args.boundaries:
        assert result['boundary_cases'] == 128, result
