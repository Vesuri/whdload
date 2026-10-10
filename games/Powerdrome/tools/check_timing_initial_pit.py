#!/usr/bin/env python3
"""Audit the initial pit's opponent timeline and first player/world entry.

Requires TIMING_EARLY capture from BC3A with native pit, opponent and first-world
probes. Establishes clock ownership and conservation, not animation calibration
or complete cross-CPU trajectory equivalence.
"""
import argparse
from collections import defaultdict
import json
from pathlib import Path


def check(root):
    cfg = json.loads((root / 'configuration.json').read_text())
    assert cfg['TIMING_EARLY'] == '1' and int(cfg['ANCHOR'], 0) == 0xbc3a
    session = pit = initial = None
    entered = returned = first_world = None
    before = flight_before = None
    restores = world_restores = movements = modal = 0
    phases = defaultdict(list)
    origin = phase = None
    capped_batches = max_debt = 0
    last_world = None
    for line in (root / 'swaps-gdb.txt').read_text().splitlines():
        v = line.split()
        if not v:
            continue
        if v[0] in ('PDSESSION_EVENT', 'PDPIT_EVENT', 'PDINITIAL_EVENT'):
            entry = (int(v[1]), int(v[2], 16), list(map(int, v[3:])))
            if v[0] == 'PDSESSION_EVENT': session = entry
            elif v[0] == 'PDPIT_EVENT': pit = entry
            else: initial = entry
        if v[0] != 'PDPOPP_EVENT':
            continue
        field, off = int(v[1]), int(v[2], 16)
        t = list(map(int, v[3:]))
        assert len(t) == 27
        assert session[:2] == pit[:2] == initial[:2] == (field, off)
        s, p, q = session[2], pit[2], initial[2]
        if off in (0x103a2, 0x13cde, 0x14764, 0x1020e, 0x10322, 0xbc44, 0xca3e):
            phases[off].append(field)
        if off == 0x103a2:
            assert entered is None and q[0] == p[0] == 1 and p[1] == p[14] == 0
            assert t[0] == 1 and t[1] == t[2] == t[7] == t[8] == 0
            assert t[4] == p[5] and t[5] == t[13] == p[5] + 18
            assert t[3] == t[23] == (t[18] + 1) & 65535
            assert s[0] == s[8] == s[13] == s[18] == 0
            entered = (field, p.copy(), t.copy())
            origin, phase = t[13], t[23]
        if entered is None:
            continue
        assert t[0] == 1 and (t[13], t[23]) == (origin, phase), 'Initial-pit timeline reset'
        assert t[7] - t[8] == t[2] and t[8] >= 0
        assert t[4] - origin + 18 == t[7] * 18 + t[6], 'Opponent time lost or duplicated'
        assert t[5] == origin + t[8] * 18
        assert t[3] == (phase + t[8]) & 65535
        if returned is None:
            assert s[0] == s[8] == s[13] == s[18] == s[16] == s[17] == 0, 'Player work leaked into initial pit'
            assert p[16:19] == entered[1][16:19], 'Player heat/control phase ran before flight'
        if off == 0xe3bc and p[0]:
            assert before is None and t[1] == 0
            before = t.copy()
        if off == 0xe3c4 and before is not None:
            assert t[1] == t[2] == t[22] == 0
            assert t[17:19] == before[17:19], 'Pit counter/RNG not restored'
            restores += 1
            before = None
        if t[1]:
            assert t[2] > 0 and t[15] == 18 and t[18] == t[3]
            assert t[22] == (not t[24])
            assert t[9] == (t[5] + t[14]) & 0xffffffff
            if off == 0xd56c:
                movements += 1
                modal += not t[24]
        if off == 0xbc44:
            assert returned is None and before is None
            assert p[0] == p[1] == p[14] == 0 and q[0] == 1
            assert t[1] == t[2] == t[21] == t[22] == 0 and t[19] == 0
            assert t[4] <= p[6] and p[6] - p[5] == p[7] > 0
            returned = (field, p.copy(), t.copy())
        if off == 0xced8 and t[24]:
            assert returned and q[0] == 0 and s[8] == 1
            assert flight_before is None
            flight_before = t.copy()
        if off == 0xd3de and flight_before is not None and t[8] == flight_before[8]:
            assert t[17] == flight_before[17], 'First flight replaced the live world stream'
        if off == 0xcedc and flight_before is not None:
            assert t[1] == t[2] == t[22] == 0
            assert t[18] == flight_before[18]
            # The production dispatcher caps each allocation at 32 updates.
            # Prove its exact service and retained debt, including a slow CPU
            # carrying a long departure tail across several world steps.
            available = flight_before[6] + t[25] - flight_before[4]
            assert available >= 0 and flight_before[2] == 0
            expected = min(32, available // 18)
            assert t[4] == t[25]
            assert t[8] - flight_before[8] == expected
            assert t[7] - flight_before[7] == expected
            assert t[6] == available - expected * 18
            capped_batches += available // 18 > 32
            max_debt = max(max_debt, t[6])
            last_world = t.copy()
            if first_world is None:
                first_world = (field, t.copy())
                previous = returned[2]
                old_debt = returned[1][6] - previous[4] + previous[6]
                after = t[4] - returned[1][6]
                served = (t[8] - previous[8]) * 18
                assert old_debt + after == served + t[6]
                print(f'{root.name}: initial-pit tail {old_debt * 5} ms + '
                      f'post-return {after * 5} ms = {served * 5} ms served + {t[6] * 5} ms retained')
            world_restores += 1
            flight_before = None
    assert entered and returned and first_world and restores and world_restores >= 50 and modal
    assert last_world[6] < 18, "Capture ended before departure backlog drained"
    print(f"  Capped batches {capped_batches}; maximum retained debt {max_debt * 5} ms; final residual {last_world[6] * 5} ms")
    assert len(phases[0x14764]) == 17 and len(phases[0x10322]) == 9
    print(f'  Pit {((returned[1][6] - entered[1][5]) * 5)} ms; '
          f'{modal}/{movements} opponent movement samples before/total; '
          f'{restores} pit and {world_restores} flight ownership restores')
    print('  Phase fields: ' + '; '.join(f'{off:#x}={values[0]}..{values[-1]} ({len(values)})'
                                         for off, values in phases.items()))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('captures', nargs='+', type=Path)
    for capture in parser.parse_args().captures:
        check(capture)
