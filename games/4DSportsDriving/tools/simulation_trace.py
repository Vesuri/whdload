#!/usr/bin/env python3
"""Count original simulation scheduling sites in existing sampled PAL traces.
No interpolation across joins: 250-field captures consist of 100/100/50 parts.
Usage: python3 tools/simulation_trace.py tmp/prof/CAPTURE [...]
"""
import collections
import json
import struct
import sys
from pathlib import Path
import _amigaxdev  # noqa: F401
from amigaxdev import barto

SITES = {0x36e0e: 'timer_irq', 0x7964: 'timer_callback',
         0x7a10: 'simulation_tick', 0x7a66: 'input_or_replay',
         0x7d38: 'live_input_append', 0xe5f2: 'step_consumer',
         0xe7b8: 'player_physics', 0xbc48: 'opponent_physics',
         0x7500: 'render_completion'}

def report(directory):
    p = Path(directory)
    meta = json.loads((p / 'anchor.json').read_text())
    capture = json.loads((p / 'capture.json').read_text())
    state = (p / 'state.bin').read_bytes()
    word = lambda displacement: struct.unpack_from('>H', state, 0x7ffe + displacement)[0]
    trace = barto.load(p / 'trace.bin')
    parts = capture.get('parts', [len(trace.fields)])
    assert sum(parts) == len(trace.fields)
    per_field = []
    for f in trace.fields:
        counts = collections.Counter()
        for pc, cost, registers in trace.instructions(f):
            label = SITES.get(pc - meta['game_base']) if pc is not None else None
            if label:
                counts[label] += 1
        per_field.append(counts)
    counts = sum(per_field, collections.Counter())
    cursor, split = 0, []
    for size in parts:
        split.append(dict(sum(per_field[cursor:cursor + size], collections.Counter())))
        cursor += size
    return dict(capture=p.name, fields=len(trace.fields), continuous=capture.get('continuous'),
                initial_active_mode=word(-0x15fa), initial_selected_mode=word(-0xbc),
                initial_timer_latch=word(-0x217c), initial_divider=word(-0xbe),
                counts=dict(counts), parts=split,
                caveat='Entry counts in sampled fields, not completed-call durations or deterministic state comparisons. Initial state need not describe every field.')

if __name__ == '__main__':
    print(json.dumps([report(p) for p in sys.argv[1:]], indent=2))
