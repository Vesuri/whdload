#!/usr/bin/env python3
"""Validate repair bitmap ownership using paired read-only chip-memory dumps.

An idle-blitter dropped step must preserve both screen buffers and the separate
background exactly. Rendered steps must exchange drawing/display roles. This is
not a comparison of rendered pixels against an independent native rendering.
"""
import argparse
import json
from pathlib import Path
import struct


def word(data, at):
    assert 0 <= at <= len(data)-2
    return struct.unpack_from('>H', data, at)[0]


def long(data, at):
    assert 0 <= at <= len(data)-4
    return struct.unpack_from('>I', data, at)[0]


def bitmap(data, at):
    stride, rows = word(data, at), word(data, at+2)
    depth = data[at+5]
    assert (stride, rows, depth) == (40, 200, 4), 'This gate covers the measured PAL pit bitmaps'
    planes = tuple(long(data, at+8+4*n) for n in range(depth))
    size = stride*rows
    assert all(0 <= p <= len(data)-size for p in planes)
    assert len(set(planes)) == depth
    return (at, stride, rows, data[at+4], depth, planes), tuple(data[p:p+size] for p in planes)


def state(data, game):
    base = game+0xa6e
    result = {'toggle': word(data, base+0x1fa)}
    for role, off in (('draw', 0x3be), ('display', 0x3b6), ('background', 0x3d2)):
        result[role] = bitmap(data, long(data, base+off))
    return result


def check(root, complete_route=False):
    assert (root/'final-code.bin').is_file(), 'Capture must be terminal'
    config = json.loads((root/'configuration.json').read_text())
    assert config['REPAIR_BUFFER_STATE'] == '1'
    game = int((root/'game-base.txt').read_text(), 0)
    observations = {}
    drop = None
    for line in (root/'swaps-gdb.txt').read_text().splitlines():
        p = line.split()
        if not p:
            continue
        if p[0] == 'PDTIME_EVENT':
            drop = None
        elif p[0] == 'PDRDROP_EVENT':
            drop = (int(p[1]), int(p[2], 16), list(map(int, p[3:])))
        elif p[0] == 'PDRBUFFER_EVENT':
            field, off, serial, dma = int(p[1]), int(p[2], 16), int(p[3]), int(p[4])
            assert drop is not None and drop[:2] == (field, off)
            label = 'entry' if off in (0x148d8, 0x14a20) else 'post'
            assert off in (0x148d8, 0x14a20, 0x14962, 0x14aa6)
            pair = observations.setdefault(serial, {})
            assert label not in pair
            pair[label] = (dma, drop[2], off)
    assert observations
    idle_drops = busy_drops = draws = visible_changes = incomplete = bank_checks = 0
    for serial, pair in observations.items():
        if set(pair) != {'entry', 'post'}:
            incomplete += 1
            continue
        before = (root/f'repair-{serial:04d}-entry.bin').read_bytes()
        after = (root/f'repair-{serial:04d}-post.bin').read_bytes()
        assert len(before) == len(after)
        a, b = state(before, game), state(after, game)
        counter = game+0xa6e+0x5e
        assert long(after, counter) == (long(before, counter)+1) & 0xffffffff, 'Native outer service counter must advance once'
        dma, drop_before, entry = pair['entry']
        _, drop_after, post = pair['post']
        assert (entry, post) in ((0x148d8, 0x14962), (0x14a20, 0x14aa6))
        assert drop_after[0] == 0
        assert a['background'][0] == b['background'][0]
        if drop_before[0]:
            assert a['toggle'] == b['toggle']
            assert all(a[role][0] == b[role][0] for role in ('draw', 'display'))
            assert drop_after[3] == drop_before[3]+1, 'Missing service-only continuation'
            if dma & 0x4000:  # DMAF_BLTDONE/BBUSY is bit 14 in the full DMACONR word.
                busy_drops += 1  # Prior DMA can finish during this interval; no byte-equality claim.
            else:
                assert all(a[role][1] == b[role][1] for role in ('draw', 'display', 'background')), f'Dropped step {serial} changed an idle bitmap'
                idle_drops += 1
            # Verify that skipping the blits did not skip the six persistent
            # part-bank selections performed by native 1432E.
            base = game+0xa6e
            assert word(after, base+0xb6) == 0
            assert not (word(after, base+0x374) and word(after, base+0x232))
            mask = word(before, base+0x138)
            source, target = long(before, game+0x6da), long(before, game+0x6de)
            for part in range(6):
                expected = long(before, source+8*part+(0 if mask & (1 << part) else 4))
                assert long(after, target+8*part) == expected, 'Native part-bank mutation was lost'
                bank_checks += 1
        else:
            assert a['toggle'] != b['toggle']
            assert a['draw'][0] == b['display'][0] and a['display'][0] == b['draw'][0]
            visible_changes += int(a['display'][1] != b['display'][1])
            draws += 1
    if complete_route:
        assert len(observations) == 264 and incomplete == 0, 'Need all eight 33-step stages'
    assert idle_drops > 0 and draws > 0 and visible_changes > 0, (
        f'Need drawn and idle-blitter dropped paths: idle={idle_drops}, busy={busy_drops}, '
        f'drawn={draws}, changed={visible_changes}')
    print(f'{root.name}: {idle_drops} idle-blitter dropped steps preserve both 32,000-byte screen buffers and background exactly')
    print(f'{bank_checks} native part-bank selections verified; {draws} normal buffer exchanges, {visible_changes} changed displayed pictures')
    print(f'{busy_drops} busy-entry drops excluded from pixel claims; {incomplete} incomplete pairs excluded')
    print('Native-render equivalence, other phases, service/register/input and nonlocal exit coverage remain separate')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('capture', type=Path)
    p.add_argument('--complete-route', action='store_true', help='Require all 264 paired repair steps')
    args = p.parse_args()
    check(args.capture, args.complete_route)
