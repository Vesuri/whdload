#!/usr/bin/env python3
"""Verify private lap start/HUD time across a real input-driven native pause."""
import argparse
from pathlib import Path
from timing_report import input_state


def check(root):
    rows = []
    current = None
    for line in (root/'swaps-gdb.txt').read_text().splitlines():
        v = line.split()
        if not v:
            continue
        if v[0] == 'PDTIME_EVENT':
            current = dict(field=int(v[1]), off=int(v[2], 16))
            rows.append(current)
        elif v[0] in ('PDPLAP_EVENT', 'PDPLAYER_CLOCK', 'PDSESSION_EVENT'):
            assert current is not None and (current['field'], current['off']) == (int(v[1]), int(v[2], 16))
            current[v[0]] = list(map(int, v[3:]))
    begins = [r for r in rows if r['off'] == 0xbe12]
    ends = [r for r in rows if r['off'] == 0xbef2]
    assert len(begins) == len(ends) == 1
    first, last = begins[0], ends[0]
    x, y = first['PDPLAP_EVENT'], last['PDPLAP_EVENT']
    assert len(x) == len(y) == 9 and x[0] == y[0] == 1
    assert all(x[i] == y[i] for i in (0, 1, 2, 3, 4, 6, 7, 8)), 'Private lap state advanced or reset during pause'
    assert x[7] == y[7] == 0, 'Unexpected native reset fallback'
    assert first['PDSESSION_EVENT'][14:16] == last['PDSESSION_EVENT'][14:16], 'World/input clock advanced during pause'
    assert first['PDPLAYER_CLOCK'][1] == last['PDPLAYER_CLOCK'][1] == x[2]
    inputs = input_state(root/'final-code.bin')
    assert inputs['produced'] == inputs['consumed'] and inputs['overflow'] == 0
    pause = inputs['pause']
    fields = last['field']-first['field']
    assert pause['active'] == 0 and pause['entries'] == pause['exits'] == 1
    assert fields == pause['fields'] and fields >= 40
    seen = resumed = 0
    for row in rows:
        if row['off'] != 0xf118:
            continue
        private = row['PDPLAP_EVENT']
        if not private[0]:
            continue
        session = row['PDSESSION_EVENT']
        clock = row['PDPLAYER_CLOCK']
        elapsed = max(0, session[14]-(0 if session[13] else 4)-private[1])
        assert clock[9] == private[8] == elapsed
        assert clock[1] == private[2]
        assert private[7] == 0
        seen += 1
        resumed += row['field'] >= last['field']
    assert seen >= 30 and resumed >= 10, 'Insufficient active and resumed HUD coverage'
    print(f'{root.name}: {fields} paused PAL fields; private/native lap starts and logical clocks unchanged')
    print(f'  {seen} exact logical HUD outputs, {resumed} after resume; no external-reset fallback')
    print('  This pause route does not cover rescue or natural player lap completion')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('capture', type=Path)
    check(p.parse_args().capture)
