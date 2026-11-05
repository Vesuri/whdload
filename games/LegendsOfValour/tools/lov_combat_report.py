#!/usr/bin/env python3
"""Decode VERIFY native combat iterations; reports observations, not acceptance."""
import argparse
import json
import re
import struct
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('capture', type=Path)
p.add_argument('--keyboard-exit', action='store_true', help='require native console space to end combat')
p.add_argument('--manual', action='store_true', help='require field-timed manual presses and native attack progression')
p.add_argument('--scheduled', action='store_true', help='require four-field combat ticks and historical pointer input')
p.add_argument('--base', type=lambda s: int(s, 0), default=0x200000)
a = p.parse_args()
if (a.manual or a.keyboard_exit) and not a.scheduled:
    p.error('--manual and --keyboard-exit require --scheduled')
metadata = json.loads((a.capture/'ticks/metadata.json').read_text())
assert metadata.get('complete'), 'incomplete capture'
memory = (a.capture/'ticks/final-code.bin').read_bytes()
listing = (a.capture/'slave.lst').read_text(errors='replace')
slave = int(re.search(r'^slave (0x[0-9a-f]+)', (a.capture/'anchor.txt').read_text(), re.M)[1], 16)
def offset(name):
    return slave + int(re.search(r'^'+name+r'\s+00:([0-9A-F]{8})\s*$', listing, re.M)[1], 16)-a.base
def value(name, size=4):
    at = offset(name)
    assert 0 <= at <= len(memory)-size
    return int.from_bytes(memory[at:at+size], 'big')
assert value('_timing_combat_requested', 2) == value('_timing_combat_returned', 2) == 1
count = value('_timing_combat_steps')
assert 1 <= count <= 64, ('unexpected combat iteration count', count)
names = ('field', 'game_clock', 'simulation_fields', 'consumed',
         'attack_countdown', 'enemy_countdown', 'enemy_frame', 'enemy_health',
         'world_enabled', 'enemy_attack')
records = [dict(zip(names, struct.unpack_from('>7IHBB', memory,
           offset('_timing_combat_records')+32*i))) for i in range(count)]
scheduled = None
if a.scheduled:
    assert value('_sim_combat_active', 2) == 0, 'combat ownership not released'
    assert value('_sim_combat_recoveries') == 0, 'combat history lost'
    scheduled = [dict(zip(('field', 'deadline', 'input_field', 'x', 'y', 'buttons', 'padding'),
        struct.unpack_from('>IIIhhHH', memory, offset('_timing_combat_clock_records')+20*i)))
        for i in range(count)]
    for i, step in enumerate(scheduled):
        assert step['deadline']-step['field'] == 4
        assert step['field'] == step['input_field'], 'wrong historical sample'
        if i:
            assert step['field']-scheduled[i-1]['field'] == 4, 'combat step skipped or duplicated'
if a.manual:
    first = scheduled[0]['field']
    for step in scheduled:
        pressed = ((step['field']-first) & 31) == 8
        assert step['buttons'] == int(pressed), 'manual pulse changed or was missed'
        if pressed:
            assert (step['x'], step['y']) == (174, 150)
    assert any(r['attack_countdown'] > 0 for r in records), 'no native attack started'
    assert records[-1]['enemy_health'] < records[0]['enemy_health'], 'no damage resolved'
keyboard = None
if a.keyboard_exit:
    assert value('_timing_keys_error', 2) == value('_sim_keys_error', 2) == 0
    assert value('_timing_keys_sent') == 2 and value('_timing_keys_done', 2) == 1
    assert value('_sim_keys_reads') == 1, 'space not consumed exactly once'
    arrival, cutoff, byte, domain = struct.unpack_from('>IIHH', memory, offset('_sim_keys_readlog'))
    assert byte == 32 and domain == 2, 'not a historical combat space read'
    assert ((cutoff-arrival) & 0xffffffff) < 4, 'space consumed outside its first eligible combat step'
    assert cutoff == scheduled[-1]['deadline'], 'combat did not exit on the space read'
    assert count < 32, 'fixture fallback exit could have ended combat'
    assert value('_sim_keys_head', 2) == value('_sim_keys_tail', 2) == 1
    assert value('_sim_keys_live', 2) == value('_sim_keys_pending', 2) == 1
    samples = json.loads((a.capture/'ticks/samples.json').read_text())
    resumed = samples[1:]
    assert len(resumed) >= 20, 'insufficient resumed-world observations'
    assert all(s['simulation']['suspended'] == 0 and s['simulation']['input_recoveries'] == 0 for s in resumed)
    assert all(y['simulation']['consumed']-x['simulation']['consumed'] == 2 for x,y in zip(resumed,resumed[1:]))
    keyboard = dict(arrival=arrival, cutoff=cutoff, byte=byte, domain=domain)
print(json.dumps(dict(iterations=count, scheduled=scheduled, keyboard=keyboard,
    field_deltas=[(y['field']-x['field']) & 0xffffffff for x,y in zip(records,records[1:])],
    input_recoveries=value('_sim_input_recoveries'),
    rendering_delays=value('_timing_study_delays'), records=records), indent=2))
