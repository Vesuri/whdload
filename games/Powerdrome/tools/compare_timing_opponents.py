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


def read(root, initial_pit=False):
    cfg = json.loads((root / 'configuration.json').read_text())
    assert re.search(r'\bCUSTOM5=13\b', cfg['WHD_ARGS'])
    assert cfg['OPPONENT_STATE'] == '1'
    if initial_pit:
        assert cfg['TIMING_EARLY'] == '1' and int(cfg['ANCHOR'], 0) == 0xbc3a
    else:
        assert int(cfg['FIELDS']) == 500
    game = int((root / 'game-base.txt').read_text(), 0)
    setup = (root / 'probe-0xe976-chip.bin').read_bytes()
    epoch = struct.unpack_from('>I', setup, game + 0xa6e + 0x206)[0]
    fixture_epoch = 0 if initial_pit else fixture(root / 'code.bin')['epoch'] * 4
    point = 0xd7f0 if initial_pit else 0xcedc
    initial_kind = 0
    pending = None
    rows = {}
    for line in (root / 'swaps-gdb.txt').read_text().splitlines():
        v = line.split()
        if not v:
            continue
        if v[0] == 'PDINITIAL_EVENT':
            initial_kind = int(v[3])
        if v[0] == 'PDPOPP_EVENT':
            if pending is not None:
                assert len(pending[3]) == 4, 'Incomplete internal opponent snapshot'
            pending = None
            if int(v[2], 16) == point:
                state = list(map(int, v[3:]))
                assert len(state) == 27
                if initial_pit:
                    if initial_kind != 1 or state[1] != 1 or state[24] != 0:
                        continue
                    time = state[5] - state[13] + 18
                    completed = state[8] + 1
                else:
                    assert state[24] == 1
                    time, completed = state[25] - fixture_epoch, state[8]
                pending = (int(v[1]), time, completed, [], state[17])
        if v[0] == 'PDOPP_ARRAY':
            if int(v[2], 16) != point or pending is None:
                continue
            assert int(v[1]) == pending[0]
            assert int(v[3]) == len(pending[3])
            record = bytearray.fromhex(v[4])
            assert len(record) == 190
            timestamp = struct.unpack_from('>I', record, 0x5c)[0]
            struct.pack_into('>I', record, 0x5c, (timestamp - epoch) & 0xffffffff)
            pending[3].append(bytes(record))
            if len(pending[3]) == 4:
                assert pending[1] not in rows
                rows[pending[1]] = (pending[0], pending[2], tuple(pending[3]), pending[4])
    assert len(rows) >= (30 if initial_pit else 450), 'Too few complete opponent snapshots'
    keys = sorted(rows)
    step = 18 if initial_pit else 4
    assert all(y - x == step for x, y in zip(keys, keys[1:])), 'Missing or repeated logical snapshot'
    return game, rows


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference', type=Path)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--report-only', action='store_true', help='Report known differences without asserting equivalence')
    parser.add_argument('--initial-pit', action='store_true',
                        help='Compare complete initial-pit updates at matching elapsed opponent deadlines')
    args = parser.parse_args()
    game, left = read(args.reference, args.initial_pit)
    other_game, right = read(args.capture, args.initial_pit)
    assert game == other_game, 'Different relocation bases need a separate pointer-field audit'
    keys = sorted(left.keys() & right.keys())
    assert len(keys) >= (30 if args.initial_pit else 450)
    bad = [k for k in keys if left[k][2] != right[k][2]]
    rng_bad = [k for k in keys if left[k][3] != right[k][3]]
    print(f'{args.capture.name} vs {args.reference.name}: {len(keys)} common complete '
          f'four-opponent snapshots; {len(bad)} differ after lap-epoch normalization; '
          f'{len(rng_bad)} RNG differences')
    if bad:
        key = bad[0]
        domain = 'initial-pit elapsed time' if args.initial_pit else 'fixture-relative world time'
        print(f'First difference at {domain} {key * 5} ms; '
              f'physical fields {left[key][0]}/{right[key][0]}; '
              f'completed opponent updates {left[key][1]}/{right[key][1]}')
        for index, (a, b) in enumerate(zip(left[key][2], right[key][2])):
            offsets = [f'${off:02x}' for off in range(0, 190, 2) if a[off:off+2] != b[off:off+2]]
            print(f'  Opponent {index}: differing words ' + ', '.join(offsets))
    if not args.report_only:
        assert not bad and not rng_bad, 'Complete opponent records or RNG differ; no trajectory equivalence claim'
