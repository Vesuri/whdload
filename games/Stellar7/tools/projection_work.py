#!/usr/bin/env python3
"""Audit native per-actor projection work from recorded instruction/register traces.

Reports an upper bound for skipping geometry on actors without visibility updates
and with null/mesh-animation callbacks. It is not a speedup measurement: a future
implementation must preserve final scratch state, view-object handling, and callbacks.
"""
import argparse
import collections
import json
import re
from pathlib import Path
import _amigaxdev  # noqa: F401 (finds amigaxdev)
from amigaxdev import barto
from stellar7_report import contexts


def inspect(folder):
    folder = Path(folder)
    code = int(re.search(r'^code=(\S+)', (folder/'anchor.txt').read_text(), re.M)[1], 0)
    trace = barto.load(folder/'trace.bin')
    ranges = contexts(trace, trace.fields)

    def context(sp):
        for i, (lo, hi) in enumerate(ranges):
            if lo <= sp < hi+0x1000:
                return i
        return ('other', sp >> 12)

    current = None
    records = []
    for field in trace.fields:
        for pc, cost, regs in trace.instructions(field):
            if pc is None or pc == 0x7fffffff:
                continue
            at = pc-code
            ctx = context(regs[15])
            if at == 0x12ae8:
                assert current is None, 'nested/incomplete projection actor'
                current = dict(context=ctx, index=regs[6]&65535, count=regs[7]&65535,
                               actor=regs[11], geometry_cycles=0, geometry_done=False)
            if current is None or ctx != current['context']:
                continue
            if at == 0x12b76:
                # Follow the executed branch: recorded SR does not reliably
                # materialize the emulator's lazy condition flags.
                current['visibility'] = False
            elif at == 0x12b7a:
                current['visibility'] = True
            elif at == 0x12bfc:
                current['geometry_done'] = True
            elif at == 0x12c00:
                current['callback'] = regs[0]-code if regs[0] else None
            elif at == 0x12c30:
                assert current['geometry_done'] and 'visibility' in current and 'callback' in current
                current.pop('context')
                current.pop('geometry_done')
                records.append(current)
                current = None
            if current is not None and not current['geometry_done']:
                current['geometry_cycles'] += cost
    assert records, 'no fully observed actor projections'
    candidates = [r for r in records if not r['visibility'] and
                  r['callback'] in (None, 0x42b0) and r['index'] < r['count']-1]
    total_cycles = sum(f.cycles for f in trace.fields)
    return dict(complete_actors=len(records), partial_at_end=current is not None,
                visibility_actors=sum(r['visibility'] for r in records),
                callback_counts=dict(collections.Counter('none' if r['callback'] is None else hex(r['callback']) for r in records)),
                geometry_cycles=sum(r['geometry_cycles'] for r in records),
                candidate_actors=len(candidates), candidate_geometry_cycles=sum(r['geometry_cycles'] for r in candidates),
                candidate_recorded_cycle_percent=100*sum(r['geometry_cycles'] for r in candidates)/total_cycles,
                records=records)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('captures', nargs='+')
    parser.add_argument('--records', action='store_true')
    args = parser.parse_args()
    for folder in args.captures:
        result = inspect(folder)
        if not args.records:
            result.pop('records')
        print(folder, json.dumps(result, sort_keys=True))
