#!/usr/bin/env python3
"""Check complete repair geometry, elapsed deadlines and native A500 cadence.

Timing gates include a conservative 40-ms two-capture endpoint allowance, and
require both the existing 90-ms and 10% limits. No tolerance is fitted to a run.
"""
import argparse
from pathlib import Path
from timing_repair_loops import read


def span(stage):
    return 20*(stage[-1]['v'][10]-stage[0]['entry_vbl'])


def pause(stages):
    return 20*(stages[1][1]['body_entry_vbl']-stages[1][0]['v'][10])


def check(reference, capture, native_steps=False, continuous_stages=False):
    refs, ref_tail = read(reference)
    actual, tail = read(capture)
    assert len(refs) == len(actual) == 4 and ref_tail == tail == 0, 'Need all four complete item/direction cases'
    cases = set()
    sequence = []
    failures = []
    for ref, run in zip(refs, actual):
        rs, ss = ref['stages'], run['stages']
        key = (rs[0][0]['v'][8], rs[0][0]['v'][0] & 65535)
        cases.add(key)
        for index, (rstage, stage) in enumerate(zip(rs, ss)):
            native_body = span(rstage)-(pause(rs) if index else 0)
            assert native_body % 5 == 0
            expected_units = native_body//5
            epochs = []
            for r, row in zip(rstage, stage):
                a, b = r['v'], row['v']
                assert [v & 65535 for v in a[:4]]+a[4:9] == [v & 65535 for v in b[:4]]+b[4:9], 'Repair word geometry changed'
                p = row['pace']
                counter = b[3] & 65535
                assert p is not None and p[0] == int(counter != 0) and p[1] == index
                assert p[3] == expected_units, 'Period differs from independent native body measurement'
                if native_steps:
                    elapsed = 20*(r['v'][10]-rstage[0]['entry_vbl'])
                    if index and counter < 32:
                        elapsed -= pause(rs)
                    assert elapsed % 5 == 0
                    offset = elapsed//5
                else:
                    offset = ((33-counter)*expected_units)//33
                assert p[4] == p[2]+offset, 'Deadline differs from the selected independent native reference'
                assert p[5] >= p[4] and p[9] == p[5]-p[4] and p[10] >= p[9]
                sequence.append((p[6], p[7]))
                epochs.append(p[2])
            if index == 0:
                assert len(set(epochs)) == 1
            else:
                assert len(set(epochs[1:])) == 1
                excluded = stage[1]['pace'][8]-stage[0]['pace'][8]
                assert epochs[1]-epochs[0] == excluded, 'Pause did not shift the epoch exactly'
                assert excluded*5 >= pause(rs), 'Sound/display pause shorter than native A500 minimum'
                assert abs(excluded*5-pause(ss)) <= 20, 'Excluded interval differs from observed sound/display pause'
            error = abs(span(stage)-span(rstage))+40
            passed = error <= 90 and error <= span(rstage)*0.1
            print(f'{key}, stage {index+1}: native {span(rstage)} ms, paced {span(stage)} ms, conservative error {error} ms')
            if not passed:
                failures.append((key, index, error))
        if continuous_stages:
            assert ss[1][0]['pace'][2] == ss[0][-1]['pace'][4], 'Stage transition discarded accumulated lateness'
        original = 20*(ref['returned_vbl']-rs[0][0]['entry_vbl'])
        observed = 20*(run['returned_vbl']-ss[0][0]['entry_vbl'])
        error = abs(observed-original)+40
        print(f'  complete invocation: native {original} ms, paced {observed} ms, conservative error {error} ms')
        if error > 90 or error > original*0.1:
            failures.append((key, 'whole', error))
    assert cases == {(0, 0), (0, 1), (1, 0), (1, 1)}
    first_stage, first_step = sequence[0]
    assert sequence == [(first_stage+i//33, first_step+i) for i in range(264)], 'Paced steps or stage ownership lost/duplicated'
    assert not failures, f'Repair cadence calibration failed: {failures}'
    print('All 264 word-geometry/deadline samples and four complete cadence cases pass')
    print('Other repair branches, nonlocal exits and full pit duration remain outside this gate')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference', type=Path)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--native-steps', action='store_true',
                        help='Require native per-step cumulative deadlines instead of the earlier uniform prototype')
    parser.add_argument('--continuous-stages', action='store_true',
                        help='Require stage two to inherit stage one’s intended completion time')
    args = parser.parse_args()
    check(args.reference, args.capture, args.native_steps, args.continuous_stages)
