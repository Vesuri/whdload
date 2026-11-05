#!/usr/bin/env python3
"""Inventory observed render-interval data changes without treating scratch as safe.

Storage-family identification is not a proof of consumer lifetime or of freedom
from gameplay effects. Changes can also originate from concurrent interrupts.
"""
import argparse
import collections
import json
import re
import struct
from pathlib import Path
import simulation_state


def inspect(folder, listing):
    folder, listing = Path(folder), Path(listing)
    assert (folder/'slave.slave').read_bytes() == listing.with_suffix('.slave').read_bytes()
    snapshots = []
    for label in ('render-before', 'render-after'):
        point = folder/label
        meta = {k: int(v, 0) for k, v in re.findall(
            r'^(code|data|base|tick)=(\S+)', (point/'anchor.txt').read_text(), re.M)}
        memory = (point/'code.bin').read_bytes()
        code = memory[meta['code']-meta['base']:meta['code']-meta['base']+0x25360]
        data = memory[meta['data']-meta['base']:meta['data']-meta['base']+0x823c]
        assert len(code) == 0x25360 and len(data) == 0x823c
        assert code[0x11750:0x11754] == bytes.fromhex('52aca4a8'), 'clock counter guard'
        for site, opcode, offset in ((0x1c858, '3c39', 0x292c),
                                     (0x1c85e, '3039', 0x292a),
                                     (0x1c864, '33c0', 0x292c),
                                     (0x1c86a, '33c6', 0x292a),
                                     (0x17b48, '41f9', 0x474c),
                                     (0x17b56, '41f9', 0x484c),
                                     (0x17b66, '41f9', 0x4c48),
                                     (0x17b76, '41f9', 0x5044),
                                     (0x17d14, '41f9', 0x5440),
                                     (0x17d34, '41f9', 0x583c),
                                     (0x14e20, '4df9', 0x5cf0),
                                     (0x14e26, '49f9', 0x5d40),
                                     (0x1c970, '23d0', 0x712c),
                                     (0x1c8b4, '23c8', 0x717a),
                                     (0x1c8ba, '23c8', 0x7166),
                                     (0x1ccc0, '4879', 0x727e),
                                     (0x1ccc6, '4879', 0x7252)):
            assert code[site:site+6] == bytes.fromhex(opcode)+struct.pack('>I', meta['data']+offset), hex(site)
        assert code[0x13b84:0x13b8e] == bytes.fromhex('3f2cdf384267486cc74c'), 'vertex-validity reset guard'
        for site, expected in ((0x14678, '43ecdc4e23817800'),
                               (0x1468e, '43ecdc9e23817800'),
                               (0x13a56, '43ecde1022d83290'),
                               (0x138b4, '3941df3a'),
                               (0x138c6, '3941df3c'),
                               (0x138d8, '3941df3e'),
                               (0x12928, '294bdd90'),
                               (0x12af0, '2940dd98'),
                               (0x12afc, '2940dd9c'),
                               (0x12b08, '2940dda0'),
                               (0x12b0c, '486cdda4486cdddc486cdd98'),
                               (0x1ccbc, '48780014'),
                               (0x2518e, '4eaefee6'),
                               (0x13a80, '41ecde6821807800'),
                               (0x13a0a, '41ecdf4c21acdf447800'),
                               (0x13ac0, '41ecde68'),
                               (0x13bdc, '47ecdf4c')):
            expected = bytes.fromhex(expected)
            assert code[site:site+len(expected)] == expected, hex(site)
        # NDK graphics/rastport.i: AreaInfo has four pointers, then
        # Count/MaxCount/FirstX/FirstY. InitArea's 20 vectors use four bytes
        # per XY pair, followed by one flag byte per vector.
        assert struct.unpack_from('>I', data, 0x7252)[0] == meta['data']+0x727e
        assert struct.unpack_from('>I', data, 0x725a)[0] == meta['data']+0x727e+80
        assert struct.unpack_from('>H', data, 0x7264)[0] == 20
        snapshots.append((meta, data))
    (before_meta, before), (after_meta, after) = snapshots
    assert before_meta == after_meta, 'render interval crosses a simulation boundary or relocation'
    assert before[0x292a:0x292c] == after[0x292c:0x292e]
    assert before[0x292c:0x292e] == after[0x292a:0x292c]
    ranges = [(0x24a8, 0x24ac, 'elapsed_clock'),
              (0x292a, 0x292e, 'display_buffer_indices'),
              (0x474c, 0x484c, 'vertex_validity_flags'),
              (0x484c, 0x5440, 'transformed_vertex_coordinates'),
              (0x5440, 0x5c38, 'projected_vertex_coordinates'),
              (0x5c4e, 0x5cee, 'polygon_screen_coordinates'),
              (0x5cf0, 0x5d90, 'clipped_polygon_coordinates'),
              (0x5d90, 0x5d94, 'projection_context_pointer'),
              (0x5e10, 0x5e16, 'model_transform_input'),
              (0x5f3a, 0x5f40, 'model_transformed_vector'),
              (0x5d98, 0x5db0, 'projection_translation_vectors'),
              (0x712c, 0x7130, 'view_copper_pointer'),
              (0x7166, 0x716a, 'rasinfo_bitmap_pointer'),
              (0x717a, 0x717e, 'rastport_bitmap_pointer'),
              (0x7266, 0x726a, 'area_first_point'),
              (0x727e, 0x72ce, 'area_vector_buffer'),
              # Only the first nine slots, whose producers/consumers are
              # observed by model_sort_lifetime.py. This is not a declaration
              # of either array's total capacity or a scratch exclusion.
              (0x5e68, 0x5e8c, 'observed_model_sort_key_prefix'),
              (0x5f4c, 0x5f70, 'observed_model_face_pointer_prefix')]
    counts = collections.Counter()
    runs = []
    for offset, (a, b) in enumerate(zip(before, after)):
        if a == b:
            continue
        category = next((name for lo, hi, name in ranges if lo <= offset < hi), 'unclassified')
        counts[category] += 1
        if runs and runs[-1]['end'] == offset and runs[-1]['category'] == category:
            runs[-1]['end'] += 1
        else:
            runs.append(dict(start=offset, end=offset+1, category=category))
    for row in runs:
        start, end = row['start'], row['end']
        row.update(start=hex(start), end=hex(end), before=before[start:end].hex(), after=after[start:end].hex())
    changes = list(simulation_state.differences(
        simulation_state.snapshot(folder/'render-before', True, True),
        simulation_state.snapshot(folder/'render-after', True, True)))
    assert all(change.startswith('projection_scratch') for change in changes), changes
    return dict(tick=before_meta['tick'], changed_bytes=sum(counts.values()),
                categories=dict(counts), changes=runs, mapped_changes=changes,
                scope='One retained render interval. Guarded storage families only; unclassified bytes are retained. No new scratch exclusion and no whole-program lifetime proof.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--listing', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(inspect(args.capture, args.listing), indent=2))
