#!/usr/bin/env python3
"""Verify an initial pit retune drains old-speed updates before native mutation.

Read-only PDRETUNE, PDPOPP, PDMREG and complete opponent records are required.
This ordinary-launch check does not certify deferred race-result delivery.
"""
import argparse
from pathlib import Path
import struct


def events(root):
    result = []
    current = None
    for line in (root / 'swaps-gdb.txt').read_text().splitlines():
        v = line.split()
        if not v:
            continue
        if v[0] == 'PDTIME_EVENT':
            current = dict(field=int(v[1]), off=int(v[2], 16), arrays=[])
            result.append(current)
        elif v[0] in ('PDRETUNE_EVENT', 'PDPOPP_EVENT', 'PDMREG_EVENT',
                       'PDSESSION_EVENT', 'PDPIT_EVENT', 'PDINITIAL_EVENT'):
            assert current is not None and (current['field'], current['off']) == (int(v[1]), int(v[2], 16))
            current[v[0]] = list(map(int, v[3:]))
        elif v[0] == 'PDOPP_ARRAY':
            assert current is not None and (current['field'], current['off']) == (int(v[1]), int(v[2], 16))
            assert int(v[3]) == len(current['arrays'])
            record = bytes.fromhex(v[4])
            assert len(record) == 190
            current['arrays'].append(record)
    return result


def speeds(event):
    assert len(event['arrays']) == 4
    return [struct.unpack_from('>H', r, 0x16)[0] for r in event['arrays']]


def check(root):
    rows = events(root)
    before, native, after = [next(e for e in rows if e['off'] == off) for off in (0x14090, 0xe8d4, 0xe976)]
    b, n, a = [e['PDPOPP_EVENT'] for e in (before, native, after)]
    br, nr, ar = [e['PDRETUNE_EVENT'] for e in (before, native, after)]
    assert br[0:2] == nr[0:2] == ar[0:2] == [0, 0]
    assert nr[4] == ar[4] == br[4] + 1 and ar[5] == 0
    cutoff = nr[2]
    assert n[4] == cutoff and n[6] < 18 and n[1] == n[2] == n[22] == 0
    available = b[6] + cutoff - b[4]
    served = n[8] - b[8]
    assert served > 0 and served * 18 + n[6] == available
    assert n[17:19] == b[17:19], 'Outer random state/counter changed across catch-up'
    # All caller registers, original stack depth and condition codes survive.
    x, y = before['PDMREG_EVENT'], native['PDMREG_EVENT']
    assert x[:15] == y[:15], 'Catch-up clobbered a caller register'
    assert y[15] == x[15] - 4, 'Native retune needs exactly one BSR return slot'
    assert len(nr) >= 8, 'Guest CCR diagnostics required; debugger SR may be stale'
    assert nr[6] & 31 == nr[7] & 31, 'Catch-up changed guest condition codes'
    old = speeds(before)
    assert speeds(native) == old
    complete = []
    for e in rows:
        t, r = e.get('PDPOPP_EVENT'), e.get('PDRETUNE_EVENT')
        if not t or not r:
            continue
        if r[0] and t[1]:
            assert r[2] == cutoff and t[5] <= cutoff and t[24] == 0
            assert t[15] == 18
            if e['off'] == 0xd7f0:
                assert speeds(e) == old, 'Historical movement used new speeds'
                complete.append(t[8] + 1)
        if e['off'] == 0xd56c and e['field'] >= after['field'] and not r[0]:
            assert t[5] > cutoff, 'Post-retune movement has a historical deadline'
    assert complete == list(range(b[8] + 1, n[8] + 1))
    # Native retune alone may alter only the speed words in these records.
    for old_record, new_record in zip(native['arrays'], after['arrays']):
        assert old_record[:0x16] == new_record[:0x16] and old_record[0x18:] == new_record[0x18:]
    seed = n[17]
    bases = []
    for speed in speeds(after):
        seed = (seed * 0x7ab7 + 1) & 65535
        bases.append(speed - (seed >> 9) + 48)
    assert len(set(bases)) == 1 and seed == a[17], 'Native speed/random arithmetic changed'
    print(f'{root.name}: {served} old-speed updates ({served * 90} ms) before retune; '
          f'{n[6] * 5} ms residual; cutoff {(cutoff - n[13] + 18) * 5} ms from opponent timeline start')
    print(f'  Speeds {old} -> {speeds(after)}; complete records, caller registers/CCR/stack and native RNG verified')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('captures', nargs='+', type=Path)
    for capture in p.parse_args().captures:
        check(capture)
