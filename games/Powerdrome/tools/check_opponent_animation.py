#!/usr/bin/env python3
"""Audit native animation arithmetic and calibrated logical preparation cadence.

Requires 9950/9A08 PDANIM probes. Logical runs also need TIMING_EARLY and CEDC.
Calibration compares the observed visible prefix, not an unobserved full lifetime.
"""
import argparse
from collections import defaultdict
from pathlib import Path
import struct


def signed(v):
    return (v ^ 0x8000)-0x8000


def inspect(root, logical=False):
    before = {}
    rows = defaultdict(list)
    session = None
    first_world = None
    event = None
    checked = calls = 0
    for line in (root/'swaps-gdb.txt').read_text().splitlines():
        v = line.split()
        if not v:
            continue
        if v[0] == 'PDTIME_EVENT':
            event = (int(v[1]), int(v[2], 16))
            session = None
        elif v[0] == 'PDSESSION_EVENT':
            assert event == (int(v[1]), int(v[2], 16))
            session = list(map(int, v[3:]))
            if event[1] == 0xcedc and session[13] and first_world is None:
                first_world = session[14]
        elif v[0] == 'PDANIM_EVENT':
            assert event == (int(v[1]), int(v[2], 16))
            t = list(map(int, v[3:]))
            assert len(t) == 27
            pilot = t[1]
            supported = t[19] == 65535 and t[23] == t[24] == 0
            if event[1] == 0x9950:
                before[pilot] = t
                if logical and supported and session and session[8]:
                    assert first_world is not None and session[13] == 1, 'Preparation ran outside a logical world step'
                    assert (session[14]-first_world+4) % 24 == 0, 'Preparation is not on the six-tick cadence'
                    calls += 1
                continue
            assert event[1] == 0x9a08 and pilot in before
            old = before.pop(pilot)
            if not supported:
                continue
            assert old[12] and not old[22]
            expected = old.copy()
            age = old[13]
            if signed(old[18]) <= 0:
                direction = 1 if signed(age) < signed(old[15]) else -1
                for i in range(3):
                    expected[9+i] = (old[9+i]+direction*old[6+i]) & 65535
                age = (age+1) & 65535
            for i in range(3):
                expected[3+i] = (old[3+i]+expected[9+i]) & 65535
            if signed(age) >= signed(old[14]):
                expected[12], age = 0, 0
            expected[13] = age
            assert expected == t, f'Native animation arithmetic differs for pilot {pilot} at field {event[0]}'
            checked += 1
            time = session[14]*5 if logical else event[0]*20
            rows[pilot].append((time, t[6:16]))
    assert checked >= 32 and set(rows) == {1, 2, 3, 4}, 'Insufficient four-pilot animation coverage'
    if logical:
        assert calls >= checked
        game = int((root/'game-base.txt').read_text(), 0)
        base = int((root/'dump-base.txt').read_text(), 0)
        chip = (root/'chip.bin').read_bytes()
        data = (root/'final-code.bin').read_bytes()
        frame = struct.unpack_from('>I', chip, game+0xca46)[0]-base
        pos = data.find(b'PDANIM01', frame, min(len(data), frame+16384))
        assert pos >= 0
        active, phase, ticks, prepared, projected, clock, phases = struct.unpack_from('>HH5I', data, pos+8)
        assert active == 0 and phase < 6 and phases >= ticks > 0
        assert prepared == calls and projected > 0
        print(f'{root.name}: {prepared} logical preparations, {projected} projection-only draws; owner cleared')
    print(f'  {checked} native animation transitions verified')
    for pilot, sequence in sorted(rows.items()):
        prefix = sequence[:9]
        assert len(prefix) == 9
        print(f'  Pilot {pilot}: first nine observed updates span {prefix[-1][0]-prefix[0][0]} ms')
    return rows


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('capture', type=Path)
    p.add_argument('--logical', action='store_true')
    p.add_argument('--reference', type=Path)
    a = p.parse_args()
    actual = inspect(a.capture, a.logical)
    if a.reference:
        assert a.logical
        reference = inspect(a.reference)
        for pilot in sorted(reference):
            expected, observed = reference[pilot][:9], actual[pilot][:9]
            assert [r[1] for r in observed] == [r[1] for r in expected], 'Visible animation state prefix differs'
            duration = expected[-1][0]-expected[0][0]
            measured = observed[-1][0]-observed[0][0]
            assert abs(measured-duration) <= 90 and abs(measured-duration) <= duration/10, 'A500 response calibration gate failed'
        print('  Four native visible prefixes match; timing passes both 10% and 90-ms limits')
