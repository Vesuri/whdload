#!/usr/bin/env python3
"""Require repeated native mouse-look transitions and equal logical world states."""
import argparse
import json
import re
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('normal', type=Path)
p.add_argument('delayed', type=Path)
a = p.parse_args()
runs = []
for root in (a.normal, a.delayed):
    metadata = json.loads((root/'ticks/metadata.json').read_text())
    assert metadata.get('complete') and metadata.get('sample_unit') == 'completed tick'
    samples = json.loads((root/'ticks/samples.json').read_text())
    listing = (root/'slave.lst').read_text(errors='replace')
    slave = int(re.search(r'^slave (0x[0-9a-f]+)', (root/'anchor.txt').read_text(), re.M)[1], 16)
    base = 0xc00000 if slave >= 0xc00000 else 0x200000
    delay_at = slave+int(re.search(r'^_timing_study_delays\s+00:([0-9A-F]{8})\s*$', listing, re.M)[1], 16)-base
    memory = (root/'ticks/final-code.bin').read_bytes()
    delay_count = int.from_bytes(memory[delay_at:delay_at+4], 'big')
    assert (delay_count == 0) if root == a.normal else (delay_count > 0), 'drawing perturbation was not exercised'
    assert len(samples) >= 121
    transitions = []
    for i, (before, after) in enumerate(zip(samples, samples[1:]), 1):
        assert after['simulation']['consumed']-before['simulation']['consumed'] == 2
        if before['mouse_look'] != after['mouse_look']:
            transitions.append((i, before['mouse_look'], after['mouse_look']))
            assert after['player']['heading'] == before['player']['heading'], 'mode transition replayed old motion'
        if not after['mouse_look']:
            assert after['player']['heading'] == before['player']['heading'], 'relative motion leaked into pointer mode'
    assert len(transitions) == 4, transitions
    assert [t[2] for t in transitions] == [1, 0, 1, 0], transitions
    assert all(s['simulation']['input_recoveries'] == 0 for s in samples)
    assert all(s['simulation']['suspended'] == 0 for s in samples)
    assert len({s['player']['heading'] for s in samples}) > 10, 'motion was not exercised'
    assert any(b['mouse_look'] and b['player']['heading'] > a['player']['heading']
               for a, b in zip(samples, samples[1:])), 'negative heading wrap was not exercised'
    # Drawing blocks simulation temporarily, so compare logical ticks and report
    # wall-clock debt separately rather than claiming instantaneous equivalence.
    ignored = {'field', 'game_clock', 'simulation'}
    logical = [{k:v for k,v in s.items() if k not in ignored} for s in samples]
    debt = [s['simulation']['fields']-s['simulation']['consumed'] for s in samples]
    print(root.name, 'transitions', transitions, 'debt range', min(debt), max(debt), 'drawing delays', delay_count)
    runs.append(logical)
assert runs[0] == runs[1], 'drawing delay changed logical world/input progression'
print('All decoded logical world states match through four native mode transitions')
