"""fr6_owners.py TRACE_DIR: cost per routine of a capture_hi25_profile.py trace.

Reuses analyze_hi25_profile.py's loader and owner() up to its native routine ranges.
Interrupt-level instructions count as IRQ. Absolute milliseconds read about 1.5-1.9x high
in traces; compare the shares.
"""
import collections
import os
import sys
from pathlib import Path

sys.argv[1] = str(Path(sys.argv[1]).resolve())
os.chdir(Path(__file__).resolve().parents[1])
src = open('tools/analyze_hi25_profile.py').read().split('# Native canonical routine ranges')[0]
exec(src)
entry = probe + sy['B8Draw']
trace = barto.load(p / 'detail.bin')
tot = collections.Counter()
entries = 0
allc = 0
for f in trace.fields:
    for pc, cost, regs in trace.instructions(f):
        if pc == entry:
            entries += 1
        irq = (regs[16] >> 8) & 7
        tot['IRQ' if irq else owner(pc)] += cost
        allc += cost
fields = len(trace.fields)
ms_field = 20.031886677085037
unit = fields * ms_field / allc
print('draw entries', entries, 'fields', fields, 'ms total', fields * ms_field)
n = max(entries, 1)
for k, v in tot.most_common(45):
    print('%8.2f ms/draw %5.1f%%  %s' % (v * unit / n, 100 * v / allc, k))
