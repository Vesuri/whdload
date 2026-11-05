"""Match owned palette calls to pending logical fades in observed log order.

This checks stored palette publication ownership, not display scanout. Arithmetic
and entry/return contracts are checked separately by check_weather_palette.
"""
import re
from weather_fade_state import parse_values as fade_values
from weather_palette_state import parse_values as palette_values


def check_publications(text, callers):
    pending = None
    expected = []
    published_steps = publications = skipped = calls = 0
    for match in re.finditer(r'^PDW(FADE|PALETTE)_EVENT -?\d+ (0x[0-9a-f]+) (.+)$', text, re.M):
        family, offset, values = match.groups()
        offset = int(offset, 16)
        if family == 'PALETTE':
            if offset != 0x17306:
                continue
            row = palette_values(values)
            kind = callers.get(row['parent_return'])
            if kind is None:
                continue
            assert pending is not None, 'Owned palette call outside observed presentation'
            assert expected, 'Unexpected extra owned palette phase'
            wanted_kind, transition = expected.pop(0)
            assert (kind, row['transition']) == (wanted_kind, transition), 'Palette phase differs from pending logical publication'
            calls += 1
            continue
        row = fade_values(values)
        if offset == 0xbd1a:
            assert pending is None, 'Missing prior presentation return'
            if row['forecast'] <= 0:
                continue
            pending = row
            kind = row['pending']
            assert kind in range(5), 'Invalid pending palette kind'
            expected = []
            if kind:
                step_count = row['positive'] + row['negative']
                assert step_count > published_steps, 'Duplicate or reversed logical publication'
                skipped += step_count - published_steps - 1
                published_steps = step_count
                direction = 'positive' if kind in (1, 3) else 'negative'
                expected.append((direction, row['published']))
                if kind == 4:
                    expected.append(('negative_zero', 0))
                publications += 1
        elif offset == 0xbd58 and pending is not None:
            assert not expected, 'Pending logical phase never reached native palette helper'
            assert all(row[k] == v for k, v in pending.items() if k not in ('pending', 'draws')), 'Presentation mutated logical fade state'
            assert row['pending'] == 0
            assert row['draws'] == pending['draws'] + int(pending['pending'] != 0)
            pending = None
    assert pending is None, 'Capture ended inside observed presentation'
    assert publications > 0, 'No owned logical palette publications observed'
    return dict(publications=publications, calls=calls, coalesced_steps=skipped,
                logical_steps=published_steps)
