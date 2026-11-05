#!/usr/bin/env python3
"""Decode optional SIM_PROBE entries from a quick_start memory capture."""
import argparse
import json
import struct
from pathlib import Path

def read_capture(directory):
    root = Path(directory)
    meta = json.loads((root / 'anchor.json').read_text())
    memory = (root / 'memory.bin').read_bytes()
    expected_a4 = meta['data_base'] + 0x7ffe
    candidates = []
    cursor = 0
    while True:
        offset = memory.find(b'4DSIMPRB', cursor)
        if offset < 0:
            break
        cursor = offset + 1
        version, size, count = struct.unpack_from('>HHI', memory, offset + 8)
        if version != 1 or size != 40 or count == 0:
            continue
        rows = []
        for sequence in range(max(0, count - 256), count):
            location = offset + 16 + (sequence % 256) * size
            values = struct.unpack_from('>IIIHHHHHBBiiiHH', memory, location)
            keys = ('raw_clock', 'callback_clock', 'a4', 'produced', 'consumed',
                    'simulation', 'divider', 'latch', 'mode', 'started',
                    'x', 'y', 'z', 'ticks', 'event_elapsed')
            row = dict(zip(keys, values))
            row['sequence'] = sequence
            row['backlog'] = (row['produced'] - row['consumed']) & 0xffff
            rows.append(row)
        if rows and all(r['a4'] == expected_a4 for r in rows):
            candidates.append(dict(version=version, total_entries=count, entries=rows))
    if len(candidates) != 1:
        raise ValueError(f'Expected one live recorder, found {len(candidates)}')
    result = candidates[0]
    result['capture'] = root.name
    result['meaning'] = 'Native simulation entry observations, before consuming input; not completion or field-time measurements.'
    return result

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    args = parser.parse_args()
    print(json.dumps(read_capture(args.capture), indent=2))
