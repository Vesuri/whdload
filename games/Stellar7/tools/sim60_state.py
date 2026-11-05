#!/usr/bin/env python3
"""Read SIM60 scheduler state from a capture; no target writes."""
import json
import re
import struct
import sys
from pathlib import Path


def decode_version(raw):
    """Decode the compatible layout byte and the 12-N substep tag."""
    version, tag = raw & 255, raw >> 8
    substeps = 12-tag
    if not 1 <= version <= 30 or substeps not in (1, 2, 3, 4, 6, 12):
        raise ValueError(f'Unsupported SIM60 ABI word {raw:#x}')
    if tag and version < 29:
        raise ValueError('Substep tag requires ABI layout 29 or later')
    return version, substeps


def build_constant(listing, name):
    """Read an absolute assembler symbol from an exact retained listing."""
    match = re.search(r'^'+re.escape(name)+r'\s+E:([0-9A-F]+)',
                      Path(listing).read_text(encoding='latin1'), re.M)
    if not match:
        raise ValueError(f'Missing build constant {name}')
    return int(match[1], 16)


def read(folder):
    folder = Path(folder)
    meta = {k: int(v, 0) for k, v in re.findall(
        r'^(code|data|base)=(\S+)', (folder/'anchor.txt').read_text(), re.M)}
    memory = (folder/'code.bin').read_bytes()
    code = meta['code'] - meta['base']
    if memory[code+0x2af6:code+0x2af8] != bytes.fromhex('4ef9'):
        raise ValueError('SIM60 entry not installed')
    target = struct.unpack_from('>I', memory, code+0x2af8)[0] - meta['base']
    if memory[target+4:target+8] != b'S760':
        raise ValueError('Unexpected SIM60 ABI')
    names = ('last_field', 'credit', 'ticks', 'renders', 'last_render_tick',
             'field_hz', 'phase', 'event_due', 'rendering', 'running', 'modal_resumes')
    result = dict(zip(names, struct.unpack_from('>5I6H', memory, target+8)))
    version, n = decode_version(struct.unpack_from('>H', memory, target+50)[0])
    result.update(abi_version=version, substeps=n, rate_hz=5*n)
    if version >= 17:
        result['session'] = struct.unpack_from('>I', memory, target+100)[0]
    if version >= 18:
        result['modal_depth'] = struct.unpack_from('>H', memory, target+106)[0]
    if 'data' in meta:
        observed = struct.unpack_from('>I', memory, meta['data']-meta['base']+0x24a8)[0]
        elapsed = (observed-result['last_field']) & 0xffffffff
        result['observed_field'] = observed
        result['unaccounted_fields'] = elapsed
        result['pending_ticks'] = (result['credit']+elapsed*result['rate_hz'])//result['field_hz']
    result['clock_origin'] = result['last_field']*result['rate_hz'] - result['ticks']*result['field_hz'] - result['credit']
    return result


if __name__ == '__main__':
    for folder in sys.argv[1:]:
        print(folder, json.dumps(read(folder), sort_keys=True))
