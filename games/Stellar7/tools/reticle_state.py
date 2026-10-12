#!/usr/bin/env python3
"""Read target-reticle clock fixture results from an exact build snapshot."""
import argparse
import json
import re
import struct
from pathlib import Path
import sim60_state
from stellar7_report import locate


def read(folder, listing):
    folder, listing = Path(folder), Path(listing)
    binary = (folder/'slave.slave').read_bytes()
    assert binary == listing.with_suffix('.slave').read_bytes(), 'listing build mismatch'
    symbols = listing.read_text(encoding='latin1')
    offset = int(re.search(r'^s60_reticle_results\s+00:([0-9A-F]+)', symbols, re.M)[1], 16)
    meta = {k: int(v, 0) for k, v in re.findall(
        r'^(code|base)=(\S+)', (folder/'anchor.txt').read_text(), re.M)}
    memory = (folder/'code.bin').read_bytes()
    size = struct.unpack_from('>I', binary, 28)[0]*4
    base = locate(memory, binary[32:32+size], meta['base'], header=32)
    assert base is not None
    at = base-meta['base']+offset
    assert memory[at:at+4] == b'RT60'
    result = dict(zip(('cases', 'errors', 'comparisons'),
                    struct.unpack_from('>HHH', memory, at+4)))
    result['tick_substeps'] = sim60_state.read(folder)['substeps']
    result['continuation_restored'] = memory[meta['code']-meta['base']+0xbd16:meta['code']-meta['base']+0xbd18] == bytes.fromhex('1039')
    return result


def validate(result):
    assert result['cases'] == 64, result
    assert result['errors'] == 0, result
    assert result['continuation_restored'], result
    assert result['comparisons'] == 128, result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--listing', type=Path, required=True)
    args = parser.parse_args()
    result = read(args.capture, args.listing)
    print(json.dumps(result, indent=2))
    validate(result)
