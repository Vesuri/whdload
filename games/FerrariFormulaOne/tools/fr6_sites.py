"""fr6_sites.py TRACE_DIR DRAWS: Fast RAM render cost per blit site of a trace.

Attributes the FastRenderBlit path (FRB*, FRTrack, FRTranslate, FRLookup, FRSpan,
FF1FastRenderSize, FRUntranslate, FastRenderBDAT) to the FRT* trampoline that entered it,
and prints the five largest inner routines per site, in ms per draw over DRAWS draws.
Absolute milliseconds read about 1.5-1.9x high in traces; compare the shares.
"""
import collections
import os
import sys
from pathlib import Path

sys.argv[1] = str(Path(sys.argv[1]).resolve())
os.chdir(Path(__file__).resolve().parents[1])
src = open('tools/analyze_hi25_profile.py').read().split('# Native canonical routine ranges')[0]
exec(src)
trace = barto.load(p / 'detail.bin')
site = collections.Counter()
inner = collections.defaultdict(collections.Counter)
cur = 'none'
allc = 0
prev = None
FR = ('fine:FRB', 'fine:FastRenderBlit', 'fine:FRT', 'fine:FRTrack', 'fine:FRTranslate',
      'fine:FRLookup', 'fine:FRSpan', 'fine:FF1FastRenderSize', 'fine:FRUntranslate',
      'fine:FastRenderBDAT')
for f in trace.fields:
    for pc, cost, regs in trace.instructions(f):
        allc += cost
        if (regs[16] >> 8) & 7:
            continue
        o = owner(pc)
        if o.startswith('fine:FRT') and not o.startswith(('fine:FRTrack', 'fine:FRTranslate')):
            cur = o
        if o.startswith(FR):
            site[cur] += cost
            inner[cur][o] += cost
        elif not o.startswith('fine:FRT'):
            cur = 'other:' + o
        prev = o
unit = len(trace.fields) * 20.031886677085037 / allc
n = float(sys.argv[2])
for k, v in site.most_common(15):
    print('%7.2f ms/draw %s' % (v * unit / n, k),
          ' | '.join('%s %.1f' % (a[5:], b * unit / n) for a, b in inner[k].most_common(5)))
