#!/usr/bin/env python3
"""Trace a window of play with the pointer moving and report frames and costs.

    python3 tools/bench.py OUT [FIELDS [DX DY ...]]

Needs a running server in play (tools/route.py hole1) on a CPU that records an instruction
trace: on a1200-030 that is EXTRA_ARGS=--uae_mmu_model=0 (WHDLoad does not use the 68030's
MMU without its MMU option, so the game runs the same). Traces FIELDS fields (default 120,
2 s NTSC) in 2-field chunks back to back; before each chunk the mouse moves by the next
(DX, DY) of the pattern (default: right, down, left, up, 15 chunks each, 10 counts a chunk).
Each chunk is reduced with tools/profile.py and deleted. Writes OUT/profile.pkl.gz,
OUT/end.png and OUT/report.txt.
"""
import collections
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import route  # noqa: E402
from profile import TwoStack  # noqa: E402

# Program addresses (FILE1 at $10000; offset = address - $10000).
SWAP = 0x114a8       # the renderer flips the copper list's plane pointers: a frame is shown
RENDER = 0x1147a     # the renderer's entry (from the threaded code)
TILE = 0x1153a       # one 8x8 tile of the full rows: 32 byte copies
ROW = 0x1151e        # one row of 40 tiles
OBJECTS = 0x116f2    # draws shapes into the back buffer (after the tiles)
VBL = 0x121e6        # the game's interrupt handler (every level; VERTB and COPER)
RANGES = [
    ((0x1147a, 0x115f2), 'renderer: full tile rows'),
    ((0x115f2, 0x11654), 'renderer: partial bottom row'),
    ((0x10100, 0x10c2a), 'threaded-code primitives'),
    ((0x121e6, 0x12272), 'interrupt handler'),
    ((0x9f0000, 0xa00000), 'WHDLoad (fast memory)'),
]


def fields_now(t):
    """The game's field counter at $1145c (low byte first) in the trace's chip snapshot. Its
    interrupt handler runs twice a field (VERTB and the copper's COPER) and counts every
    other run, so the counter counts fields."""
    c = t.chip
    return c[0x1145c] | c[0x1145d] << 8


def pattern(args):
    if args:
        v = [int(a) for a in args]
        return list(zip(v[0::2], v[1::2]))
    return [(10, 0)] * 15 + [(0, 10)] * 15 + [(-10, 0)] * 15 + [(0, -10)] * 15


def report(r):
    total = r.total()
    fc = total / len(r.fields)
    hz = 60 if os.environ.get('NTSC', '1') == '1' else 50
    swaps = [e[1] / fc for e in r.events if e[0] == 'swap']
    gaps = [b - a for a, b in zip(swaps, swaps[1:])]
    lines = [f'fields {len(r.fields)}  traced cycles {total}  ({fc:.0f} a field)',
             f'swaps {len(swaps)}  fields between swaps: ' +
             (f'mean {sum(gaps) / len(gaps):.2f}  min {min(gaps):.2f}  max {max(gaps):.2f}  '
              f'= {hz * len(gaps) / sum(gaps):.1f} frames a second at {hz} Hz' if gaps else 'n/a')]
    tiles = r.counts[TILE]
    lines.append(f'tiles drawn {tiles}  ({tiles / max(1, len(swaps)):.0f} a swap; a full screen is 800 + 40)')
    lines.append('DMA slots: ' + ', '.join(f'{k} {v:.1%}' for k, v in r.dma_shares().items()))
    lines.append('self cycles by range, % of traced cycles:')
    seen = 0
    for (lo, hi), what in RANGES:
        c = sum(v for pc, v in r.self.items() if lo <= pc < hi)
        seen += c
        lines.append(f'  {lo:06x}-{hi:06x}  {100 * c / total:5.1f}%  {what}')
    lines.append(f'  {"rest":13}  {100 * (total - seen) / total:5.1f}%')
    lines.append('per frame (swap to swap): fields; CPU in fields: renderer pages $11400-$116ff, '
                 'primitives, rest; executions: renderer entries, rows, tiles, object drawer')
    for k, iv in enumerate(r.intervals[1:-1]):
        rend = sum(c for p, c in iv.items() if not isinstance(p, tuple) and 0x11400 <= p < 0x11700)
        prim = sum(c for p, c in iv.items() if not isinstance(p, tuple) and 0x10100 <= p < 0x10d00)
        n = [iv[('n', p)] for p in (RENDER, ROW, TILE, OBJECTS)]
        t = sum(v for key, v in iv.items() if not isinstance(key, tuple))
        lines.append(f'  {k:3d}  {t / fc:5.2f}  {rend / fc:5.2f}  {prim / fc:5.2f}  '
                     f'{(t - rend - prim) / fc:5.2f}   {n[0]:2d} {n[1]:3d} {n[2]:4d} {n[3]:3d}')
    b = collections.Counter()
    for pc, c in r.self.items():
        b[pc & ~0xff] += c
    lines.append('self cycles by 256-byte page (top 16):')
    for k, c in b.most_common(16):
        lines.append(f'  {k:06x}  {100 * c / total:5.1f}%')
    return '\n'.join(lines) + '\n'


def main(argv):
    out = ROOT / argv[0]
    nfields = int(argv[1]) if len(argv) > 1 else 120
    moves = pattern(argv[2:])
    out.mkdir(parents=True, exist_ok=True)
    r = TwoStack(marks={'swap': SWAP, 'render': RENDER, 'vbl': VBL}, split=SWAP,
                 watch=(TILE, RENDER, ROW, OBJECTS))
    chunk = out / 'chunk.bin'
    last = None
    for i in range(nfields // 2):
        dx, dy = moves[i % len(moves)]
        route.req('gdb', f'monitor mouse {dx} {dy}')
        route.req('profile', '2', str(chunk))
        t = r.feed(str(chunk))
        now = fields_now(t)
        if last is not None and now != last + 2:
            sys.exit(f'chunk {i}: starts {now - last} fields after the previous one, not 2 '
                     '(was the CPU left running? tools/route.py stop)')
        last = now
        del t
        chunk.unlink()
    route.req('shot', str(out / 'end.png'))
    r.save(str(out / 'profile.pkl.gz'))
    rep = report(r)
    (out / 'report.txt').write_text(rep)
    print(rep, end='')


if __name__ == '__main__':
    main(sys.argv[1:])
