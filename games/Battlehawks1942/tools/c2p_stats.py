#!/usr/bin/env python3
"""Where the delta chunky-to-planar pass (bh:1a2c2) spends its time, per pass.

  python3 tools/c2p_stats.py TRACE.bin CODE.bin BASE

The chunky buffer is 4 bits per pixel, 8 pixels per long. The pass compares the new frame
with the previous one a long at a time (bh:1a30e cmpm.l / dbne) and converts each changed
long with 32 add/addx steps into one byte per bitplane (bh:1a318..1a3b8). Prints, per pass,
the longs compared, the longs converted (changed) and the cycles in the compare loop, the
conversion and the rest, so a replacement can be sized against the measured change rate.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import barto
from bh_report import C2P, regions

trace, code, base = barto.load(sys.argv[1]), open(sys.argv[2], 'rb').read(), int(sys.argv[3], 0)
hb = {n: lo for lo, hi, n, o in regions(code, base, trace.chip)}['bh']
END = 0x1a3d6                      # past the rts at bh:1a3d4
CMP, CONV, CONV_END = 0x1a30e, 0x1a318, 0x1a3bc

passes = []                        # [compared, converted, cmp_cycles, conv_cycles, other, d7, rows]
cur = None
total = 0
for f in trace.fields:
    for pc, cost, r in trace.instructions(f):
        total += cost
        if pc is None:
            continue
        o = pc - hb
        if o == C2P:
            cur = [0, 0, 0, 0, 0]
            passes.append(cur)
        if cur is None or not C2P <= o < END:
            continue
        if o in (CMP, CMP + 2):
            cur[2] += cost
            cur[0] += o == CMP
        elif CONV <= o < CONV_END:
            cur[3] += cost
            cur[1] += o == CONV
        else:
            cur[4] += cost

# The first pass may have started before the trace; drop incomplete edges by size.
print(f'{"pass":>4} {"compared":>9} {"changed":>8} {"%chg":>5} {"cmp cyc":>9} {"conv cyc":>9} '
      f'{"other":>7} {"total":>9} {"cyc/changed":>11}')
s = [0] * 5
for i, p in enumerate(passes):
    tot = p[2] + p[3] + p[4]
    print(f'{i:4} {p[0]:9} {p[1]:8} {100 * p[1] / max(p[0], 1):5.1f} {p[2]:9} {p[3]:9} {p[4]:7} '
          f'{tot:9} {p[3] / max(p[1], 1):11.0f}')
    s = [a + b for a, b in zip(s, p)]
c = s[2] + s[3] + s[4]
print(f'all: {s[0]} compared, {s[1]} changed ({100 * s[1] / max(s[0], 1):.1f} %); '
      f'c2p {100 * c / total:.1f} % of all cycles = compare {100 * s[2] / total:.1f} % + '
      f'convert {100 * s[3] / total:.1f} % + other {100 * s[4] / total:.1f} %')
print(f'per long compared: {s[2] / max(s[0], 1):.1f} cycles; per changed long converted: '
      f'{s[3] / max(s[1], 1):.1f} cycles; cycle unit = trace cost unit')
