#!/usr/bin/env python3
"""Check that two captures of the fixed window are the same run, field by field.

  python3 tools/compare_traces.py A/trace.bin B/trace.bin

Compares each field's CPU instruction records (PC, cost and registers), DMA records and
screenshot, and the chip RAM snapshot at the start of the trace. Whole-file `cmp` is
meaningless: the slow-RAM snapshot holds WHDLoad/host bytes that differ between boots.
Exit status 0 only if everything matches. Screenshots are compared excluding only the rightmost three host-border columns.
Powerdrome captures differed only in those columns;
the active Amiga image, instruction records, DMA and initial chip snapshot matched.
"""
import hashlib, io, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import _amigaxdev
from amigaxdev import barto

a, b = barto.load(sys.argv[1]), barto.load(sys.argv[2])
bad = 0
if len(a.fields) != len(b.fields):
    print(f'field count {len(a.fields)} != {len(b.fields)}'); bad += 1
if a.chip != b.chip:
    n = sum(x != y for x, y in zip(a.chip, b.chip))
    print(f'chip snapshot differs in {n} bytes'); bad += 1


def same_shot(x, y):
    if x == y:
        return True
    from PIL import Image, ImageChops
    X, Y = (Image.open(io.BytesIO(s)).convert('RGB') for s in (x, y))
    box = (0, 0, X.size[0] - 3, X.size[1])
    return X.size == Y.size and not ImageChops.difference(X.crop(box), Y.crop(box)).getbbox()


for fa, fb in zip(a.fields, b.fields):
    ia = hashlib.sha256(bytes(a.data[fa.insn_off:fa.insn_end])).digest()
    ib = hashlib.sha256(bytes(b.data[fb.insn_off:fb.insn_end])).digest()
    diffs = [n for n, x, y in (('instructions', ia, ib), ('dma', bytes(fa.dma), bytes(fb.dma)))
             if x != y]
    if not same_shot(fa.shot, fb.shot):
        diffs.append('screenshot')
    if diffs:
        print(f'field {fa.index}: {", ".join(diffs)} differ'); bad += 1
print('identical' if not bad else f'{bad} differences')
sys.exit(1 if bad else 0)
