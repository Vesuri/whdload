#!/usr/bin/env python3
"""Check the explicitly seeded mode-2 weather-selection fixture.

Requires the first selected publication and every tick of its lifetime/delay.
This proves one generation branch, not natural weather or sound trigger.
"""
import argparse
from pathlib import Path
import re
import struct

from report_weather import advance_seed
from weather_effect_state import locate, parse_values, snapshot


def check(root):
    code = (root / 'final-code.bin').read_bytes()
    chip = (root / 'final-chip.bin').read_bytes()
    game = int((root / 'game-base.txt').read_text(), 0)
    base = int((root / 'dump-base.txt').read_text(), 0)
    record = locate(chip, code, game, base)
    assert record is not None
    assert code[record-base:record-base+8]==b'PDWEFX01', 'Use check_weather_effect_schedule.py for the 80/140-ms schedule'
    tag = code.find(b'PDWEFT01', record - base + 48, record - base + 4096)
    assert tag >= 0, 'Missing live directed fixture record'
    activation, step, clock = struct.unpack_from('>3I', code, tag + 8)
    assert activation == 1 and step >= 200
    events = [(int(f), int(off, 16), parse_values(v)) for f, off, v in re.findall(
        r'^PDWEFX_EVENT (-?\d+) (0x[0-9a-f]+) (.+)$',
        (root / 'swaps-gdb.txt').read_text(), re.M)]
    first = next(s for _, off, s in events if off == 0xccee and s['selections'])
    assert first['clock'] == clock, 'First selection publication was not observed'
    assert first['selections'] == first['attempts'] == 1
    assert first['visual_events'] == first['visible'] == first['draws'] == 0
    trial = advance_seed(3705, 1)
    seed = advance_seed(trial, 1)
    lifetime = (trial >> 7) & 5
    delay = (seed >> 14) + 4
    assert trial >> 7 <= 6
    assert (first['rng'], first['lifetime'], first['delay']) == (seed, lifetime, delay)
    rows = []
    for n in range(delay):
        samples = [s for _, off, s in events
                   if off == 0xccee and s['ticks'] == first['ticks'] + n]
        assert samples, f'Missing logical publication at relative tick {n}'
        expected = (max(lifetime - n, 0), delay - n,
                    min(n, lifetime), max(lifetime + 1 - n, 0) if n else 0)
        for s in samples:
            assert s['selections'] == s['attempts'] == 1
            assert s['enabled'] == 65535 and s['transition'] == 0
            assert tuple(s[k] for k in ('lifetime', 'delay', 'visual_events', 'visible')) == expected
        rows.append((samples[0]['clock'] - clock, *expected))
    after = [s for _, off, s in events
             if off == 0xccee and s['ticks'] == first['ticks'] + delay]
    assert after and all(s['attempts'] == 2 for s in after), 'Delay did not release next trial'
    final = snapshot(root, True)
    print(f'{root.name}: seed {seed}, lifetime {lifetime}, delay {delay}; all first-effect logical publications verified')
    print(f'  fixture activation step={step}; final selections={final["selections"]}, visual events={final["visual_events"]}, draws={final["draws"]}, cleanups={final["cleanups"]}')
    return rows


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('captures', type=Path, nargs='+')
    args = parser.parse_args()
    results = [check(root) for root in args.captures]
    assert all(rows == results[0] for rows in results), 'Logical publication times/states differ'
    print('Seeded first-selection lifecycle matches across supplied captures; full weather remains outside this check.')
