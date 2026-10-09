#!/usr/bin/env python3
"""Exploratory Stellar 7 frame/DMA counts. Frame marker: native presentation entry s7:$6a0a.
Validate against breakpoint counts in an identical fixed window before quoting a baseline.
"""
import collections, os, struct, sys
sys.path.insert(0, os.path.dirname(__file__))
import barto
from stellar7_report import regions
C2P = 0x6a0a

trace, code, base = barto.load(sys.argv[1]), open(sys.argv[2], 'rb').read(), int(sys.argv[3], 0)
regs = {name: (lo, hi, origin) for lo, hi, name, origin in regions(code, base, trace.chip)}
kick = regs['kick'][2]  # kick ROM address = pc - kick
frame_pc = regs['s7'][0] + C2P
level3 = struct.unpack_from('>I', trace.chip, 0x6c)[0]
watch = {level3: 'level-3 interrupts', 0xfc0d38 + kick: '  blitter-finished',
         0xfc0d4a + kick: '  vertical blank'}
DMA = {0: 'free', 1: 'refresh', 2: 'CPU', 3: 'copper', 4: 'audio', 5: 'blitter', 6: 'bitplane',
       7: 'sprite', 8: 'disk'}

total = idle = 0
swaps = []
steps = []
hits = collections.Counter()
slots = collections.Counter()
for f in trace.fields:
    n = step_count = 0
    for pc, cost, r in trace.instructions(f):
        total += cost
        if pc is None:
            idle += cost
            continue
        if pc == regs['s7'][0] + 0x2d4e:
            step_count += 1
        if pc == frame_pc:
            n += 1
        if pc in watch:
            hits[watch[pc]] += 1
    swaps.append(n)
    steps.append(step_count)
    for i in range(0, len(f.dma), f.dma_size):
        slots[f.dma[i + 29]] += 1

if not total:
    sys.exit('No CPU instruction records in this trace; use fixed_window.py with --swaps-only.')
nf = len(trace.fields)
first = next((i for i, n in enumerate(swaps) if n), None)
last = max((i for i, n in enumerate(swaps) if n), default=None)
print(f'\n## Frames ({nf} fields)')
print('simulation completions per field:', ''.join(str(min(n, 9)) for n in steps))
print(f'Simulation steps: {sum(steps)} over {nf} PAL fields ({50 * sum(steps) / nf:.2f} steps/s)')
print('gameplay swaps per field:', ''.join(str(min(n, 9)) for n in swaps))
if first is not None and last > first:
    frames = sum(swaps[first + 1:last + 1])
    per = (last - first) / frames
    print(f'{frames} frames in {last - first} fields: {per:.2f} fields/frame, {50 / per:.1f} fps (PAL)')
print(f'CPU stopped (STOP): {100 * idle / total:.1f}% of cycles')
print(f'level-3 vector: {level3:#x}', next((f'({n}:{level3 - o:05x})' for lo, hi, n, o in
      [(lo, hi, n, o) for n, (lo, hi, o) in regs.items()] if lo <= level3 < hi), ''))
for k in ('level-3 interrupts', '  blitter-finished', '  vertical blank'):
    print(f'{k}: {hits[k]} ({hits[k] / nf:.1f} per field)')
n = sum(slots.values())
print('DMA slots:', ', '.join(f'{DMA.get(k, k)} {100 * v / n:.1f}%' for k, v in sorted(slots.items())))
