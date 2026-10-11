#!/usr/bin/env python3
"""Measure native presentation rates over exact gameplay-counter windows.

Requires fixed_window.py --native-events. Every native presentation anchor is
observed; noncontiguous counters, resets and missing boundaries are rejected.
The native scene checker proves CUSTOM1 is off and setup patches are removed.
"""
import argparse
import json
from pathlib import Path
import struct
import re

import native_scene_state


def interval(events, start, end, field_hz):
    if field_hz not in (50, 60) or not 0 <= start < end < 65536:
        raise ValueError('Invalid native interval or display frequency')
    if not events or [e['frame'] for e in events] != list(range(events[0]['frame'],events[-1]['frame']+1)):
        raise ValueError('Noncontiguous native presentation log')
    selected = [event for event in events if start <= event['frame'] <= end]
    if [event['frame'] for event in selected] != list(range(start, end+1)):
        raise ValueError('Missing, repeated or reset native presentation counter')
    gaps = [(b['field']-a['field']) & 0xffffffff for a,b in zip(selected,selected[1:])]
    if any(gap >= 0x80000000 for gap in gaps):
        raise ValueError('Native field clock moved backwards')
    fields = (selected[-1]['field']-selected[0]['field']) & 0xffffffff
    if not fields or fields != sum(gaps):
        raise ValueError('Empty or ambiguous field-clock interval')
    return dict(start_frame=start, end_frame=end, presentations=end-start,
                fields=fields, seconds=fields/field_hz,
                presentations_hz=(end-start)*field_hz/fields,
                largest_presentation_gap_fields=max(gaps))


def inspect(folder, listing, scene, windows):
    folder = Path(folder)
    assert (folder/'slave.slave').read_bytes() == Path(listing).with_suffix('.slave').read_bytes()
    proof = native_scene_state.inspect(folder, listing, scene)
    capture = json.loads((folder/'native-events.json').read_text())
    meta = json.loads((folder/'metadata.json').read_text())
    assert capture['anchor_offset'] == '0x2c16'
    assert capture['field_hz'] == meta['field_hz'] == meta['observed_exec_hz']
    events = capture['events']
    raw = []
    for log in sorted(folder.glob('native-events-*.txt'), key=lambda p:int(p.stem.rsplit('-',1)[1])):
        raw.extend(dict(frame=int(frame),field=int(field)) for frame,field in
                   re.findall(r'^S7NATIVE (\d+) (\d+)$',log.read_text(),re.M))
    assert raw == events[1:], 'Native event report differs from debugger observations'
    interval(events, events[0]['frame'], events[-1]['frame'], capture['field_hz'])
    for snapshot in [folder, *sorted((folder/'checkpoints').iterdir())]:
        state = (snapshot/'state.bin').read_bytes()
        frame = struct.unpack_from('>H',state,0x1e96)[0]
        field = struct.unpack_from('>I',state,0x24a8)[0]
        assert dict(frame=frame,field=field) in events
        assert struct.unpack_from('>H',state,0x46a0)[0] == proof['level']
        assert state[0x1e53] and not struct.unpack_from('>H',state,0x1e90)[0]
    return dict(native_code=proof, event_count=len(events),
                intervals=[interval(events,a,b,capture['field_hz']) for a,b in windows],
                scope='Every native presentation anchor observed; exact counter windows. Native game pace is variable. Field-resolution endpoint quantization remains.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--listing', type=Path, required=True)
    parser.add_argument('--scene', choices=('type10','boss'), required=True)
    parser.add_argument('--window', type=int, nargs=2, action='append', required=True,
                        metavar=('START_FRAME','END_FRAME'))
    args = parser.parse_args()
    print(json.dumps(inspect(args.capture,args.listing,args.scene,args.window),indent=2))
