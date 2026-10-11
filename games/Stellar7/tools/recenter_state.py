#!/usr/bin/env python3
"""Read world-recentering native-reference fixture results from an exact build snapshot."""
import argparse
import json
import re
import struct
from pathlib import Path
import sim60_state
from stellar7_report import locate


def read(folder, listing):
    folder, listing = Path(folder), Path(listing)
    n = sim60_state.read(folder)['substeps']
    binary = (folder/'slave.slave').read_bytes()
    assert binary == listing.with_suffix('.slave').read_bytes(), 'listing build mismatch'
    symbols = listing.read_text(encoding='latin1')
    offset = int(re.search(r'^s60_recenter_results\s+00:([0-9A-F]+)', symbols, re.M)[1], 16)
    meta = {k: int(v, 0) for k, v in re.findall(
        r'^(code|base)=(\S+)', (folder/'anchor.txt').read_text(), re.M)}
    memory = (folder/'code.bin').read_bytes()
    size = struct.unpack_from('>I', binary, 28)[0]*4
    base = locate(memory, binary[32:32+size], meta['base'], header=32)
    assert base is not None
    at = base-meta['base']+offset
    signature = memory[at:at+4]
    assert signature == b'RC60'
    completed, failed = struct.unpack_from('>2H', memory, at+4)
    errors = list(struct.unpack_from('>128H', memory, at+8))
    return dict(tick_substeps=n, cases=completed, failed=failed, errors=errors)


def validate(result):
    assert result['cases'] == 128 and result['failed'] == 0, result
    assert not any(result['errors']), result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--listing', type=Path, required=True)
    args = parser.parse_args()
    result = read(args.capture, args.listing)
    print(json.dumps(result, indent=2))
    validate(result)
