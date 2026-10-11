#!/usr/bin/env python3
"""Check observed native fade and palette-copy calls, not displayed pixels.

Requires complete entry/return probes and all 31 owned interpolation phases.
This is intentionally a full directed-fade gate; coalesced presentation needs a
separate accounting check and must not be treated as missing observations here.
"""
import argparse
from collections import Counter
from pathlib import Path
import re
import struct
from weather_palette_state import interpolate, owned_fade_returns, parse_values


def palette(row, name):
    return tuple(row[f'{name}_{i}'] for i in range(16))


def check_interpolation(before, after, kind, target):
    transition = before['transition']
    signed = transition if transition < 32768 else transition - 65536
    if kind == 'positive':
        assert 1 <= signed <= 15
        phase = 15 - signed
    elif kind == 'negative':
        assert -15 <= signed <= -1
        phase = -signed
    else:
        assert kind == 'negative_zero' and signed == 0
        phase = 0
    assert (before['d0'] & 65535) == before['source_colour']
    assert (before['d1'] & 65535) == target
    assert (before['d6'] & 65535, before['d7'] & 65535) == (phase, 5)
    colour = interpolate(before['source_colour'], target, phase)
    for name in ('saved', 'current'):
        expected = list(palette(before, name))
        expected[5] = colour
        assert palette(after, name) == tuple(expected), f'{kind}: wrong {name} interpolation output'
    return phase, colour


def check_copy(before, after):
    assert before['restore_source'] == before['a2'] == after['restore_source'] == after['a2']
    expected = list(palette(before, 'restore'))
    expected[5] = before['current_5']
    assert palette(after, 'current') == tuple(expected), 'Restoration did not preserve entry 5 and copy other entries'
    saved_expected = tuple(expected) if before['saved_pointer'] == before['current_pointer'] else palette(before, 'saved')
    assert palette(after, 'saved') == saved_expected, 'Restoration changed unrelated saved palette'


def check(root):
    game = int((root / 'game-base.txt').read_text(), 0)
    base = int((root / 'dump-base.txt').read_text(), 0)
    chip = (root / 'chip.bin').read_bytes()
    code = (root / 'code.bin').read_bytes()
    final_chip = (root / 'final-chip.bin').read_bytes()
    final_code = (root / 'final-code.bin').read_bytes()
    callers = owned_fade_returns(chip, code, game, base)
    assert owned_fade_returns(final_chip, final_code, game, base) == callers
    targets = struct.unpack_from('>7H', chip, game + 0x203e)
    assert struct.unpack_from('>7H', final_chip, game + 0x203e) == targets
    text = (root / 'swaps-gdb.txt').read_text()
    assert 'PDWPALETTE_INVALID' not in text, 'Invalid live palette pointer'
    events = [(int(f), int(o, 16), parse_values(v)) for f, o, v in re.findall(
        r'^PDWPALETTE_EVENT (-?\d+) (0x[0-9a-f]+) (.+)$', text, re.M)]
    assert events, 'Palette call probes missing'
    assert all(a[0] <= b[0] for a, b in zip(events, events[1:]))
    pending = {0x17306: [], 0x17062: []}
    exits = {0x173a8: 0x17306, 0x1708c: 0x17062}
    phases = Counter()
    history = []
    copies = unowned = 0
    for _, offset, row in events:
        if offset in pending:
            pending[offset].append(row)
            continue
        assert offset in exits, 'Unexpected palette boundary'
        entry = exits[offset]
        assert pending[entry], 'Palette return without observed entry'
        before = pending[entry].pop()
        assert (row['sp'], row['return_address'], row['parent_return']) == (before['sp'], before['return_address'], before['parent_return']), 'Palette call stack mismatch'
        for key in ('track', 'view', 'transition', 'transient', 'source_colour', 'saved_pointer', 'current_pointer'):
            assert row[key] == before[key], f'Palette helper changed {key}'
        if entry == 0x17062:
            check_copy(before, row)
            copies += 1
            continue
        kind = callers.get(before['parent_return'])
        if kind is None:
            unowned += 1
            continue
        native_return = game + (0x8a4a if kind == 'positive' else 0x8a8c)
        assert before['return_address'] == native_return, 'Wrong native interpolation caller'
        index = 0 if before['view'] else before['track']
        assert 0 <= index < len(targets)
        phase, colour = check_interpolation(before, row, kind, targets[index])
        phases[kind, phase] += 1
        history.append((kind, phase, before['source_colour'], targets[index], colour))
    assert not any(pending.values()), 'Capture ended inside palette helper'
    expected = Counter({('positive', i): 1 for i in range(15)})
    expected.update({('negative', i): 1 for i in range(1, 16)})
    expected['negative_zero', 0] = 1
    assert phases == expected, 'Missing, duplicate or coalesced directed fade phase'
    assert copies > 0, 'No complete palette restoration observed'
    print(f'{root.name}: 31 owned interpolation calls match native integer arithmetic; {copies} restoration calls preserve entry 5')
    print(f'  {unowned} unrelated interpolation calls excluded by caller identity; palette memory only, not scanout')
    return history


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('captures', type=Path, nargs='+')
    histories = [check(root) for root in parser.parse_args().captures]
    assert all(h == histories[0] for h in histories), 'Cross-CPU palette histories differ'
