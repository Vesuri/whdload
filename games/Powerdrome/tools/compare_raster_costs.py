#!/usr/bin/env python3
"""Compare fast polygon costs for matching geometry/color across twin captures.

Use native edge inputs as the geometry key. Count only copied raster instructions,
not verification wrappers or interrupt handlers. Report medians per common shape
with equal weight per shape; elapsed playback is measured separately.
"""
import argparse
from collections import defaultdict
import json
from pathlib import Path
from statistics import median
import _amigaxdev
from amigaxdev import barto
from perf_status import status


def polygons(path):
    game = int((path/'game-base.txt').read_text(), 0)
    code = status(path/'code.bin')['raster_code']
    trace = barto.load(path/'trace.bin')
    result = defaultdict(list)
    geometry, color, active, cost = [], None, False, 0
    for field in trace.fields:
        for pc, cycles, regs in trace.instructions(field):
            if pc == game+0x15eee:
                geometry, color = [], None
            if pc == game+0x15f10:
                geometry.append(tuple(r & 65535 for r in regs[:4]))
            if pc == game+0x16000:
                color = regs[7] & 65535
            if pc == code+0x15eee-0x15b68:
                active, cost = True, 0
            if active and pc is not None and code <= pc < code+0x534+16*124:
                cost += cycles
                clone = pc-(code+0x534)
                if pc == code+0x1609a-0x15b68 or (0 <= clone < 16*124 and clone % 124 == 122):
                    if color is not None:
                        result[(tuple(geometry), color)].append(cost)
                    active = False
    return result

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('before', type=Path)
p.add_argument('after', type=Path)
a = p.parse_args()
before, after = polygons(a.before), polygons(a.after)
common = before.keys() & after.keys()
assert common, 'No matching polygon geometry/color'
b, c = [sum(median(d[k]) for k in common) for d in (before, after)]
print(json.dumps({'common_shapes': len(common),
 'before_matched_polygons':sum(len(before[k]) for k in common),
 'after_matched_polygons':sum(len(after[k]) for k in common),
 'before_sum_shape_medians':b, 'after_sum_shape_medians':c,
 'instruction_cost_reduction_percent':100*(1-c/b),
 'includes_interrupt_cost':False}, indent=2))
