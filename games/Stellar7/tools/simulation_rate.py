#!/usr/bin/env python3
"""Measure update/presentation throughput between captured SIM60 boundaries.

Uses observed display fields, not the scheduler's last clock poll. Refuses
session changes and modal-clock rebasing; those need separate active-time analysis.
Checkpoint averages do not establish maximum presentation latency.
"""
import argparse
import json
from sim60_state import read


def interval(before, after):
    a, b = read(before), read(after)
    for key in ('session', 'field_hz', 'substeps', 'clock_origin'):
        if a.get(key) != b.get(key):
            raise ValueError(f'{key} changed; interval crosses a reset or clock rebase')
    if not a['running'] or not b['running'] or a.get('modal_depth', 0) or b.get('modal_depth', 0):
        raise ValueError('both boundaries must be active gameplay outside modals')
    fields = (b['observed_field']-a['observed_field']) & 0xffffffff
    ticks = (b['ticks']-a['ticks']) & 0xffffffff
    renders = (b['renders']-a['renders']) & 0xffffffff
    if not 0 < fields < 0x80000000 or not 0 < ticks < 0x80000000 or renders >= 0x80000000:
        raise ValueError('boundaries must advance in time within the same session')
    seconds = fields / a['field_hz']
    return dict(ticks=ticks, fields=fields, seconds=seconds, updates_hz=ticks/seconds,
                presentations=renders, presentation_hz=renders/seconds,
                pending_before=a['pending_ticks'], pending_after=b['pending_ticks'],
                pending_growth=b['pending_ticks']-a['pending_ticks'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('captures', nargs='+', help='successive checkpoints in time order')
    args = parser.parse_args()
    if len(args.captures) < 2:
        parser.error('provide at least two checkpoints')
    for before, after in zip(args.captures, args.captures[1:]):
        print(f'{before} -> {after}', json.dumps(interval(before, after), sort_keys=True))
