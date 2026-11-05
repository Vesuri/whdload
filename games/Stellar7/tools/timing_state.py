#!/usr/bin/env python3
"""Read the timing prototype's debugger ABI from a fixed-window capture."""
import json
import re
import struct
import sys
from pathlib import Path


def read(folder):
    folder = Path(folder)
    meta = {k: int(v, 0) for k, v in re.findall(
        r'^(code|base)=(\S+)', (folder/'anchor.txt').read_text(), re.M)}
    memory = (folder/'code.bin').read_bytes()
    code = meta['code'] - meta['base']
    if memory[code+0x2af6:code+0x2af8] != b'\x4e\xb9':
        return {'enabled': False}
    target = struct.unpack_from('>I', memory, code+0x2af8)[0] - meta['base']
    if memory[target+4:target+8] != b'S7TM':
        raise ValueError('Unexpected timing hook/ABI')
    keys = ('last_field', 'credit', 'steps_started', 'presents', 'skipped',
            'simulation_hz', 'field_hz', 'last_step', 'draw', 'draw_countdown')
    result = dict(zip(keys, struct.unpack_from('>5I5H', memory, target+8)))
    result['phase_origin_units'] = result['last_field'] * result['simulation_hz'] - result['last_step'] * result['field_hz'] - result['credit']
    return result


if __name__ == '__main__':
    for folder in sys.argv[1:]:
        print(folder, json.dumps(read(folder), sort_keys=True))
