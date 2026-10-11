#!/usr/bin/env python3
"""Read HUD simulation-clock fixture results from an exact build snapshot."""
import argparse
import json
import re
import struct
from pathlib import Path
from stellar7_report import locate


def read(folder, listing):
    folder, listing = Path(folder), Path(listing)
    binary = (folder/'slave.slave').read_bytes()
    assert binary == listing.with_suffix('.slave').read_bytes(), 'listing build mismatch'
    symbols = listing.read_text(encoding='latin1')
    offset = int(re.search(r'^s60_hud_results\s+00:([0-9A-F]+)', symbols, re.M)[1], 16)
    meta = {k: int(v, 0) for k, v in re.findall(
        r'^(code|base)=(\S+)', (folder/'anchor.txt').read_text(), re.M)}
    memory = (folder/'code.bin').read_bytes()
    size = struct.unpack_from('>I', binary, 28)[0]*4
    base = locate(memory, binary[32:32+size], meta['base'], header=32)
    assert base is not None
    at = base-meta['base']+offset
    assert memory[at:at+4] == b'HT60'
    result = dict(zip(('cases', 'errors', 'substeps', 'render_checks', 'inactive_checks', 'reappear_checks'),
                    struct.unpack_from('>HHIHHH', memory, at+4)))
    result['continuation_restored'] = memory[meta['code']-meta['base']+0xc3ea:meta['code']-meta['base']+0xc3ec] == bytes.fromhex('3039')
    return result


def validate(result):
    assert result['cases'] == 64, result
    assert result['errors'] == 0, result
    assert result['continuation_restored'], result
    assert result['substeps'] == result['render_checks'] == 2304, result
    assert result['inactive_checks'] == result['reappear_checks'] == 64, result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--listing', type=Path, required=True)
    args = parser.parse_args()
    result = read(args.capture, args.listing)
    print(json.dumps(result, indent=2))
    validate(result)
