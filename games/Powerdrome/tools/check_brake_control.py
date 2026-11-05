#!/usr/bin/env python3
"""Attribute native brake decrements and overspeed damping at control boundaries.

Checks arithmetic rather than certifying A500 response calibration. The native
brake body is NOPed in periodic builds, where queued braking occurs elsewhere.
"""
import argparse
import json
from pathlib import Path
import struct
from coverage_status import fixture


def signed(value):
    return (value ^ 0x8000)-0x8000


def check(root):
    assert (root/'final-code.bin').is_file(), 'Capture must be terminal'
    cfg = json.loads((root/'configuration.json').read_text())
    options = dict(v.split('=', 1) for v in cfg['WHD_ARGS'].split() if '=' in v)
    assert options['CUSTOM5'] == '9', 'This report is scoped to the joystick fixture'
    game = int((root/'game-base.txt').read_text(), 0)
    # Read installed behavior: option meanings changed, and hardware can fall back.
    hook = (root/'chip.bin').read_bytes()[game+0xca44:game+0xca46]
    assert hook in (bytes.fromhex('082e'), bytes.fromhex('4ef9'))
    native = hook == bytes.fromhex('082e')
    epoch = fixture(root/'code.bin')['epoch']
    anchor = struct.unpack_from('>I', (root/'chip.bin').read_bytes(), game+0x48fe)[0]
    shift = (anchor-epoch) & 0xffffffff
    active = None
    logical = None
    checked = brake_checks = 0
    held = []
    for line in (root/'swaps-gdb.txt').read_text().splitlines():
        v = line.split()
        if not v:
            continue
        if v[0] == 'PDINPUT_EVENT':
            logical = (int(v[1]), int(v[2], 16), list(map(int, v[3:])))
        if v[0] != 'PDBCTL_EVENT':
            continue
        field, off = int(v[1])+shift, int(v[2], 16)
        state = list(map(int, v[3:]))
        assert len(state) == 10
        if off == 0xcf2e:
            assert active is None, 'Nested or incomplete control call'
            logical_ms = None
            if not native:
                assert logical is not None and logical[:2] == (int(v[1]), off)
                assert logical[2][3] == 1, 'Unscheduled control call needs separate incident attribution'
                logical_ms = (logical[2][0]-epoch*4)*5
            active = {'field': field, 'entry': state, 'logical_ms': logical_ms}
        elif active is not None and off == 0xd000:
            assert 'brake' not in active
            active['brake'] = state
        elif active is not None and off == 0xd038:
            active['damping'] = state
            if 'brake' in active:
                before = active['brake']
                decrement = (3 if before[3] & 32 else before[2]) if native else 0
                assert signed(state[0]) == signed((before[0]-decrement) & 65535), 'Unexpected native brake decrement'
                brake_checks += 1
        elif active is not None and off == 0xd058:
            if 'damping' in active:
                before = active['damping']
                speed = max(0, signed(before[0]))
                cruise = signed(before[1])
                expected = speed-((speed-cruise)//2 if speed > cruise else 0)
                assert signed(state[0]) == expected, 'Unexpected overspeed damping'
                checked += 1
            at_ms = active['field']*20 if native else active['logical_ms']
            if 2000 <= at_ms < 3000:
                held.append({'field': active['field'], 'logical_ms': active['logical_ms'], 'entry_speed': signed(active['entry'][0]),
                             'brake_body': 'brake' in active,
                             'before_damping': signed(active['damping'][0]) if 'damping' in active else None,
                             'exit_speed': signed(state[0]), 'cruise': state[1]})
            active = None
    assert checked and brake_checks and held
    if not native:
        assert all(b['logical_ms']-a['logical_ms'] == 90 for a,b in zip(held, held[1:])), 'Control cadence changed during braking'
    result = {'capture': root.name, 'native': native,
              'checked_damping_calls': checked, 'checked_brake_bodies': brake_checks,
              'held_brake_controls': held, 'incomplete_tail': active is not None}
    print(json.dumps(result, indent=2))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('captures', type=Path, nargs='+')
    reports = [check(root) for root in parser.parse_args().captures]
    periodic = [report for report in reports if not report['native']]
    if len(periodic) > 1:
        sequences = [[{k:v for k,v in row.items() if k != 'field'} for row in report['held_brake_controls']]
                     for report in periodic]
        assert all(rows == sequences[0] for rows in sequences[1:]), 'Logical high-speed control sequence differs'
        print(f'All {len(sequences[0])} held-brake logical control states match across {len(periodic)} captures')
