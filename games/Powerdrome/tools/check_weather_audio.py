#!/usr/bin/env python3
"""Validate observed weather audio helper calls, not audible output or scheduling.

Requires read-only PDWAUDIO_EVENT entry/return probes, available native samples,
and a capture ending outside a weather helper call. Other audio callers are ignored
only after identification by the installed weather wrapper's exact return address.
"""
import argparse
from pathlib import Path
import re
import struct
from weather_audio_state import snapshot, owned_return, parse_values, REGISTERS
from weather_effect_state import snapshot as effect_snapshot, parse_values as effect_values, locate as effect_locate
from weather_effect_clock import parse_values as clock_values, snapshot as clock_snapshot


def check(root, require_mute=False, require_unavailable=False):
    game = int((root / 'game-base.txt').read_text(), 0)
    base = int((root / 'dump-base.txt').read_text(), 0)
    states = []
    returns = []
    for prefix in ('', 'final-'):
        chip = (root / (prefix + 'chip.bin')).read_bytes()
        code = (root / (prefix + 'code.bin')).read_bytes()
        state = snapshot(chip, game)
        if require_unavailable:
            assert state['available'] == state['sample_table'] == 0, 'Expected absent optional weather samples'
        else:
            assert state['available'], 'Optional weather samples absent'
        assert chip[game + 0x17836:game + 0x1783e] == bytes.fromhex('4a6e02f4660000aa')
        assert chip[game + 0x178e6:game + 0x178e8] == bytes.fromhex('4e75')
        states.append(state)
        returns.append(owned_return(chip, code, game, base))
    assert returns[0] == returns[1], 'Installed caller changed during capture'
    resource_keys = ('allocation_base', 'allocation_size', 'sample_table')
    if not require_unavailable:
        resource_keys += ('sample_pointer', 'sample_words', 'sample_period')
    for key in resource_keys:
        assert states[0][key] == states[1][key], f'Resources changed: {key}'
    events = [(int(field), int(offset, 16), parse_values(values))
              for field, offset, values in re.findall(
                  r'^PDWAUDIO_EVENT (-?\d+) (0x[0-9a-f]+) (.+)$',
                  (root / 'swaps-gdb.txt').read_text(), re.M)]
    assert events, 'Audio boundary probes missing'
    assert all(a[0] <= b[0] for a, b in zip(events, events[1:])), 'Unordered audio probes'
    if require_unavailable:
        assert all(s['return_address'] != returns[0] and s['available'] == 0 for _, _, s in events), 'Unavailable weather sample was used'
        effects = [effect_values(v) for v in re.findall(
            r'^PDWEFX_EVENT -?\d+ 0x[0-9a-f]+ (.+)$',
            (root / 'swaps-gdb.txt').read_text(), re.M)]
        assert effects, 'No effect observations'
        assert any(a['delay'] == 1 and b['ticks'] == a['ticks'] + 1 and b['attempts'] == a['attempts'] + 1 for a, b in zip(effects, effects[1:])), 'No observed delay expiry exercised the missing-resource guard'
        effects += [effect_snapshot(root), effect_snapshot(root, True)]
        assert all(s['cleanup_pending'] == s['cleanups'] == 0 for s in effects), 'Unavailable sound was queued or called'
        print(f'{root.name}: optional samples absent; no weather audio call or queued request across observed boundaries')
        print('  Missing-resource guard only; generation/stall accounting must be checked separately.')
        return ('unavailable',)
    before = None
    completed = started = suppressed = other = 0
    waits = []
    outcomes = []
    key_before = None
    toggles = []
    for field, offset, state in events:
        if offset == 0xc5fc:
            assert key_before is None, 'Missing native mute-key completion'
            assert state['a6'] == game + 0xa6e
            key_before = state
            continue
        if offset == 0xc600:
            assert key_before is not None, 'Mute-key completion without entry'
            assert state['suppressed'] == (key_before['suppressed'] ^ 65535)
            assert all(state[r] == key_before[r] for r in REGISTERS), 'Native sound toggle changed registers'
            toggles.append((key_before['suppressed'], state['suppressed']))
            key_before = None
            continue
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
            outcomes.append(bool(entry['suppressed']))
            waits.append((field - entry_field) * 20)
            completed += 1
            before = None
    assert key_before is None, 'Capture ended inside native sound toggle'
    if require_mute:
        assert toggles == [(0, 65535), (65535, 0)], 'Missing native mute/unmute sequence'
        assert outcomes == [True, False, False], 'Expected first weather sound suppressed and two resumed starts'
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
    effect_address = effect_locate(chip, code, game, base)
    direct = code[effect_address-base:effect_address-base+8] == b'PDWEFX03'
    if direct:
        # Audio probes do not repeat PDW20. Use the most recent world boundary
        # in log order; the end probe precedes the weather update in that step.
        audio_worlds = []
        world_cursor = None
        for line in text.splitlines():
            if line.startswith('PDW20_EVENT '):
                world_cursor = int(line.split()[3])
            elif line.startswith('PDWAUDIO_EVENT '):
                parts = line.split()
                if int(parts[2], 16) in (0x17836, 0x178e6):
                    audio_worlds.append((int(parts[1]), int(parts[2], 16), world_cursor))
        audio_rows = [row for row in events if row[1] in (0x17836, 0x178e6)]
        audio_clocks = [row for row in clocks if row[1] in (0x17836, 0x178e6)]
        audio_effects = [row for row in effects if row[1] in (0x17836, 0x178e6)]
        assert len(audio_rows) == len(audio_clocks) == len(audio_effects) == len(audio_worlds)
        logical_entry = None
        for (f, o, a), (cf, co, c), (ef, eo, e), (wf, wo, w) in zip(audio_rows, audio_clocks, audio_effects, audio_worlds):
            assert (f, o) == (cf, co) == (ef, eo) == (wf, wo)
            if a['return_address'] != returns[0]:
                continue
            assert c['generation_clock'] == c['next_generation'] == w, 'Sound call escaped its logical generation boundary'
            assert e['delay'] == e['cleanup_pending'] == 0
            if o == 0x17836:
                logical_entry = c, e
            else:
                assert logical_entry == (c, e), 'Audio helper mutated logical weather state'
                logical_entry = None
        assert logical_entry is None
    fixture = code.find(b'PDWEFT03', effect_address - base + 48, effect_address - base + 4096)
    fixture_clock = None
    fixture_requests = 0
    if fixture >= 0:
        count, step, fixture_clock = struct.unpack_from('>3I', code, fixture + 8)
        assert count == 1 and step >= 200, 'Sound stress fixture did not activate'
    previous = None
    pending = requests = 0
    request_clocks = []
    for (field, offset, clock), (efield, eoffset, effect) in zip(clocks, effects):
        assert (field, offset) == (efield, eoffset)
        if direct and offset in (0x17836, 0x178e6):
            # V3 calls audio before the generation RNG/phase commit. The native
            # call contract is checked above; reconcile requests at complete world
            # observations, never interpreting an in-progress generation as final.
            continue
        if previous is None:
            assert effect['cleanups'] == first['cleanups'] and effect['cleanup_pending'] == 0, 'Unobserved initial audio work'
        else:
            pc, pe = previous
            generated = clock['generations'] - pc['generations']
            assert generated in (0, 1), 'Missing generation boundary or lifecycle reset'
            injected_first = generated and fixture_clock == clock['generation_clock']
            if injected_first:
                assert (clock['generation_seed'], effect['lifetime'], effect['delay']) == (6005, 0, 4), 'Wrong seeded sound stress selection'
                fixture_requests += 1
            if generated and (injected_first or (pe['delay'] == 1 and effect['attempts'] == pe['attempts'] + 1)):
                assert pending == 0, 'Weather sound requests coalesced before delivery'
                pending += 1
                requests += 1
                request_clocks.append(clock['generation_clock'])
            calls = effect['cleanups'] - pe['cleanups']
            assert calls in (0, 1) and calls <= pending, 'Unaccounted sound helper call'
            pending -= calls
            assert effect['cleanup_pending'] == pending, 'Sound request ledger disagrees with queue'
        previous = clock, effect
    assert fixture_requests == int(fixture_clock is not None), 'Missing directed first sound request'
    assert pending == last['cleanup_pending'] == 0, 'Undelivered sound request at endpoint'
    assert requests == completed, 'Generated sounds and complete calls differ'
    origin = clock_snapshot(root)['generation_clock']
    relative_requests = tuple((clock - origin) * 5 for clock in request_clocks)
    print(f'  {requests} observed delay-expiry requests delivered without coalescing; request times from initial generation: {relative_requests} ms')
    print(f'{root.name}: {completed} weather audio calls, {started} native starts, {suppressed} suppressed')
    print(f'  Sample/channel arguments match; helper duration {min(waits)}–{max(waits)} ms in PAL fields; {other} other audio boundary rows excluded')
    print('  Native helper contract only; audible output, unobserved stalls/modes and timing acceptance remain separate.')
    return relative_requests, tuple(outcomes)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('captures', type=Path, nargs='+')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--require-mute', action='store_true', help='Require native Tab mute/unmute and suppressed-then-resumed weather sounds')
    mode.add_argument('--require-unavailable', action='store_true', help='Require absent optional resources and no weather audio delivery')
    args = parser.parse_args()
    histories = [check(root, args.require_mute, args.require_unavailable) for root in args.captures]
    assert all(history == histories[0] for history in histories), 'Weather audio request timelines differ'
    print('All supplied observed sound-request timelines match.')
