#!/usr/bin/env python3
"""Validate native timing-enabled save/load checkpoint captures and resumed ticks.

The route stops at before-save, before-load, then the final tape anchor.
Checkpoint memory and anchor files must be retained by the capture driver.
"""
import argparse
import json
import re
from pathlib import Path
from lov_timing_state import decode, simulation_symbols, simulation_state

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('capture', type=Path)
parser.add_argument('--base', type=lambda value: int(value, 0), default=0x200000)
args = parser.parse_args()
root = args.capture
listing = (root/'slave.lst').read_text(errors='replace')
states = []
for memory_name, anchor_name in [('before-save.bin', 'before-save-anchor.txt'),
                                  ('before-load.bin', 'before-load-anchor.txt'),
                                  ('code.bin', 'anchor.txt')]:
    anchor = (root/anchor_name).read_text()
    slave = int(re.search(r'^slave (0x[0-9a-f]+)', anchor, re.M)[1], 16)
    def symbol(name):
        return slave + int(re.search(r'^'+name+r'\s+00:([0-9A-F]{8})\s*$', listing, re.M)[1], 16)
    stop = re.search(r'^Breakpoint \d+, (0x[0-9a-f]+)', anchor, re.M)
    assert stop and int(stop[1], 16) == symbol('_tape_anchor'), 'missing real checkpoint'
    memory = (root/memory_name).read_bytes()
    def read(address, size):
        offset = address-args.base
        assert 0 <= offset <= len(memory)-size
        return memory[offset:offset+size]
    h11 = int.from_bytes(read(symbol('_h11'), 4), 'big')
    h12 = int.from_bytes(read(symbol('_h12'), 4), 'big')
    state = decode(read, h11, h12)
    state['simulation'] = simulation_state(read, simulation_symbols(listing, slave))
    states.append(state)
headings = [state['player']['heading'] for state in states]
assert headings[0] == headings[2] and headings[0] != headings[1], headings
assert all(state['player']['quantized_heading'] == heading for state, heading in zip(states, headings))
for expected, state in enumerate(states, 1):
    sim = state['simulation']
    assert sim['suspended'] == 0 and sim['input_recoveries'] == 0, sim
    assert sim['options_entries'] == sim['options_returns'] == expected, sim
metadata = json.loads((root/'ticks/metadata.json').read_text())
assert metadata.get('complete') and metadata.get('sample_unit') == 'completed tick'
samples = json.loads((root/'ticks/samples.json').read_text())
assert len(samples) >= 41
for before, after in zip(samples, samples[1:]):
    a, b = before['simulation'], after['simulation']
    assert b['started_ticks'] == a['started_ticks']+1
    assert (b['consumed']-a['consumed']) & 0xffffffff == 2, 'lost active simulation time'
    assert b['suspended'] == b['input_recoveries'] == 0
    assert after['player']['heading'] == headings[2], 'stale turn after loading'
print(f'Save/load headings {headings}; exactly three balanced option visits; '
      f'{len(samples)-1} resumed ticks, no history recovery or stale turning')
print('Suppressed UI-consumed button samples:', states[-1]['simulation'].get('ui_suppressed'))
