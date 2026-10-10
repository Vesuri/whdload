#!/usr/bin/env python3
"""Compare complete four-opponent records at matching early-flight world times.

The bounded CUSTOM5=13 fixture must include OPPONENT_STATE and CEDC probes.
Only +$5c, the known absolute lap-start timestamp, is normalized to the native
setup epoch. Other differences are reported, including rendering scratch data.
This deliberately fails on unequal starts; it is not a trajectory tolerance test.
"""
import argparse
import json
from pathlib import Path
import re
import struct
from coverage_status import fixture


def read(root):
    cfg = json.loads((root / 'configuration.json').read_text())
    assert re.search(r'\bCUSTOM5=13\b', cfg['WHD_ARGS'])
    assert cfg['OPPONENT_STATE'] == '1' and int(cfg['FIELDS']) == 500
    game = int((root / 'game-base.txt').read_text(), 0)
    setup = (root / 'probe-0xe976-chip.bin').read_bytes()
    epoch = struct.unpack_from('>I', setup, game + 0xa6e + 0x206)[0]
    fixture_epoch = fixture(root / 'code.bin')['epoch'] * 4
    pending = None
    rows = {}
    for line in (root / 'swaps-gdb.txt').read_text().splitlines():
        v = line.split()
        if not v:
            continue
        if v[0] == 'PDPOPP_EVENT':
            if pending is not None:
                assert len(pending[3]) == 4, 'Incomplete internal opponent snapshot'
            pending = None
            if int(v[2], 16) == 0xcedc:
                state = list(map(int, v[3:]))
                assert len(state) == 27 and state[24] == 1
                pending = (int(v[1]), state[25] - fixture_epoch, state[8], [])
        if v[0] == 'PDOPP_ARRAY':
            assert pending is not None and int(v[1]) == pending[0] and int(v[2], 16) == 0xcedc
            assert int(v[3]) == len(pending[3])
            record = bytearray.fromhex(v[4])
            assert len(record) == 190
            timestamp = struct.unpack_from('>I', record, 0x5c)[0]
            struct.pack_into('>I', record, 0x5c, (timestamp - epoch) & 0xffffffff)
            pending[3].append(bytes(record))
            if len(pending[3]) == 4:
                assert pending[1] not in rows
                rows[pending[1]] = (pending[0], pending[2], tuple(pending[3]))
    assert len(rows) >= 450, 'Too few complete early-flight snapshots'
    keys = sorted(rows)
    assert all(y - x == 4 for x, y in zip(keys, keys[1:])), 'Missing or repeated 20-ms snapshot'
    return game, rows


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference', type=Path)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--report-only', action='store_true', help='Report known differences without asserting equivalence')
    args = parser.parse_args()
    game, left = read(args.reference)
    other_game, right = read(args.capture)
    assert game == other_game, 'Different relocation bases need a separate pointer-field audit'
    keys = sorted(left.keys() & right.keys())
    assert len(keys) >= 450
    bad = [k for k in keys if left[k][2] != right[k][2]]
    print(f'{args.capture.name} vs {args.reference.name}: {len(keys)} common complete '
          f'four-opponent snapshots; {len(bad)} differ after lap-epoch normalization')
    if bad:
        key = bad[0]
        print(f'First difference at fixture-relative world time {key * 5} ms; '
              f'physical fields {left[key][0]}/{right[key][0]}; '
              f'completed opponent updates {left[key][1]}/{right[key][1]}')
        for index, (a, b) in enumerate(zip(left[key][2], right[key][2])):
            offsets = [f'${off:02x}' for off in range(0, 190, 2) if a[off:off+2] != b[off:off+2]]
            print(f'  Opponent {index}: differing words ' + ', '.join(offsets))
    if not args.report_only:
        assert not bad, 'Complete opponent records differ; no trajectory equivalence claim'
