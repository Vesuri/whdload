#!/usr/bin/env python3
"""Measure instruction-record cycles for fully observed game/slave calls.

Excludes all profiler gap and missing-PC costs, not only interrupt costs.
Same-context gap costs are reported separately when paired snapshots match.
These samples are not elapsed wall-clock or total CPU-cycle measurements."""
import argparse
import json
import re
import statistics
import struct
from pathlib import Path
import barto
from stellar7_report import contexts, locate


def measure(folder, offset, slave=False):
    folder = Path(folder)
    meta = {k: int(v, 0) for k, v in re.findall(
        r'^(code|base)=(\S+)', (folder/'anchor.txt').read_text(), re.M)}
    trace = barto.load(folder/'trace.bin')
    ranges = contexts(trace, trace.fields)

    def context(sp):
        for i, (lo, hi) in enumerate(ranges):
            if lo <= sp < hi+0x1000:
                return i
        return ('other', sp >> 12)

    if slave:
        binary = (folder/'slave.slave').read_bytes()
        size = struct.unpack_from('>I', binary, 0x1c)[0]*4
        body = binary[0x20:0x20+size]
        assert 0 <= offset < size, 'slave offset is outside the retained code hunk'
        address = locate((folder/'code.bin').read_bytes(), body, meta['base'], header=0x20)
        assert address is not None, 'retained slave is not found in captured memory'
    else:
        address = meta['code']
    target = address+offset
    active = None
    samples, gap_samples = [], []
    entered = 0
    previous_context = None
    pending_gap = None
    for field in trace.fields:
        for pc, cost, regs in trace.instructions(field):
            if pc == 0x7fffffff:
                assert pending_gap is None, 'consecutive profiler gaps'
                pending_gap = cost, tuple(regs)
                continue
            gap_cost = 0
            if pending_gap is not None:
                gap_cost, snapshot = pending_gap
                assert snapshot == tuple(regs), 'gap/instruction register snapshots differ'
                pending_gap = None
            if pc is None:
                previous_context = None
                continue
            sp = regs[15]
            ctx = context(sp)
            if active is not None and ctx == active['context'] and sp > active['sp']:
                samples.append(active['cycles'])
                gap_samples.append(active['gap_cycles'])
                active = None
            # Attribute only gaps between records in the same inferred stack
            # context, inside an already entered and not yet returned call.
            # Entry/return and context-switch gaps remain outside the sample.
            if active is not None and ctx == active['context'] and ctx == previous_context:
                active['gap_cycles'] += gap_cost
            if pc == target:
                assert active is None, 'recursive/overlapping target calls need a stack-aware extension'
                active = dict(sp=sp, context=ctx, cycles=0, gap_cycles=0)
                entered += 1
            if active is not None and ctx == active['context']:
                active['cycles'] += cost
            previous_context = ctx
    assert samples, 'no complete calls at this entry'
    return dict(gap_scope='paired gaps inside an active call with unchanged inferred stack context; excludes entry/return and context-switch gaps',
                mean_same_context_gap_cycles=statistics.mean(gap_samples),
                same_context_gap_samples=gap_samples,
                mean_cycles_with_same_context_gaps=statistics.mean([a+b for a,b in zip(samples,gap_samples)]),
                cycle_scope='instruction records only; excludes gap/missing-PC costs and other stack contexts', **{'slave_offset' if slave else 'hunk_offset': hex(offset)}, entered=entered, completed=len(samples),
                incomplete_at_end=int(active is not None),
                mean_cycles=statistics.mean(samples), median_cycles=statistics.median(samples),
                min_cycles=min(samples), max_cycles=max(samples), samples=samples)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('captures', nargs='+')
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--offset', type=lambda s: int(s, 0), help='game-hunk entry offset')
    source.add_argument('--slave-offset', type=lambda s: int(s, 0), help='entry offset in the retained slave code hunk')
    parser.add_argument('--samples', action='store_true', help='include individual complete-call cycle counts')
    args = parser.parse_args()
    for folder in args.captures:
        result = measure(folder, args.slave_offset if args.slave_offset is not None else args.offset,
                         slave=args.slave_offset is not None)
        if not args.samples:
            result.pop('samples')
            result.pop('same_context_gap_samples')
        print(folder, json.dumps(result, sort_keys=True))
