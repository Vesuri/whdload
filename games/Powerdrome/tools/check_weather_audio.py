#!/usr/bin/env python3
"""Validate observed weather audio helper calls, not audible output or scheduling.

Requires read-only PDWAUDIO_EVENT entry/return probes, available native samples,
and a capture ending outside a weather helper call. Other audio callers are ignored
only after identification by the installed weather wrapper's exact return address.
"""
import argparse
from pathlib import Path
import re
from weather_audio_state import snapshot, owned_return, parse_values, REGISTERS
from weather_effect_state import snapshot as effect_snapshot


def check(root):
    game = int((root / 'game-base.txt').read_text(), 0)
    base = int((root / 'dump-base.txt').read_text(), 0)
    states = []
    returns = []
    for prefix in ('', 'final-'):
        chip = (root / (prefix + 'chip.bin')).read_bytes()
        code = (root / (prefix + 'code.bin')).read_bytes()
        state = snapshot(chip, game)
        assert state['available'], 'Optional weather samples absent'
        assert chip[game + 0x17836:game + 0x1783e] == bytes.fromhex('4a6e02f4660000aa')
        assert chip[game + 0x178e6:game + 0x178e8] == bytes.fromhex('4e75')
        states.append(state)
        returns.append(owned_return(chip, code, game, base))
    assert returns[0] == returns[1], 'Installed caller changed during capture'
    for key in ('allocation_base', 'allocation_size', 'sample_table',
                'sample_pointer', 'sample_words', 'sample_period'):
        assert states[0][key] == states[1][key], f'Resources changed: {key}'
    events = [(int(field), int(offset, 16), parse_values(values))
              for field, offset, values in re.findall(
                  r'^PDWAUDIO_EVENT (-?\d+) (0x[0-9a-f]+) (.+)$',
                  (root / 'swaps-gdb.txt').read_text(), re.M)]
    assert events, 'Audio boundary probes missing'
    assert all(a[0] <= b[0] for a, b in zip(events, events[1:])), 'Unordered audio probes'
    before = None
    completed = started = suppressed = other = 0
    waits = []
    for field, offset, state in events:
        assert offset in (0x17836, 0x178e6)
        if state['return_address'] != returns[0]:
            other += 1
            continue
        assert state['available'] == 0xffffffff
        if offset == 0x17836:
            assert before is None, 'Weather audio entry without preceding return'
            assert (state['a0'], state['d0'], state['d1'], state['d2'], state['d3']) == (
                states[0]['sample_pointer'], states[0]['sample_words'], 63,
                states[0]['sample_period'], 3), 'Wrong weather sample/channel arguments'
            assert state['a6'] == game + 0xa6e
            before = field, state
        else:
            assert before is not None, 'Weather audio return without entry'
            entry_field, entry = before
            assert state['sp'] == entry['sp'], 'Audio stack changed'
            if entry['suppressed']:
                assert all(state[r] == entry[r] for r in REGISTERS), 'Suppressed helper changed registers'
                suppressed += 1
            else:
                assert (state['d0'], state['d1'], state['d4']) == (0x8208, 0x8400, 48), 'Native channel-start path not completed'
                assert all(state[r] == entry[r] for r in ('d2', 'd3', 'd6', 'd7', 'a0', 'a2', 'a3', 'a4', 'a5', 'a6'))
                started += 1
            waits.append((field - entry_field) * 20)
            completed += 1
            before = None
    assert before is None, 'Capture ended inside weather audio helper'
    assert completed > 0, 'No complete weather audio calls'
    first = effect_snapshot(root)
    last = effect_snapshot(root, True)
    assert last['cleanups'] - first['cleanups'] == completed, 'Unobserved weather wrapper calls'
    print(f'{root.name}: {completed} weather audio calls, {started} native starts, {suppressed} suppressed')
    print(f'  Sample/channel arguments match; helper duration {min(waits)}–{max(waits)} ms in PAL fields; {other} other audio boundary rows excluded')
    print('  Native helper contract only; audible output, request loss/coalescing and timing acceptance remain separate.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    check(parser.parse_args().capture)
