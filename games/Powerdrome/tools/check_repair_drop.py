#!/usr/bin/env python3
"""Check logical repair-step and presentation-drop accounting in a field capture.

This does not prove displayed bitmap equivalence, guest register/CCR contracts,
input histories, opponent continuity or native nonlocal result exits.
"""
import argparse
from pathlib import Path
from timing_repair_loops import read


def check(root, allow_no_drops=False):
    cases, tail = read(root)
    assert len(cases) == 4 and tail == 0
    posts = []
    for line in (root/'swaps-gdb.txt').read_text().splitlines():
        p = line.split()
        if p and p[0] == 'PDRDROP_EVENT' and int(p[2], 16) in (0x14962, 0x14aa6):
            values = list(map(int, p[3:]))
            assert len(values) == 6
            posts.append((int(p[1]), int(p[2], 16), values))
    rows = [(stage_index, row) for case in cases
            for stage_index, stage in enumerate(case['stages']) for row in stage]
    assert len(rows) == len(posts) == 264
    previous = [0]*6
    per_stage = [0]*8
    for n, ((stage, row), (field, off, v)) in enumerate(zip(rows, posts)):
        assert field == row['field'] and off == (0x14962, 0x14aa6)[stage]
        active, dropped, bitmaps, services, rendered, late = v
        assert active == 0, 'Suppression escaped into the next step/native continuation'
        delta = dropped-previous[1]
        assert delta in (0, 1)
        assert rendered-previous[4] == 1-delta, 'Logical step lost or double-counted'
        assert dropped+rendered == n+1
        assert services == dropped, 'Suppressed drawing did not rejoin native service'
        assert bitmaps == 9*dropped, 'Unexpected suppressed caller set in this route'
        counter = row['v'][3] & 65535
        if delta:
            assert counter not in (32, 0), 'Stage endpoint was not rendered'
            assert not (stage == 1 and counter == 31), 'Post-repair event frame was dropped'
            assert 4 <= late < 0x80000000, 'Drop was not justified by at least one PAL field of lateness'
            per_stage[n//33] += 1
        previous = v
    assert previous[1] > 0 or allow_no_drops, 'No late drawing was suppressed; this is not drop-path coverage'
    if previous[1] == 0:
        print('No dropped presentations: normal-path accounting only, not drop-path coverage')
    print(f'{root.name}: 264 logical steps = {previous[4]} rendered + {previous[1]} dropped')
    print(f'{previous[2]} bitmap calls suppressed; {previous[3]} native service continuations; suppression cleared after every step')
    print('Drops per stage: ' + ', '.join(map(str, per_stage)))
    print('Cadence, displayed buffers and broader service/exit contracts require separate checks')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--allow-no-drops', action='store_true',
                        help='Check normal-path accounting on a CPU with no overdue drawing')
    args = parser.parse_args()
    check(args.capture, args.allow_no_drops)
