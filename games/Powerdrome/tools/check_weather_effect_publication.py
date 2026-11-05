#!/usr/bin/env python3
"""Account for effect publications omitted or repeated by actual rendering.

Requires the logical schedule and complete draw ownership probes. This does not
prove palette writes or displayed pixels, and does not accept unobserved draws.
"""
import argparse
from bisect import bisect_right
from collections import Counter
from pathlib import Path
import re
from check_weather_effect_schedule import check as check_schedule
from check_weather_effect_draw import check as check_draw
from weather_effect_clock import snapshot as clock_snapshot
from weather_effect_state import parse_values, snapshot


def check(root):
    history = check_schedule(root, seeded=False)
    check_draw(root)
    origin = clock_snapshot(root)['generation_clock']
    visuals = {origin + clock: row for (kind, clock), row in history.items() if kind == 'v'}
    deadlines = sorted(visuals)
    assert deadlines, 'No logical publication boundaries'
    text = (root / 'swaps-gdb.txt').read_text()
    effects = []
    completed_clock = None
    for match in re.finditer(r'^(PDWEFX|PDW20)_EVENT -?\d+ (0x[0-9a-f]+) (.+)$', text, re.M):
        tag, off, values = match.groups()
        if tag == 'PDW20' and off == '0xcedc':
            # This is the native world-end boundary before the patched end hook.
            # The following render follows its weather update and cursor advance.
            completed_clock = int(values.split()[0])
        elif tag == 'PDWEFX' and off == '0x112f0':
            assert completed_clock is not None, 'Missing preceding world-end observation'
            effects.append((parse_values(values), completed_clock))
    assert effects, 'No draw boundaries observed'
    first, last = snapshot(root), snapshot(root, True)
    assert first['drawing'] == last['drawing'] == 0, 'Partial draw needs separate accounting'
    assert len(effects) == last['draws'] - first['draws'], 'Unobserved effect draw'
    rendered = Counter()
    for effect, completed_clock in effects:
        index = bisect_right(deadlines, completed_clock) - 1
        assert index >= 0, 'Draw precedes observed publication history'
        deadline = deadlines[index]
        visual = visuals[deadline]
        assert effect['clock'] == deadline, 'Draw replays stale logical publication'
        assert effect['visible'] == visual[0] > 0
        assert effect['visual_seed'] == visual[4], 'Draw seed differs from logical publication'
        rendered[deadline] += 1
    # Only count states with an observed successor; the last publication may still
    # be waiting for its first presentation when capture ends.
    eligible = {d for d in deadlines[:-1] if visuals[d][0] > 0}
    omitted = eligible - rendered.keys()
    repeated = sum(n - 1 for n in rendered.values())
    print(f'{root.name}: {len(eligible)} closed visible publications; {len(omitted)} never drawn; {repeated} repeated draws')
    print('  Every observed draw uses the latest completed logical publication; pixels and palette publication remain separate.')
    return len(omitted)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('captures', type=Path, nargs='+')
    p.add_argument('--require-omitted', action='store_true')
    args = p.parse_args()
    for root in args.captures:
        omitted = check(root)
        if args.require_omitted:
            assert omitted > 0, 'No skipped presentation was exercised'
