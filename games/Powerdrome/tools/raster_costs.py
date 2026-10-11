#!/usr/bin/env python3
"""Attribute fast-raster instruction cycles; exclude wrappers and interrupts.

Offsets refer to the original copied routine; cloned row loops form one bucket.
The shift counter establishes an upper bound, not a predicted optimization gain.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import _amigaxdev
from amigaxdev import barto
from perf_status import status

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('capture', type=Path)
a = p.parse_args()
code = status(a.capture/'code.bin')['raster_code']
trace = barto.load(a.capture/'trace.bin')
cycles, instructions = Counter(), Counter()
shifts = Counter()
edge_memory_loop = Counter()
for field in trace.fields:
    for pc, cost, regs in trace.instructions(field):
        if pc is None:
            continue
        off = pc-code+0x15b68
        if 0x15b68 <= off < 0x15e68:
            group = 'span_writers'
        elif any(lo <= off < hi for lo, hi in ((0x15f3e,0x15f4e), (0x15f64,0x15f72), (0x15f9e,0x15fae), (0x15fc4,0x15fd2))):
            group = 'edge_steps'
        elif 0x15ee8 <= off < 0x15fd4:
            group = 'edge_setup'
        elif 0x15fd4 <= off < 0x16020:
            group = 'polygon_span_setup'
        elif 0x16020 <= off < 0x1609c+16*124:
            group = 'scanline_setup_and_return'
        else:
            continue
        cycles[group] += cost
        instructions[group] += 1
        if off in (0x15f42, 0x15f4a, 0x15f68, 0x15f6e, 0x15fa2, 0x15faa, 0x15fc8, 0x15fce):
            edge_memory_loop['instructions'] += 1
            edge_memory_loop['cycles'] += cost
        if off in (0x15f40, 0x15f66, 0x15fa0, 0x15fc6):
            shifts['instructions'] += 1
            shifts['cycles'] += cost
print(json.dumps({'instruction_cycles':dict(cycles), 'instructions':dict(instructions),
                  'total_cycles':sum(cycles.values()), 'edge_extract_shifts':dict(shifts),
                  'edge_stores_and_loop_control':dict(edge_memory_loop),
                  'includes_interrupt_cost':False}, indent=2))
