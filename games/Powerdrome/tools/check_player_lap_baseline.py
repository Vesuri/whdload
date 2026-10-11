#!/usr/bin/env python3
"""Verify the native first player-lap boundary and inventory timer clock drift.

Requires read-only PDPLAYER_CLOCK and PDSESSION probes around 10BF0..10C00,
F9A2 and F108/F10E. This is a baseline audit, not a timing-correction gate.
"""
import argparse
import struct
from collections import defaultdict
from pathlib import Path


def check(root, logical=False):
    rows = defaultdict(list)
    session = None
    for line in (root/'swaps-gdb.txt').read_text().splitlines():
        v = line.split()
        if not v:
            continue
        if v[0] == 'PDTIME_EVENT':
            session = None
        elif v[0] == 'PDSESSION_EVENT':
            session = (int(v[1]), int(v[2], 16), list(map(int, v[3:])))
        elif v[0] == 'PDPLAYER_CLOCK':
            field, off = int(v[1]), int(v[2], 16)
            assert session is not None and session[:2] == (field, off)
            values = list(map(int, v[3:]))
            assert len(values) == 13
            rows[off].append((field, values, session[2]))
    stages = (0x10bf0, 0x10bf6, 0x10c00, 0xf9a2) if logical else (0x10bf0, 0x10bf6, 0x10bfc, 0x10c00, 0xf9a2)
    assert all(len(rows[o]) == 1 for o in stages), 'Need exactly one first-lap boundary'
    first, read, stored, committed = [rows[o][0] for o in (0x10bf0, 0x10bf6, 0x10c00, 0xf9a2)]
    old, clock = first[1], read[1][10]
    assert first[2][8] == first[2][13] == 1, 'Lap boundary must execute inside a logical world step'
    assert old[5:9] == [65535, 65535, 0, 0], 'Expected first human qualifying lap'
    assert read[1][0] == clock
    if not logical:
        assert rows[0x10bfc][0][1][9] == (clock-old[1]) & 0xffffffff
    assert stored[1][1] == committed[1][1] == clock
    assert committed[1][2] == committed[1][3] == 0, 'First crossing must not charge a completed lap'
    assert len(rows[0xf108]) == len(rows[0xf10e]) >= 20
    start = first[2][14]
    if logical:
        assert len(rows[0xf118]) == len(rows[0xf108])
        for entered, observed in zip(rows[0xf108], rows[0xf118]):
            assert entered[0] == observed[0]
            cursor = observed[2][14] - (0 if observed[2][13] else 4)
            expected = max(0, cursor-start)
            assert observed[1][9] == expected, 'HUD differs from elapsed completed-world time'
            assert observed[1][1] == clock, 'Logical HUD changed the native shared timestamp'
        game = int((root/'game-base.txt').read_text(), 0)
        base = int((root/'dump-base.txt').read_text(), 0)
        chip = (root/'chip.bin').read_bytes()
        before = (root/'code.bin').read_bytes()
        after = (root/'final-code.bin').read_bytes()
        frame = struct.unpack_from('>I', chip, game+0xca46)[0]-base
        pos = after.find(b'PDPLAP01', frame, frame+16384)
        assert pos >= 0
        assert struct.unpack_from('>H', after, pos+8)[0] == 1
        assert struct.unpack_from('>II', after, pos+12) == (start, clock)
        reads = struct.unpack_from('>I', after, pos+28)[0]-struct.unpack_from('>I', before, pos+28)[0]
        assert reads == len(rows[0xf118])
        assert struct.unpack_from('>I', after, pos+36)[0] == struct.unpack_from('>I', before, pos+36)[0], 'Unexpected native reset fallback'
        print(f'  {reads} corrected HUD durations match completed logical steps; private/native starts preserved, no reset fallback')
    gaps = []
    for before, after in zip(rows[0xf108], rows[0xf10e]):
        assert before[0] == after[0]
        assert before[1][1] == after[1][1] == clock, 'Native lap start changed during display window'
        assert before[1][5] == after[1][5] == 0
        assert after[1][10] == after[1][0], 'HUD did not read the native physical clock'
        physical = (after[1][10]-clock) & 0xffffffff
        elapsed = (after[2][14]-start) & 0xffffffff
        gap = (physical-elapsed) & 0xffffffff
        if gap & 0x80000000:
            gap -= 1 << 32
        gaps.append(gap*5)
    print(f'{root.name}: first natural lap crossing owns a logical world step; native subtraction/store and zero initial lap total pass')
    print(f'  {len(gaps)} HUD clock pairs; physical minus retained-world elapsed: {min(gaps)}..{max(gaps)} ms, final {gaps[-1]} ms')
    print('  No completed player lap or player finish is covered')
    if not logical:
        print('  Baseline only: not a correction pass')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('capture', type=Path)
    p.add_argument('--logical', action='store_true', help='Check corrected HUD output at F118 and private lap state')
    a = p.parse_args()
    check(a.capture, a.logical)
