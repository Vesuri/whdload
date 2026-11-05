#!/usr/bin/env python3
"""Whole-trace summary for a Legends of Valour trace: frame rate, blitter waits, interrupts, bus use.

  python3 tools/frames.py TRACE.bin CODE.bin BASE

The game draws through the OS and never writes the copper: the 3D view is rendered off
screen (h12:027bc) and then made visible by h12:05ea6, which waits for the beam and copies
the view into the screen bitmap (CPU byte copy, or BltBitMap + WaitBlit).  Frames are
counted at the entries of h12:05ea6.  Blitter waits are the
cycles spent on `btst #6,2(a6)` polls (DMACONR BBUSY) and the nop/bne around them.
Interrupts are counted at Kickstart 1.3's level-3 handler (ROM $FC0D14) and its BLIT ($FC0D38)
and VERTB ($FC0D4A) branches.  DMA slot types come from the per-field DMA records.
"""
import collections, os, struct, sys
sys.path.insert(0, os.path.dirname(__file__))
import _amigaxdev
from amigaxdev import barto
from lov_report import regions

trace, code, base = barto.load(sys.argv[1]), open(sys.argv[2], 'rb').read(), int(sys.argv[3], 0)
regs = {name: (lo, hi, origin) for lo, hi, name, origin in regions(code, base)}
kick = regs['kick'][2]  # kick ROM address = pc - kick

def raw(a, n):
    o = a - base
    return code[o:o + n] if 0 <= o and o + n <= len(code) else b''

POLL = bytes.fromhex('082e00060002')  # btst #6,2(a6)
cop = regs['h12'][0] + 0x5ea6  # the view copy: one per displayed frame
watch = {0xfc0d14 + kick: 'level-3 interrupts', 0xfc0d38 + kick: '  blitter-finished',
         0xfc0d4a + kick: '  vertical blank'}
DMA = {0: 'free', 1: 'refresh', 2: 'CPU', 3: 'copper', 4: 'audio', 5: 'blitter', 6: 'bitplane',
       7: 'sprite', 8: 'disk'}

total = wait = 0
swaps = []
hits = collections.Counter()
slots = collections.Counter()
for f in trace.fields:
    n = 0
    for pc, cost, r in trace.instructions(f):
        total += cost
        if pc is None:
            continue
        if pc == cop:
            n += 1
        if pc in watch:
            hits[watch[pc]] += 1
        b = raw(pc, 6)
        if b == POLL or (b[:2] == b'\x4e\x71' and POLL in raw(pc, 10)) or (b[:2] in (b'\x66\xf4', b'\x66\xf8') and raw(pc - 6, 6) == POLL):
            wait += cost
    swaps.append(n)
    for i in range(0, len(f.dma), f.dma_size):
        slots[f.dma[i + 29]] += 1

if not total:
    sys.exit('No CPU instruction records in this trace; use fixed_window.sh with SWAP_ONLY=1.')
nf = len(trace.fields)
first = next((i for i, n in enumerate(swaps) if n), None)
last = max((i for i, n in enumerate(swaps) if n), default=None)
print(f'\n## Frames ({nf} fields)')
print('buffer swaps per field:', ''.join(str(min(n, 9)) for n in swaps))
if first is not None and last > first:
    frames = sum(swaps[first + 1:last + 1])
    per = (last - first) / frames
    print(f'{frames} frames in {last - first} fields: {per:.2f} fields/frame, {50 / per:.1f} fps (PAL)')
print(f'blitter busy-wait polling: {100 * wait / total:.1f}% of CPU cycles')
for k in ('level-3 interrupts', '  blitter-finished', '  vertical blank'):
    print(f'{k}: {hits[k]} ({hits[k] / nf:.1f} per field)')
n = sum(slots.values())
print('DMA slots:', ', '.join(f'{DMA.get(k, k)} {100 * v / n:.1f}%' for k, v in sorted(slots.items())))
