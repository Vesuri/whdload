#!/usr/bin/env python3
"""Validate native death/retry, or decline/menu/new-game with --decline."""
import argparse
import json
import re
import struct
from pathlib import Path
from sim60_state import decode_version


def read(folder, decline=False, natural=False):
    folder = Path(folder)
    meta = {k: int(v, 0) for k, v in re.findall(
        r'^(code|base)=(\S+)', (folder/'anchor.txt').read_text(), re.M)}
    memory = (folder/'code.bin').read_bytes()
    code = meta['code'] - meta['base']
    assert memory[code+0x2af6:code+0x2af8] == bytes.fromhex('4ef9')
    entry = struct.unpack_from('>I', memory, code+0x2af8)[0] - meta['base']
    assert memory[entry+4:entry+8] == b'S760'
    assert decode_version(struct.unpack_from('>H', memory, entry+50)[0])[0] >= 17
    offset = struct.unpack_from('>H', memory, entry+104)[0]
    assert offset, 'DEATH_TEST fixture is absent'
    at = entry+offset
    assert memory[at:at+4] == b'R760'
    names = ('stage', 'errors', 'injection_tick', 'exit_tick', 'exit_field',
             'dialog_start', 'dialog_answer', 'resume_field', 'resume_credit',
             'resume_last', 'resume_ticks', 'resume_renders', 'resume_phase',
             'resume_energy', 'resume_level', 'resume_death', 'exit_energy',
             'exit_active', 'exit_death', 'resume_session', 'dialogs')
    result = dict(zip(names, struct.unpack_from('>2H10I9H', memory, at+4)))
    result['captured_session'] = struct.unpack_from('>I', memory, entry+100)[0]
    result['captured_tick'] = struct.unpack_from('>I', memory, entry+16)[0]
    result['field_hz'] = struct.unpack_from('>H', memory, entry+28)[0]
    if natural:
        assert not decline
        assert memory[at+66:at+70] == b'RN61', 'DEATH_NATURAL fixture is absent'
        result['armed_session'], result['armed_level'] = struct.unpack_from('>IH', memory, at+70)
    if decline:
        assert memory[at+66:at+70] == b'ND60', 'DEATH_DECLINE fixture is absent'
        result.update(zip(('menu_count', 'menu_running', 'menu_tick', 'menu_field',
                           'menu_session', 'dialog_choice'),
                          struct.unpack_from('>HHIIHH', memory, at+70)))
    return result


def validate(r, decline=False, natural=False):
    assert r['stage'] == 3 and r['errors'] == 0, r
    if natural:
        assert not decline and r['exit_tick'] > r['injection_tick']
    else:
        assert r['exit_tick'] == r['injection_tick']+1
    assert r['exit_energy'] >= 0x8000 and r['exit_active'] == 0 and r['exit_death'] == 1
    assert r['dialog_answer']-r['dialog_start'] >= 60
    assert r['exit_field'] <= r['dialog_start'] <= r['dialog_answer'] <= r['resume_last'] <= r['resume_field']
    assert r['resume_credit'] == r['field_hz']
    assert (r['resume_ticks'], r['resume_renders'], r['resume_phase'],
            r['resume_energy'], r['resume_level'], r['resume_death']) == (0, 0, 0, 680, r['armed_level'] if natural else 0, 0)
    session = r['armed_session']+1 if natural else 2
    assert r['resume_session'] == r['captured_session'] == session and r['dialogs'] == 1
    if decline:
        assert r['dialog_choice'] == 2 and r['menu_count'] == 1
        assert r['menu_running'] == 0 and r['menu_session'] == 1
        assert r['menu_tick'] == r['exit_tick']
        assert r['dialog_answer'] <= r['menu_field'] <= r['resume_last']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('captures', nargs='+', help='capture after gameplay has resumed, e.g. checkpoints/600')
    parser.add_argument('--decline', action='store_true', help='validate No, native menu return and new-game entry')
    parser.add_argument('--natural', action='store_true', help='validate observed death and Continue at the armed level')
    args = parser.parse_args()
    if args.natural and args.decline:
        parser.error('--natural cannot be combined with --decline')
    for folder in args.captures:
        result = read(folder, args.decline, args.natural)
        print(folder, json.dumps(result, sort_keys=True))
        validate(result, args.decline, args.natural)
