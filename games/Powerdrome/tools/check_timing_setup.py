#!/usr/bin/env python3
"""Check fixed setup seeding through native opponent initialization checkpoints.

Compares complete 190-byte opponent records at setup and first flight. Only the
known absolute lap-start clock at +$5c is normalized to the setup epoch; no other
field differences are hidden. Full-flight record comparison is a separate check.
"""
import argparse
from pathlib import Path
import re
import struct


def u16(data, at):
    return struct.unpack_from('>H', data, at)[0]


def u32(data, at):
    return struct.unpack_from('>I', data, at)[0]


def snapshot(root, phase):
    data = (root / f'probe-{phase}-chip.bin').read_bytes()
    game = int((root / 'game-base.txt').read_text(), 0)
    state = game + 0xa6e
    count = struct.unpack_from('>h', data, state + 0x340)[0] + 1
    pointer = u32(data, state + 0x342)
    assert count == 4 and pointer == game + 0x1ab0
    records = [data[pointer + i * 190:pointer + (i + 1) * 190] for i in range(count)]
    assert all(len(r) == 190 for r in records)
    return data, state, records


def check(root):
    other = (root / 'probe-0xe976-other.bin').read_bytes()
    live = [m.start() for m in re.finditer(b'PDSETUP1', other)
            if u32(other, m.start() + 12) == u32(other, m.start() + 16) == 1]
    assert len(live) == 1, 'Expected one native initialization and clock reseed'
    seed = u16(other, live[0] + 8)
    before = (root / 'probe-0xbade-chip.bin').read_bytes()
    data, state, records = snapshot(root, '0xe976')
    assert u16(before, state + 0x62) == seed, 'Native speed selection did not receive fixed seed'
    baseline = u16(data, state + 0x2d2)
    expected = []
    rng = seed
    for record in records:
        rng = (rng * 0x7ab7 + 1) & 65535
        speed = (baseline + (rng >> 9) - 48) & 65535
        if not 0 < speed < 32768:
            speed = 10
        expected.append(speed)
        assert u16(record, 0x16) == speed, 'Native initial speed differs from seeded arithmetic'
    assert u16(data, state + 0x62) == rng
    epoch = u32(data, state + 0x206)
    assert all(u32(r, 0x5c) == epoch for r in records)
    print(f'{root.name}: seed {seed}, native baseline {baseline}, four initial speeds {expected}')
    flight, _, final_records = snapshot(root, '0xca3e')
    game = state - 0xa6e
    fields = u32(flight, game + 0x48fe) - u32(data, game + 0x48fe)
    print(f'  Setup-to-flight: {fields} PAL fields / {fields * 20} ms; '
          f'segments {[u16(r, 2) for r in final_records]}; '
          f'speeds {[u16(r, 0x16) for r in final_records]}')
    result = {}
    for phase in ('0xe976', '0xca3e'):
        _, _, rows = snapshot(root, phase)
        normalized = []
        for record in rows:
            row = bytearray(record)
            struct.pack_into('>I', row, 0x5c, (u32(row, 0x5c) - epoch) & 0xffffffff)
            normalized.append(bytes(row))
        result[phase] = normalized
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('captures', nargs='+', type=Path)
    parser.add_argument('--require-equal', action='store_true',
                        help='Fail if either complete-record checkpoint differs across captures')
    parser.add_argument('--require-initial-equal', action='store_true',
                        help='Require matching complete records at E976 while reporting later differences')
    args = parser.parse_args()
    rows = [check(root) for root in args.captures]
    if args.require_initial_equal:
        assert len(rows) > 1 and all(r['0xe976'] == rows[0]['0xe976'] for r in rows[1:]), 'Native initial opponent records differ'
    different = False
    for root, current in zip(args.captures[1:], rows[1:]):
        for phase in rows[0]:
            differences = []
            for index, (left, right) in enumerate(zip(rows[0][phase], current[phase])):
                words = [f'+${off:02x}:{u16(left, off):04x}/{u16(right, off):04x}'
                         for off in range(0, 190, 2) if left[off:off+2] != right[off:off+2]]
                if words:
                    differences.append(f'opponent {index}: ' + ', '.join(words))
            print(f'{root.name} vs {args.captures[0].name} at {phase}: ' +
                  ('all four complete records match after lap-epoch normalization' if not differences
                   else '\n  ' + '\n  '.join(differences)))
            different |= bool(differences)
    if args.require_equal:
        assert len(rows) > 1 and not different, 'Complete native opponent checkpoint records differ'
