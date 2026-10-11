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
from weather_effect_state import snapshot as effect_snapshot, parse_values as effect_values
from weather_effect_clock import parse_values as clock_values, snapshot as clock_snapshot


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
    text = (root / 'swaps-gdb.txt').read_text()
    clocks = [(int(f), int(o, 16), clock_values(v)) for f, o, v in re.findall(
        r'^PDWECLK_EVENT (-?\d+) (0x[0-9a-f]+) (.+)$', text, re.M)]
    effects = [(int(f), int(o, 16), effect_values(v)) for f, o, v in re.findall(
        r'^PDWEFX_EVENT (-?\d+) (0x[0-9a-f]+) (.+)$', text, re.M)]
    assert clocks and len(clocks) == len(effects), 'Missing sound-request observations'
    assert first['cleanup_pending'] == 0, 'Unobserved request before capture'
    previous = None
    pending = requests = 0
    request_clocks = []
    for (field, offset, clock), (efield, eoffset, effect) in zip(clocks, effects):
        assert (field, offset) == (efield, eoffset)
        if previous is None:
            assert effect['cleanups'] == first['cleanups'] and effect['cleanup_pending'] == 0, 'Unobserved initial audio work'
        else:
            pc, pe = previous
            generated = clock['generations'] - pc['generations']
            assert generated in (0, 1), 'Missing generation boundary or lifecycle reset'
            if generated and pe['delay'] == 1 and effect['attempts'] == pe['attempts'] + 1:
                assert pending == 0, 'Weather sound requests coalesced before delivery'
                pending += 1
                requests += 1
                request_clocks.append(clock['generation_clock'])
            calls = effect['cleanups'] - pe['cleanups']
            assert calls in (0, 1) and calls <= pending, 'Unaccounted sound helper call'
            pending -= calls
            assert effect['cleanup_pending'] == pending, 'Sound request ledger disagrees with queue'
        previous = clock, effect
    assert pending == last['cleanup_pending'] == 0, 'Undelivered sound request at endpoint'
    assert requests == completed, 'Generated sounds and complete calls differ'
    origin = clock_snapshot(root)['generation_clock']
    relative_requests = tuple((clock - origin) * 5 for clock in request_clocks)
    print(f'  {requests} observed delay-expiry requests delivered without coalescing; request times from initial generation: {relative_requests} ms')
    print(f'{root.name}: {completed} weather audio calls, {started} native starts, {suppressed} suppressed')
    print(f'  Sample/channel arguments match; helper duration {min(waits)}–{max(waits)} ms in PAL fields; {other} other audio boundary rows excluded')
    print('  Native helper contract only; audible output, unobserved stalls/modes and timing acceptance remain separate.')
    return relative_requests


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('captures', type=Path, nargs='+')
    histories = [check(root) for root in parser.parse_args().captures]
    assert all(history == histories[0] for history in histories), 'Weather audio request timelines differ'
    print('All supplied observed sound-request timelines match.')
