#!/usr/bin/env python3
"""Report the two 33-step native repair stages from read-only PDREPAIR probes.

Post-draw intervals include any intervening sound/display wait. They are not FPS
measurements, and each stage span excludes its first represented movement step.
"""
import argparse
from collections import Counter
import json
import struct
from pathlib import Path


def read(root):
    assert (root/'final-code.bin').is_file(), 'Need a terminal capture'
    config = json.loads((root/'configuration.json').read_text())
    assert int(config['ANCHOR'], 0) == 0x148d0
    game = int((root/'game-base.txt').read_text(), 0)
    chip = (root/'chip.bin').read_bytes()
    anchor_vbl = struct.unpack_from('>I', chip, game+0x48fe)[0]
    completed = []
    stages = [[], []]
    # The first entry breakpoint is the capture anchor; its initial timestamp
    # comes from the stopped memory snapshot, before the debugger continues.
    pending = [(32, anchor_vbl), None]
    for line in (root/'swaps-gdb.txt').read_text().splitlines():
        v = line.split()
        if not v or v[0] != 'PDREPAIR_EVENT':
            continue
        field, off = int(v[1]), int(v[2], 16)
        values = list(map(int, v[3:]))
        assert len(values) == 14
        if off in (0x148d0, 0x14a18):
            stage = int(off == 0x14a18)
            assert pending[stage] is None, 'Unpaired repair entry'
            pending[stage] = (values[3] & 65535, values[10])
        if off in (0x14962, 0x14aa6):
            stage = int(off == 0x14aa6)
            assert pending[stage] is not None and pending[stage][0] == values[3] & 65535
            stages[stage].append(dict(field=field, v=values, entry_vbl=pending[stage][1]))
            pending[stage] = None
        elif off == 0x14ac4:
            for stage in stages:
                assert [row['v'][3] & 65535 for row in stage] == list(range(32, -1, -1)), 'Incomplete or reordered repair stage'
                assert all(row['v'][0] == stage[0]['v'][0] and row['v'][8] == stage[0]['v'][8] for row in stage)
                for x, y in zip(stage, stage[1:]):
                    assert y['v'][10]-x['v'][10] == y['field']-x['field'], 'Field observations disagree'
            assert stages[0][0]['v'][0] == stages[1][0]['v'][0]
            assert stages[0][0]['v'][8] == stages[1][0]['v'][8]
            assert pending == [None, None]
            completed.append(dict(stages=stages, returned_vbl=values[10]))
            stages = [[], []]
    assert completed, 'No complete two-stage repair invocation'
    return completed, sum(map(len, stages))


def report(root):
    completed, trailing = read(root)
    result = []
    for invocation in completed:
        stages = invocation['stages']
        entry = dict(direction=stages[0][0]['v'][0], item=stages[0][0]['v'][8], stages=[])
        for stage in stages:
            intervals = [20*(y['v'][10]-x['v'][10]) for x, y in zip(stage, stage[1:])]
            entry['stages'].append(dict(post_draw_samples=len(stage), first_to_last_post_ms=sum(intervals),
                                        first_entry_to_last_post_ms=20*(stage[-1]['v'][10]-stage[0]['entry_vbl']),
                                        body_histogram_ms=dict(sorted(Counter(20*(r['v'][10]-r['entry_vbl']) for r in stage).items())),
                                        intervals_ms=intervals, histogram_ms=dict(sorted(Counter(intervals).items()))))
        entry['between_stages_ms'] = 20*(stages[1][0]['v'][10]-stages[0][-1]['v'][10])
        entry['second_stage_wait_before_counter31_ms'] = 20*(stages[1][1]['entry_vbl']-stages[1][0]['v'][10])
        entry['last_post_to_return_ms'] = 20*(invocation['returned_vbl']-stages[1][-1]['v'][10])
        entry['complete_invocation_ms'] = 20*(invocation['returned_vbl']-stages[0][0]['entry_vbl'])
        result.append(entry)
    print(json.dumps(dict(capture=root.name, complete_invocations=result, trailing_post_draw_samples=trailing), indent=2))
    return completed


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('captures', type=Path, nargs='+')
    args = parser.parse_args()
    for root in args.captures:
        report(root)
