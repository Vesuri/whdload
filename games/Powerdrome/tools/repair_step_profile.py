#!/usr/bin/env python3
"""Attribute complete first-stage repair steps in read-only A500 instruction traces.

Use unpaced native or WORLD20 captures anchored at hunk $148d0. Unlike the
whole-window call report, this excludes the opening/closing partial steps.
Recorded cycles include interrupt and stopped time between boundary instructions.
No game state is changed; this is not a renderer throughput benchmark.
"""
import argparse
import json
from pathlib import Path
import statistics

import _amigaxdev
from amigaxdev import barto

# Ordered boundaries in the native repair loop and its E296 presenter.
BOUNDARIES = (
    (0x148d0, 'begin'), (0x148e0, 'composed'), (0x14956, 'drawn'),
    (0xe334, 'prepared'), (0xe33a, 'clocked'), (0xe34a, 'scrolled'),
    (0xe35a, 'display_ready'), (0xe364, 'waited'), (0xe378, 'copied'),
    (0xe3bc, 'opponents_begin'), (0xe3c0, 'opponents_end'), (0x1495e, 'end'),
)
SEGMENTS = (
    ('body_bitmap', 'begin', 'composed'),
    ('moving_parts', 'composed', 'drawn'),
    ('presentation_prepare', 'drawn', 'prepared'),
    ('frame_clock', 'prepared', 'clocked'),
    ('scroll_viewport', 'clocked', 'scrolled'),
    ('display_setup', 'scrolled', 'display_ready'),
    ('wait_tof', 'display_ready', 'waited'),
    ('bitmap_copy', 'waited', 'copied'),
    ('hud_and_input', 'copied', 'opponents_begin'),
    ('opponents', 'opponents_begin', 'opponents_end'),
    ('presenter_tail', 'opponents_end', 'end'),
)
# Same PAL CPU-backend scale as powerdrome_report.py: 142102 cycles per field.
CYCLES_PER_MS = 142102 / 20


def profile(root):
    config = json.loads((root / 'configuration.json').read_text())
    assert config['CPU'] == '68000' and config['AMIGA_MODEL'] == 'A500'
    assert int(config['ANCHOR'], 0) == 0x148d0
    assert config['SWAP_ONLY'] == '0', 'Full instruction trace required'
    base = int((root / 'game-base.txt').read_text(), 0)
    trace = barto.load(root / 'trace.bin')
    names = dict(BOUNDARIES)
    expected = list(names.values())
    cycles = 0
    current = None
    complete = []
    partial = []
    for field in trace.fields:
        for pc, cost, regs in trace.instructions(field):
            offset = (pc or 0) - base
            if offset == 0x148d0:
                if current is not None:
                    partial.append(current['counter'])
                current = {'counter': regs[7] & 0xffff, 'boundaries': {},
                           'opponent_body_entries': 0}
            if current is not None and offset == 0xe2a6:
                current['message_deadline'] = regs[0]
            if current is not None and offset == 0xe2ac:
                current['message_expired'] = True
            if current is not None and offset == 0xe330:
                current['message_hunk_offset'] = regs[11] - base
            if current is not None and offset == 0xd3de:
                assert 'opponents_begin' in current['boundaries']
                assert 'opponents_end' not in current['boundaries']
                current['opponent_body_entries'] += 1
            if current is not None and offset in names:
                name = names[offset]
                assert name not in current['boundaries'], (root, name, current)
                current['boundaries'][name] = cycles
                if name == 'end':
                    assert list(current['boundaries']) == expected, (root, current)
                    points = current.pop('boundaries')
                    current['cycles'] = {
                        label: points[end] - points[start]
                        for label, start, end in SEGMENTS
                    }
                    current['total_cycles'] = points['end'] - points['begin']
                    assert sum(current['cycles'].values()) == current['total_cycles']
                    assert 0 <= current['counter'] <= 32
                    complete.append(current)
                    current = None
            cycles += cost
    if current is not None:
        partial.append(current['counter'])
    assert complete, 'No complete repair steps; capture a longer unpaced window'
    counters = [row['counter'] for row in complete]
    assert counters == list(range(counters[0], counters[-1] - 1, -1)), counters
    state = base + 0xa6e
    assert state + 0x68 <= len(trace.chip), 'A500 state must reside in chip memory'
    initial_counter = int.from_bytes(trace.chip[state + 0x5e:state + 0x62], 'big')
    initial_deadline = int.from_bytes(trace.chip[state + 0x64:state + 0x68], 'big')
    return {'capture': root.name, 'complete_steps': complete,
            'initial_counter': initial_counter, 'initial_message_deadline': initial_deadline,
            'partial_step_counters': partial,
            'opening_prefix_excluded': counters[0] != 32,
            'cycle_scale_per_ms': CYCLES_PER_MS}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('captures', type=Path, nargs='+')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    reports = [profile(root) for root in args.captures]
    if args.json:
        print(json.dumps(reports, indent=2))
        return
    for report in reports:
        rows = report['complete_steps']
        print(f"{report['capture']}: {len(rows)} complete steps, counters "
              f"{rows[0]['counter']}..{rows[-1]['counter']}; "
              f"partial counters {report['partial_step_counters']}; "
              f"opening prefix excluded={report['opening_prefix_excluded']}")
        print(f"initial frame counter={report['initial_counter']}, "
              f"message deadline={report['initial_message_deadline']}")
        print('message transitions (counter, hunk offset, expired): ' + ', '.join(
            f"{r['counter']}, ${r.get('message_hunk_offset', 0):x}, "
            f"{bool(r.get('message_expired'))}"
            for i, r in enumerate(rows) if i == 0 or
            (r.get('message_hunk_offset'), bool(r.get('message_expired'))) !=
            (rows[i-1].get('message_hunk_offset'), bool(rows[i-1].get('message_expired')))))
        print('segment                 mean_ms    min_ms    max_ms')
        for label in [s[0] for s in SEGMENTS] + ['total']:
            values = [(r['total_cycles'] if label == 'total' else r['cycles'][label])
                      / CYCLES_PER_MS for r in rows]
            print(f'{label:23s} {statistics.mean(values):8.3f} '
                  f'{min(values):9.3f} {max(values):9.3f}')
        print('opponent body entries: ' + ', '.join(
            f"{r['counter']}={r['opponent_body_entries']}" for r in rows))
        print('step totals (ms): ' + ', '.join(
            f"{r['counter']}={r['total_cycles'] / CYCLES_PER_MS:.3f}" for r in rows))


if __name__ == '__main__':
    main()
