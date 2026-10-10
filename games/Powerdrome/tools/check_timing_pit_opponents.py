#!/usr/bin/env python3
"""Check the modal opponent time ledger, native clock views and return drain.

Requires PDPOPP_EVENT and PDPIT_EVENT at pit entry/return, E3BC/E3C4 and
D56C. Clock-result probes are optional and reported individually. This does
not certify complete opponent arrays, native A500 calibration or nonlocal exits.
"""
import argparse
from collections import Counter
from pathlib import Path


def check(root):
    pit = entry = before = None
    visits = samples = restored = 0
    clocks = Counter()
    for line in (root / 'swaps-gdb.txt').read_text().splitlines():
        v = line.split()
        if not v:
            continue
        if v[0] == 'PDPIT_EVENT':
            pit = (int(v[1]), int(v[2], 16), list(map(int, v[3:])))
        if v[0] != 'PDPOPP_EVENT':
            continue
        field, off = int(v[1]), int(v[2], 16)
        t = list(map(int, v[3:]))
        assert len(t) == 21 and pit[:2] == (field, off)
        p = pit[2]
        if off == 0x103a2:
            assert entry is None and p[0] == 1
            assert t[0] == 1 and t[1] == t[2] == t[6] == 0
            assert t[4] == p[5] and t[5] == p[5] + 18
            entry = t.copy()
        if entry is None:
            continue
        assigned, completed = t[7] - entry[7], t[8] - entry[8]
        assert 0 <= completed <= assigned
        assert t[2] == assigned - completed, 'Assigned updates lost or repeated'
        assert t[4] - entry[4] == assigned * 18 + t[6], 'Time ledger does not balance'
        assert t[5] == entry[5] + completed * 18, 'Opponent deadline skipped/repeated'
        assert t[3] == (entry[3] + completed) & 65535, 'Counter phase differs from updates'
        if off == 0xe3bc:
            assert not t[1] and before is None
            before = t.copy()
        if off == 0xe3c4 and before is not None:
            assert t[1] == t[2] == 0
            assert t[17:19] == before[17:19], 'Outer RNG/counter not restored'
            before = None
            restored += 1
        if t[1]:
            assert t[2] > 0 and t[15] == 18 and t[18] == t[3]
            assert t[9] == (t[5] + t[14]) & 0xffffffff, 'Logical native epoch is incorrect'
            if off == 0xd56c:
                samples += 1
            register = {0xd4bc: 20, 0xd504: 19, 0xd7fe: 20,
                        0xd83c: 20, 0xd86c: 20}.get(off)
            if register is not None:
                assert t[register] == t[9], f'Clock result differs at {off:#x}'
                clocks[off] += 1
        if off == 0xce28:
            elapsed = p[6] - p[5]
            assert t[1] == t[2] == 0 and before is None
            assert t[4] == p[6], 'Final pit time was not allocated'
            assert completed == elapsed // 18, 'Missing opponent updates at pit return'
            assert t[6] == elapsed % 18 and t[5] > p[6]
            print(f'{root.name}: visit {visits + 1}: {completed} updates over '
                  f'{elapsed * 5} ms; {t[6] * 5} ms retained; complete return drain')
            visits += 1
            entry = None
    assert visits and entry is None and samples and restored
    assert clocks, 'No logical timer result was observed'
    print(f'  {samples} scheduled opponent movement samples; {restored} outer-state restores; '
          f'clock-result probes ' + ', '.join(f'{k:#x}={v}' for k, v in sorted(clocks.items())))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('captures', type=Path, nargs='+')
    for capture in parser.parse_args().captures:
        check(capture)
