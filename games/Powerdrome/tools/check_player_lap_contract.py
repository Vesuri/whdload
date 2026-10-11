#!/usr/bin/env python3
"""Verify player lap/HUD hook registers, stack, physical SUB and native MOVE flags.

Requires PDPLCON_EVENT guest observations and before/after PDMREG_EVENT pairs.
Debugger SR is deliberately ignored: guest diagnostics provide architectural CCR.
"""
import argparse
from pathlib import Path

MASK = 0xffffffff


def sub_flags(a, b):
    value = (a-b) & MASK
    borrow = a < b
    overflow = bool((a ^ b) & (a ^ value) & 0x80000000)
    return (17 if borrow else 0) | (8 if value & 0x80000000 else 0) | (4 if value == 0 else 0) | (2 if overflow else 0)


def check(root):
    assert (root/'final-code.bin').is_file(), 'Need a terminal capture'
    rows = []
    current = None
    names = ('PDPLAP_EVENT', 'PDPLAYER_CLOCK', 'PDSESSION_EVENT', 'PDPLCON_EVENT', 'PDMREG_EVENT')
    for line in (root/'swaps-gdb.txt').read_text().splitlines():
        v = line.split()
        if not v:
            continue
        if v[0] == 'PDTIME_EVENT':
            current = dict(field=int(v[1]), off=int(v[2], 16))
            rows.append(current)
        elif v[0] in names:
            assert current is not None and (current['field'], current['off']) == (int(v[1]), int(v[2], 16))
            current[v[0]] = list(map(int, v[3:]))
    pending = None
    counts = {1: 0, 2: 0}
    logical_laps = 0
    for row in rows:
        off = row['off']
        if off in (0x10bf8, 0xf110):
            assert pending is None, 'Nested or missing hook observation'
            pending = row
            continue
        if off not in (0x10c00, 0xf118):
            continue
        site = 1 if off == 0x10c00 else 2
        assert pending is not None and pending['off'] == (0x10bf8 if site == 1 else 0xf110)
        x, y = pending['PDMREG_EVENT'], row['PDMREG_EVENT']
        private = pending['PDPLAP_EVENT']
        session = pending['PDSESSION_EVENT']
        native = pending['PDPLAYER_CLOCK']
        diagnostic = row['PDPLCON_EVENT']
        assert len(x) == len(y) == 19 and len(diagnostic) == 8
        assert diagnostic[2] == site and x[0] == x[7]
        physical = (x[0]-native[1]) & MASK
        assert diagnostic[3:6] == [physical, x[7], native[1]]
        flags = sub_flags(x[0], native[1])
        assert diagnostic[0] & 31 == flags, 'Physical SUB condition codes changed'
        final_flags = flags & 16
        if site == 1:
            final_flags |= 8 if x[7] & 0x80000000 else 4 if x[7] == 0 else 0
        assert diagnostic[1] & 31 == final_flags, 'Final native MOVE condition codes changed'
        expected = x[:16]
        expected[0] = physical
        eligible = session[8] and native[8] == 0 and native[6] & 0x8000
        if site == 1:
            eligible = eligible and session[13]
        if eligible and private[0] and native[1] == private[2]:
            cursor = session[14]-(4 if site == 2 and not session[13] else 0)
            expected[0] = (cursor-private[1]) & MASK if site == 1 else max(0, cursor-private[1])
            logical_laps += site == 1
        if site == 2:
            expected[1] = (x[1] & 0xffff0000) | 0x12
        assert y[:16] == expected, f'Register or stack contract changed at {off:#x}'
        assert row['PDPLAYER_CLOCK'][1] == (x[7] if site == 1 else native[1]), 'Native shared timestamp contract changed'
        old_diagnostic = pending['PDPLCON_EVENT']
        counter = 6 if site == 1 else 7
        assert diagnostic[counter] == old_diagnostic[counter]+1
        assert diagnostic[13-counter] == old_diagnostic[13-counter]
        counts[site] += 1
        pending = None
    assert pending is None and counts[1] >= 1 and counts[2] >= 20, 'Insufficient complete lap/HUD pairs'
    print(f'{root.name}: {counts[1]} lap hooks ({logical_laps} logical durations), {counts[2]} HUD hooks')
    print('  All native registers/stack, shared timestamp, physical SUB and final MOVE guest flags pass')
    print('  Coverage is limited to observed values and modes; this is not a complete timing gate')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    check(parser.parse_args().capture)
