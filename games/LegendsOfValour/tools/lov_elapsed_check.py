#!/usr/bin/env python3
"""Audit equal elapsed-field world captures and report synchronous-drawing lag.

This deliberately does not require instantaneous state equality: a VBL can
interrupt a world update. Pair with lov_modes_check.py's complete-tick equality.
Initial clock epochs are reported separately, never silently normalized.
The initial sample is the tape anchor late in VBL; later samples stop at
h12:0640a before the private/game clock increment, hence the one-field phase.
"""
import argparse
import json
import re
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('normal', type=Path)
p.add_argument('delayed', type=Path)
a = p.parse_args()
runs = []
report = []
for root in (a.normal, a.delayed):
    metadata = json.loads((root/'state/metadata.json').read_text())
    assert metadata.get('complete') and metadata.get('sample_unit') == 'VBL field'
    samples = json.loads((root/'state/samples.json').read_text())
    assert len(samples) == 241
    initial = samples[0]
    assert [s['field']-initial['field'] for s in samples] == list(range(241))
    for i, s in enumerate(samples):
        sim = s['simulation']
        assert s['simulation_enabled'] == 1 and sim['suspended'] == 0
        assert sim['input_recoveries'] == 0
        assert 0 <= sim['started_ticks']-sim['completed_ticks'] <= 1
        assert sim['fields']-initial['simulation']['fields'] == max(0, i-1), 'active field accounting changed'
    listing = (root/'slave.lst').read_text(errors='replace')
    slave = int(re.search(r'^slave (0x[0-9a-f]+)', (root/'anchor.txt').read_text(), re.M)[1], 16)
    base = 0xc00000 if slave >= 0xc00000 else 0x200000
    at = slave+int(re.search(r'^_timing_study_delays\s+00:([0-9A-F]{8})\s*$', listing, re.M)[1], 16)-base
    memory = (root/'code.bin').read_bytes()
    delays = int.from_bytes(memory[at:at+4], 'big')
    assert (delays == 0) if root == a.normal else (delays > 0)
    debt = [s['simulation']['fields']-s['simulation']['consumed'] for s in samples]
    report.append(dict(capture=root.name, elapsed_fields=240, drawing_delays=delays,
        completed_ticks=samples[-1]['simulation']['completed_ticks']-initial['simulation']['completed_ticks'],
        debt_range=[min(debt), max(debt)], final_heading=samples[-1]['player']['heading']))
    runs.append(samples)

def world(s):
    return {k:v for k,v in s.items() if k not in ('field', 'game_clock', 'simulation')}
assert world(runs[0][0]) == world(runs[1][0]), 'unequal initial non-clock world'
gaps = [x['simulation']['completed_ticks']-y['simulation']['completed_ticks'] for x,y in zip(*runs)]
actor_positions = lambda s: [(a['x'], a['y']) for a in s['actors']]
report.append(dict(completed_tick_gap_normal_minus_delayed=[min(gaps), max(gaps)],
    equal_field_samples_with_different_actor_positions=sum(actor_positions(x)!=actor_positions(y) for x,y in zip(*runs)),
    final_different_actor_positions=[x['index'] for x,y in zip(runs[0][-1]['actors'],runs[1][-1]['actors'])
                                    if (x['x'],x['y']) != (y['x'],y['y'])],
    initial_nonclock_world_equal=True,
    initial_game_clock_offset_delayed_minus_normal=runs[1][0]['game_clock']-runs[0][0]['game_clock'],
    initial_logical_clock_offset_delayed_minus_normal=runs[1][0]['simulation']['tick_clock']-runs[0][0]['simulation']['tick_clock'],
    interpretation='Equal elapsed-field samples expose drawing lag; complete-tick equality is a separate gate.'))
print(json.dumps(report, indent=2))
