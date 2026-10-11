#!/usr/bin/env python3
"""Read whole projection-pass native-comparison fixture results from an exact build snapshot."""
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
    offset = int(re.search(r'^s60_batch_results\s+00:([0-9A-F]+)', symbols, re.M)[1], 16)
    meta = {k: int(v, 0) for k, v in re.findall(
        r'^(code|base)=(\S+)', (folder/'anchor.txt').read_text(), re.M)}
    memory = (folder/'code.bin').read_bytes()
    size = struct.unpack_from('>I', binary, 28)[0]*4
    base = locate(memory, binary[32:32+size], meta['base'], header=32)
    assert base is not None
    at = base-meta['base']+offset
    assert memory[at:at+4] == b'Q760'
    result = dict(zip(('cases', 'actor_errors', 'record_errors', 'scratch_errors', 'path_errors', 'busy'),
                    struct.unpack_from('>6H', memory, at+4)))
    def value(name, fmt):
        off = int(re.search(r'^'+name+r'\s+00:([0-9A-F]+)', symbols, re.M)[1], 16)
        return struct.unpack_from(fmt, memory, base-meta['base']+off)[0]
    result['motion_table_restored'] = value('s60_motion_table', '>I') == value('s60_batch_saved_table', '>I')
    result['mesh_entry_restored'] = struct.unpack_from('>H', memory, meta['code']-meta['base']+0x132b2)[0] == value('s60_batch_saved_mesh', '>H')
    result['tick_substeps'] = n
    return result


def validate(result):
    assert result['cases'] == 64, result
    assert result['motion_table_restored'] and result['mesh_entry_restored'], result
    assert not any(result[name] for name in ('actor_errors', 'record_errors', 'scratch_errors', 'path_errors', 'busy')), result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--listing', type=Path, required=True)
    args = parser.parse_args()
    result = read(args.capture, args.listing)
    print(json.dumps(result, indent=2))
    validate(result)
