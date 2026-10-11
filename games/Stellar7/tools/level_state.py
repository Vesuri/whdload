#!/usr/bin/env python3
"""Validate a native level-exit and resume capture (LEVEL_TEST)."""
import argparse
import json
import re
import struct
from pathlib import Path


def read(folder):
    folder = Path(folder)
    meta = {k: int(v, 0) for k, v in re.findall(
        r'^(code|base)=(\S+)', (folder/'anchor.txt').read_text(), re.M)}
    memory = (folder/'code.bin').read_bytes()
    code = meta['code'] - meta['base']
    assert memory[code+0x2af6:code+0x2af8] == bytes.fromhex('4ef9')
    entry = struct.unpack_from('>I', memory, code+0x2af8)[0] - meta['base']
    assert memory[entry+4:entry+8] == b'S760'
    assert struct.unpack_from('>H', memory, entry+50)[0] >= 28
    offset = struct.unpack_from('>H', memory, entry+130)[0]
    assert offset, 'LEVEL_TEST fixture is absent'
    at = entry+offset
    signature = memory[at:at+4]
    assert signature in (b'W760', b'W761', b'W762')
    names = ('stage', 'errors', 'trigger_tick', 'exit_tick', 'exit_field',
             'resume_field', 'resume_last', 'resume_credit', 'resume_ticks',
             'resume_renders', 'exit_level', 'resume_level', 'resume_phase',
             'resume_death', 'old_session', 'new_session', 'resume_energy',
             'exit_active')
    result = dict(zip(names, struct.unpack_from('>2H8I4H2I2H', memory, at+4)))
    if signature in (b'W761', b'W762'):
        count, target = struct.unpack_from('>2H', memory, at+60)
        assert 0 <= count <= 6 and 1 <= target <= 6
        result['completed_transitions'] = count
        result['target_level'] = target
        result['transitions'] = [dict(zip(names, struct.unpack_from(
            '>2H8I4H2I2H', memory, at+64+i*60+4))) for i in range(count)]
    result['passive_observation'] = signature == b'W762'
    result['captured_session'] = struct.unpack_from('>I', memory, entry+100)[0]
    result['captured_tick'] = struct.unpack_from('>I', memory, entry+16)[0]
    result['field_hz'] = struct.unpack_from('>H', memory, entry+28)[0]
    return result


def validate_transition(r, field_hz):
    assert r['stage'] == 3 and r['errors'] == 0, r
    assert r['exit_tick'] == r['trigger_tick']+1
    assert r['exit_active'] == 0
    assert r['exit_field'] <= r['resume_last'] <= r['resume_field']
    assert r['resume_credit'] == field_hz
    assert (r['resume_ticks'], r['resume_renders'], r['resume_phase'],
            r['resume_death']) == (0, 0, 0, 0)
    assert r['resume_level'] == r['exit_level']+1
    assert r['new_session'] == r['old_session']+1


def validate(r):
    validate_transition(r, r['field_hz'])
    assert r['new_session'] == r['captured_session']
    if 'transitions' in r:
        assert r['completed_transitions'] == r['target_level'] == r['resume_level']
        previous = None
        for index, transition in enumerate(r['transitions']):
            validate_transition(transition, r['field_hz'])
            assert transition['exit_level'] == index
            assert transition['old_session'] == index+1
            if previous is not None:
                assert previous['resume_field'] <= transition['exit_field']
            previous = transition
        assert previous is not None
        assert all(r[key] == value for key, value in previous.items())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('captures', nargs='+', help='capture after gameplay has resumed, e.g. checkpoints/600')
    args = parser.parse_args()
    for folder in args.captures:
        result = read(folder)
        print(folder, json.dumps(result, sort_keys=True))
        validate(result)
