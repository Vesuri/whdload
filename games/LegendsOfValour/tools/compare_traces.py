#!/usr/bin/env python3
"""Reproducibility check: compare two fixed-window traces field by field.

  python3 tools/compare_traces.py A/trace.bin B/trace.bin

For every field: the CPU instruction records (PCs, costs, registers), the DMA records and
the screenshot.  Whole files differ anyway (the slow-RAM snapshot holds WHDLoad and host bytes
that change between boots), so only these per-field parts are compared.  Exits 1 on any
difference and names the first differing field of each kind.
"""
import sys
import barto

a, b = barto.load(sys.argv[1]), barto.load(sys.argv[2])
if len(a.fields) != len(b.fields):
    sys.exit(f'field counts differ: {len(a.fields)} vs {len(b.fields)}')
first = {}
for fa, fb in zip(a.fields, b.fields):
    parts = {'instructions': (a.data[fa.insn_off:fa.insn_end], b.data[fb.insn_off:fb.insn_end]),
             'dma': (fa.dma, fb.dma), 'screenshot': (fa.shot, fb.shot)}
    for k, (x, y) in parts.items():
        if k not in first and bytes(x) != bytes(y):
            first[k] = fa.index
print(f'{len(a.fields)} fields compared')
for k in ('instructions', 'dma', 'screenshot'):
    print(f'{k:13s}', 'identical' if k not in first else f'first differs at field {first[k]}')
sys.exit(1 if first else 0)
