#!/usr/bin/env python3
"""Read native neutral-braking endpoint comparisons from an exact retained build."""
import argparse
import json
import re
import struct
from pathlib import Path
import sim60_state
from patchlist import slave_code
from stellar7_report import locate


def read(folder, listing):
    folder, listing = Path(folder), Path(listing)
    root = folder
    while not (root/'slave.slave').exists():
        assert root != root.parent, 'retained slave missing'
        root = root.parent
    assert (root/'slave.slave').read_bytes() == listing.with_suffix('.slave').read_bytes()
    symbol = re.search(r'^s60_input_neutral_results\s+00:([0-9A-F]+)', listing.read_text(encoding='latin1'), re.M)
    assert symbol, 'neutral-input fixture missing'
    meta = {k:int(v,0) for k,v in re.findall(r'^(code|base)=(\S+)', (folder/'anchor.txt').read_text(), re.M)}
    memory = (folder/'code.bin').read_bytes()
    body = slave_code(root/'slave.slave')
    base = locate(memory, body, meta['base'], header=32)
    assert base is not None
    offset = base-meta['base']+int(symbol[1],16)
    assert memory[offset:offset+4] == b'NI60'
    count, errors = struct.unpack_from('>II', memory, offset+4)
    phase, initial, expected, actual = struct.unpack_from('>Hhhh', memory, offset+12)
    return dict(tick_substeps=sim60_state.read(folder)['substeps'], cases=count, mismatches=errors,
                first_failure=dict(phase=phase, initial=initial, expected=expected, actual=actual),
                scope='Fifteen signed neutral-turn velocities at all N starting phases; N substeps compared with one original native 80-unit braking fragment. Private actors; not a complete native input dispatch test.')


def validate(result):
    assert result['cases'] == 15*result['tick_substeps'] and result['mismatches'] == 0, result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--listing', type=Path, required=True)
    args = parser.parse_args()
    result = read(args.capture, args.listing)
    print(json.dumps(result, indent=2))
    validate(result)
