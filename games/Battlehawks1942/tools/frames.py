#!/usr/bin/env python3
"""Whole-trace summary for a Battlehawks 1942 trace: frame rate, interrupts, idle, bus use.

  python3 tools/frames.py TRACE.bin CODE.bin BASE

Frames are counted at the entry of the 3D view's delta chunky-to-planar pass (bh:1a2c2).
The game has one displayed buffer: each pass compares the new chunky frame with the previous
one and writes only the changed longs into the visible bitplanes, so one pass is one new
frame (docs/profiling.md §5). The renderer never uses the blitter, so there is no blitter
wait to count. Level-3 interrupts are counted at the handler the
$6C vector points to (in flight that is the game's sound sequencer, bh:1ac26, which then
jumps into Kickstart 1.3's handler past its prologue), and the Kickstart handler's BLIT
($FC0D38) and VERTB ($FC0D4A) branches. DMA slot types come from the per-field DMA
records. CODE.bin is the dump of the "other" memory at BASE (Kickstart, slave, and BH itself
with the slave's fast memory; with a chip-only slave BH is in the trace's chip snapshot).
"""
import collections, os, struct, sys
sys.path.insert(0, os.path.dirname(__file__))
import _amigaxdev  # noqa: F401
from amigaxdev import barto
from bh_report import C2P, regions

trace, code, base = barto.load(sys.argv[1]), open(sys.argv[2], 'rb').read(), int(sys.argv[3], 0)
regs = {name: (lo, hi, origin) for lo, hi, name, origin in regions(code, base, trace.chip)}
kick = regs['kick'][2]  # kick ROM address = pc - kick
frame_pc = regs['bh'][0] + C2P
level3 = struct.unpack_from('>I', trace.chip, 0x6c)[0]
watch = {level3: 'level-3 interrupts', 0xfc0d38 + kick: '  blitter-finished',
         0xfc0d4a + kick: '  vertical blank'}
DMA = {0: 'free', 1: 'refresh', 2: 'CPU', 3: 'copper', 4: 'audio', 5: 'blitter', 6: 'bitplane',
       7: 'sprite', 8: 'disk'}

total = idle = 0
swaps = []
hits = collections.Counter()
slots = collections.Counter()
for f in trace.fields:
    n = 0
    for pc, cost, r in trace.instructions(f):
        total += cost
        if pc is None:
            idle += cost
            continue
        if pc == frame_pc:
            n += 1
        if pc in watch:
            hits[watch[pc]] += 1
    swaps.append(n)
    for i in range(0, len(f.dma), f.dma_size):
        slots[f.dma[i + 29]] += 1

if not total:
    sys.exit('No CPU instruction records in this trace; use fixed_window.sh with SWAP_ONLY=1.')
nf = len(trace.fields)
first = next((i for i, n in enumerate(swaps) if n), None)
last = max((i for i, n in enumerate(swaps) if n), default=None)
print(f'\n## Frames ({nf} fields)')
print('c2p passes per field:', ''.join(str(min(n, 9)) for n in swaps))
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
