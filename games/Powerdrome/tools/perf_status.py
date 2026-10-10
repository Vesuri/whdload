#!/usr/bin/env python3
"""Read the optional planar renderer's diagnostic block from a capture directory."""
import argparse
import json
import struct
from pathlib import Path


def status(path):
    data = path.read_bytes()
    found = []
    start = 0
    while (start := data.find(b'PDPERF0', start)) >= 0:
        version = data[start + 7:start + 8]
        assert version in (b'1', b'2', b'3')
        values = struct.unpack_from('>9IH' + ('I' if version != b'1' else ''), data, start + 8)
        if version == b'1':
            values += (0,)
        if values[3]:
            found.append(dict(zip(('arena', 'arena_bytes', 'bitmap', 'game', 'chip',
                                   'entries', 'staged_frames', 'pixel_failures',
                                   'first_bad_pixel_end_offset', 'active', 'guard_failures'), values)))
        start += 8
    assert len(found) == 1, f'{path}: expected one initialized diagnostic block, got {len(found)}'
    result = found[0]
    start = 0
    while (start := data.find(b'PDRAST0', start)) >= 0:
        new = data[start+7:start+8] == b'2'
        values = struct.unpack_from('>4IHI' + ('I' if new else ''), data, start + 8)
        if not new:
            values += (0,)
        if values[0] or values[3]:
            result.update(zip(('raster_code', 'span_resume', 'native_edge', 'fast_edge',
                               'edge_active', 'scratch_failures', 'register_failures'), values))
        start += 8
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    args = parser.parse_args()
    result = {name: status(args.capture / filename) for name, filename in
              (('initial', 'code.bin'), ('final', 'final-code.bin'))}
    result['captured'] = {key: result['final'][key] - result['initial'][key]
                          for key in ('entries', 'staged_frames', 'pixel_failures')}
    if result['initial'].get('raster_code'):
        base = int((args.capture/'dump-base.txt').read_text(), 0)
        offset = result['initial']['raster_code'] - base
        size = (0x1609c-0x15b68) + 16*(0x1609c-0x16020) + 64
        before = (args.capture/'code.bin').read_bytes()[offset:offset+size]
        after = (args.capture/'final-code.bin').read_bytes()[offset:offset+size]
        result['raster_code_unchanged'] = len(before) == size and before == after
        assert result['raster_code_unchanged'], 'Fast rasterizer code changed during the run'
    data = (args.capture/'final-code.bin').read_bytes()
    pos = 0
    while (pos := data.find(b'PDMISM01', pos)) >= 0:
        snapshots = [struct.unpack_from('>15IH', data, pos+8+i*62) for i in range(4)]
        if any(snapshots[0]):
            names = [f'd{i}' for i in range(8)] + [f'a{i}' for i in range(7)] + ['ccr']
            result['first_register_mismatch'] = {
                name: dict(zip(('normalized', 'raw', 'reference', 'input'), map(hex, values)))
                for name, values in zip(names, zip(*snapshots))
                if (values[0] ^ values[2]) & (31 if name == 'ccr' else 0xffffffff)
            }
        pos += 8
    print(json.dumps(result, indent=2))
    assert not (result['final']['pixel_failures'] or result['final']['guard_failures'] or result['final'].get('scratch_failures', 0) or result['final'].get('register_failures', 0)), 'Planar verification failed'


if __name__ == '__main__':
    main()
