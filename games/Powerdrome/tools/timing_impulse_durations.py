#!/usr/bin/env python3
"""Report observed impulse expiry boundaries for the bounded C5=11 route.

VBL durations measure first movement entry to expiry decision (20-ms resolution).
They exclude the final represented movement interval. Logical durations, when
available, use the same boundaries; the full integrated lifetime adds 20 ms.
This report does not assert equivalent trajectories or an A500 calibration pass.
"""
import argparse
import json
from pathlib import Path
import re


def episodes(log, tag):
    start = pending = None
    known_reset = False
    result = []
    count = 0
    for field, offset, values in re.findall(
            rf'^{tag} (-?\d+) (0x[0-9a-f]+) (.+)$', log, re.M):
        field, offset = int(field), int(offset, 16)
        v = list(map(int, values.split()))
        active, age = v[17:19] if tag == 'PDTIME_EVENT' else v[10:12]
        clock = None if tag == 'PDTIME_EVENT' else v[0]
        if offset in (0xadba, 0x9c8c):
            assert pending is None, 'Reset interrupted an impulse probe pair'
            start, known_reset, count = None, True, 0
        elif offset == 0xcd96:
            assert pending is None and active
            if start is None:
                start = (field, clock, age)
            pending = age
            count += 1
        elif offset == 0xcdc4 and pending is not None:
            assert pending <= age <= pending + 1, 'Unexpected age change'
            pending = None
            if not active:
                if known_reset:
                    assert start[2] == 0 and age == 10, 'Unexpected fixture impulse lifetime'
                    result.append(dict(first_field=start[0], expiry_field=field,
                                       steps=count, boundary_vbl_ms=20*(field-start[0]),
                                       boundary_logical_ms=None if clock is None else 5*(clock-start[1])))
                start, known_reset, count = None, False, 0
    assert len(result) == 3, 'Expected three complete observed C5=11 impulses'
    return result


p = argparse.ArgumentParser(description=__doc__)
p.add_argument('captures', type=Path, nargs='+')
a = p.parse_args()
for root in a.captures:
    cfg = json.loads((root/'configuration.json').read_text())
    assert re.search(r'\bCUSTOM5=11\b', cfg['WHD_ARGS']) and int(cfg['FIELDS']) == 750
    log = (root/'swaps-gdb.txt').read_text()
    rows = episodes(log, 'PDTIME_EVENT')
    if re.search(r'^PDFORCE_EVENT ', log, re.M):
        logical = episodes(log, 'PDFORCE_EVENT')
        for row, other in zip(rows, logical):
            assert all(row[k] == other[k] for k in ('first_field', 'expiry_field', 'steps', 'boundary_vbl_ms'))
            row['boundary_logical_ms'] = other['boundary_logical_ms']
            assert row['boundary_logical_ms'] == 880 and row['steps'] == 45
    else:
        game = int((root/'game-base.txt').read_text(), 0)
        assert (root/'chip.bin').read_bytes()[game+0xca44:game+0xca46] == bytes.fromhex('082e'), 'Reference needs native timing'
        assert all(row['steps'] == 10 for row in rows)
    print(json.dumps(dict(capture=root.name, episodes=rows), indent=2))
