#!/usr/bin/env python3
"""Attract-demo frames, waits and DMA from a Powerdrome instruction trace.
The marker is game:1067e (ScrollVPort call after each moving-inset frame).
This is not a general racing FPS counter; menu/pit paths and other demo views differ.
Usage: SLAVE=capture/slave.slave python3 tools/frames.py TRACE DUMP BASE
"""
import collections, os, struct, sys
sys.path.insert(0, os.path.dirname(__file__))
import barto
from powerdrome_report import regions

SWAP = 0x1067e  # attract-demo completed frame

trace, code, base = barto.load(sys.argv[1]), open(sys.argv[2], 'rb').read(), int(sys.argv[3], 0)
regs = {name: (lo, hi, origin) for lo, hi, name, origin in regions(code, base, trace.chip)}
game = regs['game'][0]

def raw(a, n):
    o = a - base
    if 0 <= o and o + n <= len(code):
        return code[o:o + n]
    return trace.chip[a:a + n] if a + n <= len(trace.chip) else b''

POLL = bytes.fromhex('0839000600dff002')  # btst #6,$dff002
SWAP_WAIT = (0x112a6, 0x112aa)  # renderer VBL handshake
btst_dn_an = lambda w: (w & 0xf1f8) == 0x0110  # btst Dn,(An)
cop = game + SWAP
vec = lambda v: struct.unpack('>I', trace.chip[v:v + 4])[0]
watch = {vec(0x64): 'level-1 interrupts', vec(0x68): 'level-2 interrupts',
         vec(0x6c): 'level-3 interrupts', game + 0x5684: 'game VBL callbacks'}
DMA = {0: 'free', 1: 'refresh', 2: 'CPU', 3: 'copper', 4: 'audio', 5: 'blitter', 6: 'bitplane',
       7: 'sprite', 8: 'disk'}

# KickEmu WaitBlit includes two CIA reads between busy polls; include those costs separately.
waitblit = None
if 'slave' in regs:
    slo, shi, _ = regs['slave']
    sb = raw(slo, shi-slo)
    idx = sb.find(bytes.fromhex('4a3900dff0020839000600dff002660000044e75'))
    if idx >= 0: waitblit = (slo+idx, slo+idx+0x34)
total = wait = swait = stopped = waitroutine = stopinsn = 0
swait_pcs = {game + o for o in SWAP_WAIT}
swaps = []
hits = collections.Counter()
slots = collections.Counter()
for f in trace.fields:
    n = 0
    for pc, cost, r in trace.instructions(f):
        total += cost
        if pc is None:
            stopped += cost
            continue
        if pc == cop:
            n += 1
        if pc in watch:
            hits[watch[pc]] += 1
        b = raw(pc, 8)
        w = struct.unpack('>H', b[:2])[0] if len(b) >= 2 else 0
        if w == 0x4e72: stopinsn += cost
        if waitblit and waitblit[0] <= pc < waitblit[1]: waitroutine += cost
        if (b == POLL or (b[:1] == b'\x66' and raw(pc - 8, 8) == POLL)
                or (btst_dn_an(w) and r[8 + (w & 7)] == 0xdff002)
                or (b[:2] == b'\x66\xfc' and btst_dn_an(struct.unpack('>H', raw(pc - 2, 2))[0]))):
            wait += cost
        elif pc in swait_pcs:
            swait += cost
    swaps.append(n)
    for i in range(0, len(f.dma), f.dma_size):
        slots[f.dma[i + 29]] += 1

if not total:
    sys.exit('No CPU instruction records in this trace; use fixed_window.sh with SWAP_ONLY=1.')
nf = len(trace.fields)
first = next((i for i, n in enumerate(swaps) if n), None)
last = max((i for i, n in enumerate(swaps) if n), default=None)
print(f'\n## Frames ({nf} fields)')
print('demo frame completions per field:', ''.join(str(min(n, 9)) for n in swaps))
if first is not None and last > first:
    frames = sum(swaps[first + 1:last + 1])
    per = (last - first) / frames
    gaps = collections.Counter(b - a for a, b in zip(
        [i for i, n in enumerate(swaps) if n], [i for i, n in enumerate(swaps) if n][1:]))
    print(f'{frames} frames in {last - first} fields: {per:.2f} fields/frame, {50 / per:.1f} fps (PAL)')
    print('fields between swaps:', dict(sorted(gaps.items())))
print(f'recognized blitter polling instructions: {100 * wait / total:.1f}% of CPU cycles')
print(f'waiting for the VBL handshake: {100 * swait / total:.1f}% of CPU cycles')
for k in sorted(set(watch.values())):
    print(f'{k}: {hits[k]} ({hits[k] / nf:.1f} per field)')
n = sum(slots.values())
print('DMA slots:', ', '.join(f'{DMA.get(k, k)} {100 * v / n:.1f}%' for k, v in sorted(slots.items())))

print(f"Records without PCs: {100 * stopped / total:.2f}% of recorded cycles")

print(f"KickEmu complete WaitBlit routine: {100 * waitroutine / total:.2f}% of recorded cycles")
print(f"STOP instruction records: {100 * stopinsn / total:.2f}% of recorded cycles")
