#!/usr/bin/env python3
"""Check PC accounting against an enclosed trace; not a routine-context gate."""
import argparse
import collections
import json
from pathlib import Path
import _amigaxdev
from amigaxdev import barto
from matrix_report import read_aprof


def check(control, candidate):
    left = barto.load(str(control/'credits.bin'))
    right = barto.load(str(candidate/'credits.bin'))
    if len(left.fields) != len(right.fields) or not right.fields:
        raise ValueError('trace window mismatch')
    if (left.rom, left.chip, left.slow) != (right.rom, right.chip, right.slow):
        raise ValueError('trace memory differs')
    header, pcs, nodes, inclusive, residual = read_aprof(candidate/'credits.aprof')
    counts = collections.Counter()
    units = collections.Counter()
    dma_differences = custom_differences = 0
    for a, b in zip(left.fields, right.fields):
        if (a.cycles, a.idle, a.shot, a.aga_colors) != (b.cycles, b.idle, b.shot, b.aga_colors):
            raise ValueError('trace timing/picture differs')
        before = list(left.instructions(a))
        after = list(right.instructions(b))
        if before != after:
            raise ValueError('instruction PC/cost/register stream differs')
        dma_differences += sum(x != y for x, y in zip(a.dma, b.dma))
        custom_differences += sum(x != y for x, y in zip(a.custom, b.custom))
        for pc, cost, regs in after:
            if pc not in (None, 0x7fffffff):
                counts[pc] += 1
                units[pc] += cost*header['cycleunit']
    if not counts:
        raise ValueError('no instruction coverage')
    aggregate = {row[0]: row for row in pcs}
    missing_counts = [pc for pc in counts if aggregate.get(pc, [0, 0, 0])[2] < counts[pc]]
    missing_costs = [pc for pc in units if aggregate.get(pc, [0, 0, 0])[1] < units[pc]]
    if missing_counts or missing_costs:
        raise ValueError(f'aggregate undercovers trace: {len(missing_counts)} count PCs, {len(missing_costs)} cost PCs')
    return dict(pc_subset_check=True, instructions=sum(counts.values()), pcs=len(counts),
                source_pc_stable=header.get('source_pc_stable', 0), residual_units=residual,
                instruction_stream_identical=True, trace_memory_and_picture_identical=True,
                dma_byte_differences=dma_differences, custom_byte_differences=custom_differences,
                unmatched_rts=header['unmatched_rts'], unmatched_rte=header['unmatched_rte'],
                validated_baseline=False,
                scope='Enclosed five-field trace; aggregate includes additional edge instructions. '
                      'This lower-bound check does not validate routine contexts or all DMA state.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('control', type=Path)
    parser.add_argument('candidate', type=Path)
    args = parser.parse_args()
    print(json.dumps(check(args.control, args.candidate), indent=2))


if __name__ == '__main__':
    main()
