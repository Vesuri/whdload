#!/usr/bin/env python3
"""Split complete simulation ticks and renderer calls into drawing/catch-up costs.

Use a retained fixed-window trace and its exact slave/listing. Main-task costs
exclude interrupt/worker stacks by the same 64 KiB stack-distance rule as
render_report.py. Tick totals include input and any scheduler wait; renderer
costs include actor/world updates but exclude the separate sprite/C2P calls.
Boundary-partial scopes are excluded. No game-state equality is implied.
"""
import argparse
import os
import re
import statistics
from pathlib import Path
import _amigaxdev
from amigaxdev import barto
from lov_report import regions


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('capture', type=Path)
    p.add_argument('--base', type=lambda s: int(s, 0), default=0xc00000)
    a = p.parse_args()
    os.environ['SLAVE'] = str(a.capture / 'slave.slave')
    trace = barto.load(str(a.capture / 'trace.bin'))
    blob = (a.capture / 'code.bin').read_bytes()
    region = {name: lo for lo, hi, name, offset in regions(blob, a.base, trace.chip)}
    listing = (a.capture / 'slave.lst').read_text(errors='replace')
    def symbol(name):
        match = re.search(r'^' + re.escape(name) + r'\s+00:([0-9A-F]{8})\s*$', listing, re.M)
        if not match:
            p.error(f'missing symbol {name}')
        return region['slave'] + int(match[1], 16)
    starts = {symbol('_sim_loop'): 'tick', region['h12'] + 0x27bc: 'renderer'}
    ends = {symbol('_sim_tick_complete'): 'tick', region['h12'] + 0x2806: 'renderer'}
    drawing = region['h12'] + 0x27e6
    active = {}
    samples = {}
    for field in trace.fields:
        for pc, cost, regs in trace.instructions(field):
            if pc in starts:
                scope = starts[pc]
                if scope in active:
                    raise ValueError(f'nested {scope} scope')
                active[scope] = [regs[15], 0, 0, False]
            for scope, sample in list(active.items()):
                if ends.get(pc) == scope and regs[15] == sample[0]:
                    kind = 'draw' if sample[3] else 'logic only'
                    samples.setdefault((scope, kind), []).append(sample[1:3])
                    del active[scope]
                    continue
                sample[1] += cost
                if abs(regs[15] - sample[0]) < 0x10000:
                    sample[2] += cost
                    if pc == drawing:
                        sample[3] = True
    for (scope, kind), values in sorted(samples.items()):
        inclusive, main_task = zip(*values)
        print(f'{scope} {kind}: {len(values)} complete calls; '
              f'inclusive {statistics.mean(inclusive):.0f}, '
              f'main-task {statistics.mean(main_task):.0f} cycles/call; '
              f'main-task range {min(main_task)}..{max(main_task)}')
    if not samples:
        p.error('no complete scopes')


if __name__ == '__main__':
    main()
