#!/usr/bin/env python3
"""Measure native/fast polygons drawn from identical inputs by the VERIFY twin.
The first MOVEA and verification wrappers are excluded from both costs.
"""
import argparse
import json
from pathlib import Path
import statistics
import _amigaxdev
from amigaxdev import barto
from perf_status import status

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('capture', type=Path)
a = p.parse_args()
game = int((a.capture/'game-base.txt').read_text(), 0)
s = status(a.capture/'code.bin')
code = s['raster_code']
trace = barto.load(a.capture/'trace.bin')
active = None
pending = None
cycles = 0
pairs = []
input_failures = 0
for f in trace.fields:
    for pc, cost, regs in trace.instructions(f):
        if pc in (game+0x15eee, code+0x15eee-0x15b68):
            kind = 'native' if pc == game+0x15eee else 'fast'
            # a2 is the edge-table pointer loaded by the excluded MOVEA.
            inputs = tuple(regs[i] for i in range(15) if i != 10)
            active = [kind, cycles, inputs]
        cycles += cost
        clone = pc-(code+0x1609c-0x15b68) if pc is not None else -1
        end = pc in (game+0x1609a, code+0x1609a-0x15b68) or (0 <= clone < 16*124 and clone % 124 == 122)
        if active and end:
            kind, start, inputs = active
            elapsed = cycles-start
            if kind == 'native':
                pending = (elapsed, inputs)
            elif pending:
                input_failures += pending[1] != inputs
                pairs.append((pending[0], elapsed))
                pending = None
            active = None
assert pairs and not input_failures, f'{len(pairs)} pairs; {input_failures} input mismatches'
native = [x for x,y in pairs]
fast = [y for x,y in pairs]
print(json.dumps({'paired_polygons': len(pairs), 'input_register_mismatches': input_failures,
                  'native_mean_cycles': statistics.mean(native), 'fast_mean_cycles': statistics.mean(fast),
                  'native_total_cycles': sum(native), 'fast_total_cycles': sum(fast),
                  'cost_reduction_percent': 100*(1-sum(fast)/sum(native)),
                  'includes_interrupt_cost': True}, indent=2))
